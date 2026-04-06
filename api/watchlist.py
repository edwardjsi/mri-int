from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
import psycopg2.extras

import csv
import io
from api.deps import get_db, get_current_client
from engine_core.on_demand_ingest import ingest_missing_symbols_sync

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

class WatchlistAddRequest(BaseModel):
    symbol: str

class WatchlistItem(BaseModel):
    symbol: str
    price: Optional[float] = None
    score: Optional[int] = None
    regime: Optional[str] = None
    trend_alignment: Optional[str] = None
    is_not_found: bool = False
    is_pending: bool = False

@router.get("/universal", response_model=List[str])
def get_universal_watchlist(conn=Depends(get_db)):
    """Return all unique symbols currently being tracked by any user."""
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT symbol FROM client_watchlist")
    rows = cur.fetchall()
    cur.close()
    return [row[0] for row in rows]


@router.get("/search")
def search_universe(q: str, conn=Depends(get_db)):
    """Search the 500+ stock universe by symbol or name for autocomplete."""
    if not q or len(q) < 2:
        return []
    
    query = f"%{q.upper()}%"
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT symbol, company_name 
            FROM universe 
            WHERE symbol ILIKE %s OR company_name ILIKE %s 
            LIMIT 10
        """, (query, query))
        return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        return []
    finally:
        cur.close()

@router.get("", response_model=List[WatchlistItem])
def get_watchlist(client=Depends(get_current_client), conn=Depends(get_db)):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Fetch symbols from watchlist
    cur.execute("SELECT symbol FROM client_watchlist WHERE client_id = %s::uuid", (str(client["id"]),))
    rows = cur.fetchall()
    
    if not rows:
        cur.close()
        return []

    is_dict_sym = isinstance(rows[0], dict)
    symbols = [row["symbol"] if is_dict_sym else row[0] for row in rows]
    
    # Fetch latest scores and prices (using LEFT JOIN so we don't lose new symbols)
    cur.execute("""
        SELECT 
            cw.symbol,
            ss.score,
            dp.close as current_price,
            CASE 
                WHEN dp.close > dp.ema_200 THEN 'BULL'
                WHEN dp.close < dp.ema_200 THEN 'BEAR'
                ELSE 'NEUTRAL'
            END as trend_alignment,
            (dp.close IS NULL AND cw.created_at < (NOW() - INTERVAL '5 minutes')) as is_not_found
        FROM client_watchlist cw
        LEFT JOIN (
            SELECT DISTINCT ON (symbol) symbol, total_score as score, date 
            FROM stock_scores 
            ORDER BY symbol, date DESC
        ) ss ON ss.symbol = cw.symbol
        LEFT JOIN (
            SELECT DISTINCT ON (symbol) symbol, close, ema_200, date
            FROM daily_prices
            ORDER BY symbol, date DESC
        ) dp ON dp.symbol = cw.symbol
        WHERE cw.client_id = %s::uuid
    """, (str(client["id"]),))
    
    data = cur.fetchall()
    cur.close()
    
    results = []
    for row in data:
        # Determine if row is dict (RealDictCursor) or tuple
        is_dict = isinstance(row, dict)
        sym = row["symbol"] if is_dict else row[0]
        
        price = None
        score = None
        trend = None
        
        if row:
            try:
                price_raw = row["current_price"] if is_dict else row[2]
                price = float(price_raw) if price_raw is not None else None
                
                score = row["score"] if is_dict else row[1]
                trend = row["trend_alignment"] if is_dict else row[3]
            except (IndexError, KeyError, TypeError):
                pass

        results.append(WatchlistItem(
            symbol=sym,
            price=price,
            score=score,
            trend_alignment=trend,
            is_not_found=row["is_not_found"] if is_dict else False
        ))
        
    return results

@router.post("", status_code=status.HTTP_201_CREATED)
def add_to_watchlist(req: WatchlistAddRequest, background_tasks: BackgroundTasks, client=Depends(get_current_client), conn=Depends(get_db)):
    symbol = req.symbol.upper().strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")
        
    cur = conn.cursor()
    try:
        # Check if it already exists to prevent unique constraint error
        cur.execute("SELECT 1 FROM client_watchlist WHERE client_id = %s::uuid AND symbol = %s", (str(client["id"]), symbol))
        if cur.fetchone():
            return {"message": f"{symbol} already in watchlist"}

        cur.execute(
            "INSERT INTO client_watchlist (client_id, symbol) VALUES (%s::uuid, %s)",
            (str(client["id"]), symbol)
        )
        conn.commit()
        # Trigger background data sync (this makes sure RELIANCE is fetched if missing)
        background_tasks.add_task(
            ingest_missing_symbols_sync, 
            [symbol], 
            str(client["id"]), 
            client.get("email"),
            client.get("name")
        )
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add symbol: {e}")
    finally:
        cur.close()
        
    return {"message": f"{symbol} added to watchlist"}

@router.delete("/{symbol}")
def remove_from_watchlist(symbol: str, client=Depends(get_current_client), conn=Depends(get_db)):
    symbol = symbol.upper().strip()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM client_watchlist WHERE client_id = %s::uuid AND symbol = %s",
        (str(client["id"]), symbol)
    )
    conn.commit()
    cur.close()
    return {"message": f"{symbol} removed from watchlist"}

@router.post("/upload-csv")
async def upload_watchlist_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    client=Depends(get_current_client),
    conn=Depends(get_db)
):
    """Bulk upload symbols to watchlist from CSV."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    content = await file.read()
    try:
        decoded = content.decode('utf-8-sig').splitlines()
        reader = csv.reader(decoded)
        
        symbols = []
        first_row = next(reader, None)
        if not first_row:
            return {"message": "Empty file", "added": 0}

        # Check for header
        header = [h.strip().lower() for h in first_row]
        symbol_idx = -1
        if "symbol" in header:
            symbol_idx = header.index("symbol")
        elif "ticker" in header:
            symbol_idx = header.index("ticker")
        
        if symbol_idx != -1:
            # File has headers
            for row in reader:
                if len(row) > symbol_idx:
                    sym = row[symbol_idx].strip().upper()
                    if sym: symbols.append(sym)
        else:
            # Assume no header, first row was a ticker
            sym = first_row[0].strip().upper()
            if sym: symbols.append(sym)
            for row in reader:
                if row:
                    sym = row[0].strip().upper()
                    if sym: symbols.append(sym)

        if not symbols:
            return {"message": "No valid symbols found in CSV", "added": 0}

        cur = conn.cursor()
        added_count = 0
        for symbol in set(symbols): # Deduplicate
            try:
                cur.execute(
                    "INSERT INTO client_watchlist (client_id, symbol) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (str(client["id"]), symbol)
                )
                if cur.rowcount > 0:
                    added_count += 1
            except Exception:
                continue
        
        conn.commit()
        if symbols:
            background_tasks.add_task(ingest_missing_symbols_sync, list(set(symbols)), 'admin', client["email"])
        return {"message": f"Bulk upload successful. Added {added_count} new symbols.", "total_processed": len(symbols)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CSV processing failed: {str(e)}")
