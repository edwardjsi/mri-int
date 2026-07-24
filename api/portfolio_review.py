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
from engine_fundamental.aae_data_primer import prime_aae_data, prime_aae_data_batch
from engine_guidance.guidance_primer import prime_guidance_data, prime_guidance_data_batch
from engine_core.cai_weekly_chart_engine import generate_weekly_candles
from engine_core.cai_health_engine import compute_position_health
from engine_core.cai_candidate_review import evaluate_candidate
from engine_core.cai_position_review import evaluate_position
from engine_core.cai_committee import generate_committee_report, approve_committee_report
from engine_core.cai_ledger import get_ledger_history, execute_ledger_decisions
from api.schema import ensure_required_tables
from api.deps import get_db, get_current_client
import json

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
        processed_symbols = []
        skipped_symbols = []
        # WISE GUARD: Pre-fetch universe for bulk check
        cur.execute("SELECT symbol FROM market_index_prices")
        rows = cur.fetchall()
        universe_map = set()
        for r in rows:
            if isinstance(r, dict):
                universe_map.add(r.get('symbol'))
            elif len(r) > 0:
                universe_map.add(r[0])
        universe_map.discard(None)

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
        # Trigger AAE fundamental data backfill (quarterly financials + governance)
        background_tasks.add_task(prime_aae_data_batch, processed_symbols)
        # Trigger GuidanceCheck data prime (concalls + guidance extraction)
        background_tasks.add_task(prime_guidance_data_batch, processed_symbols)
        # Trigger GuidanceCheck data prime (concalls + guidance extraction)
        background_tasks.add_task(prime_guidance_data_batch, processed_symbols)
        
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
    background_tasks: BackgroundTasks,
    client=Depends(get_current_client),
    conn=Depends(get_db)
):
    cur = conn.cursor()
    try:
        client_id = str(client["id"])
        symbols_added = []
        for h in holdings:
            sym = h.symbol.upper().strip()
            cur.execute("""
                INSERT INTO client_external_holdings (client_id, symbol, quantity, avg_cost)
                VALUES (%s::uuid, %s, %s, %s)
                ON CONFLICT (client_id, symbol) DO UPDATE SET 
                    quantity = EXCLUDED.quantity, 
                    avg_cost = EXCLUDED.avg_cost,
                    updated_at = NOW()
            """, (client_id, sym, h.quantity, h.avg_cost))
            symbols_added.append(sym)
        conn.commit()
        # Trigger AAE fundamental data backfill (quarterly financials + governance)
        if symbols_added:
            background_tasks.add_task(prime_aae_data_batch, symbols_added)
            background_tasks.add_task(prime_guidance_data_batch, symbols_added)
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
    """Universal CSV ingest -> save holdings -> analyze and return."""
    try:
        client_id = str(client["id"])
        cur_rls = conn.cursor()
        cur_rls.execute("SELECT set_config('app.current_client_id', %s::text, true);", (client_id,))
        cur_rls.close()

        contents = await file.read()
        sep = ','
        try:
            snippet = contents.decode('utf-8', errors='ignore')[:1024]
            dialect = csv.Sniffer().sniff(snippet, delimiters=',;\t|')
            sep = dialect.delimiter
        except Exception:
            pass

        df = None
        for enc in ['utf-8', 'latin-1', 'utf-8-sig']:
            try:
                df = pd.read_csv(io.StringIO(contents.decode(enc, errors='ignore')), sep=sep)
                break
            except Exception:
                continue
        if df is None:
            raise HTTPException(status_code=400, detail="Invalid CSV format.")

        df.columns = [c.lower().strip() for c in df.columns]
        symbol_aliases = ('symbol','ticker','instrument','stock','isin','tradingsymbol','trading symbol','holding','asset','script')
        qty_aliases = ('quantity','shares','qty','qty.','available quantity','vol','volume','current qty','net qty')
        cost_aliases = ('avg_cost','avg cost','cost','avg_buy_price','avg. cost','average price','buy price','average buy price','purchase price','avg price','avg. price')

        sym_col = next((c for c in df.columns if c in symbol_aliases), None)
        qty_col = next((c for c in df.columns if c in qty_aliases), None)
        cst_col = next((c for c in df.columns if c in cost_aliases), None)
        if not sym_col:
            obj_cols = df.select_dtypes(include=['object'])
            sym_col = obj_cols.columns[0] if not obj_cols.empty else None
        if not sym_col:
            raise HTTPException(status_code=400, detail="Could not find a Symbol column.")

        cur = conn.cursor()
        processed_symbols = []
        skipped_symbols = []
        cur.execute("SELECT symbol FROM market_index_prices")
        rows = cur.fetchall()
        universe_map = set()
        for r in rows:
            if isinstance(r, dict):
                universe_map.add(r.get('symbol'))
            elif len(r) > 0:
                universe_map.add(r[0])
        universe_map.discard(None)

        processed_holdings = []
        for _, row in df.iterrows():
            sym = str(row[sym_col]).upper().strip()
            if not sym or sym == 'NAN':
                continue
            if universe_map and sym not in universe_map:
                cur.execute("SELECT 1 FROM daily_prices WHERE symbol = %s LIMIT 1", (sym,))
                if not cur.fetchone():
                    pass
            qty = float(row[qty_col]) if qty_col and pd.notna(row[qty_col]) else 0.0
            cost = float(row[cst_col]) if cst_col and pd.notna(row[cst_col]) else 0.0
            processed_holdings.append({"symbol": sym, "quantity": qty, "avg_cost": cost})
            processed_symbols.append(sym)
            cur.execute(
                """
                INSERT INTO client_external_holdings (client_id, symbol, quantity, avg_cost)
                VALUES (%s::uuid, %s, %s, %s)
                ON CONFLICT (client_id, symbol)
                DO UPDATE SET quantity = EXCLUDED.quantity, avg_cost = EXCLUDED.avg_cost, updated_at = NOW()
                """,
                (client_id, sym, qty, cost),
            )
        conn.commit()
        cur.close()

        background_tasks.add_task(ingest_missing_symbols_sync, processed_symbols, client_id, client.get("email"), client.get("name"))
        # Trigger AAE fundamental data backfill (quarterly financials + governance)
        background_tasks.add_task(prime_aae_data_batch, processed_symbols)
        # Trigger GuidanceCheck data prime (concalls + guidance extraction)
        background_tasks.add_task(prime_guidance_data_batch, processed_symbols)
        # Trigger GuidanceCheck data prime (concalls + guidance extraction)
        background_tasks.add_task(prime_guidance_data_batch, processed_symbols)

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

@router.get("/chart/{symbol}")
async def get_weekly_chart(symbol: str, years: int = 3, client=Depends(get_current_client)):
    """Fetch weekly candlestick data for CAI Review UI charts."""
    candles = generate_weekly_candles(symbol.upper().strip(), years)
    if not candles:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
    return {"symbol": symbol.upper(), "data": candles}

@router.get("/candidate/{symbol}")
async def get_candidate_review(symbol: str, client=Depends(get_current_client)):
    """Evaluate a candidate for the first tranche."""
    res = evaluate_candidate(symbol.upper().strip())
    if res.get("recommendation") == "ERROR":
        raise HTTPException(status_code=400, detail=res.get("reason"))
    return res

@router.get("/position/{position_id}")
async def get_position_review(position_id: str, client=Depends(get_current_client)):
    """Evaluate an existing position for subsequent tranches/exit."""
    res = evaluate_position(position_id, str(client["id"]))
    if res.get("recommendation") == "ERROR":
        raise HTTPException(status_code=400, detail=res.get("reason"))
    return res

class ReviewSubmitRequest(BaseModel):
    position_id: str
    trigger: Optional[str] = None
    weekly_candle: Optional[dict] = None
    swing_low: Optional[dict] = None
    structure_break: Optional[dict] = None
    story_status: Optional[str] = None
    trend_status: Optional[str] = None
    recommendation: str
    notes: Optional[str] = None

@router.post("/reviews")
async def save_position_review(req: ReviewSubmitRequest, client=Depends(get_current_client), conn=Depends(get_db)):
    """Save a CAI Position Review, calculate post-ownership health, and record the decision."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # 1. Verify position belongs to user's portfolio and get symbol
        cur.execute(
            \"\"\"
            SELECT p.id, p.symbol, port.id as portfolio_id 
            FROM cai_position p
            JOIN cai_portfolio port ON p.portfolio_id = port.id
            WHERE p.id = %s AND port.id = %s
            \"\"\",
            (req.position_id, str(client["id"]))
        )
        pos = cur.fetchone()
        if not pos:
            raise HTTPException(status_code=404, detail="Position not found in your portfolio")
            
        # 2. Compute live position health
        health_score = compute_position_health(pos["symbol"])
        
        # 3. Save the review
        review_id = str(uuid.uuid4())
        cur.execute(
            \"\"\"
            INSERT INTO cai_position_review (
                id, position_id, trigger, weekly_candle, swing_low, 
                structure_break, story_status, trend_status, position_health, 
                recommendation, notes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, review_date
            \"\"\",
            (
                review_id, req.position_id, req.trigger, 
                json.dumps(req.weekly_candle) if req.weekly_candle else None,
                json.dumps(req.swing_low) if req.swing_low else None,
                json.dumps(req.structure_break) if req.structure_break else None,
                req.story_status, req.trend_status, health_score,
                req.recommendation, req.notes
            )
        )
        new_review = cur.fetchone()
        
        # 4. Update the position status/health if needed
        if req.recommendation.upper() == 'EXIT':
            cur.execute("UPDATE cai_position SET status = 'CLOSED' WHERE id = %s", (req.position_id,))
            
        conn.commit()
        return {
            "status": "success",
            "review_id": new_review["id"],
            "review_date": new_review["review_date"],
            "health_score": health_score
        }
        
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to save review: {e}")
        raise HTTPException(status_code=500, detail="Failed to save review")
    finally:
        cur.close()

@router.post("/committee/generate")
async def generate_committee(client=Depends(get_current_client)):
    """Generate a weekly committee report for the portfolio."""
    res = generate_committee_report(str(client["id"]))
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@router.post("/committee/approve/{report_id}")
async def approve_committee(report_id: str, client=Depends(get_current_client)):
    """Approve a committee report and push decisions to the ledger."""
    res = approve_committee_report(report_id)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@router.get("/ledger")
async def get_ledger(client=Depends(get_current_client)):
    """Get the immutable decision ledger."""
    return get_ledger_history(str(client["id"]))

@router.post("/ledger/execute")
async def execute_ledger(client=Depends(get_current_client)):
    """Execute pending ledger decisions."""
    res = execute_ledger_decisions()
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res
