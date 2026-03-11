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
from src.on_demand_ingest import ingest_missing_symbols_async

router = APIRouter(prefix="/api/portfolio-review", tags=["portfolio-review"])


class HoldingInput(BaseModel):
    symbol: str
    quantity: float = Field(ge=0, description="Number of shares held")
    avg_cost: Optional[float] = Field(default=None, ge=0, description="Average purchase price")


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
                ingest_missing_symbols_async, 
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
