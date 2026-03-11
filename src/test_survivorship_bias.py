"""
TEST-01: Survivorship Bias Check
=================================
Counts distinct symbols per year in daily_prices.

PASS: Count varies across years (universe grew over time)
FAIL: Count is flat every year → dataset is survivorship-biased

Run from project root:
    source venv/bin/activate
    python3 src/test_survivorship_bias.py
"""
import sys
import os
# Load .env before importing src.db so DATABASE_URL is set correctly
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from src.db import get_connection

def run():
    print("\n" + "=" * 55)
    print("TEST-01: Survivorship Bias Check")
    print("=" * 55)

    conn = get_connection()
    cur = conn.cursor()

    # Annual distinct symbol count
    cur.execute("""
        SELECT EXTRACT(YEAR FROM date)::int AS year,
               COUNT(DISTINCT symbol)       AS distinct_symbols,
               COUNT(*)                     AS total_rows,
               MIN(date)                    AS first_date,
               MAX(date)                    AS last_date
        FROM daily_prices
        GROUP BY year
        ORDER BY year
    """)
    rows = cur.fetchall()

    print(f"\n{'Year':<6} {'Symbols':>8} {'Rows':>10}  Date Range")
    print("-" * 55)
    counts = []
    for year, sym_count, row_count, first, last in rows:
        print(f"{year:<6} {sym_count:>8,} {row_count:>10,}  {first} → {last}")
        counts.append(sym_count)

    # Diagnosis
    min_c, max_c = min(counts), max(counts)
    variation = max_c - min_c
    pct_variation = (variation / min_c) * 100 if min_c > 0 else 0

    print("\n" + "=" * 55)
    print("DIAGNOSIS")
    print("-" * 55)
    print(f"Min symbols in any year : {min_c:,}")
    print(f"Max symbols in any year : {max_c:,}")
    print(f"Variation               : {variation:,} symbols ({pct_variation:.1f}%)")

    if pct_variation > 20:
        print("\n✅ PASS — Universe varies significantly across years.")
        print("   This suggests historical constituents (including")
        print("   delisted stocks) are present in the dataset.")
    elif pct_variation > 5:
        print("\n⚠️  PARTIAL — Some variation found, but relatively small.")
        print("   Verify that delisted stocks from 2005-2015 are included.")
    else:
        print("\n❌ FAIL — Symbol count is nearly flat across years.")
        print("   Dataset likely contains only current Nifty500 members.")
        print("   All backtested CAGR numbers may be inflated by survivorship bias.")
        print("   Fix: ingest NSE CM bhavcopy master files including delisted symbols.")

    # Check if any data pre-2010
    cur.execute("SELECT MIN(date) FROM daily_prices")
    earliest = cur.fetchone()[0]
    print(f"\nEarliest data point     : {earliest}")
    if earliest and earliest.year <= 2005:
        print("✅ Data goes back to 2005 — full backtest window covered.")
    elif earliest and earliest.year <= 2007:
        print("⚠️  Data starts in 2006-2007 — 2005 coverage may be incomplete.")
    else:
        print("❌ Data does not cover 2005 — backtest window is shorter than claimed.")

    # Top 10 most represented symbols (sanity check)
    cur.execute("""
        SELECT symbol, COUNT(*) AS days
        FROM daily_prices
        GROUP BY symbol
        ORDER BY days DESC
        LIMIT 10
    """)
    top_symbols = cur.fetchall()
    print("\nTop 10 symbols by history length (should be large caps):")
    for sym, days in top_symbols:
        years = days / 252
        print(f"  {sym:<15} {days:>5,} trading days (~{years:.1f} yrs)")

    cur.close()
    conn.close()
    print("\n" + "=" * 55 + "\n")

if __name__ == "__main__":
    run()
