import sys
import os
import argparse
from datetime import date

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_core.db import get_connection

def scan_pre_breakout():
    print("Running Pre-Breakout Scanner...")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # First, get the latest date available in daily_prices
            cur.execute("SELECT MAX(date) as max_date FROM daily_prices")
            res = cur.fetchone()
            if not res or not res['max_date']:
                print("No price data found.")
                return
            latest_date = res['max_date']
            print(f"Scanning data for latest date: {latest_date}")

            # Note on SMA(200): The DB currently tracks EMA(200). We substitute SMA(200) with EMA(200) for this scan.
            query = """
                SELECT p.symbol, p.close, p.rolling_high_52w, p.ema_20, p.ema_50, p.ema_200, p.rsi_14, p.avg_volume_20d
                FROM daily_prices p
                WHERE p.date = %s
                  -- 1. Daily Close is greater than 95 percent of Daily Max(252, High)
                  AND p.close > 0.95 * p.rolling_high_52w
                  
                  -- 2. Daily Close is less than Daily Max(252, High)
                  AND p.close < p.rolling_high_52w
                  
                  -- 3. Daily Close is greater than Daily EMA(Close, 20)
                  AND p.close > p.ema_20
                  
                  -- 4. Daily Close is greater than Daily EMA(Close, 50)
                  AND p.close > p.ema_50
                  
                  -- 5. Daily Close is greater than Daily SMA(Close, 200) (Using EMA_200)
                  AND p.close > p.ema_200
                  
                  -- 6. Daily EMA(Close, 20) is greater than Daily EMA(Close, 50)
                  AND p.ema_20 > p.ema_50
                  
                  -- 7. Daily RSI(14) is greater than 55
                  AND p.rsi_14 > 55
                  
                  -- 8. Daily RSI(14) is less than 70
                  AND p.rsi_14 < 70
                  
                  -- 9. Daily SMA(Volume, 20) is greater than 100000
                  AND p.avg_volume_20d > 100000
                  
                  -- 10. Daily Close is less than 108 percent of Daily EMA(Close, 20)
                  AND p.close < 1.08 * p.ema_20
                  
                  -- Do not include stocks that have already made a very large vertical move. 
                  -- (Conditions 8 and 10 handle this primarily)
                ORDER BY p.rsi_14 DESC
            """
            cur.execute(query, (latest_date,))
            results = cur.fetchall()
            
            print("-" * 120)
            print(f"{'SYMBOL':<15} | {'CLOSE':<10} | {'52W HIGH':<10} | {'% OFF HIGH':<12} | {'EMA 20':<10} | {'% FROM 20EMA':<15} | {'RSI 14':<8} | {'VOL (20D)':<12}")
            print("-" * 120)
            
            if not results:
                print("No stocks met all the criteria.")
            else:
                for row in results:
                    sym = row['symbol']
                    close = float(row['close'])
                    high = float(row['rolling_high_52w'])
                    ema20 = float(row['ema_20'])
                    rsi = float(row['rsi_14'])
                    vol = float(row['avg_volume_20d'])
                    
                    pct_off_high = ((high - close) / high) * 100
                    pct_from_ema20 = ((close - ema20) / ema20) * 100
                    
                    print(f"{sym:<15} | {close:<10.2f} | {high:<10.2f} | {pct_off_high:<11.2f}% | {ema20:<10.2f} | {pct_from_ema20:<14.2f}% | {rsi:<8.2f} | {int(vol):<12,}")
                    
            print("-" * 120)
            print(f"Total Pre-Breakout Candidates found: {len(results)}")

    except Exception as e:
        print(f"Error executing scanner: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    scan_pre_breakout()
