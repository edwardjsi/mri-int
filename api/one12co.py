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
    Sorted: BROKEN_OUT first, then READY_TO_BREAKOUT, then CONSOLIDATING, then MISSING.
    LEFT JOIN ensures stocks without Yahoo data still appear.
    Includes all 7 MRI gate conditions from stock_scores.
    """
    query = """
        SELECT
            COALESCE(dp.symbol, u.symbol) AS symbol,
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
            COALESCE(dp.breakout_state, 'MISSING') AS breakout_state,
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
        LEFT JOIN daily_prices dp ON dp.symbol = u.symbol
            AND dp.date = (SELECT MAX(date) FROM daily_prices)
        LEFT JOIN stock_scores ss ON ss.symbol = dp.symbol AND ss.date = dp.date
        WHERE u.is_active = TRUE
        ORDER BY
            CASE COALESCE(dp.breakout_state, 'MISSING')
                WHEN 'BROKEN_OUT' THEN 1
                WHEN 'READY_TO_BREAKOUT' THEN 2
                WHEN 'CONSOLIDATING' THEN 3
                ELSE 4
            END,
            COALESCE(ss.total_score, 0) DESC,
            u.symbol
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


@router.post("/add")
def add_112co_symbol(symbol: str, conn=Depends(get_db)):
    """Add a symbol to the 112Co universe."""
    sym = symbol.upper().strip()
    cur = conn.cursor()
    try:
        cur.execute("SELECT is_active FROM universe_112co WHERE symbol = %s", (sym,))
        row = cur.fetchone()
        if row:
            if row['is_active']:
                return {"status": "already_present", "symbol": sym}
            cur.execute("UPDATE universe_112co SET is_active = TRUE WHERE symbol = %s", (sym,))
            conn.commit()
            return {"status": "reactivated", "symbol": sym}
        cur.execute("INSERT INTO universe_112co (symbol, is_active) VALUES (%s, TRUE) ON CONFLICT DO NOTHING", (sym,))
        conn.commit()
        cur.execute("SELECT COUNT(*) AS c FROM daily_prices WHERE symbol = %s", (sym,))
        has_data = cur.fetchone()['c'] > 0
        if not has_data:
            try:
                from engine_core.ingestion_engine import load_stocks
                load_stocks([sym])
                cur.execute("SELECT COUNT(*) AS c FROM daily_prices WHERE symbol = %s", (sym,))
                has_data = cur.fetchone()['c'] > 0
            except Exception:
                pass
        status = "added_with_data" if has_data else "added_no_data"
        return {"status": status, "symbol": sym, "has_data": has_data}
    except Exception as e:
        log.error(f"112Co add error: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        cur.close()


@router.post("/remove")
def remove_112co_symbol(symbol: str, conn=Depends(get_db)):
    sym = symbol.upper().strip()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE universe_112co SET is_active = FALSE WHERE symbol = %s", (sym,))
        conn.commit()
        return {"status": "removed", "symbol": sym}
    except Exception as e:
        log.error(f"112Co remove error: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        cur.close()


@router.get("/search")
def search_112co_symbols(q: str = "", limit: int = 20, conn=Depends(get_db)):
    if not q or len(q.strip()) < 2:
        return []
    query = q.strip().upper()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        sql = """
            SELECT DISTINCT dp.symbol, NULL AS stock_name,
                   EXISTS (SELECT 1 FROM universe_112co u WHERE u.symbol = dp.symbol AND u.is_active = TRUE) AS in_universe
            FROM daily_prices dp
            WHERE dp.symbol ILIKE %s
            LIMIT %s
        """
        cur.execute(sql, (f'%{query}%', limit))
        results = cur.fetchall()
        if len(results) < limit:
            sql2 = """
                SELECT symbol, stock_name, TRUE AS in_universe
                FROM universe_112co
                WHERE stock_name ILIKE %s AND is_active = TRUE
                LIMIT %s
            """
            cur.execute(sql2, (f'%{query}%', limit - len(results)))
            existing = {r['symbol'] for r in results}
            for r in cur.fetchall():
                if r['symbol'] not in existing:
                    results.append(r)
        return results
    except Exception as e:
        log.error(f"112Co search error: {e}")
        return []
    finally:
        cur.close()
