"""
Prime guidance data for ALL stocks in the system — every symbol from every user's
watchlist and holdings. Runs sequentially with progress reporting.

Usage:
    python3 scripts/prime_all_guidance.py
    python3 scripts/prime_all_guidance.py --dry-run
"""
import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("prime_all")

from engine_core.db import get_connection
from engine_guidance.guidance_primer import prime_guidance_data


def get_all_symbols():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT UPPER(symbol) FROM watchlist")
        wl = {row[0] for row in cur.fetchall()}
        cur.execute("SELECT DISTINCT UPPER(symbol) FROM holdings")
        hl = {row[0] for row in cur.fetchall()}
        all_syms = sorted(wl | hl)
        logger.info(f"Found {len(all_syms)} unique symbols: {len(wl)} from watchlist, {len(hl)} from holdings")
        return all_syms
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Prime guidance for all system stocks")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--start-from", type=str)
    args = parser.parse_args()

    symbols = get_all_symbols()
    if not symbols:
        logger.error("No symbols found in the system")
        return 1

    sep = "=" * 50
    print(f"\n{sep}")
    print(f"  Total unique symbols: {len(symbols)}")
    print(f"{sep}\n")
    for i, sym in enumerate(symbols, 1):
        print(f"  {i:>3}. {sym}")

    if args.dry_run:
        print(f"\n  [DRY RUN] — remove --dry-run to execute.")
        return 0

    if args.start_from:
        symbols = [s for s in symbols if s >= args.start_from.upper()]
    if args.limit:
        symbols = symbols[:args.limit]

    total = len(symbols)
    success = 0
    failed = 0

    print(f"\n{sep}")
    print(f"  Priming {total} stocks...")
    print(f"{sep}\n")

    for i, sym in enumerate(symbols, 1):
        print(f"[{i}/{total}] {sym} ... ", end="", flush=True)
        try:
            prime_guidance_data(sym)
            print("OK")
            success += 1
        except Exception as e:
            print(f"FAIL ({e})")
            failed += 1

    print(f"\n{sep}")
    print(f"  Done. {success} succeeded, {failed} failed")
    print(f"{sep}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
