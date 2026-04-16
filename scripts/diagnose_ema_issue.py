#!/usr/bin/env python3
"""
Diagnostic script for the EMA-50 NULL indicator issue.

Usage:
  python scripts/diagnose_ema_issue.py [--threshold=20] [--sample-size=10]
                                      [--lookback-days=30]

Requires:
  DATABASE_URL environment variable
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

import psycopg2


INDICATOR_COLUMNS = (
    "ema_50",
    "ema_200",
    "rs_90d",
    "avg_volume_20d",
    "rolling_high_6m",
)


def get_connection():
    """Get a PostgreSQL connection from DATABASE_URL with SSL fallback."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL environment variable not set")
        print("Set it with: export DATABASE_URL='postgresql://...'")
        sys.exit(1)

    last_error = None
    for sslmode in ("prefer", None):
        try:
            if sslmode:
                return psycopg2.connect(url, sslmode=sslmode)
            return psycopg2.connect(url)
        except Exception as exc:
            last_error = exc

    print(f"ERROR: Could not connect to database: {last_error}")
    sys.exit(1)


def print_header(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def fetch_one(cur, query, params=None):
    cur.execute(query, params or ())
    return cur.fetchone()


def fetch_all(cur, query, params=None):
    cur.execute(query, params or ())
    return cur.fetchall()


def build_report(cur, threshold: float, sample_size: int, lookback_days: int):
    """Collect a structured snapshot of the indicator state."""
    report = {
        "threshold": threshold,
        "sample_size": sample_size,
        "lookback_days": lookback_days,
        "latest_date": None,
        "total_symbols": 0,
        "null_ema_50": 0,
        "null_rates": {},
        "indicator_columns": [],
        "sample_symbols": [],
        "insufficient_history": [],
        "detected_symbols": 0,
        "last_non_null_ema_50": None,
        "days_since_last_update": None,
    }

    latest_date = fetch_one(cur, "SELECT MAX(date) FROM daily_prices")[0]
    report["latest_date"] = latest_date
    if not latest_date:
        return report

    total_symbols = fetch_one(
        cur,
        """
        SELECT COUNT(DISTINCT symbol)
        FROM daily_prices
        WHERE date = %s
        """,
        (latest_date,),
    )[0]
    report["total_symbols"] = total_symbols or 0

    for column in INDICATOR_COLUMNS:
        count = fetch_one(
            cur,
            f"""
            SELECT COUNT(DISTINCT symbol)
            FROM daily_prices
            WHERE date = %s AND {column} IS NULL
            """,
            (latest_date,),
        )[0]
        report["null_rates"][column] = count or 0

    report["null_ema_50"] = report["null_rates"].get("ema_50", 0)

    indicator_columns = fetch_all(
        cur,
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'daily_prices'
          AND column_name = ANY(%s)
        ORDER BY column_name
        """,
        (list(INDICATOR_COLUMNS),),
    )
    report["indicator_columns"] = [row[0] for row in indicator_columns]

    sample_rows = fetch_all(
        cur,
        """
        SELECT symbol, COUNT(*) AS rows, MIN(date) AS first_date, MAX(date) AS last_date
        FROM daily_prices
        WHERE symbol IN (
            SELECT DISTINCT symbol
            FROM daily_prices
            WHERE date = %s AND ema_50 IS NULL
            ORDER BY symbol
            LIMIT %s
        )
        GROUP BY symbol
        ORDER BY rows DESC, symbol
        """,
        (latest_date, sample_size),
    )
    report["sample_symbols"] = sample_rows

    report["insufficient_history"] = fetch_all(
        cur,
        """
        SELECT symbol, COUNT(*) AS rows
        FROM daily_prices
        GROUP BY symbol
        HAVING COUNT(*) < 50
        ORDER BY rows, symbol
        LIMIT %s
        """,
        (sample_size,),
    )

    report["detected_symbols"] = fetch_one(
        cur,
        """
        SELECT COUNT(DISTINCT symbol)
        FROM daily_prices
        WHERE date >= %s - (%s * INTERVAL '1 day')
          AND (
              ema_50 IS NULL OR ema_200 IS NULL OR rs_90d IS NULL
              OR avg_volume_20d IS NULL OR rolling_high_6m IS NULL
          )
        """,
        (latest_date, lookback_days),
    )[0] or 0

    last_non_null = fetch_one(
        cur,
        """
        SELECT MAX(date)
        FROM daily_prices
        WHERE ema_50 IS NOT NULL
        """,
    )[0]
    report["last_non_null_ema_50"] = last_non_null

    if latest_date and last_non_null:
        report["days_since_last_update"] = (latest_date - last_non_null).days

    return report


def print_report(report):
    """Render the diagnostic report to stdout."""
    print_header("EMA-50 NULL INDICATOR DIAGNOSTIC REPORT")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    latest_date = report["latest_date"]
    if not latest_date:
        print("\nNo rows found in daily_prices.")
        return 1

    total_symbols = report["total_symbols"]
    null_ema_50 = report["null_ema_50"]
    null_rate = (null_ema_50 / total_symbols * 100) if total_symbols else 100.0

    print(f"1. Latest date in daily_prices: {latest_date}")
    print(f"2. Total symbols with data on {latest_date}: {total_symbols}")
    print(f"3. Symbols with NULL EMA-50 on {latest_date}: {null_ema_50}")
    print(f"4. NULL EMA-50 rate: {null_rate:.1f}%")
    if null_rate > report["threshold"]:
        print(
            f"   CRITICAL: NULL rate exceeds threshold of {report['threshold']:.1f}%"
        )
    else:
        print(
            f"   OK: NULL rate is within the threshold of {report['threshold']:.1f}%"
        )

    print(
        f"5. Indicator columns found: {report['indicator_columns']}"
    )
    missing_columns = set(INDICATOR_COLUMNS) - set(report["indicator_columns"])
    if missing_columns:
        print(f"   MISSING COLUMNS: {sorted(missing_columns)}")

    print("\n6. NULL counts for other indicators:")
    for column in INDICATOR_COLUMNS:
        if column == "ema_50":
            continue
        print(f"   - {column}: {report['null_rates'].get(column, 0)}")

    print("\n7. Sample symbols with NULL EMA-50:")
    if report["sample_symbols"]:
        for symbol, rows, first_date, last_date in report["sample_symbols"]:
            print(f"   - {symbol}: {rows} rows, {first_date} to {last_date}")
    else:
        print("   - none")

    print("\n8. Symbols with insufficient history (< 50 rows):")
    if report["insufficient_history"]:
        for symbol, rows in report["insufficient_history"]:
            print(f"   - {symbol}: {rows} rows")
    else:
        print("   - none in the sampled set")

    print("\n9. Indicator update history:")
    print(f"   Last date with non-NULL EMA-50: {report['last_non_null_ema_50']}")
    if report["days_since_last_update"] is not None:
        print(
            f"   Days since last EMA-50 update: {report['days_since_last_update']}"
        )

    print("\n10. Current detection logic check:")
    print(
        f"   Symbols detected by the current 30-day NULL scan: {report['detected_symbols']}"
    )

    print_header("RECOMMENDED ACTIONS")
    if null_rate > report["threshold"]:
        print("1. Run the recovery script for the affected symbols.")
        print("2. Verify the active engine is `engine_core/indicator_engine.py`.")
        print("3. Confirm the pipeline is using write-verify-read validation.")
        print("4. Re-run this diagnostic after the fix.")
        return 2

    print("✅ No critical EMA-50 NULL issue detected.")
    print("1. Keep the validation checks in the daily pipeline.")
    print("2. Review the sample symbols if scores still look stale.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Diagnose NULL EMA-50 indicators in daily_prices"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=20.0,
        help="Critical NULL rate threshold percentage (default: 20)",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=10,
        help="Number of affected symbols to sample (default: 10)",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=30,
        help="Lookback window for detection logic checks (default: 30)",
    )
    args = parser.parse_args()

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            report = build_report(
                cur,
                threshold=args.threshold,
                sample_size=args.sample_size,
                lookback_days=args.lookback_days,
            )
        exit_code = print_report(report)
    finally:
        conn.close()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
