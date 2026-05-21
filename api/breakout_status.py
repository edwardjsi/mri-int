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
