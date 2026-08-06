from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import psycopg2.extras
import logging
import uuid
from api.deps import get_db, get_current_client
from engine_core.cai_replay import fetch_replay_data
from engine_core.cai_decision_ladder_engine import load_mri_inputs, compute_thresholds, evaluate_position_health, resolve_state, ALGORITHM_VERSION
import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cai/portfolio", tags=["cai_portfolio"])

class PositionCreate(BaseModel):
    symbol: str
    quantity: Optional[int] = None
    average_price: Optional[float] = None
    idempotency_key: Optional[str] = None

class TrancheAdd(BaseModel):
    quantity: Optional[int] = None
    entry_price: float
    allow_average_down: Optional[bool] = False
    idempotency_key: Optional[str] = None

class SellRequest(BaseModel):
    quantity: Optional[int] = None
    sell_price: float
    idempotency_key: Optional[str] = None

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

def _insert_ledger_event(cur, portfolio_id, position_id, symbol, event_type, allocation_reason, price, quantity, idempotency_key=None, reference_event_id=None):
    """Helper to insert an immutable event into the CAI Trade Ledger."""
    event_id = str(uuid.uuid4())
    capital = float(price) * float(quantity) if price and quantity else 0.0
    
    # Simple uniqueness check on idempotency key if provided
    if idempotency_key:
        cur.execute("SELECT id FROM cai_trade_ledger WHERE idempotency_key = %s", (idempotency_key,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Duplicate request detected (Idempotency Key Conflict)")

    cur.execute(
        """
        INSERT INTO cai_trade_ledger 
        (id, portfolio_id, position_id, symbol, event_type, allocation_reason, price, quantity, capital_allocated, idempotency_key, reference_event_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (event_id, portfolio_id, position_id, symbol, event_type, allocation_reason, price, quantity, capital, idempotency_key, reference_event_id)
    )

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
        
        # Dual Write: Insert Ledger Event (Initial Position = BUY, D1_ENTRY)
        _insert_ledger_event(
            cur, portfolio["id"], pos_id, req.symbol.upper(),
            "BUY", "D1_ENTRY", req.average_price, req.quantity, req.idempotency_key
        )
        
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
        
        # Dual Write: Insert Ledger Event (Tranche Add = BUY, D{N}_TRANCHE)
        _insert_ledger_event(
            cur, portfolio["id"], position_id, pos["symbol"],
            "BUY", f"D{new_tranche}_TRANCHE", req.entry_price, req.quantity, req.idempotency_key
        )
        
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
        
        # Dual Write: Insert Ledger Event (Sell = SELL, REDUCE or FULL_EXIT)
        alloc_reason = "FULL_EXIT" if new_qty == 0 else "REDUCE"
        _insert_ledger_event(
            cur, portfolio["id"], position_id, pos["symbol"],
            "SELL", alloc_reason, req.sell_price, req.quantity, req.idempotency_key
        )
        
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

@router.get("/positions/{position_id}/ledger")
def get_position_ledger(position_id: str, client=Depends(get_current_client), conn=Depends(get_db)):
    """Fetch the chronological event stream (Capital Allocation Ledger) for a position."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        portfolio = get_or_create_portfolio(cur, client)
        
        # Verify ownership
        cur.execute("SELECT id FROM cai_position WHERE id = %s AND portfolio_id = %s", (position_id, portfolio["id"]))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Position not found")
            
        cur.execute(
            """
            SELECT id, event_type, allocation_reason, CAST(execution_date AS VARCHAR) as execution_date,
                   price, quantity, capital_allocated, portfolio_weight, decision_state,
                   decision_ladder_version, notes, reference_event_id
            FROM cai_trade_ledger
            WHERE position_id = %s
            ORDER BY execution_date ASC
            """,
            (position_id,)
        )
        return cur.fetchall()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching ledger: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch ledger")
    finally:
        cur.close()

class CorrectionRequest(BaseModel):
    reference_event_id: str
    event_type: str
    allocation_reason: str
    price: float
    quantity: int
    notes: Optional[str] = None

@router.post("/positions/{position_id}/ledger/correction")
def correct_ledger_event(position_id: str, req: CorrectionRequest, client=Depends(get_current_client), conn=Depends(get_db)):
    """Insert a compensating event to correct a human mistake, preserving append-only immutability."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        portfolio = get_or_create_portfolio(cur, client)
        
        cur.execute("SELECT symbol FROM cai_position WHERE id = %s AND portfolio_id = %s", (position_id, portfolio["id"]))
        pos = cur.fetchone()
        if not pos:
            raise HTTPException(status_code=404, detail="Position not found")
            
        # Optional: verify reference_event_id belongs to this position
        cur.execute("SELECT id FROM cai_trade_ledger WHERE id = %s AND position_id = %s", (req.reference_event_id, position_id))
        if not cur.fetchone():
            raise HTTPException(status_code=400, detail="Referenced event not found in this position's ledger")
            
        _insert_ledger_event(
            cur, portfolio["id"], position_id, pos["symbol"],
            req.event_type, req.allocation_reason, req.price, req.quantity,
            idempotency_key=None,
            reference_event_id=req.reference_event_id
        )
        
        # Note: A correction might also require adjusting the cai_position current state.
        # For V1.0, we just insert the compensating ledger event. To keep the state perfectly synced, 
        # a more advanced recalculation logic could run here.
        
        conn.commit()
        return {"status": "success", "message": "Correction event logged."}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Error inserting correction: {e}")
        raise HTTPException(status_code=500, detail="Failed to insert correction")
    finally:
        cur.close()

class LedgerInitEvent(BaseModel):
    symbol: str
    date: str
    quantity: int
    price: float
    allocation_reason: str

class LedgerInitRequest(BaseModel):
    events: List[LedgerInitEvent]

@router.post("/init-ledger")
def init_ledger(req: LedgerInitRequest, client=Depends(get_current_client), conn=Depends(get_db)):
    """
    Bootstrap a CAI portfolio by importing existing holdings.
    Generates chronological ledger events and builds the final position state.
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        portfolio = get_or_create_portfolio(cur, client)
        
        # Sort events chronologically to process them in order
        events = sorted(req.events, key=lambda x: x.date)
        
        for event in events:
            symbol = event.symbol.upper()
            
            # Check if active position exists
            cur.execute(
                "SELECT id, quantity, average_price, tranche FROM cai_position WHERE portfolio_id = %s AND symbol = %s AND status = 'ACTIVE'",
                (portfolio["id"], symbol)
            )
            pos = cur.fetchone()
            
            if not pos:
                # Open a new position
                pos_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO cai_position (id, portfolio_id, symbol, quantity, average_price, tranche, status)
                    VALUES (%s, %s, %s, %s, %s, 1, 'ACTIVE')
                    """,
                    (pos_id, portfolio["id"], symbol, event.quantity, event.price)
                )
                
                # Insert Ledger Event
                _insert_ledger_event(
                    cur, portfolio["id"], pos_id, symbol,
                    "BUY", event.allocation_reason, event.price, event.quantity
                )
                
                # Override the execution_date to the historical date
                cur.execute(
                    "UPDATE cai_trade_ledger SET execution_date = %s WHERE position_id = %s AND allocation_reason = %s",
                    (event.date, pos_id, event.allocation_reason)
                )
                
            else:
                # Add tranche to existing position
                pos_id = pos["id"]
                new_qty = pos["quantity"] + event.quantity
                total_cost = (float(pos["average_price"]) * pos["quantity"]) + (event.price * event.quantity)
                new_avg_price = total_cost / new_qty
                new_tranche = pos["tranche"] + 1
                
                cur.execute(
                    """
                    UPDATE cai_position 
                    SET quantity = %s, average_price = %s, tranche = %s
                    WHERE id = %s
                    """,
                    (new_qty, new_avg_price, new_tranche, pos_id)
                )
                
                # Insert Ledger Event
                _insert_ledger_event(
                    cur, portfolio["id"], pos_id, symbol,
                    "BUY", event.allocation_reason, event.price, event.quantity
                )
                
                # Override the execution_date to the historical date
                cur.execute(
                    "UPDATE cai_trade_ledger SET execution_date = %s WHERE position_id = %s AND allocation_reason = %s",
                    (event.date, pos_id, event.allocation_reason)
                )
                
        conn.commit()
        return {"status": "success", "message": f"Successfully initialized {len(events)} ledger events."}
    except Exception as e:
        conn.rollback()
        logger.error(f"Error initializing ledger: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize ledger")
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

@router.get("/debug/{symbol}")
def debug_symbol_decision_ladder(symbol: str, conn=Depends(get_db)):
    """
    Developer Truth Table endpoint.
    Returns the exact inputs, computed thresholds, and final decision state for a single symbol.
    """
    try:
        inputs = load_mri_inputs(conn, symbol.upper())
        if not inputs:
            raise HTTPException(status_code=404, detail="No technical data found for symbol.")
            
        thresholds = compute_thresholds(inputs)
        evaluation = evaluate_position_health(inputs["current_price"], thresholds)
        state = resolve_state(evaluation)
        
        return {
            "symbol": symbol.upper(),
            "inputs": inputs,
            "outputs": thresholds,
            "decision_state": state,
            "algorithm": ALGORITHM_VERSION,
            "calculated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error debugging {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to compute debug inputs")
