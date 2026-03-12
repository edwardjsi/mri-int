"""
Portfolio Review API — endpoints for portfolio risk analysis.

POST /api/portfolio-review/analyze  — full portfolio risk analysis
GET  /api/portfolio-review/quick/{symbol}  — single stock MRI check
POST /api/portfolio-review/upload-csv  — import broker holdings for analysis
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional
import pandas as pd
import io

from api.deps import get_db, get_current_client
from src.portfolio_review_engine import analyze_portfolio, analyze_single_stock
from src.on_demand_ingest import ingest_missing_symbols_sync

router = APIRouter(prefix="/api/portfolio-review", tags=["portfolio-review"])


class HoldingInput(BaseModel):
    symbol: str
    quantity: float = Field(default=0.0, ge=0, description="Number of shares held")
    avg_cost: Optional[float] = Field(default=None, ge=0, description="Average purchase price")


class PortfolioSaveInput(BaseModel):
    symbol: str
    quantity: float = Field(ge=0)
    avg_cost: float = Field(ge=0)


class PortfolioInput(BaseModel):
    holdings: List[HoldingInput] = Field(min_length=1, max_length=100)


@router.post("/analyze")
def analyze(
    body: PortfolioInput,
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """
    Full portfolio risk analysis.
    Submit holdings → get per-stock MRI score breakdown + aggregate risk level.
    """
    holdings = [h.model_dump() for h in body.holdings]
    result = analyze_portfolio(holdings, conn=conn)
    return result


@router.post("/upload-csv")
async def upload_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """
    Upload a CSV file (e.g., Zerodha holdings) for portfolio risk audit.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")
    
    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        
        portfolio = []
        orig_cols = list(df.columns)
        cols = [str(c).strip().lower() for c in orig_cols]
        
        sym_col = None
        qty_col = None
        cost_col = None
        
        for i, c in enumerate(cols):
            if not sym_col and c in ('symbol', 'ticker', 'instrument'):
                sym_col = orig_cols[i]
            if not qty_col and c in ('quantity', 'qty', 'shares', 'qty.'):
                qty_col = orig_cols[i]
            if not cost_col and c in ('avg_cost', 'cost', 'price', 'buy_price', 'avg. cost'):
                cost_col = orig_cols[i]
        
        if not sym_col:
            raise HTTPException(status_code=400, detail="CSV must contain a 'symbol' or 'instrument' column.")
            
        for _, row in df.iterrows():
            if pd.isna(row[sym_col]):
                continue
            portfolio.append({
                "symbol": str(row[sym_col]).strip(),
                "quantity": float(row[qty_col]) if qty_col and pd.notna(row[qty_col]) else 0.0,
                "avg_cost": float(row[cost_col]) if cost_col and pd.notna(row[cost_col]) else 0.0,
            })
            
        result = analyze_portfolio(portfolio, conn=conn)
        
        missing = result.get("missing_symbols", [])
        if missing:
            background_tasks.add_task(
                ingest_missing_symbols_sync, 
                missing, 
                portfolio, 
                str(client['id']), 
                client['email'], 
                client['name']
            )
            result["async_processing"] = True
        else:
            result["async_processing"] = False
            
        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")


@router.get("/holdings")
def get_holdings(
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Retrieve saved external holdings with MRI analysis."""
    from psycopg2.extras import RealDictCursor
    client_id = str(client["id"])
    print(f"DEBUG: Fetching holdings for client_id: {client_id}")
    
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT symbol, quantity, avg_cost
        FROM client_external_holdings
        WHERE client_id = %s
        ORDER BY symbol
    """, (client_id,))
    rows = cur.fetchall()
    cur.close()

    print(f"DEBUG: Found {len(rows)} rows for client_id: {client_id}")

    if not rows:
        return {
            "regime": None,
            "risk_level": "LOW",
            "risk_score": 0,
            "holdings": [],
            "summary": "No saved holdings yet.",
        }

    holdings = [dict(r) for r in rows]
    result = analyze_portfolio(holdings, conn=conn)
    return result


@router.post("/save-bulk")
def save_holdings_bulk(
    body: List[PortfolioSaveInput],
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Bulk save or update holdings in the persistent Digital Twin layer."""
    client_id = str(client["id"])
    print(f"DEBUG: Bulk saving {len(body)} holdings for client_id: {client_id}")
    
    cur = conn.cursor()
    try:
        # Use execute_values or a manual loop for best performance/reliability
        # For simplicity and clear debugging, we'll use a transaction loop
        for holding in body:
            cur.execute("""
                INSERT INTO client_external_holdings (client_id, symbol, quantity, avg_cost, updated_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (client_id, symbol) DO UPDATE
                SET quantity = EXCLUDED.quantity,
                    avg_cost = EXCLUDED.avg_cost,
                    updated_at = NOW()
            """, (client_id, holding.symbol.upper().strip(), holding.quantity, holding.avg_cost))
        
        conn.commit()
        print(f"DEBUG: Successfully bulk saved {len(body)} symbols")
        return {"status": "success", "count": len(body)}
    except Exception as e:
        print(f"DEBUG: Bulk save error: {e}")
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()


@router.post("/save")
def save_holding(
    body: PortfolioSaveInput,
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Save or update a single holding."""
    # (Existing implementation kept for compatibility)
    client_id = str(client["id"])
    print(f"DEBUG: Saving holding {body.symbol} for client_id: {client_id}")
    
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO client_external_holdings (client_id, symbol, quantity, avg_cost, updated_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (client_id, symbol) DO UPDATE
            SET quantity = EXCLUDED.quantity,
                avg_cost = EXCLUDED.avg_cost,
                updated_at = NOW()
        """, (client_id, body.symbol.upper().strip(), body.quantity, body.avg_cost))
        conn.commit()
        print(f"DEBUG: Successfully saved {body.symbol}")
        return {"status": "success", "message": f"Saved {body.symbol}"}
    except Exception as e:
        print(f"DEBUG: Error saving {body.symbol}: {e}")
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()


@router.delete("/holdings/{symbol}")
def delete_holding(
    symbol: str,
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Remove a holding from the persistent layer."""
    cur = conn.cursor()
    try:
        cur.execute("""
            DELETE FROM client_external_holdings
            WHERE client_id = %s AND symbol = %s
        """, (str(client["id"]), symbol.upper().strip()))
        conn.commit()
        return {"status": "success", "message": f"Deleted {symbol}"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()


@router.get("/quick/{symbol}")
def quick_check(
    symbol: str,
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Quick single-stock MRI analysis: score, regime alignment, EMA position."""
    result = analyze_single_stock(symbol, conn=conn)
    if not result.get("found", True):
        raise HTTPException(status_code=404, detail=result.get("message", "Symbol not found"))
    return result
