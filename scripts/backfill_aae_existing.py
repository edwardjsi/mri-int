"""
One-time backfill: Prime AAE V3 data (quarterly financials + governance)
for every symbol currently in any user's Watchlist or Digital Twin.

Usage:
    DATABASE_URL=... python scripts/backfill_aae_existing.py

Safe to re-run (all INSERTs are ON CONFLICT upserts).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from engine_core.db import get_connection
from engine_fundamental.aae_data_primer import prime_aae_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


def get_all_tracked_symbols():
    """Collect every unique symbol from watchlist + external holdings."""
    conn = get_connection()
    cur = conn.cursor()
    symbols = set()

    # Watchlist
    try:
        cur.execute("SELECT DISTINCT symbol FROM client_watchlist")
        for row in cur.fetchall():
            sym = row[0] if not isinstance(row, dict) else row.get("symbol")
            if sym:
                symbols.add(sym.upper().strip())
    except Exception as e:
        logger.warning(f"Could not read client_watchlist: {e}")
        conn.rollback()

    # Digital Twin (external holdings)
    try:
        cur.execute("SELECT DISTINCT symbol FROM client_external_holdings")
        for row in cur.fetchall():
            sym = row[0] if not isinstance(row, dict) else row.get("symbol")
            if sym:
                symbols.add(sym.upper().strip())
    except Exception as e:
        logger.warning(f"Could not read client_external_holdings: {e}")
        conn.rollback()

    cur.close()
    conn.close()
    return sorted(symbols)


def main():
    symbols = get_all_tracked_symbols()
    total = len(symbols)
    logger.info(f"Found {total} unique symbols across Watchlist + Digital Twin")

    if total == 0:
        logger.info("Nothing to backfill.")
        return

    success = 0
    failed = []
    for i, sym in enumerate(symbols, 1):
        logger.info(f"[{i}/{total}] Priming AAE data for {sym}...")
        try:
            prime_aae_data(sym)
            success += 1
        except Exception as e:
            logger.error(f"  FAILED for {sym}: {e}")
            failed.append(sym)

    logger.info(f"\n{'='*50}")
    logger.info(f"AAE Backfill Complete: {success}/{total} succeeded")
    if failed:
        logger.info(f"Failed symbols: {failed}")
    logger.info(f"{'='*50}")


if __name__ == "__main__":
    main()
