"""
Prime guidance for symbols that have ZERO rows in management_guidance.
Skips already-primed symbols — saves ~70% runtime on the second run.

Usage:
    python3 scripts/prime_missing_only.py            # default: union of 112co + watchlist + holdings
    python3 scripts/prime_missing_only.py --limit 30
    python3 scripts/prime_missing_only.py --source 112co
"""
import argparse
import logging
import sys
from engine_core.db import get_connection
from engine_guidance.guidance_primer import prime_guidance_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("prime_missing")


def get_missing_symbols(source: str) -> list[str]:
    """Return sorted list of symbols in the chosen source(s) that have NO
    rows in management_guidance yet."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        syms: set[str] = set()
        if source in ("all", "watchlist"):
            cur.execute("SELECT DISTINCT UPPER(symbol) AS symbol FROM client_watchlist")
            syms |= {r["symbol"] for r in cur.fetchall()}
        if source in ("all", "holdings"):
            cur.execute("SELECT DISTINCT UPPER(symbol) AS symbol FROM client_external_holdings")
            syms |= {r["symbol"] for r in cur.fetchall()}
        if source in ("all", "112co"):
            cur.execute(
                "SELECT DISTINCT UPPER(symbol) AS symbol FROM universe_112co WHERE is_active = TRUE"
            )
            syms |= {r["symbol"] for r in cur.fetchall()}

        if not syms:
            return []

        # Find which already have at least one management_guidance row
        cur.execute(
            "SELECT DISTINCT UPPER(symbol) AS symbol FROM management_guidance "
            "WHERE symbol = ANY(%s)",
            (list(syms),),
        )
        primed = {r["symbol"] for r in cur.fetchall()}
        missing = sorted(syms - primed)
        logger.info(
            f"{len(syms)} total in source(s) {source!r}; "
            f"{len(primed)} already primed; {len(missing)} need priming"
        )
        return missing
    finally:
        conn.close()


def main() -> int:
    ap = argparse.ArgumentParser(description="Prime only symbols missing from management_guidance")
    ap.add_argument("--source", choices=["all", "watchlist", "holdings", "112co"], default="all")
    ap.add_argument("--limit", type=int, default=0, help="Max symbols to process (0 = all)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    symbols = get_missing_symbols(args.source)
    if args.limit:
        symbols = symbols[: args.limit]
    if not symbols:
        logger.info("Nothing to prime.")
        return 0

    if args.dry_run:
        print(f"\n  Would prime {len(symbols)} symbols:")
        for s in symbols:
            print(f"    {s}")
        return 0

    success = failed = 0
    for i, sym in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] {sym} ... ", end="", flush=True)
        try:
            prime_guidance_data(sym)
            print("OK")
            success += 1
        except Exception as e:
            print(f"FAIL ({e})")
            failed += 1

    print(f"\nDone. {success} succeeded, {failed} failed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
