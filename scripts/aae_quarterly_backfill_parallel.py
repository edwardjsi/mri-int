"""Parallel backfill of quarterly financials for the entire active universe.

Usage:
    python scripts/aae_quarterly_backfill_parallel.py                    # all active (595)
    python scripts/aae_quarterly_backfill_parallel.py --all              # all stock_scores (993)
    python scripts/aae_quarterly_backfill_parallel.py --limit 100        # first 100 (test)
    python scripts/aae_quarterly_backfill_parallel.py --workers 15       # 15 concurrent workers
    python scripts/aae_quarterly_backfill_parallel.py --symbol TCS.NS    # single symbol

No LLM costs. Uses yfinance (Yahoo Finance), which is free.
"""

import logging
import sys
import os
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_fundamental.quarterly_collector import fetch_and_store_quarterly
from engine_core.db import fetch_df

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_symbols(use_all: bool = False, limit: int | None = None) -> list[str]:
    """Get symbols to backfill.

    Args:
        use_all: If True, include ALL stock_scores symbols (not just active 30d).
        limit: Cap the total count (for test runs).
    """
    query = (
        "SELECT DISTINCT symbol FROM stock_scores ORDER BY symbol"
        if use_all
        else "SELECT DISTINCT symbol FROM stock_scores WHERE date > NOW() - INTERVAL '30 days' ORDER BY symbol"
    )
    if limit:
        query += f" LIMIT {limit}"

    df = fetch_df(query)
    if df is None or df.empty:
        logger.warning("No symbols found.")
        return []

    return df["symbol"].tolist()


def run_backfill(
    symbols: list[str],
    workers: int = 10,
) -> tuple[int, int, float]:
    """Run fetch_and_store_quarterly in parallel.

    Each worker thread opens its own DB connection (the function does this
    internally), so no connection sharing issues.

    Returns:
        (success_count, fail_count, elapsed_seconds)
    """
    total = len(symbols)
    success_count = 0
    fail_count = 0
    start = time.time()

    logger.info(
        "Starting parallel quarterly backfill: %d symbols, %d workers",
        total,
        workers,
    )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(fetch_and_store_quarterly, sym): sym for sym in symbols
        }

        completed = 0
        for future in as_completed(futures):
            sym = futures[future]
            completed += 1
            try:
                res = future.result()
                if res and res > 0:
                    success_count += 1
                else:
                    fail_count += 1
                    logger.debug("  [%d/%d] %s → no data", completed, total, sym)
            except Exception as e:
                fail_count += 1
                logger.debug("  [%d/%d] %s failed: %s", completed, total, sym, e)

            if completed % 25 == 0 or completed == total:
                elapsed = time.time() - start
                rate = completed / elapsed if elapsed > 0 else 0
                logger.info(
                    "  [%d/%d] %d OK, %d fail — %.1f sym/s, %.0fs elapsed",
                    completed, total, success_count, fail_count, rate, elapsed,
                )

    elapsed = time.time() - start
    logger.info(
        "Done: %d/%d succeeded, %d failed in %.0fs (%.1f sym/s)",
        success_count, total, fail_count, elapsed, total / elapsed if elapsed > 0 else 0,
    )
    return success_count, fail_count, elapsed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parallel backfill of quarterly financials from yfinance."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include ALL stock_scores symbols (default: active in last 30d only)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit to N symbols (test run)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Number of parallel workers (default: 10)",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default=None,
        help="Single symbol to process (skips bulk)",
    )

    args = parser.parse_args()

    if args.symbol:
        sym = args.symbol.upper()
        if not sym.endswith((".NS", ".BO")):
            sym += ".NS"
        logger.info("Single symbol: %s", sym)
        res = fetch_and_store_quarterly(sym)
        if res:
            logger.info("Stored %d quarters for %s", res, sym)
        else:
            logger.warning("No data for %s", sym)
        sys.exit(0)

    symbols = get_symbols(use_all=args.all, limit=args.limit)
    if not symbols:
        logger.warning("No symbols to process. Exiting.")
        sys.exit(0)

    success, fail, elapsed = run_backfill(symbols, workers=args.workers)
    sys.exit(0 if fail == 0 else 1)
