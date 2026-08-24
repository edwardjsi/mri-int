"""
scripts/check_freshness.py
===========================
MRI Data Freshness Gate — Step 1b in the production pipeline.

Verifies that required market data has been PERSISTED to the database
for the latest expected trading session, before any downstream computation
(indicators, regime, signals) is allowed to proceed.

Exit codes:
    0 = All required data is fresh → pipeline may continue
    1 = Required data is stale or missing → pipeline MUST abort

Pipeline position:
    Step 1:  ingestion (load_indices + load_stocks)
    Step 1b: python scripts/check_freshness.py   ← THIS SCRIPT
    Step 2:  indicator_engine.py
    Step 3:  regime_engine.py
    ...

Usage:
    Normal:
        python scripts/check_freshness.py

    Stale-data test (safe — does not corrupt production data):
        python scripts/check_freshness.py --override-expected-date 2999-12-31

    Debug:
        python scripts/check_freshness.py --verbose

Never prints DATABASE_URL, passwords, or credentials of any kind.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta

# Ensure project root is on PYTHONPATH when run as a script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from engine_core.db import get_connection


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# NIFTY50 is REQUIRED: the regime engine reads exclusively from
# market_index_prices WHERE symbol = 'NIFTY50'.
# Pipeline MUST abort if NIFTY50 is stale.
REQUIRED_INDEX_SYMBOL = "NIFTY50"
INDEX_TABLE = "market_index_prices"

# The authoritative source for the expected Nifty 500 equity universe.
# This matches the pipeline_cloud.sh ingestion step perfectly.
NIFTY500_URL = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"

# Stale-data age at which we switch from WARN to FAIL for a holiday ambiguity.
# A single day behind the last weekday could be an NSE holiday. Two days cannot.
HOLIDAY_GRACE_DAYS = 1

# ---------------------------------------------------------------------------
# Expected trading date
# ---------------------------------------------------------------------------

def _expected_trading_date(override: date | None = None) -> date:
    """
    Return the date we expect the latest persisted data to be ON or AFTER.

    Logic:
      - If today is Monday–Friday (weekday), the expected session is today.
        (The pipeline runs post-market at 4:15 PM IST; NSE closes 3:30 PM IST.)
      - If today is Saturday, expected = last Friday.
      - If today is Sunday, expected = last Friday.

    NSE holidays:
      We cannot enumerate all NSE holidays without an external calendar.
      Instead we use a 1-day grace: if data is 1 weekday behind, we emit a
      WARNING but do NOT fail — a single missing day is plausibly a holiday.
      If data is 2+ weekdays behind, we FAIL unconditionally.

    Override:
      Passing --override-expected-date allows safe stale-path testing
      (e.g. 2999-12-31) without corrupting production data.
    """
    if override is not None:
        return override

    today = date.today()
    weekday = today.weekday()  # 0=Mon ... 6=Sun
    if weekday == 5:   # Saturday → last Friday
        return today - timedelta(days=1)
    if weekday == 6:   # Sunday → last Friday
        return today - timedelta(days=2)
    return today       # weekday → expect today's data


# ---------------------------------------------------------------------------
# Check helpers
# ---------------------------------------------------------------------------

def _last_weekday(d: date) -> date:
    """Return the most recent weekday on or before d."""
    w = d.weekday()
    if w == 5:
        return d - timedelta(days=1)
    if w == 6:
        return d - timedelta(days=2)
    return d


def check_nifty50(conn, expected: date, verbose: bool) -> tuple[bool, dict]:
    """
    Verify NIFTY50 in market_index_prices has data through `expected`.

    Returns (ok: bool, detail: dict)
    """
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT MAX(date) AS latest FROM {INDEX_TABLE} WHERE symbol = %s",
            (REQUIRED_INDEX_SYMBOL,),
        )
        row = cur.fetchone()

    latest = row["latest"] if row else None

    if latest is None:
        return False, {
            "symbol": REQUIRED_INDEX_SYMBOL,
            "db_latest": None,
            "expected": expected,
            "status": "MISSING — no rows in market_index_prices for NIFTY50",
        }

    if latest >= expected:
        return True, {
            "symbol": REQUIRED_INDEX_SYMBOL,
            "db_latest": latest,
            "expected": expected,
            "status": "FRESH",
        }

    # How many weekdays behind?
    days_behind = (expected - latest).days
    if days_behind <= HOLIDAY_GRACE_DAYS:
        # Could be an NSE holiday — warn but do not block
        return True, {
            "symbol": REQUIRED_INDEX_SYMBOL,
            "db_latest": latest,
            "expected": expected,
            "status": f"WARNING — 1 day behind (possible NSE holiday; not treated as failure)",
        }

    # 2+ weekdays stale — definite failure
    return False, {
        "symbol": REQUIRED_INDEX_SYMBOL,
        "db_latest": latest,
        "expected": expected,
        "status": "STALE",
    }


def _get_expected_equity_universe() -> set[str]:
    """
    Fetch the definitive list of Nifty 500 symbols from NSE.
    This exactly matches the universe requested in pipeline_cloud.sh.
    """
    import io
    import requests
    import pandas as pd

    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(NIFTY500_URL, headers=headers, timeout=30)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text))
        return set(df["Symbol"].dropna().unique().tolist())
    except Exception as exc:
        print(f"WARNING: Could not fetch expected equity universe from NSE: {exc}")
        return set()


def check_equity_symbols(conn, expected: date, verbose: bool) -> tuple[bool, dict]:
    """
    Verify equity symbols in daily_prices against the exact Nifty 500 universe.

    The safest interim policy (Decision from architect):
    For equities, report the exact stale/missing symbol count and symbols.
    Do not silently describe an arbitrary percentage as "healthy".
    NIFTY50 is the hard blocker; equity freshness is diagnostic but does not exit 1.
    """
    expected_universe = _get_expected_equity_universe()
    total_expected = len(expected_universe)

    if total_expected == 0:
        return True, {
            "total": 0,
            "fresh": 0,
            "stale": 0,
            "stale_symbols": [],
            "status": "UNKNOWN — Could not determine expected universe",
        }

    with conn.cursor() as cur:
        # Get latest date for ALL symbols in DB
        cur.execute(
            """
            SELECT symbol, MAX(date) AS latest
            FROM daily_prices
            WHERE symbol NOT IN ('NIFTY50', 'SENSEX', 'NIFTY500')
            GROUP BY symbol
            """
        )
        db_latest = {r["symbol"]: r["latest"] for r in cur.fetchall()}

    fresh_count = 0
    stale_symbols: list[str] = []

    # Sort to ensure stable diagnostic output
    for sym in sorted(expected_universe):
        latest = db_latest.get(sym)
        if latest is not None and latest >= expected:
            fresh_count += 1
        else:
            status_str = f"{sym} (latest={latest})" if latest else f"{sym} (MISSING)"
            stale_symbols.append(status_str)

    stale_count = total_expected - fresh_count

    # Truncate verbose output if there are too many (keeps logs readable)
    display_stale = stale_symbols
    if len(stale_symbols) > 50 and not verbose:
        display_stale = stale_symbols[:50]
        display_stale.append(f"... and {len(stale_symbols) - 50} more")

    # The pipeline is NOT blocked by equities right now per architect instructions
    ok = True

    return ok, {
        "total": total_expected,
        "fresh": fresh_count,
        "stale": stale_count,
        "stale_symbols": display_stale,
        "status": "DIAGNOSTIC",
    }


# ---------------------------------------------------------------------------
# Formatted output
# ---------------------------------------------------------------------------

def _print_pass(expected: date, nifty_detail: dict, equity_detail: dict) -> None:
    print()
    print("MRI DATA FRESHNESS CHECK: PASSED")
    print()
    print(f"  Expected trading date : {expected}")
    print()
    print(f"  {REQUIRED_INDEX_SYMBOL} (market_index_prices):")
    print(f"    DB latest date : {nifty_detail['db_latest']}")
    print(f"    STATUS         : {nifty_detail['status']}")
    print()
    print("  Equity symbols (daily_prices):")
    print(f"    Expected universe: {equity_detail['total']}")
    print(f"    Fresh            : {equity_detail['fresh']}")
    print(f"    Stale/missing    : {equity_detail['stale']}")
    if equity_detail.get("stale_symbols"):
        print(f"    STALE/MISSING SYMBOLS:")
        for sym in equity_detail["stale_symbols"]:
            print(f"        {sym}")
    print()
    print("  Pipeline may continue.")
    print()


def _print_fail(
    expected: date,
    nifty_ok: bool,
    nifty_detail: dict,
    equity_ok: bool,
    equity_detail: dict,
) -> None:
    print()
    print("MRI DATA FRESHNESS CHECK: FAILED")
    print()
    print(f"  Expected trading date : {expected}")
    print()
    print(f"  {REQUIRED_INDEX_SYMBOL} (market_index_prices):")
    db_latest = nifty_detail.get("db_latest", "N/A")
    print(f"    DB latest date : {db_latest}")
    print(f"    STATUS         : {nifty_detail['status']}")
    if not nifty_ok:
        print(f"    *** BLOCKER: NIFTY50 is required by the regime engine. ***")
    print()
    print("  Equity symbols (daily_prices):")
    print(f"    Expected universe: {equity_detail['total']}")
    print(f"    Fresh            : {equity_detail['fresh']}")
    print(f"    Stale/missing    : {equity_detail['stale']}")
    if equity_detail.get("stale_symbols"):
        print(f"    STALE/MISSING SYMBOLS:")
        for sym in equity_detail["stale_symbols"]:
            print(f"        {sym}")
    print()
    print("  Pipeline ABORTED.")
    print("  Downstream calculations were NOT executed.")
    print("  indicator_engine.py was NOT called.")
    print("  regime_engine.py was NOT called.")
    print("  signal_generator.py was NOT called.")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="MRI Data Freshness Gate — verifies DB state before downstream computation."
    )
    parser.add_argument(
        "--override-expected-date",
        metavar="YYYY-MM-DD",
        default=None,
        help=(
            "Override the expected trading date. "
            "Use a future date (e.g. 2999-12-31) to safely test the stale-data path "
            "without modifying production data."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="Print detailed stale symbol list.",
    )
    args = parser.parse_args(argv)

    # Parse override date
    override_date: date | None = None
    if args.override_expected_date:
        try:
            override_date = date.fromisoformat(args.override_expected_date)
        except ValueError:
            print(
                f"ERROR: --override-expected-date must be YYYY-MM-DD, "
                f"got: {args.override_expected_date}"
            )
            return 1

    expected = _expected_trading_date(override_date)

    # Connect to DB
    try:
        conn = get_connection()
    except Exception as exc:
        print(f"MRI DATA FRESHNESS CHECK: FAILED")
        print(f"  Cannot connect to database: {exc}")
        print("  Pipeline ABORTED.")
        return 1

    try:
        nifty_ok, nifty_detail = check_nifty50(conn, expected, args.verbose)
        equity_ok, equity_detail = check_equity_symbols(conn, expected, args.verbose)
    finally:
        conn.close()

    all_ok = nifty_ok and equity_ok

    if all_ok:
        _print_pass(expected, nifty_detail, equity_detail)
        return 0
    else:
        _print_fail(expected, nifty_ok, nifty_detail, equity_ok, equity_detail)
        return 1


if __name__ == "__main__":
    sys.exit(main())
