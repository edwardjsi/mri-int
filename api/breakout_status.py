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
    Logic mirrors the existing breakout UI:
      • READY_TO_BREAKOUT – all five breakout conditions are true.
      • BROKEN_OUT      – the symbol is already flagged as a breakout candidate.
      • CONSOLIDATING   – none of the above.
    """
    query = """
        SELECT
            cw.symbol,
            CASE
                WHEN ss.condition_ema_50_200
                 AND ss.condition_ema_200_slope
                 AND ss.condition_6m_high
                 AND ss.condition_volume
                 AND ss.condition_rs
                THEN 'READY_TO_BREAKOUT'
                WHEN cw.breakout_candidate THEN 'BROKEN_OUT'
                ELSE 'CONSOLIDATING'
            END AS state
        FROM client_watchlist cw
        LEFT JOIN (
            SELECT DISTINCT ON (symbol)
                symbol,
                condition_ema_50_200,
                condition_ema_200_slope,
                condition_6m_high,
                condition_volume,
                condition_rs
            FROM stock_scores
            ORDER BY symbol, date DESC
        ) ss ON ss.symbol = cw.symbol;
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
    Return all stocks that are in ANY user's watchlist or portfolio
    and are currently flagged as READY_TO_BREAKOUT or BROKEN_OUT.
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
          AND (
              EXISTS (SELECT 1 FROM client_watchlist WHERE symbol = dp.symbol)
              OR 
              EXISTS (SELECT 1 FROM client_portfolio WHERE symbol = dp.symbol AND is_open = true)
          )
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
