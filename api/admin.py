# Updated: 2026-04-24
import logging
import psycopg2.extras
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from api.deps import get_db, get_current_client
from engine_core.indicator_engine import compute_indicators_all

router = APIRouter(prefix="/api/admin", tags=["admin"])

logger = logging.getLogger("mri_api.admin")

class GlobalSymbolAdd(BaseModel):
    symbol: str

class DataHealthResponse(BaseModel):
    total_symbols: int
    null_indicators: int
    suspicious_rs: int
    stale_indicators: int
    coverage_pct: float
    last_price_date: Optional[str]
    last_score_date: Optional[str]
    last_regime_date: Optional[str]
    drift_days: int

def verify_admin(client=Depends(get_current_client), conn=Depends(get_db)):
    """Dependency to check if the current user is an admin."""
    try:
        cur = conn.cursor()
        cur.execute("SELECT is_admin FROM clients WHERE id = %s", (str(client["id"]),))
        record = cur.fetchone()
        cur.close()
        
        is_admin = False
        if record:
            # Tuple-safe check
            is_admin = record[0] if isinstance(record, (list, tuple)) else record.get("is_admin", False)

        if not is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
        return client
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ADMIN VERIFY CRASH: {e}")
        raise HTTPException(status_code=500, detail=f"Admin verification failed: {e}")

@router.get("/strategy-shadow")
def get_strategy_shadow(conn=Depends(get_db), admin=Depends(verify_admin)):
    """Fetch the Strategy Shadow Portfolio performance."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT *,
                   ROUND(((latest_price - entry_price) / entry_price) * 100, 2) as perf_pct
            FROM public.strategy_shadow_portfolio
            ORDER BY is_active DESC, first_entry_date DESC
        """)
        return cur.fetchall()
    except Exception as e:
        logger.error(f"SHADOW STRATEGY ERROR: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        cur.close()

@router.get("/swing-trades")
def get_swing_trades(conn=Depends(get_db), admin=Depends(verify_admin)):
    """Fetch all swing trades across all clients with performance metrics."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT 
                st.*,
                c.name as client_name,
                dp.close as current_price,
                ROUND(((COALESCE(st.exit_price, dp.close) - st.entry_price) / st.entry_price) * 100, 2) as perf_pct,
                ROUND((COALESCE(st.exit_price, dp.close) - st.entry_price) * st.quantity, 2) as pnl_abs
            FROM public.swing_trades st
            JOIN public.clients c ON c.id = st.client_id
            LEFT JOIN (
                SELECT DISTINCT ON (symbol) symbol, close 
                FROM daily_prices ORDER BY symbol, date DESC
            ) dp ON dp.symbol = st.symbol
            ORDER BY st.entry_date DESC, st.symbol ASC
        """)
        return cur.fetchall()
    except Exception as e:
        logger.error(f"SWING TRADES ERROR: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        cur.close()

@router.get("/audit-logs")
def get_audit_logs(limit: int = 50, conn=Depends(get_db), admin=Depends(verify_admin)):
    """Fetch latest system audit logs for compliance monitoring."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT id, timestamp, event_type, severity, message, metadata
            FROM public.system_audit_logs
            ORDER BY timestamp DESC
            LIMIT %s
        """, (limit,))
        return cur.fetchall()
    except Exception as e:
        logger.error(f"AUDIT LOGS ERROR: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        cur.close()

@router.get("/hall-of-fame")
def get_hall_of_fame(conn=Depends(get_db), admin=Depends(verify_admin)):
    """Fetch all-time top performers and their performance from first appearance."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT *,
                   ROUND(((latest_price - entry_price) / entry_price) * 100, 2) as perf_pct
            FROM public.top_score_tracking
            ORDER BY first_appeared_date DESC, symbol ASC
        """)
        return cur.fetchall()
    except Exception as e:
        logger.error(f"HALL OF FAME ERROR: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        cur.close()

@router.get("/daily-leaderboard")
def get_daily_leaderboard(conn=Depends(get_db), admin=Depends(verify_admin)):
    """Fetch the top scoring stocks for the most recent date with component breakdown."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT ss.symbol, ss.total_score, ss.date,
                   ss.condition_ema_50_200, ss.condition_ema_200_slope,
                   ss.condition_6m_high, ss.condition_volume, ss.condition_rs,
                   dp.close, dp.volume
            FROM stock_scores ss
            JOIN daily_prices dp ON dp.symbol = ss.symbol AND dp.date = ss.date
            WHERE ss.date = (SELECT MAX(date) FROM stock_scores)
            ORDER BY ss.total_score DESC, ss.symbol ASC
            LIMIT 20
        """)
        rows = cur.fetchall()
        return {
            "date": str(rows[0]["date"]) if rows else None,
            "top_stocks": [dict(r) for r in rows]
        }
    except Exception as e:
        logger.error(f"LEADERBOARD ERROR: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        cur.close()

@router.get("/metrics")
def get_metrics(conn=Depends(get_db), admin=Depends(verify_admin)):
    """Get 30,000 foot view metrics of the MRI platform."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Optimized single-pass aggregation
        cur.execute("""
            SELECT 
                (SELECT COUNT(*) FROM clients) as total_users,
                (SELECT COUNT(DISTINCT client_id) FROM client_watchlist) as active_watchlists,
                (SELECT COUNT(DISTINCT client_id) FROM client_external_holdings) as active_portfolios,
                (SELECT MAX(date) FROM daily_prices) as last_ingestion
        """)
        row = cur.fetchone()
        return {
            "total_users": row["total_users"],
            "active_watchlists": row["active_watchlists"],
            "active_portfolios": row["active_portfolios"],
            "last_ingestion": str(row["last_ingestion"]) if row["last_ingestion"] else None
        }
    except Exception as e:
        logger.error(f"METRICS ERROR: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Metrics Error: {str(e)}"})
    finally:
        cur.close()

@router.get("/global-universe")
def get_global_universe(conn=Depends(get_db), admin=Depends(verify_admin)):
    """Unified master list of every unique symbol tracked/owned across all users, with latest scores."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Get interest counts and join with latest scores/prices
        cur.execute("""
            WITH watch_counts AS (
                SELECT symbol, COUNT(DISTINCT client_id) as watchers
                FROM client_watchlist GROUP BY symbol
            ),
            hold_counts AS (
                SELECT symbol, COUNT(DISTINCT client_id) as holders
                FROM client_external_holdings GROUP BY symbol
            ),
            interest AS (
                SELECT 
                    COALESCE(w.symbol, h.symbol) as symbol,
                    COALESCE(w.watchers, 0) as watchers,
                    COALESCE(h.holders, 0) as holders,
                    (COALESCE(w.watchers, 0) + COALESCE(h.holders, 0)) as total_interest
                FROM watch_counts w
                FULL OUTER JOIN hold_counts h ON h.symbol = w.symbol
            )
            SELECT 
                i.*,
                ss.total_score as score,
                ss.condition_ema_50_200, ss.condition_ema_200_slope,
                ss.condition_6m_high, ss.condition_volume, ss.condition_rs,
                dp.close as current_price,
                dp.rs_90d,
                (COALESCE(ss.condition_6m_high, FALSE) AND COALESCE(ss.condition_volume, FALSE)) as is_breakout
            FROM interest i
            LEFT JOIN (
                SELECT DISTINCT ON (symbol) 
                    symbol, total_score, date,
                    condition_ema_50_200, condition_ema_200_slope,
                    condition_6m_high, condition_volume, condition_rs
                FROM stock_scores 
                ORDER BY symbol, date DESC
            ) ss ON ss.symbol = i.symbol
            LEFT JOIN (
                SELECT DISTINCT ON (symbol) symbol, close, rs_90d, date
                FROM daily_prices
                ORDER BY symbol, date DESC
            ) dp ON dp.symbol = i.symbol
            ORDER BY i.total_interest DESC, i.symbol ASC
        """)
        return cur.fetchall()
    except Exception as e:
        logger.error(f"GLOBAL UNIVERSE ERROR: {e}")
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        cur.close()

@router.get("/data-health", response_model=DataHealthResponse)
def get_data_health(conn=Depends(get_db), admin=Depends(verify_admin)):
    """Analyze database for NULL indicators and date drift."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            WITH latest_date AS (SELECT MAX(date) FROM daily_prices),
            prev_date AS (SELECT DISTINCT date FROM daily_prices WHERE date < (SELECT MAX(date) FROM daily_prices) ORDER BY date DESC LIMIT 1),
            stats AS (
                SELECT 
                    COUNT(DISTINCT symbol) as total,
                    COUNT(DISTINCT CASE WHEN ema_50 IS NULL THEN symbol END) as nulls,
                    COUNT(DISTINCT CASE WHEN rs_90d = 0 OR rs_90d IS NULL THEN symbol END) as susp_rs
                FROM daily_prices
                WHERE date = (SELECT * FROM latest_date)
            ),
            stale_check AS (
                SELECT COUNT(DISTINCT curr.symbol) as stale
                FROM daily_prices curr
                JOIN daily_prices prev ON curr.symbol = prev.symbol AND prev.date = (SELECT * FROM prev_date)
                WHERE curr.date = (SELECT * FROM latest_date)
                  AND curr.ema_50 = prev.ema_50
                  AND curr.volume > 0 -- Only check if market was actually open for that stock
            ),
            dates AS (
                SELECT 
                    (SELECT * FROM latest_date) as last_p,
                    (SELECT MAX(date) FROM stock_scores) as last_s,
                    (SELECT MAX(date) FROM market_regime) as last_r
            )
            SELECT * FROM stats, dates, stale_check
        """)
        row = cur.fetchone()
        
        total = row["total"] or 0
        nulls = row["nulls"] or 0
        coverage = ((total - nulls) / total * 100) if total > 0 else 0
        
        last_p = row["last_p"]
        last_s = row["last_s"]
        drift = 0
        if last_p and last_s:
            drift = (last_p - last_s).days

        return {
            "total_symbols": total,
            "null_indicators": nulls,
            "suspicious_rs": row["susp_rs"] or 0,
            "stale_indicators": row["stale"] or 0,
            "coverage_pct": round(coverage, 2),
            "last_price_date": str(last_p) if last_p else None,
            "last_score_date": str(last_s) if last_s else None,
            "last_regime_date": str(row["last_r"]) if row["last_r"] else None,
            "drift_days": drift
        }
    except Exception as e:
        logger.error(f"HEALTH ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()

@router.post("/trigger-recovery")
def trigger_recovery(background_tasks: BackgroundTasks, admin=Depends(verify_admin)):
    """Manually trigger a background indicator recompute for NULL values."""
    try:
        background_tasks.add_task(compute_indicators_all)
        return {"message": "Indicator recovery task started in background."}
    except Exception as e:
        logger.error(f"RECOVERY TRIGGER ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/global-universe/add")
def add_global_symbol(payload: GlobalSymbolAdd, conn=Depends(get_db), admin=Depends(verify_admin)):
    """Manually add a symbol to the global tracking universe."""
    symbol = payload.symbol.upper().strip()
    cur = conn.cursor()
    try:
        # We 'track' it by adding it to a system-wide watchlist or simply 
        # ensuring it will be picked up by the next pipeline run.
        # For now, we'll insert it into client_watchlist for a dummy 'system' user (ID 0)
        # or a dedicated 'universe_expansion' table if it exists.
        # Decision: Use client_watchlist with a reserved '00000000-0000-0000-0000-000000000000' ID.
        system_id = '00000000-0000-0000-0000-000000000000'
        cur.execute("""
            INSERT INTO client_watchlist (client_id, symbol)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (system_id, symbol))
        conn.commit()
        return {"message": f"Symbol {symbol} added to global tracking universe."}
    except Exception as e:
        logger.error(f"GLOBAL ADD ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()

@router.post("/symbol/repair")
def repair_symbol(payload: GlobalSymbolAdd, background_tasks: BackgroundTasks, conn=Depends(get_db), admin=Depends(verify_admin)):
    """Nuke and re-ingest a specific symbol. Use when Yahoo data goes 'wack'."""
    symbol = payload.symbol.upper().strip()
    cur = conn.cursor()
    try:
        # 1. Clear existing price/score data for this symbol
        cur.execute("DELETE FROM daily_prices WHERE symbol = %s", (symbol,))
        cur.execute("DELETE FROM stock_scores WHERE symbol = %s", (symbol,))
        conn.commit()
        
        # 2. Trigger background re-ingestion
        # We'll use the on_demand_ingest logic if available, or just rely on next pipeline
        # For now, we'll mark it as needing repair by the indicator engine which will find it missing
        logger.info(f"Surgical repair triggered for {symbol}: Data cleared, awaiting re-ingestion.")
        return {"message": f"Symbol {symbol} data cleared. It will be re-fetched in the next background cycle."}
    except Exception as e:
        logger.error(f"SYMBOL REPAIR ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()

@router.get("/top-stocks")
def get_top_stocks(conn=Depends(get_db), admin=Depends(verify_admin)):
    """Legacy leaderboard for dashboard cards."""
    # ... call the new logic or just use a simpler query
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT symbol, COUNT(*) as count FROM client_watchlist GROUP BY symbol ORDER BY count DESC LIMIT 15")
        top_watched = cur.fetchall()
        cur.execute("SELECT symbol, COUNT(*) as count FROM client_external_holdings GROUP BY symbol ORDER BY count DESC LIMIT 15")
        top_held = cur.fetchall()
        return {"top_watched": top_watched, "top_held": top_held}
    finally:
        cur.close()


@router.get("/clients")
def get_clients(conn=Depends(get_db), admin=Depends(verify_admin)):
    """Fetch list of all clients for admin selection."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT id, email, name, is_active FROM clients ORDER BY name")
        clients = cur.fetchall()
        return [dict(c) for c in clients]
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        cur.close()


@router.get("/clients/{client_id}/portfolio")
def get_client_portfolio(client_id: str, conn=Depends(get_db), admin=Depends(verify_admin)):
    """Fetch specific client's portfolio with MRI grades for admin review."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Get latest score for each symbol in holdings
        cur.execute("""
            SELECT eh.symbol, eh.quantity, eh.avg_cost, ss.total_score, ss.date as last_score_date
            FROM client_external_holdings eh
            LEFT JOIN (
                SELECT symbol, total_score, date FROM stock_scores s1
                WHERE date = (SELECT MAX(date) FROM stock_scores WHERE symbol = s1.symbol)
            ) ss ON ss.symbol = eh.symbol
            WHERE eh.client_id = %s
        """, (client_id,))
        holdings = cur.fetchall()
        return [dict(h) for h in holdings]
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        cur.close()
