from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from pydantic import BaseModel
import psycopg2.extras

import csv
import io
import logging
from api.deps import get_db, get_current_client
from engine_core.on_demand_ingest import ingest_missing_symbols_sync
from engine_fundamental.aae_data_primer import prime_aae_data, prime_aae_data_batch

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

class WatchlistAddRequest(BaseModel):
    symbol: str

class ScoreConditions(BaseModel):
    ema_50_above_200: bool
    ema_200_slope_positive: bool
    at_6m_high: bool
    volume_surge: bool
    relative_strength: bool

class WatchlistItem(BaseModel):
    symbol: str
    price: Optional[float] = None
    score: Optional[int] = None
    regime: Optional[str] = None
    trend_alignment: Optional[str] = None
    conditions: Optional[ScoreConditions] = None
    breakout_candidate: bool = False
    is_not_found: bool = False
    is_pending: bool = False
    perx_score: Optional[float] = None
    perx_lifecycle: Optional[str] = None

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
            ss.condition_ema_50_200,
            ss.condition_ema_200_slope,
            ss.condition_6m_high,
            ss.condition_volume,
            ss.condition_rs,
            dp.close as current_price,
            CASE 
                WHEN dp.close > dp.ema_200 THEN 'BULL'
                WHEN dp.close < dp.ema_200 THEN 'BEAR'
                ELSE 'NEUTRAL'
            END as trend_alignment,
            (dp.close IS NULL AND cw.created_at < (NOW() - INTERVAL '5 minutes')) as is_not_found,
            cw.breakout_candidate,
            ps.perx_score,
            ps.lifecycle_stage as perx_lifecycle
        FROM client_watchlist cw
        LEFT JOIN (
            SELECT DISTINCT ON (symbol) 
                symbol, total_score as score, date,
                condition_ema_50_200, condition_ema_200_slope,
                condition_6m_high, condition_volume, condition_rs
            FROM stock_scores 
            ORDER BY symbol, date DESC
        ) ss ON ss.symbol = cw.symbol
        LEFT JOIN (
            SELECT DISTINCT ON (symbol) symbol, close, ema_200, date
            FROM daily_prices
            ORDER BY symbol, date DESC
        ) dp ON dp.symbol = cw.symbol
        LEFT JOIN perx_scores ps ON cw.symbol = ps.symbol
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
        conditions = None
        breakout_candidate = row["breakout_candidate"] if is_dict else row[10]
        
        if row:
            try:
                price_raw = row["current_price"] if is_dict else row[7]
                price = float(price_raw) if price_raw is not None else None
                
                score = row["score"] if is_dict else row[1]
                trend = row["trend_alignment"] if is_dict else row[8]

                # Extract conditions
                has_conditions = (row["condition_ema_50_200"] is not None) if is_dict else (row[2] is not None)
                if has_conditions:
                    conditions = {
                        "ema_50_above_200": bool(row["condition_ema_50_200"] if is_dict else row[2]),
                        "ema_200_slope_positive": bool(row["condition_ema_200_slope"] if is_dict else row[3]),
                        "at_6m_high": bool(row["condition_6m_high"] if is_dict else row[4]),
                        "volume_surge": bool(row["condition_volume"] if is_dict else row[5]),
                        "relative_strength": bool(row["condition_rs"] if is_dict else row[6]),
                    }
            except (IndexError, KeyError, TypeError):
                pass

        results.append(WatchlistItem(
            symbol=sym,
            price=price,
            score=score,
            trend_alignment=trend,
            conditions=conditions,
            breakout_candidate=bool(breakout_candidate),
            is_not_found=row["is_not_found"] if is_dict else False,
            perx_score=float(row["perx_score"]) if (is_dict and row["perx_score"]) else (float(row[11]) if not is_dict and row[11] else None),
            perx_lifecycle=row["perx_lifecycle"] if is_dict else row[12]
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
        # Trigger AAE fundamental data backfill (quarterly financials + governance)
        background_tasks.add_task(prime_aae_data, symbol)
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
    # Log the start of upload
    logger.info(f"Bulk upload triggered by client {client.get('email')} for file {file.filename}")

    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    try:
        content = await file.read()
        # Try multiple encodings
        decoded_str = ""
        for encoding in ['utf-8-sig', 'utf-8', 'latin-1']:
            try:
                decoded_str = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        
        if not decoded_str:
            raise ValueError("Could not decode CSV file. Please ensure it is in UTF-8 or Latin-1 format.")

        lines = decoded_str.splitlines()
        reader = csv.reader(lines)
        
        symbols = []
        first_row = next(reader, None)
        if not first_row:
            return {"message": "Empty file", "added": 0}

        # Check for header
        header = [str(h).strip().lower() for h in first_row]
        logger.info(f"CSV Headers detected: {header}")
        
        symbol_idx = -1
        # Flexible header detection
        for idx, h in enumerate(header):
            if any(term in h for term in ["symbol", "ticker", "stock", "code", "scrip"]):
                symbol_idx = idx
                break
        
        if symbol_idx != -1:
            logger.info(f"Using column index {symbol_idx} for symbols")
            for row in reader:
                if len(row) > symbol_idx:
                    sym = row[symbol_idx].strip().upper()
                    if sym: symbols.append(sym)
        else:
            logger.info("No clear header found. Defaulting to first column.")
            # Assume no header, first row was a ticker
            sym = first_row[0].strip().upper()
            if sym: symbols.append(sym)
            for row in reader:
                if row and len(row) > 0:
                    sym = row[0].strip().upper()
                    if sym: symbols.append(sym)

        # Cleanup symbols (remove .NS, .BO for normalization if present)
        symbols = [s.replace('.NS', '').replace('.BO', '') for s in symbols if s]
        unique_symbols = list(set(symbols))
        
        if not unique_symbols:
            return {"message": "No valid symbols found in CSV", "added": 0}

        logger.info(f"Processing {len(unique_symbols)} unique symbols")

        cur = conn.cursor()
        added_count = 0
        client_id_str = str(client["id"])
        
        logger.info(f"[BULK_UPLOAD] Client {client_id_str} attempting to upload {len(unique_symbols)} unique symbols")
        
        for symbol in unique_symbols:
            try:
                cur.execute(
                    "INSERT INTO client_watchlist (client_id, symbol) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (client_id_str, symbol)
                )
                if cur.rowcount > 0:
                    added_count += 1
            except Exception as e:
                logger.error(f"[BULK_UPLOAD] Error inserting {symbol}: {e}")
        
        conn.commit()
        cur.close()
        
        if unique_symbols:
            logger.info(f"Triggering background ingestion for {len(unique_symbols)} symbols")
            background_tasks.add_task(ingest_missing_symbols_sync, unique_symbols, str(client["id"]), client["email"])
            background_tasks.add_task(prime_aae_data_batch, unique_symbols)
            
        return {
            "message": f"Bulk upload successful. Found {len(unique_symbols)} symbols, added {added_count} new ones.", 
            "total_processed": len(unique_symbols),
            "added_count": added_count
        }

    except Exception as e:
        logger.error(f"CSV Upload Failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"CSV processing failed: {str(e)}")
