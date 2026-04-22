#!/usr/bin/env python3
"""Detailed diagnostic for Golden Path scoring."""
import os
import sys
from datetime import datetime

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_core.db import get_connection

def main():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Get latest date
            cur.execute("SELECT MAX(date) FROM stock_scores")
            latest_date = cur.fetchone()["max"]
            print(f"=== Golden Path Debug — {latest_date} ===")

            # 2. Get top 15 stocks and their breakdown
            cur.execute("""
                SELECT symbol, total_score, 
                       condition_ema_50_200, condition_ema_200_slope, 
                       condition_rs, condition_6m_high, condition_volume
                FROM stock_scores
                WHERE date = %s
                ORDER BY total_score DESC, symbol
                LIMIT 15
            """, (latest_date,))
            rows = cur.fetchall()
            
            print("\nTop 15 Stocks Breakdown:")
            print(f"{'Symbol':<12} | {'Score':<5} | {'E_50_200':<8} | {'Slope':<8} | {'RS':<5} | {'High':<5} | {'Vol':<5}")
            print("-" * 70)
            for r in rows:
                print(f"{r['symbol']:<12} | {r['total_score']:<5} | "
                      f"{str(r['condition_ema_50_200']):<8} | {str(r['condition_ema_200_slope']):<8} | "
                      f"{str(r['condition_rs']):<5} | {str(r['condition_6m_high']):<5} | {str(r['condition_volume']):<5}")

            # 3. Check for "The 70-Point Trap"
            cur.execute("""
                SELECT COUNT(*) FROM stock_scores 
                WHERE date = %s AND total_score = 70
            """, (latest_date,))
            trap_count = cur.fetchone()["count"]
            print(f"\nStocks stuck at 70 points: {trap_count}")

            # 4. Global Condition Pass Rates
            print("\nCondition Pass Rates (Latest Date):")
            conditions = [
                "condition_ema_50_200", "condition_ema_200_slope", 
                "condition_rs", "condition_6m_high", "condition_volume"
            ]
            for cond in conditions:
                cur.execute(f"SELECT COUNT(*) FROM stock_scores WHERE date = %s AND {cond} = true", (latest_date,))
                passed = cur.fetchone()["count"]
                cur.execute(f"SELECT COUNT(*) FROM stock_scores WHERE date = %s", (latest_date,))
                total = cur.fetchone()["count"]
                rate = (passed / total * 100) if total > 0 else 0
                print(f"  {cond:<25}: {rate:>5.1f}% ({passed}/{total})")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
