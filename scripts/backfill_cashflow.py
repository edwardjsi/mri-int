"""Backfill Cash Flow Data into fundamental_financials.

Fetches annual Operating Cash Flow and Free Cash Flow from yfinance
for every symbol in the fundamental_financials table and updates
the newly added operating_cashflow and free_cashflow columns.

Usage:
    cd /path/to/mri-int
    export $(grep -v '^#' .env | xargs)
    python3 scripts/backfill_cashflow.py
"""

import sys
import os
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def sanitize_val(val):
    """Convert numpy/pandas types to native Python types for SQL compatibility."""
    if val is None:
        return None
    try:
        import numpy as np
        if isinstance(val, (float, int)) and np.isnan(val):
            return None
        if hasattr(val, "item"):
            return val.item()
    except ImportError:
        pass
    return val


def backfill_cashflow(symbol, cur):
    """Fetch annual cash flow from yfinance and update fundamental_financials for a symbol."""
    import yfinance as yf

    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        yf_sym = symbol
    elif symbol.isdigit():
        yf_sym = f"{symbol}.BO"
    else:
        yf_sym = f"{symbol}.NS"

    base_sym = symbol.replace(".NS", "").replace(".BO", "").upper()

    try:
        ticker = yf.Ticker(yf_sym)
        cf = ticker.cashflow
    except Exception as e:
        logger.warning(f"  yfinance error for {symbol} ({yf_sym}): {e}")
        return 0

    if cf is None or cf.empty:
        logger.warning(f"  No cash flow data for {symbol}")
        return 0

    rows = list(cf.index)
    if "Operating Cash Flow" not in rows:
        logger.warning(f"  No Operating Cash Flow row for {symbol}")
        return 0

    has_fcf = "Free Cash Flow" in rows
    updated = 0

    for year_col in cf.columns:
        try:
            year = year_col.year if hasattr(year_col, "year") else int(str(year_col)[:4])
        except (ValueError, TypeError):
            continue

        ocf = sanitize_val(cf.loc["Operating Cash Flow", year_col])
        fcf = sanitize_val(cf.loc["Free Cash Flow", year_col]) if has_fcf else None

        if ocf is None and fcf is None:
            continue
        if ocf is not None and abs(ocf) > 1e15:
            continue
        if fcf is not None and abs(fcf) > 1e15:
            continue

        cur.execute(
            """
            UPDATE public.fundamental_financials
            SET operating_cashflow = %s,
                free_cashflow = %s,
                updated_at = NOW()
            WHERE symbol = %s AND year = %s
            """,
            (ocf, fcf, base_sym, year),
        )
        if cur.rowcount > 0:
            updated += 1

    return updated


def main():
    from engine_core.db import get_connection

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT DISTINCT symbol FROM public.fundamental_financials ORDER BY symbol")
    symbols = [r.get('symbol') if isinstance(r, dict) else r[0] for r in cur.fetchall()]
    logger.info(f"Found {len(symbols)} symbols in fundamental_financials")

    total_updated = 0
    total_skipped = 0
    total_errors = 0

    for i, symbol in enumerate(symbols):
        if i > 0 and i % 50 == 0:
            logger.info(f"Progress: {i}/{len(symbols)} processed ({total_updated} rows updated)")

        try:
            updated = backfill_cashflow(symbol, cur)
            if updated > 0:
                total_updated += updated
                if i < 5 or i % 25 == 0:
                    logger.info(f"  [{i+1}/{len(symbols)}] {symbol}: updated {updated} rows")
            else:
                total_skipped += 1
            conn.commit()
        except Exception as e:
            conn.rollback()
            total_errors += 1
            logger.error(f"  [{i+1}/{len(symbols)}] {symbol}: ERROR - {e}")

        time.sleep(0.25)

    cur.close()
    conn.close()

    logger.info("=" * 60)
    logger.info(f"Backfill complete.")
    logger.info(f"  Symbols processed: {len(symbols)}")
    logger.info(f"  Rows updated: {total_updated}")
    logger.info(f"  Skipped (no data): {total_skipped}")
    logger.info(f"  Errors: {total_errors}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
