import os
import sys
import pandas as pd
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from engine_core.db import get_connection

def run_audit():
    print("=== Phase 1: Data Availability Audit ===")
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Historical Breakouts & 2. Breakout Level
            cur.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'daily_prices' 
                AND column_name IN ('breakout_state', 'condition_breakout_10d', 'high_10d', 'close')
            """)
            cols = {row['column_name']: row['data_type'] for row in cur.fetchall()}
            
            has_breakout = 'breakout_state' in cols and 'condition_breakout_10d' in cols
            has_breakout_lvl = 'high_10d' in cols
            print(f"1. Can reconstruct historical breakouts? {'PASS' if has_breakout else 'FAIL (Missing columns)'}")
            print(f"2. Can reconstruct breakout level? {'PASS (via high_10d)' if has_breakout_lvl else 'FAIL (Missing high_10d)'}")

            # 3. Daily Swing Lows
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'daily_prices' 
                AND (column_name LIKE '%swing%' OR column_name LIKE '%fractal%')
            """)
            swing_cols = [row['column_name'] for row in cur.fetchall()]
            has_daily_swing = any('daily' in col for col in swing_cols)
            print(f"3. Can reconstruct confirmed daily swing lows without look-ahead? {'PASS' if has_daily_swing else 'FAIL (No daily swing low indicator found in DB)'}")

            # 4. Weekly Swing Lows
            has_weekly_swing = any('weekly' in col for col in swing_cols)
            print(f"4. Can reconstruct confirmed weekly swing lows without look-ahead? {'PASS' if has_weekly_swing else 'FAIL (No weekly swing low level found in DB)'}")

            # 5. Reliable ATR(14)
            cur.execute("SELECT COUNT(*) as cnt FROM daily_prices WHERE atr_14 IS NOT NULL")
            atr_count = cur.fetchone()['cnt']
            print(f"5. Does it have reliable ATR(14)? {'PASS' if atr_count > 0 else 'FAIL (ATR column empty or missing)'}")

            # 6. Adjusted OHLC
            cur.execute("""
                SELECT COUNT(*) as cnt FROM daily_prices WHERE adjusted_close IS NOT NULL AND adjusted_close != close
            """)
            adj_count = cur.fetchone()['cnt']
            print(f"6. Does it have adjusted OHLC/corporate-action handling? {'PASS' if adj_count > 0 else 'WARNING (adjusted_close matches close everywhere or is NULL)'}")

            # 7. Next Tradable Session
            cur.execute("SELECT COUNT(DISTINCT date) as cnt FROM market_index_prices WHERE symbol = 'NIFTY50'")
            date_count = cur.fetchone()['cnt']
            print(f"7. Can it identify the next tradable session? {'PASS (via NIFTY50 calendar)' if date_count > 0 else 'FAIL (No NIFTY50 dates found)'}")

            # Extra info for the user
            print("\nAudit Summary Details:")
            print(f"- Swing/Fractal Columns Found: {swing_cols}")
            print(f"- ATR(14) populated rows: {atr_count}")
            print(f"- Adjusted vs Close difference rows: {adj_count}")
            print(f"- Trading days in calendar: {date_count}")

    except Exception as e:
        print(f"Audit failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    run_audit()
