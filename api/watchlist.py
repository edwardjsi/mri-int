from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
import psycopg2.extras

from api.deps import get_db, get_current_client

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

class WatchlistAddRequest(BaseModel):
    symbol: str

class WatchlistItem(BaseModel):
    symbol: str
    price: Optional[float] = None
    score: Optional[int] = None
    regime: Optional[str] = None
    trend_alignment: Optional[str] = None # BULL / BEAR / NEUTRAL (from EMA-200)

@router.get("/", response_model=List[WatchlistItem])
def get_watchlist(client=Depends(get_current_client), conn=Depends(get_db)):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Fetch symbols from watchlist
    cur.execute("SELECT symbol FROM client_watchlist WHERE client_id = %s", (str(client["id"]),))
    symbols = [row["symbol"] for row in cur.fetchall()]
    
    if not symbols:
        return []
    
    # Fetch latest scores and prices for these symbols
    # We use a subquery to get the latest date from stock_scores
    cur.execute("""
        WITH latest_scores AS (
            SELECT ss.symbol, ss.score, ss.date,
                   dp.close as current_price,
                   CASE 
                     WHEN dp.close > dp.ema_200 THEN 'BULL'
                     WHEN dp.close < dp.ema_200 THEN 'BEAR'
                     ELSE 'NEUTRAL'
                   END as trend_alignment
            FROM stock_scores ss
            JOIN daily_prices dp ON dp.symbol = ss.symbol AND dp.date = ss.date
            WHERE ss.symbol = ANY(%s)
            AND ss.date = (SELECT MAX(date) FROM stock_scores WHERE symbol = ss.symbol)
        )
        SELECT * FROM latest_scores
    """, (symbols,))
    
    data = cur.fetchall()
    
    # Map back to symbols to handle missing data cases
    results = []
    data_map = {row["symbol"]: row for row in data}
    
    for symbol in symbols:
        row = data_map.get(symbol)
        results.append(WatchlistItem(
            symbol=symbol,
            price=float(row["current_price"]) if row and row["current_price"] else None,
            score=row["score"] if row else None,
            trend_alignment=row["trend_alignment"] if row else None
        ))
        
    return results

@router.post("/", status_code=status.HTTP_201_CREATED)
def add_to_watchlist(req: WatchlistAddRequest, client=Depends(get_current_client), conn=Depends(get_db)):
    symbol = req.symbol.upper().strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")
        
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO client_watchlist (client_id, symbol) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (str(client["id"]), symbol)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add symbol: {e}")
        
    return {"message": f"{symbol} added to watchlist"}

@router.delete("/{symbol}")
def remove_from_watchlist(symbol: str, client=Depends(get_current_client), conn=Depends(get_db)):
    symbol = symbol.upper().strip()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM client_watchlist WHERE client_id = %s AND symbol = %s",
        (str(client["id"]), symbol)
    )
    conn.commit()
    return {"message": f"{symbol} removed from watchlist"}
