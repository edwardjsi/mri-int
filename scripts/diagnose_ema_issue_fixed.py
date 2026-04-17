#!/usr/bin/env python3
"""
Diagnostic script for EMA-50 NULL indicator issue - FIXED VERSION
Usage: python scripts/diagnose_ema_issue_fixed.py
Requires: DATABASE_URL environment variable
"""
import os
import sys
import psycopg2
import pandas as pd
from datetime import datetime, timedelta
import traceback

def get_connection():
    """Get database connection from DATABASE_URL - FIXED SSL ISSUE"""
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL environment variable not set")
        print("Set it with: export DATABASE_URL='postgresql://...'")
        sys.exit(1)
    
    try:
        # FIX: Use 'prefer' instead of 'require' for SSL
        # This will use SSL if available, but won't fail if not
        conn = psycopg2.connect(url, sslmode="prefer")
        return conn
    except Exception as e:
        print(f"ERROR: Could not connect to database: {e}")
        print("\nTrying without SSL...")
        try:
            # Try without SSL
            conn = psycopg2.connect(url)
            return conn
        except Exception as e2:
            print(f"ERROR: Connection failed even without SSL: {e2}")
            sys.exit(1)

def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def check_ema_null_issue():
    """Check the scope of EMA-50 NULL indicator problem"""
    conn = get_connection()
    
    print_header("EMA-50 NULL INDICATOR DIAGNOSTIC REPORT")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    try:
        with conn.cursor() as cur:
            # 1. Get latest date in database
            cur.execute("SELECT MAX(date) FROM daily_prices")
            latest_date = cur.fetchone()[0]
            print(f"1. Latest date in daily_prices: {latest_date}")
            
            if not latest_date:
                print("ERROR: No data found in daily_prices table")
                return
            
            # 2. Count total symbols with data on latest date
            cur.execute("""
                SELECT COUNT(DISTINCT symbol) 
                FROM daily_prices 
                WHERE date = %s
            """, (latest_date,))
            total_symbols = cur.fetchone()[0]
            print(f"2. Total symbols with data on {latest_date}: {total_symbols}")
            
            # 3. Count symbols with NULL EMA-50 on latest date
            cur.execute("""
                SELECT COUNT(DISTINCT symbol) 
                FROM daily_prices 
                WHERE date = %s AND ema_50 IS NULL
            """, (latest_date,))
            null_ema_symbols = cur.fetchone()[0]
            print(f"3. Symbols with NULL EMA-50 on {latest_date}: {null_ema_symbols}")
            
            # 4. Calculate percentage
            if total_symbols > 0:
                percentage = (null_ema_symbols / total_symbols) * 100
                print(f"4. Percentage with NULL EMA-50: {percentage:.1f}%")
                
                if percentage > 50:
                    print("   ⚠️  CRITICAL: More than 50% symbols have NULL EMA-50")
                elif percentage > 20:
                    print("   ⚠️  WARNING: More than 20% symbols have NULL EMA-50")
                else:
                    print("   ✅ ACCEPTABLE: NULL EMA-50 rate within limits")
            
            # 5. Check if indicators columns exist
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'daily_prices' 
                AND column_name IN ('ema_50', 'ema_200', 'rs_90d', 'avg_volume_20d', 'rolling_high_6m')
            """)
            indicator_columns = [row[0] for row in cur.fetchall()]
            print(f"5. Indicator columns found: {indicator_columns}")
            
            missing_columns = {'ema_50', 'ema_200', 'rs_90d', 'avg_volume_20d', 'rolling_high_6m'} - set(indicator_columns)
            if missing_columns:
                print(f"   ❌ MISSING COLUMNS: {missing_columns}")
            
            # 6. Check data completeness for a sample of symbols
            print_header("DATA COMPLETENESS CHECK")
            print("Sample of 10 symbols with NULL EMA-50:")
            cur.execute("""
                SELECT symbol, COUNT(*) as rows, MIN(date), MAX(date)
                FROM daily_prices 
                WHERE symbol IN (
                    SELECT DISTINCT symbol 
                    FROM daily_prices 
                    WHERE date = %s AND ema_50 IS NULL 
                    LIMIT 10
                )
                GROUP BY symbol
                ORDER BY rows
            """, (latest_date,))
            
            sample_symbols = []
            for symbol, rows, min_date, max_date in cur.fetchall():
                print(f"   - {symbol}: {rows} rows, {min_date} to {max_date}")
                sample_symbols.append(symbol)
            
            # 7. Check when indicators were last updated
            print_header("INDICATOR UPDATE HISTORY")
            cur.execute("""
                SELECT MAX(date) as last_updated
                FROM daily_prices 
                WHERE ema_50 IS NOT NULL
            """)
            last_updated = cur.fetchone()[0]
            print(f"Last date with non-NULL EMA-50: {last_updated}")
            
            if last_updated and latest_date:
                days_since_update = (latest_date - last_updated).days
                print(f"Days since last EMA-50 update: {days_since_update}")
                
                if days_since_update > 7:
                    print("   ⚠️  WARNING: Indicators haven't been updated in over a week")
            
            # 8. Check indicator engine's detection query
            print_header("INDICATOR ENGINE DETECTION LOGIC TEST")
            cur.execute("""
                SELECT COUNT(DISTINCT symbol) as detected_count
                FROM daily_prices
                WHERE date >= %s - INTERVAL '30 days'
                  AND (ema_50 IS NULL OR ema_200 IS NULL OR rs_90d IS NULL
                       OR avg_volume_20d IS NULL OR rolling_high_6m IS NULL)
            """, (latest_date,))
            detected_count = cur.fetchone()[0]
            print(f"Symbols detected by current logic: {detected_count}")
            
            # 9. Check if symbols have sufficient data for EMA calculation
            print_header("DATA SUFFICIENCY CHECK")
            if sample_symbols:
                cur.execute("""
                    SELECT symbol, COUNT(*) as rows
                    FROM daily_prices 
                    WHERE symbol = ANY(%s)
                    GROUP BY symbol
                    HAVING COUNT(*) < 50
                    ORDER BY rows
                """, (sample_symbols,))
                
                insufficient_data = cur.fetchall()
                if insufficient_data:
                    print("Symbols with insufficient data for EMA-50 (< 50 rows):")
                    for symbol, rows in insufficient_data:
                        print(f"   - {symbol}: {rows} rows (needs 50 for EMA-50)")
                else:
                    print("✅ All sample symbols have sufficient data for EMA-50")
            
            # 10. Check scoring engine output
            print_header("SCORING ENGINE STATUS")
            cur.execute("SELECT MAX(date) FROM stock_scores")
            latest_score_date = cur.fetchone()[0]
            print(f"Latest score date: {latest_score_date}")
            
            if latest_score_date:
                cur.execute("SELECT COUNT(DISTINCT symbol) FROM stock_scores WHERE date = %s", (latest_score_date,))
                scored_symbols = cur.fetchone()[0]
                print(f"Symbols with scores on latest date: {scored_symbols}")
            
    except Exception as e:
        print(f"ERROR during diagnosis: {e}")
        traceback.print_exc()
    finally:
        conn.close()
    
    print_header("RECOMMENDED ACTIONS")
    
    if null_ema_symbols > 0:
        print(f"1. Run forced indicator recompute for {null_ema_symbols} symbols")
        print("2. Check indicator engine logic in `engine_core/indicator_engine.py`")
        print("3. Verify database connection and permissions")
        print("4. Run: python scripts/recover_null_indicators.py")
    else:
        print("✅ No EMA-50 NULL issues detected!")
    
    print("\n" + "=" * 80)
    print("Next steps:")
    print("1. Review this diagnostic report")
    print("2. Fix indicator engine logic")
    print("3. Run recovery script")
    print("4. Re-run diagnostic to verify fix")

if __name__ == "__main__":
    check_ema_null_issue()
