"""Fetch annual Basic EPS from yfinance and store it in fundamental_financials.

Usage:
    python scripts/aae_annual_eps_backfill_parallel.py                    # 576 symbols, ~30s
    python scripts/aae_annual_eps_backfill_parallel.py --symbol TCS.NS    # single
    python scripts/aae_annual_eps_backfill_parallel.py --limit 50         # test

No LLM costs. yfinance is free.
"""

import logging
import sys
import os
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_core.db import get_connection
from engine_core.db import fetch_df

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def ensure_eps_column():
    """Add eps column to fundamental_financials if missing."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "ALTER TABLE fundamental_financials ADD COLUMN IF NOT EXISTS eps NUMERIC"
    )
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Ensured eps column exists on fundamental_financials")


def fetch_and_store_annual_eps(symbol: str) -> int:
    """Fetch annual Basic EPS from yfinance and store in fundamental_financials."""
    import yfinance as yf

    if symbol.endswith(".NS") or symbol.endswith(".BO"):
        yf_sym = symbol
    elif symbol.isdigit():
        yf_sym = f"{symbol}.BO"
    else:
        yf_sym = f"{symbol}.NS"

    base_sym = symbol.replace(".NS", "").replace(".BO", "").upper()

    stock = yf.Ticker(yf_sym)
    try:
        inc = stock.income_stmt
    except Exception as e:
        logger.debug("%s: income_stmt failed: %s", yf_sym, e)
        return 0

    if inc is None or inc.empty:
        return 0

    if 'Basic EPS' not in inc.index:
        return 0

    eps_series = inc.loc['Basic EPS']
    records = 0
    conn = get_connection()
    cur = conn.cursor()
    try:
        for date_idx, eps_val in eps_series.items():
            year = date_idx.year
            if eps_val is None or eps_val == 0:
                continue
            cur.execute(
                """UPDATE fundamental_financials
                   SET eps = %s
                   WHERE symbol = %s AND year = %s AND (eps IS NULL OR eps != %s)""",
                (float(eps_val), base_sym, year, float(eps_val)),
            )
            if cur.rowcount == 0:
                cur.execute(
                    """INSERT INTO fundamental_financials (symbol, year, eps)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (symbol, year) DO UPDATE SET eps = EXCLUDED.eps""",
                    (base_sym, year, float(eps_val)),
                )
            records += 1
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.debug("%s: DB error: %s", base_sym, e)
        records = 0
    finally:
        cur.close()
        conn.close()
    return records


def run_backfill(symbols: list[str], workers: int = 10) -> tuple[int, int, float]:
    """Run annual EPS fetch in parallel."""
    total = len(symbols)
    success = 0
    fail = 0
    start = time.time()

    logger.info(
        "Starting annual EPS backfill: %d symbols, %d workers", total, workers
    )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(fetch_and_store_annual_eps, sym): sym
            for sym in symbols
        }
        completed = 0
        for future in as_completed(futures):
            sym = futures[future]
            completed += 1
            try:
                res = future.result()
                if res and res > 0:
                    success += 1
                else:
                    fail += 1
            except Exception:
                fail += 1

            if completed % 50 == 0 or completed == total:
                elapsed = time.time() - start
                rate = completed / elapsed if elapsed > 0 else 0
                logger.info(
                    "  [%d/%d] %d OK, %d fail — %.1f sym/s, %.0fs",
                    completed, total, success, fail, rate, elapsed,
                )

    elapsed = time.time() - start
    logger.info(
        "Done: %d/%d OK, %d fail in %.0fs (%.1f sym/s)",
        success, total, fail, elapsed, total / elapsed if elapsed > 0 else 0,
    )
    return success, fail, elapsed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parallel backfill of annual EPS from yfinance."
    )
    parser.add_argument("--symbol", type=str, default=None, help="Single symbol")
    parser.add_argument("--limit", type=int, default=None, help="Test limit")
    parser.add_argument(
        "--workers", type=int, default=10, help="Parallel workers (default: 10)"
    )
    args = parser.parse_args()

    ensure_eps_column()

    if args.symbol:
        sym = args.symbol.upper()
        if not sym.endswith((".NS", ".BO")):
            sym += ".NS"
        logger.info("Single symbol: %s", sym)
        res = fetch_and_store_annual_eps(sym)
        logger.info("Stored %d years of EPS for %s", res, sym)
        sys.exit(0)

    df = fetch_df(
        "SELECT DISTINCT symbol FROM aae_quarterly_financials "
        "WHERE eps IS NOT NULL AND eps > 0 ORDER BY symbol"
    )
    symbols = df["symbol"].tolist()
    if args.limit:
        symbols = symbols[: args.limit]

    if not symbols:
        logger.warning("No symbols found.")
        sys.exit(0)

    run_backfill(symbols, workers=args.workers)
