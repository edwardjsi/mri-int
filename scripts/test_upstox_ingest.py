"""
scripts/test_upstox_ingest.py
==============================
Acceptance test for the Upstox V3 OHLCV adapter.

Usage:
    cd /home/immanuels/Desktop/mri-int
    source venv/bin/activate
    UPSTOX_ACCESS_TOKEN=<token> python scripts/test_upstox_ingest.py

Expected output:
    5 recent trading rows per symbol (RELIANCE, TCS, INFY)
    with non-null OHLCV values.

Exit code:
    0 = all checks pass
    1 = any check fails
"""

import os
import sys
import logging

# Ensure project root on PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

from engine_core.upstox_ingest import (
    fetch_daily_ohlcv,
    fetch_index_ohlcv,
    UpstoxAuthError,
    UpstoxInstrumentNotFoundError,
)

TEST_SYMBOLS = ["RELIANCE", "TCS", "INFY"]
REQUIRED_COLUMNS = {"date", "open", "high", "low", "close", "volume"}
LOOKBACK_DAYS = 14          # ~5-7 trading days in a 14-day window
MIN_ROWS_EXPECTED = 3       # at least 3 trading days


def banner(text: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def check_equity_symbols() -> bool:
    banner("EQUITY SYMBOL ACCEPTANCE TEST")
    passed = True

    try:
        results = fetch_daily_ohlcv(TEST_SYMBOLS, lookback_calendar_days=LOOKBACK_DAYS)
    except UpstoxAuthError as e:
        print(f"\n❌ AUTH FAILURE: Analytics Token authentication failed.")
        return False
    except Exception as e:
        print(f"\n❌ EXCEPTION: Request failed. (Details suppressed for security)")
        return False

    for sym in TEST_SYMBOLS:
        print(f"\n--- {sym} ---")
        if sym not in results:
            print(f"  ❌ FAIL: No data returned for {sym}")
            passed = False
            continue

        df = results[sym]
        print(df[["date", "open", "high", "low", "close", "volume"]].tail(7).to_string(index=False))

        # Check 1: required columns
        missing_cols = REQUIRED_COLUMNS - set(df.columns)
        if missing_cols:
            print(f"  ❌ FAIL: Missing columns: {missing_cols}")
            passed = False

        # Check 2: minimum rows
        if len(df) < MIN_ROWS_EXPECTED:
            print(f"  ❌ FAIL: Only {len(df)} row(s), expected >= {MIN_ROWS_EXPECTED}")
            passed = False

        # Check 3: no null close
        null_closes = df["close"].isna().sum()
        if null_closes > 0:
            print(f"  ❌ FAIL: {null_closes} null close price(s)")
            passed = False

        # Check 4: positive prices
        if (df["close"] <= 0).any():
            print(f"  ❌ FAIL: Non-positive close prices detected")
            passed = False

        # Check 5: dates are reasonable (within last 30 days)
        from datetime import date, timedelta
        latest = df["date"].max()
        cutoff = date.today() - timedelta(days=30)
        if latest < cutoff:
            print(f"  ❌ FAIL: Latest date {latest} is older than 30 days")
            passed = False

        if passed:
            print(f"  ✅ {sym}: {len(df)} rows, latest={df['date'].max()}")

    return passed


def check_index(index_name: str) -> bool:
    print(f"\n--- Index: {index_name} ---")
    try:
        result = fetch_index_ohlcv(index_name, lookback_calendar_days=LOOKBACK_DAYS)
    except UpstoxAuthError as e:
        print(f"  ❌ AUTH FAILURE: Analytics Token authentication failed.")
        return False
    except Exception as e:
        print(f"  ❌ EXCEPTION: Request failed. (Details suppressed for security)")
        return False

    if not result:
        # SENSEX failure is non-blocking (BSE instrument key hardcoded)
        if index_name == "SENSEX":
            print(f"  ⚠️  SENSEX: No data (BSE instrument key may be stale — non-blocking).")
            return True  # non-fatal
        print(f"  ❌ FAIL: No data for {index_name}")
        return False

    df = result[index_name]
    print(df[["date", "open", "high", "low", "close", "volume"]].tail(5).to_string(index=False))
    print(f"  ✅ {index_name}: {len(df)} rows, latest={df['date'].max()}")
    return True


def check_instrument_resolution() -> bool:
    banner("INSTRUMENT RESOLUTION TEST")
    from engine_core.upstox_ingest import _resolve_equity_symbol, _resolve_index_key
    passed = True

    cases = [
        ("RELIANCE",  "NSE_EQ"),
        ("TCS",       "NSE_EQ"),
        ("INFY",      "NSE_EQ"),
    ]
    for sym, expected_exchange in cases:
        try:
            key = _resolve_equity_symbol(sym)
            if not key.startswith(expected_exchange):
                print(f"  ❌ {sym}: expected {expected_exchange} key, got {key}")
                passed = False
            else:
                print(f"  ✅ {sym} → {key}")
        except UpstoxInstrumentNotFoundError as e:
            print(f"  ❌ {sym}: {e}")
            passed = False

    # Index keys
    for idx_name, expected_prefix in [("NIFTY50", "NSE_INDEX")]:
        try:
            key = _resolve_index_key(idx_name)
            if not key.startswith(expected_prefix):
                print(f"  ❌ {idx_name}: expected {expected_prefix}, got {key}")
                passed = False
            else:
                print(f"  ✅ {idx_name} → {key}")
        except UpstoxInstrumentNotFoundError as e:
            print(f"  ❌ {idx_name}: {e}")
            passed = False

    return passed


def main() -> int:
    banner("MRI UPSTOX ADAPTER — ACCEPTANCE TEST")
    print(f"  Token set: {'YES' if os.environ.get('UPSTOX_ACCESS_TOKEN') else 'NO — will fail'}")

    resolution_ok = check_instrument_resolution()

    banner("EQUITY DATA TEST")
    equity_ok = check_equity_symbols()
    banner("INDEX DATA TEST")
    idx_ok = True
    for idx in ["NIFTY50"]:
        if not check_index(idx):
            idx_ok = False

    banner("SUMMARY")
    all_pass = resolution_ok and equity_ok and idx_ok
    if all_pass:
        print("  ✅ ALL CHECKS PASSED — Upstox adapter is operational.")
        print("  You may now run the full pipeline:")
        print("    UPSTOX_ACCESS_TOKEN=<token> bash run_daily_pipeline.sh")
    else:
        print("  ❌ SOME CHECKS FAILED — see details above.")
        if not resolution_ok:
            print("  → Instrument resolution failed. Check scratch/NSE.csv.")
        if not equity_ok:
            print("  → Equity data fetch failed. Check token and Upstox connectivity.")
        if not idx_ok:
            print("  → NIFTY50 index fetch failed. Regime engine will have stale data.")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
