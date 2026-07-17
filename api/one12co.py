"""
112Co Universe API — dedicated endpoints for the 112-company breakout watchlist.
"""
from fastapi import APIRouter, Depends
from api.deps import get_db
import psycopg2.extras
import logging

router = APIRouter(prefix="/api/112co", tags=["112Co Universe"])
log = logging.getLogger(__name__)


@router.get("/breakouts")
def get_112co_breakouts(conn=Depends(get_db)):
    """
    Return breakout radar for 112Co universe only.
    Sorted: BROKEN_OUT first, then READY_TO_BREAKOUT, then CONSOLIDATING.
    Includes all 7 MRI gate conditions from stock_scores.
    """
    query = """
        SELECT
            dp.symbol,
            u.stock_name,
            dp.close,
            dp.volume,
            dp.avg_volume_20d,
            CASE WHEN dp.avg_volume_20d > 0
                 THEN ROUND((dp.volume::numeric / dp.avg_volume_20d), 2)
                 ELSE 0 END AS volume_multiplier,
            dp.rsi_14 AS rsi,
            dp.atr_14 AS atr,
            CASE WHEN dp.close > 0
                 THEN ROUND((dp.atr_14::numeric / dp.close * 100), 2)
                 ELSE 0 END AS atr_pct,
            CASE WHEN dp.rolling_high_6m > 0
                 THEN ROUND(((dp.close::numeric / dp.rolling_high_6m) - 1) * 100, 2)
                 ELSE NULL END AS proximity_to_6m_high,
            COALESCE(dp.breakout_state, 'CONSOLIDATING') AS breakout_state,
            COALESCE(ss.total_score, 0) AS mri_score,
            COALESCE(ss.condition_ema_50_200, FALSE) AS gate_ema_50_200,
            COALESCE(ss.condition_ema_200_slope, FALSE) AS gate_ema_200_slope,
            COALESCE(ss.condition_rs, FALSE) AS gate_rs,
            COALESCE(ss.condition_6m_high, FALSE) AS gate_6m_high,
            COALESCE(ss.condition_volume, FALSE) AS gate_volume,
            COALESCE(ss.condition_breakout_10d, FALSE) AS gate_breakout_10d,
            COALESCE(ss.condition_price_quality, FALSE) AS gate_price_quality,
            dp.condition_breakout_10d,
            dp.ema_50,
            dp.ema_200,
            dp.rs_90d,
            dp.date AS last_date
        FROM universe_112co u
        JOIN daily_prices dp ON dp.symbol = u.symbol
        LEFT JOIN stock_scores ss ON ss.symbol = dp.symbol AND ss.date = dp.date
        WHERE u.is_active = TRUE
          AND dp.date = (SELECT MAX(date) FROM daily_prices)
        ORDER BY
            CASE dp.breakout_state
                WHEN 'BROKEN_OUT' THEN 1
                WHEN 'READY_TO_BREAKOUT' THEN 2
                ELSE 3
            END,
            COALESCE(ss.total_score, 0) DESC,
            dp.symbol
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(query)
        rows = cur.fetchall()
        return rows
    except Exception as e:
        log.error(f"112Co breakouts error: {e}")
        return []
    finally:
        cur.close()


@router.get("/summary")
def get_112co_summary(conn=Depends(get_db)):
    """
    Return summary counts: BROKEN_OUT, READY_TO_BREAKOUT, CONSOLIDATING, missing.
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT
                COALESCE(dp.breakout_state, 'MISSING') AS state,
                COUNT(*) AS count
            FROM universe_112co u
            LEFT JOIN daily_prices dp ON dp.symbol = u.symbol
                AND dp.date = (SELECT MAX(date) FROM daily_prices)
            WHERE u.is_active = TRUE
            GROUP BY COALESCE(dp.breakout_state, 'MISSING')
            ORDER BY state
        """)
        rows = cur.fetchall()
        summary = {r['state']: r['count'] for r in rows}
        cur.execute("SELECT COUNT(*) FROM universe_112co WHERE is_active = TRUE")
        summary['total'] = cur.fetchone()['count']
        return summary
    except Exception as e:
        log.error(f"112Co summary error: {e}")
        return {"error": str(e)}
    finally:
        cur.close()
