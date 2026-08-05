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
    quantity: Optional[int] = None
    average_price: Optional[float] = None

class TrancheAdd(BaseModel):
    quantity: Optional[int] = None
    entry_price: float
    allow_average_down: Optional[bool] = False

class SellRequest(BaseModel):
    quantity: Optional[int] = None
    sell_price: float

class PositionResponse(BaseModel):
    id: str
    symbol: str
    quantity: Optional[int] = None
    average_price: Optional[float] = None
    allocation: Optional[float] = None
    tranche: Optional[int] = None
    status: Optional[str] = None
    decision_state: Optional[str] = None
    add_level: Optional[float] = None
    alert_level: Optional[float] = None
    structure_level: Optional[float] = None
    quit_level: Optional[float] = None
    decision_calculated_at: Optional[str] = None
    current_price: Optional[float] = None
    models: Optional[List[dict]] = None

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
            SELECT cp.id, cp.symbol, cp.quantity, cp.average_price, cp.allocation, cp.tranche, cp.status,
                   cp.decision_state, cp.add_level, cp.alert_level, cp.structure_level, cp.quit_level,
                   CAST(cp.decision_calculated_at AS VARCHAR) as decision_calculated_at,
                   dp.close as current_price
            FROM cai_position cp
            LEFT JOIN (
                SELECT symbol, close
                FROM daily_prices
                WHERE date = (SELECT MAX(date) FROM daily_prices)
            ) dp ON cp.symbol = dp.symbol
            WHERE cp.portfolio_id = %s AND cp.status = 'ACTIVE'
            ORDER BY cp.symbol ASC
            """,
            (portfolio["id"],)
        )
        positions = cur.fetchall()
        
        symbols = [p['symbol'] for p in positions]
        
        # Attach latest models
        from engine_core.model_results_repository import ModelResultRepository
        model_repo = ModelResultRepository()
        models = model_repo.latest_for_symbols(symbols)
        models_by_symbol = {}
        for m in models:
            if m.symbol not in models_by_symbol:
                models_by_symbol[m.symbol] = []
            models_by_symbol[m.symbol].append({
                "id": m.model_id,
                "version": m.model_version,
                "status": m.status,
                "score": float(m.score) if m.score is not None else None,
                "evaluation_date": m.evaluation_date.isoformat() if m.evaluation_date else None,
            })
            
        position_list = []
        for p in positions:
            p_dict = dict(p)
            p_dict['models'] = models_by_symbol.get(p['symbol'], [])
            position_list.append(p_dict)
        
        cash_val = portfolio["cash"]
        health_val = portfolio["health"]
        return PortfolioResponse(
            id=portfolio["id"],
            owner=portfolio["owner"],
            cash=float(cash_val) if cash_val is not None else 0.0,
            health=float(health_val) if health_val is not None else None,
            positions=[PositionResponse(**p) for p in position_list]
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
            
        # 1. Enforce "NO averaging down" (unless explicitly allowed by override)
        if req.entry_price <= float(pos["average_price"]) and not req.allow_average_down:
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

@router.post("/positions/{position_id}/sell", response_model=PositionResponse)
def sell_position(position_id: str, req: SellRequest, client=Depends(get_current_client), conn=Depends(get_db)):
    """Sell a portion or all of a position."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        portfolio = get_or_create_portfolio(cur, client)
        
        cur.execute(
            "SELECT id, symbol, quantity, average_price, tranche FROM cai_position WHERE id = %s AND portfolio_id = %s AND status = 'ACTIVE'",
            (position_id, portfolio["id"])
        )
        pos = cur.fetchone()
        
        if not pos:
            raise HTTPException(status_code=404, detail="Active position not found")
            
        if req.quantity <= 0:
            raise HTTPException(status_code=400, detail="Sell quantity must be greater than 0")
            
        if req.quantity > pos["quantity"]:
            raise HTTPException(status_code=400, detail=f"Cannot sell more than owned ({pos['quantity']})")
            
        new_qty = pos["quantity"] - req.quantity
        new_status = 'CLOSED' if new_qty == 0 else 'ACTIVE'
        
        cur.execute(
            """
            UPDATE cai_position 
            SET quantity = %s, status = %s
            WHERE id = %s
            RETURNING id, symbol, quantity, average_price, allocation, tranche, status
            """,
            (new_qty, new_status, position_id)
        )
        updated_pos = cur.fetchone()
        conn.commit()
        return PositionResponse(**updated_pos)
        
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Error selling position: {e}")
        raise HTTPException(status_code=500, detail="Failed to sell position")
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
