"""
Phase D3 of docs/INITIATIVE_DATA_RICHNESS_2026-06-19.md.

Re-run engine_fundamental.pipeline.run_quality_pipeline() for every symbol
that already has rows in fundamental_financials, so the new agent_details
JSONB column gets populated for the ~63 already-covered stocks.

Unlike scripts/backfill_nifty500_quality.py (Phase A3), this script does
NOT fetch from Yahoo — it only re-computes the pipeline against existing
data. Phase D3 is idempotent and $0 LLM (QIF is pure Python math).

Usage:
    python scripts/rerun_quality_for_covered_stocks.py
    python scripts/rerun_quality_for_covered_stocks.py --limit 10
    python scripts/rerun_quality_for_covered_stocks.py --symbols POLYCAB KIRLOSENG
"""

import argparse
import logging
import sys
import time

from engine_core.db import get_connection
from engine_fundamental.pipeline import run_quality_pipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_covered_symbols(limit=None):
    """Distinct symbols from fundamental_financials."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        if limit:
            cur.execute("""
                SELECT symbol, COUNT(*) AS year_count
                FROM fundamental_financials
                GROUP BY symbol
                ORDER BY year_count DESC, symbol ASC
                LIMIT %s
            """, (limit,))
        else:
            cur.execute("""
                SELECT symbol, COUNT(*) AS year_count
                FROM fundamental_financials
                GROUP BY symbol
                ORDER BY year_count DESC, symbol ASC
            """)
        return [(row["symbol"], row["year_count"]) for row in cur.fetchall()]
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Phase D3: re-run QIF for stocks with existing fundamentals")
    parser.add_argument("--limit", type=int, default=None, help="Limit to N symbols (default: all)")
    parser.add_argument("--symbols", nargs="+", default=None, help="Specific symbols to rerun (overrides --limit)")
    parser.add_argument("--dry-run", action="store_true", help="List symbols without running")
    args = parser.parse_args()

    if args.symbols:
        symbols = [(s.upper().replace(".NS", "").replace(".BO", ""), None) for s in args.symbols]
    else:
        symbols = get_covered_symbols(limit=args.limit)

    if not symbols:
        logger.warning("No symbols found in fundamental_financials")
        return

    logger.info(f"Phase D3: re-running QIF pipeline for {len(symbols)} symbols")
    if args.dry_run:
        for sym, yc in symbols:
            print(f"  {sym}  ({yc or '?'} yrs)")
        return

    success = 0
    fail = 0
    skipped = 0
    t0 = time.time()

    for i, (sym, year_count) in enumerate(symbols):
        logger.info(f"[{i+1}/{len(symbols)}] {sym} ({year_count or '?'} yrs)")
        try:
            verdict = run_quality_pipeline(sym)
            if verdict:
                agent_details = verdict.get("agent_details", {})
                traj = agent_details.get("trajectory", {})
                by_year_count = len(agent_details.get("by_year", []))
                logger.info(
                    f"  ✅ score={verdict['score']:.1f} {verdict['category']} | "
                    f"agent_details: {by_year_count} yrs, "
                    f"trajectory={traj.get('score_trend', 'n/a')}"
                )
                success += 1
            else:
                logger.warning(f"  ⚠️ pipeline returned None (no fundamentals or other issue)")
                skipped += 1
        except Exception as e:
            logger.error(f"  ❌ {sym}: {e}")
            fail += 1

    elapsed = time.time() - t0
    logger.info(f"")
    logger.info(f"🏁 Phase D3 complete in {elapsed:.1f}s")
    logger.info(f"   ✅ success: {success}")
    logger.info(f"   ⚠️ skipped: {skipped}")
    logger.info(f"   ❌ failed:  {fail}")
    logger.info(f"   total:     {len(symbols)}")


if __name__ == "__main__":
    main()
