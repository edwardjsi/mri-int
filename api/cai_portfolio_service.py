from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import psycopg2.extras
import logging
import uuid
from api.deps import get_db, get_current_client
from engine_core.cai_replay import fetch_replay_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cai/portfolio", tags=["cai_portfolio"])

class PositionCreate(BaseModel):
    symbol: str
    quantity: int
    average_price: float

class TrancheAdd(BaseModel):
    quantity: int
    entry_price: float

class PositionResponse(BaseModel):
    id: str
    symbol: str
    quantity: int
    average_price: float
    allocation: float
    tranche: int
    status: str

class PortfolioResponse(BaseModel):
    id: str
    owner: str
    cash: float
    health: Optional[float]
    positions: List[PositionResponse]

def get_or_create_portfolio(cur, client):
    """Ensure a CAI portfolio exists for the client."""
    client_id = str(client["id"])
    email = client.get("email", "unknown")
    
    # Check by owner (client UUID) first. Legacy code might have set owner=email, so check both.
    cur.execute("SELECT id, owner, cash, health FROM cai_portfolio WHERE owner = %s OR owner = %s LIMIT 1", (client_id, email))
    portfolio = cur.fetchone()
    
    if not portfolio:
        new_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO cai_portfolio (id, owner, cash, health)
            VALUES (%s, %s, 0.00, NULL)
            RETURNING id, owner, cash, health
            """,
            (new_id, client_id)
        )
        portfolio = cur.fetchone()
        
    return portfolio

@router.get("", response_model=PortfolioResponse)
def get_portfolio_endpoint(client=Depends(get_current_client), conn=Depends(get_db)):
    """Fetch the CAI portfolio and its active positions."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        portfolio = get_or_create_portfolio(cur, client)
        
        cur.execute(
            """
            SELECT id, symbol, quantity, average_price, allocation, tranche, status
            FROM cai_position
            WHERE portfolio_id = %s AND status = 'ACTIVE'
            ORDER BY symbol ASC
            """,
            (portfolio["id"],)
        )
        positions = cur.fetchall()
        
        return PortfolioResponse(
            id=portfolio["id"],
            owner=portfolio["owner"],
            cash=float(portfolio["cash"]),
            health=float(portfolio["health"]) if portfolio["health"] else None,
            positions=[PositionResponse(**p) for p in positions]
        )
    except Exception as e:
        logger.error(f"Error fetching CAI portfolio: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch portfolio")
    finally:
        cur.close()

@router.post("/positions", response_model=PositionResponse)
def add_position(req: PositionCreate, client=Depends(get_current_client), conn=Depends(get_db)):
    """Open a new position (First Tranche)."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        portfolio = get_or_create_portfolio(cur, client)
        
        # Check if active position already exists
        cur.execute(
            "SELECT id FROM cai_position WHERE portfolio_id = %s AND symbol = %s AND status = 'ACTIVE'",
            (portfolio["id"], req.symbol.upper())
        )
        if cur.fetchone():
            raise HTTPException(status_code=400, detail=f"Active position for {req.symbol} already exists. Use add tranche instead.")
            
        pos_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO cai_position (id, portfolio_id, symbol, quantity, average_price, tranche, status)
            VALUES (%s, %s, %s, %s, %s, 1, 'ACTIVE')
            RETURNING id, symbol, quantity, average_price, allocation, tranche, status
            """,
            (pos_id, portfolio["id"], req.symbol.upper(), req.quantity, req.average_price)
        )
        new_pos = cur.fetchone()
        conn.commit()
        return PositionResponse(**new_pos)
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Error adding CAI position: {e}")
        raise HTTPException(status_code=500, detail="Failed to add position")
    finally:
        cur.close()

@router.post("/positions/{position_id}/tranches", response_model=PositionResponse)
def add_tranche(position_id: str, req: TrancheAdd, client=Depends(get_current_client), conn=Depends(get_db)):
    """Add a new tranche to an existing position. Enforces the 'NO averaging down' rule."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        portfolio = get_or_create_portfolio(cur, client)
        
        # Fetch current position
        cur.execute(
            "SELECT id, symbol, quantity, average_price, tranche FROM cai_position WHERE id = %s AND portfolio_id = %s AND status = 'ACTIVE'",
            (position_id, portfolio["id"])
        )
        pos = cur.fetchone()
        
        if not pos:
            raise HTTPException(status_code=404, detail="Active position not found")
            
        # 1. Enforce "NO averaging down"
        if req.entry_price <= float(pos["average_price"]):
            raise HTTPException(
                status_code=400, 
                detail=f"Averaging down is strictly prohibited. New entry price ({req.entry_price}) must be higher than current average ({pos['average_price']})."
            )
            
        # 2. Enforce 10-tranche limit (optional max cap based on PRD, but assumed here)
        if pos["tranche"] >= 10:
            raise HTTPException(status_code=400, detail="Maximum of 10 tranches reached for this position.")
            
        # 3. Calculate new weighted average
        total_cost = (float(pos["average_price"]) * pos["quantity"]) + (req.entry_price * req.quantity)
        new_qty = pos["quantity"] + req.quantity
        new_avg_price = total_cost / new_qty
        new_tranche = pos["tranche"] + 1
        
        cur.execute(
            """
            UPDATE cai_position 
            SET quantity = %s, average_price = %s, tranche = %s
            WHERE id = %s
            RETURNING id, symbol, quantity, average_price, allocation, tranche, status
            """,
            (new_qty, new_avg_price, new_tranche, position_id)
        )
        updated_pos = cur.fetchone()
        conn.commit()
        return PositionResponse(**updated_pos)
        
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Error adding tranche: {e}")
        raise HTTPException(status_code=500, detail="Failed to add tranche")
    finally:
        cur.close()

@router.get("/reviews/{review_id}/replay")
def get_replay(review_id: str, client=Depends(get_current_client)):
    """Fetch replay data for a past position review to reconstruct the chart."""
    client_id = str(client["id"])
    data = fetch_replay_data(review_id, client_id)
    if not data:
        raise HTTPException(status_code=404, detail="Review not found or access denied")
    return data
