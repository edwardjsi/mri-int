from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import logging
import psycopg2.extras
from api.deps import get_db, get_current_client

router = APIRouter(prefix="/api/admin", tags=["admin"])

logger = logging.getLogger("mri_api.admin")

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
                (ss.condition_6m_high AND ss.condition_volume) as is_breakout
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
                SELECT DISTINCT ON (symbol) symbol, close, date
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
