import logging
import io
import uuid
import csv
import pandas as pd
import psycopg2.extras
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from engine_core.db import get_connection
from engine_core.on_demand_ingest import ingest_missing_symbols_sync
from api.schema import ensure_required_tables
from api.deps import get_db, get_current_client

router = APIRouter(prefix="/api/portfolio-review", tags=["Portfolio Review"])
logger = logging.getLogger(__name__)

@router.get("/holdings-status")
@router.get("/holdings_status")
@router.get("/holdings") 
@router.get("")
async def get_holdings(
    client=Depends(get_current_client),
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        client_id = str(client["id"])
        email = client["email"]
        
        cur.execute("""
            SELECT symbol, quantity, avg_cost 
            FROM client_external_holdings 
            WHERE client_id = %s::uuid
        """, (str(client_id),))
        holdings_list = cur.fetchall()
        
        # Fallback to legacy table if it exists and we found nothing yet
        if not holdings_list:
            try:
                cur.execute("SELECT symbol FROM holdings WHERE email = %s", (email,))
                legacy_rows = cur.fetchall()
                is_dict_legacy = not legacy_rows or isinstance(legacy_rows[0], dict)
                for r in legacy_rows:
                    holdings_list.append({
                        "symbol": r["symbol"] if is_dict_legacy else r[0],
                        "quantity": 0,
                        "avg_cost": 0
                    })
            except Exception:
                conn.rollback()
            finally:
                pass

        # Enrich with analysis if we have holdings
        enriched_holdings = []
        if holdings_list:
            from engine_core.portfolio_review_engine import analyze_portfolio
            try:
                is_dict_holdings = not holdings_list or isinstance(holdings_list[0], dict)
                raw_list = []
                for h in holdings_list:
                    raw_list.append({
                        "symbol": h["symbol"] if is_dict_holdings else h[0],
                        "quantity": h["quantity"] if is_dict_holdings else h[1],
                        "avg_cost": h["avg_cost"] if is_dict_holdings else h[2]
                    })
                
                # Use standard analyzer with persistence support
                analysis_results = analyze_portfolio(raw_list, conn)
                analysis_results["storage_ready"] = True
                return analysis_results
            except Exception as e:
                logger.error(f"ANALYSIS CRASH: {e}")
                return {
                    "storage_ready": True,
                    "holdings": holdings_list,
                    "summary": "Holdings loaded but analysis failed.",
                    "risk_level": "UNKNOWN",
                    "analysis_error": str(e)
                }
        
        return {
            "storage_ready": True,
            "holdings": [],
            "summary": "No holdings found. Upload your broker CSV to begin.",
            "risk_level": "N/A"
        }
    except Exception as e:
        logger.error(f"FETCH HOLDINGS ERROR: {e}")
        return {
            "storage_ready": False,
            "error": str(e),
            "summary": "Database connectivity issue."
        }
    finally:
        cur.close()

class SingleHoldingAddRequest(BaseModel):
    symbol: str
    quantity: float
    avg_cost: float

@router.post("/add")
async def add_single_holding(
    req: SingleHoldingAddRequest,
    background_tasks: BackgroundTasks,
    client=Depends(get_current_client),
    conn=Depends(get_db)
):
    """Save a single stock holding (Watchlist-style functionality for Portfolio)."""
    try:
        cur = conn.cursor()
        sym = req.symbol.upper().strip()
        client_id = str(client["id"])

        cur.execute("""
            INSERT INTO client_external_holdings (client_id, symbol, quantity, avg_cost)
            VALUES (%s::uuid, %s, %s, %s)
            ON CONFLICT (client_id, symbol) 
            DO UPDATE SET 
                quantity = EXCLUDED.quantity,
                avg_cost = EXCLUDED.avg_cost,
                updated_at = NOW()
        """, (client_id, sym, req.quantity, req.avg_cost))
        
        conn.commit()
        cur.close()
        
        background_tasks.add_task(ingest_missing_symbols_sync, [req.symbol.upper()], client_id)
        return {"message": f"Successfully added {req.symbol.upper()}."}
    except Exception as e:
        conn.rollback()
        logger.exception(f"UPLOAD ERROR: {repr(e)} ({type(e).__name__})")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-csv")
@router.post("/upload_csv")
async def upload_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    conn=Depends(get_db),
    client=Depends(get_current_client),
    email: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
):
    """Universal Unbreakable CSV Parser for Portfolios."""
    try:
        client_id = client["id"]
        current_email = email or client.get("email")
        # Ensure RLS policies see the current client on this connection
        cur_rls = conn.cursor()
        cur_rls.execute("SELECT set_config('app.current_client_id', %s::text, true);", (str(client_id),))
        cur_rls.close()
        contents = await file.read()
        
        # Resilient Reading
        sep = ','
        try:
            snippet = contents.decode('utf-8', errors='ignore')[:1024]
            dialect = csv.Sniffer().sniff(snippet, delimiters=',;\t|')
            sep = dialect.delimiter
        except: pass

        df = None
        for enc in ['utf-8', 'latin-1', 'utf-8-sig']:
            try:
                df = pd.read_csv(io.StringIO(contents.decode(enc, errors='ignore')), sep=sep)
                break
            except: continue
        
        if df is None:
            raise HTTPException(status_code=400, detail="Invalid CSV format.")

        df.columns = [c.lower().strip() for c in df.columns]
        symbol_aliases = ('symbol', 'ticker', 'instrument', 'stock', 'isin', 'tradingsymbol', 'trading symbol', 'holding', 'asset', 'script')
        qty_aliases = ('quantity', 'shares', 'qty', 'qty.', 'available quantity', 'vol', 'volume', 'current qty', 'net qty')
        cost_aliases = ('avg_cost', 'avg cost', 'cost', 'avg_buy_price', 'avg. cost', 'average price', 'buy price', 'average buy price', 'purchase price', 'avg price', 'avg. price')
        
        sym_col = next((c for c in df.columns if c in symbol_aliases), None)
        qty_col = next((c for c in df.columns if c in qty_aliases), None)
        cst_col = next((c for c in df.columns if c in cost_aliases), None)
        
        if not sym_col:
             sym_col = df.select_dtypes(include=['object']).columns[0] if not df.select_dtypes(include=['object']).empty else None
        
        if not sym_col:
            raise HTTPException(status_code=400, detail="Could not find a Symbol column.")

        cur = conn.cursor()
        processed_symbols = []
        skipped_symbols = []
        
        # WISE GUARD: Pre-fetch universe for bulk check
        cur.execute("SELECT symbol FROM market_index_prices")
        universe_map = {r[0] for r in cur.fetchall()}

        processed_holdings = []

        for _, row in df.iterrows():
            sym = str(row[sym_col]).upper().strip()
            if not sym or sym == 'NAN': continue
            
            # Wise Filtering: We want to accept most stocks during bulk upload for 'Trust & Track'
            # Only skip if it's truly broken or empty.
            if universe_map and sym not in universe_map and sym not in universe_map:
                # Check price DB as secondary validation
                cur.execute("SELECT 1 FROM daily_prices WHERE symbol = %s LIMIT 1", (sym,))
                if not cur.fetchone():
                    # GRACE RULE: We'll accept it anyway but it will stay 'Unknown' until background fetch finishes
                    pass

            qty = 0.0
            try: qty = float(row[qty_col]) if qty_col and pd.notna(row[qty_col]) else 0.0
            except: pass
            
            cost = 0.0
            try: cost = float(row[cst_col]) if cst_col and pd.notna(row[cst_col]) else 0.0
            except: pass
            
            processed_holdings.append({"symbol": sym, "quantity": qty, "avg_cost": cost})
            processed_symbols.append(sym)
            cur.execute("""
                INSERT INTO client_external_holdings (client_id, symbol, quantity, avg_cost)
                VALUES (%s::uuid, %s, %s, %s)
                ON CONFLICT (client_id, symbol) 
                DO UPDATE SET quantity = EXCLUDED.quantity, avg_cost = EXCLUDED.avg_cost, updated_at = NOW()
            """, (str(client_id), sym, qty, cost))
        
        conn.commit()
        if skipped_symbols:
            logger.warning(f"Skipped {len(skipped_symbols)} stocks not found in universe: {skipped_symbols[:5]}...")

        cur.close()

        # Trigger on-demand sync
        background_tasks.add_task(
            ingest_missing_symbols_sync, 
            processed_symbols, 
            client_id, 
            client.get("email"), 
            client.get("name")
        )
        
        # Analyze and return instantly
        from engine_core.portfolio_review_engine import analyze_portfolio
        analysis = analyze_portfolio(processed_holdings, conn)
        analysis["storage_ready"] = True
        analysis["digital_twin_saved"] = True
        analysis["digital_twin_row_count"] = len(processed_symbols)
        analysis["skipped_symbols"] = skipped_symbols
        return analysis

    except Exception as e:
        logger.exception(f"UPLOAD ERROR: {repr(e)} ({type(e).__name__})")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save-bulk")
@router.post("/save_bulk")
async def save_holdings_bulk(
    holdings: List[SingleHoldingAddRequest],
    client=Depends(get_current_client),
    conn=Depends(get_db)
):
    cur = conn.cursor()
    try:
        client_id = str(client["id"])
        for h in holdings:
            cur.execute("""
                INSERT INTO client_external_holdings (client_id, symbol, quantity, avg_cost)
                VALUES (%s::uuid, %s, %s, %s)
                ON CONFLICT (client_id, symbol) DO UPDATE SET 
                    quantity = EXCLUDED.quantity, 
                    avg_cost = EXCLUDED.avg_cost,
                    updated_at = NOW()
            """, (client_id, h.symbol.upper().strip(), h.quantity, h.avg_cost))
        conn.commit()
        return {"status": "success", "count": len(holdings)}
    except Exception as e:
        conn.rollback()
        logger.exception(f"UPLOAD ERROR: {repr(e)} ({type(e).__name__})")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()

@router.delete("/holdings/{symbol}")
async def delete_holding(
    symbol: str,
    client=Depends(get_current_client),
    conn=Depends(get_db)
):
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM client_external_holdings WHERE client_id = %s AND symbol = %s", (str(client["id"]), symbol.upper().strip()))
        conn.commit()
        return {"status": "success"}
    finally:
        cur.close()

@router.post("/holdings/delete-all")
async def delete_all_holdings(
    client=Depends(get_current_client),
    conn=Depends(get_db)
):
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM client_external_holdings WHERE client_id = %s", (str(client["id"]),))
        conn.commit()
        return {"status": "success"}
    finally:
        cur.close()

@router.post("/holdings/regrade-sync")
async def regrade_holdings_sync(
    send_email: bool = False,
    client=Depends(get_current_client),
    conn=Depends(get_db)
):
    """Manual trigger to refresh grades for all holdings."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        client_id = str(client["id"])
        cur.execute("SELECT symbol, quantity, avg_cost FROM client_external_holdings WHERE client_id = %s", (str(client_id),))
        holdings = cur.fetchall()
        
        from engine_core.portfolio_review_engine import analyze_portfolio
        results = analyze_portfolio(holdings, conn)
        
        if send_email:
            from engine_core.email_service import send_portfolio_review
            send_portfolio_review(client["email"], client["name"], results)
            
        return results
    finally:
        cur.close()

