from fastapi import APIRouter, Depends
from api.deps import get_db
import psycopg2.extras
import logging

router = APIRouter(prefix="/api/breakout", tags=["Breakout Status"])
log = logging.getLogger(__name__)

@router.get("/map")
def get_breakout_map(conn=Depends(get_db)):
    """
    Return a dict {symbol: "READY_TO_BREAKOUT" | "BROKEN_OUT" | "CONSOLIDATING"}.
    Pulls directly from the engine-calculated `breakout_state` column in the daily_prices table.
    """
    query = """
        SELECT
            cw.symbol,
            COALESCE(dp.breakout_state, 'CONSOLIDATING') AS state
        FROM client_watchlist cw
        LEFT JOIN (
            SELECT DISTINCT ON (symbol)
                symbol,
                breakout_state
            FROM daily_prices
            ORDER BY symbol, date DESC
        ) dp ON dp.symbol = cw.symbol;
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(query)
        rows = cur.fetchall()
        return {r["symbol"]: r["state"] for r in rows}
    except Exception as e:
        log.error(f"Breakout map error: {e}")
        return {}
    finally:
        cur.close()

@router.get("/radar")
def get_breakout_radar(conn=Depends(get_db)):
    """
    Return all stocks in the full universe that are currently
    flagged as READY_TO_BREAKOUT or BROKEN_OUT, regardless of watchlist.
    """
    query = """
        SELECT 
            dp.symbol, 
            dp.close, 
            dp.volume, 
            dp.ema_50, 
            dp.ema_200, 
            dp.breakout_state,
            (SELECT COUNT(DISTINCT client_id) FROM client_watchlist WHERE symbol = dp.symbol) as watchers,
            (SELECT COUNT(DISTINCT client_id) FROM client_portfolio WHERE symbol = dp.symbol AND is_open = true) as holders
        FROM daily_prices dp
        WHERE dp.date = (SELECT MAX(date) FROM daily_prices)
          AND dp.breakout_state IN ('READY_TO_BREAKOUT', 'BROKEN_OUT')
        ORDER BY dp.breakout_state, dp.symbol;
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(query)
        rows = cur.fetchall()
        return rows
    except Exception as e:
        log.error(f"Breakout radar error: {e}")
        return []
    finally:
        cur.close()
