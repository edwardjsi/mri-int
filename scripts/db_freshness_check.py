"""
DB Freshness Check: compares MAX(date) across core tables to detect drift.
Run with DATABASE_URL set; exits non-zero if tables differ by more than ALLOWED_DRIFT_DAYS.
"""
import os
import sys
from datetime import datetime
import psycopg2

ALLOWED_DRIFT_DAYS = 2

CHECK_QUERY = """
WITH max_dates AS (
  SELECT MAX(date) AS max_date FROM daily_prices
),
sc AS (
  SELECT MAX(date) AS max_date FROM stock_scores
),
mr AS (
  SELECT MAX(date) AS max_date FROM market_regime
),
idx AS (
  SELECT MAX(date) AS max_date FROM market_index_prices
)
SELECT 'daily_prices' AS table, max_date FROM max_dates
UNION ALL
SELECT 'stock_scores', max_date FROM sc
UNION ALL
SELECT 'market_regime', max_date FROM mr
UNION ALL
SELECT 'market_index_prices', max_date FROM idx;
"""


def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(url, sslmode="require")
    cur = conn.cursor()
    cur.execute(CHECK_QUERY)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    # Compute drift vs most recent date
    max_date = max(r[1] for r in rows if r[1])
    failures = []
    for table, dt in rows:
        if dt is None:
            failures.append(f"{table}: NULL")
            continue
        drift = (max_date - dt).days
        if drift > ALLOWED_DRIFT_DAYS:
            failures.append(f"{table}: {dt} (drift {drift} days)")
        print(f"{table}: {dt} (drift {drift} days)")

    if failures:
        print("❌ Drift detected:", "; ".join(failures), file=sys.stderr)
        sys.exit(2)
    print("✅ Dates within allowed drift.")


if __name__ == "__main__":
    main()
