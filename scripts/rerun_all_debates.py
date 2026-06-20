"""
Phase A5 of docs/INITIATIVE_DATA_RICHNESS_2026-06-19.md.

Force-rerun bear/bull debates for all 149 Expansion Lens universe symbols.
To be executed AFTER Phase A2 (AAE backfill) and Phase A3 (QIF backfill)
complete.

Approach:
1. Iterate perx_pe_scores (149 symbols)
2. For each, build guidance + pe_expansion contexts
3. Call debate_engine.run_debate() for each context kind

Natural regeneration: symbols whose AAE or QIF data changed will produce a
DIFEERENT context_hash → cache MISS → new LLM debate generated.
Unchanged symbols will produce the SAME hash → cache HIT → free.

Optional --force flag: wipe conviction_debates for matching symbols first
(costs $0.002 × 149 symbols ≈ $0.30).

Usage:
    # After A2+A3 complete — natural regeneration of changed symbols:
    python scripts/rerun_all_debates.py

    # Force-regenerate ALL debates (user's Q4 choice):
    python scripts/rerun_all_debates.py --force

    # Dry-run (show which symbols would regenerate):
    python scripts/rerun_all_debates.py --dry-run
"""

import argparse
import logging
import time

from engine_core.db import get_connection
from engine_debate.debate_engine import run_debate
from engine_debate.context_guidance import build_guidance_context
from engine_debate.context_pe_expansion import build_pe_expansion_context
from engine_debate.cache import canonical_hash

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_universe_symbols():
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT symbol FROM perx_pe_scores ORDER BY symbol")
        return [row["symbol"] for row in cur.fetchall()]
    finally:
        conn.close()


def clear_cache_for_symbol(cur, symbol):
    """Delete all conviction_debates rows for a symbol (both context kinds)."""
    cur.execute(
        "DELETE FROM conviction_debates WHERE symbol = %s",
        (symbol.upper(),),
    )


def run_for_symbol(sym, force=False, dry_run=False):
    """Run debates for both context kinds. Returns stats dict."""
    results = {
        "symbol": sym,
        "guidance": {"status": "skipped", "cached": None},
        "pe_expansion": {"status": "skipped", "cached": None},
    }

    # GuidanceCheck context
    try:
        gctx = build_guidance_context(sym)
        ghash = canonical_hash(gctx)

        if force:
            conn = get_connection()
            try:
                cur = conn.cursor()
                clear_cache_for_symbol(cur, sym)
                conn.commit()
            finally:
                conn.close()

        if dry_run:
            # Check if there's a cached row with this hash
            conn = get_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    """SELECT id FROM conviction_debates
                       WHERE symbol = %s AND context_kind = 'guidance' AND context_hash = %s""",
                    (sym.upper(), ghash),
                )
                cached = cur.fetchone() is not None
                results["guidance"]["status"] = "dry_run"
                results["guidance"]["cached"] = cached
            finally:
                conn.close()
        else:
            gres = run_debate(sym, context_kind="guidance", context_payload=gctx, include_adjudicator=False)
            results["guidance"]["status"] = "generated"
            results["guidance"]["cached"] = gres.cached
    except Exception as e:
        logger.error(f"  ❌ guidance debate failed for {sym}: {e}")
        results["guidance"]["status"] = "error"

    # PE Expansion context
    try:
        pctx = build_pe_expansion_context(sym)
        phash = canonical_hash(pctx)

        if dry_run:
            conn = get_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    """SELECT id FROM conviction_debates
                       WHERE symbol = %s AND context_kind = 'pe_expansion' AND context_hash = %s""",
                    (sym.upper(), phash),
                )
                cached = cur.fetchone() is not None
                results["pe_expansion"]["status"] = "dry_run"
                results["pe_expansion"]["cached"] = cached
            finally:
                conn.close()
        else:
            pres = run_debate(sym, context_kind="pe_expansion", context_payload=pctx, include_adjudicator=False)
            results["pe_expansion"]["status"] = "generated"
            results["pe_expansion"]["cached"] = pres.cached
    except Exception as e:
        logger.error(f"  ❌ pe_expansion debate failed for {sym}: {e}")
        results["pe_expansion"]["status"] = "error"

    return results


def main():
    parser = argparse.ArgumentParser(description="Phase A5: regenerate all debates")
    parser.add_argument("--force", action="store_true", help="Wipe cache first (costs ~$0.30)")
    parser.add_argument("--dry-run", action="store_true", help="Show which would regenerate without LLM calls")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    symbols = get_universe_symbols()
    if args.limit:
        symbols = symbols[:args.limit]

    mode = "force" if args.force else ("dry-run" if args.dry_run else "natural")
    logger.info(f"Phase A5: {len(symbols)} symbols | mode={mode}")

    if args.force:
        # Batch clear all caches for efficiency
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """DELETE FROM conviction_debates
                   WHERE symbol IN (SELECT symbol FROM perx_pe_scores)"""
            )
            deleted = cur.rowcount
            conn.commit()
            logger.info(f"🗑️  Cleared {deleted} cached debate rows")
        finally:
            conn.close()

    stats = {
        "total": len(symbols),
        "guidance_generated": 0,
        "guidance_cached": 0,
        "guidance_errors": 0,
        "pe_generated": 0,
        "pe_cached": 0,
        "pe_errors": 0,
    }

    t0 = time.time()
    for i, sym in enumerate(symbols):
        if not args.dry_run and i % 10 == 0 and i > 0:
            logger.info(f"Progress: {i}/{len(symbols)} symbols")

        res = run_for_symbol(sym, force=False, dry_run=args.dry_run)
        for kind in ("guidance", "pe_expansion"):
            s = res[kind]["status"]
            cached = res[kind]["cached"]
            prefix = "guidance" if kind == "guidance" else "pe"
            if s == "error":
                stats[f"{prefix}_errors"] += 1
            elif s in ("generated", "dry_run"):
                if cached:
                    stats[f"{prefix}_cached"] += 1
                else:
                    stats[f"{prefix}_generated"] += 1

    elapsed = time.time() - t0
    logger.info("")
    logger.info(f"🏁 Phase A5 complete in {elapsed:.1f}s")
    logger.info(f"   Total symbols: {stats['total']}")
    if args.dry_run:
        logger.info(f"   Guidance: {stats['guidance_generated']} would regenerate, {stats['guidance_cached']} cache hits")
        logger.info(f"   PE Exp:   {stats['pe_generated']} would regenerate, {stats['pe_cached']} cache hits")
    else:
        logger.info(f"   Guidance: {stats['guidance_generated']} generated, {stats['guidance_cached']} cache hits, {stats['guidance_errors']} errors")
        logger.info(f"   PE Exp:   {stats['pe_generated']} generated, {stats['pe_cached']} cache hits, {stats['pe_errors']} errors")


if __name__ == "__main__":
    main()
