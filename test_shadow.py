from engine_core.db import get_connection
import traceback

try:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
            SELECT s.symbol, s.total_score, s.date,
                   s.condition_ema_50_200, s.condition_ema_200_slope,
                   s.condition_6m_high, s.condition_volume, s.condition_rs,
                   s.condition_breakout_10d, s.condition_price_quality,
                   dp.close, dp.breakout_state, dp.breakout_age
            FROM public.stock_scores s
            LEFT JOIN public.daily_prices dp
              ON dp.symbol = s.symbol AND dp.date = s.date
            WHERE s.date = (SELECT MAX(date) FROM public.stock_scores)
            ORDER BY s.total_score DESC, (s.condition_6m_high AND s.condition_volume) DESC, s.symbol ASC
            LIMIT 1
    """)
    print("Success")
except Exception as e:
    traceback.print_exc()
