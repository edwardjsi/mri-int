import psycopg2
import os
import sys
import pandas as pd
# Path setup so we can import src.db
sys.path.append(os.getcwd())

from src.db import get_connection

def diagnose_volume():
    print("--- 🔍 Initiating Volume Integrity Diagnostic ---")
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            # 1. Overall Null/Zero check
            cur.execute("""
                SELECT 
                    COUNT(*) as total_rows,
                    SUM(CASE WHEN volume IS NULL THEN 1 ELSE 0 END) as null_volume,
                    SUM(CASE WHEN volume = 0 THEN 1 ELSE 0 END) as zero_volume,
                    COUNT(DISTINCT symbol) as unique_symbols
                FROM daily_prices;
            """)
            row = cur.fetchone()
            total, nulls, zeros, symbols = row
            
            print(f"Total Rows Analyzed: {total:,}")
            print(f"Unique Symbols:      {symbols:,}")
            print(f"NULL Volume Rows:    {nulls:,} ({(nulls/total*100):.2f}%)")
            print(f"ZERO Volume Rows:    {zeros:,} ({(zeros/total*100):.2f}%)")
            
            # 2. Recent Volume Check (Last 30 days)
            cur.execute("""
                SELECT 
                    symbol, 
                    MAX(date) as last_date, 
                    AVG(volume) as avg_vol_recent
                FROM daily_prices
                WHERE date > CURRENT_DATE - INTERVAL '30 days'
                GROUP BY symbol
                HAVING AVG(volume) = 0 OR AVG(volume) IS NULL;
            """)
            problematic = cur.fetchall()
            
            if problematic:
                print(f"\n🚩 WARNING: Found {len(problematic)} symbols with ZERO/NULL volume in the last 30 days:")
                for sym, ldt, avg_v in problematic[:10]: # Show top 10
                    print(f"   - {sym:10} | Last Date: {ldt} | Avg Volume: {avg_v}")
                if len(problematic) > 10:
                    print(f"   ... and {len(problematic)-10} more.")
            else:
                print("\n✅ All symbols have active trading volume in the last 30 days.")

            # 3. Index Volume Check
            cur.execute("SELECT symbol, AVG(volume) FROM index_prices GROUP BY symbol;")
            indices = cur.fetchall()
            print("\n--- 〽️ Index Volume Status ---")
            for idx_sym, avg_v in indices:
                status = "✅ Active" if (avg_v or 0) > 0 else "⚠️ No Volume (Common for Indices)"
                print(f"   {idx_sym:10} | Stats: {status}")

    except Exception as e:
        print(f"CRITICAL: Failed to run diagnostic: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    diagnose_volume()
