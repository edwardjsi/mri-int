"""
Run the iterative narrative tracer across ALL companies with transcripts.

Builds management_narrative_timeline rows for every symbol that has
at least 1 transcript in aae_transcripts. Idempotent — re-runs upsert.

Usage:
    python3 scripts/run_narrative_tracer_universe.py
    python3 scripts/run_narrative_tracer_universe.py --limit 5
    python3 scripts/run_narrative_tracer_universe.py --skip CGCL  # skip pilot
    python3 scripts/run_narrative_tracer_universe.py --min-transcripts 2

Logs to logs/narrative_tracer_universe_<date>.log
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
import traceback
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("narrative_universe")

from engine_core.db import get_connection
from engine_guidance.narrative_tracer import (
    NarrativeTracer,
    upsert_timeline,
    load_transcripts,
)


def get_company_symbols(min_transcripts: int = 1) -> list[tuple[str, int]]:
    """Return (symbol, transcript_count) sorted by transcript count desc."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT symbol, COUNT(*) AS n
               FROM aae_transcripts
               WHERE raw_text IS NOT NULL AND LENGTH(raw_text) > 200
               GROUP BY symbol
               HAVING COUNT(*) >= %s
               ORDER BY n DESC""",
            (min_transcripts,),
        )
        return [(r["symbol"], r["n"]) for r in cur.fetchall()]
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="Max companies to process (0=all)")
    ap.add_argument("--skip", nargs="*", default=[], help="Symbols to skip (e.g. CGCL)")
    ap.add_argument("--min-transcripts", type=int, default=1,
                    help="Skip companies with fewer than N transcripts (default 1)")
    ap.add_argument("--max-chars", type=int, default=100000,
                    help="Max chars per transcript sent to LLM (default 100000)")
    ap.add_argument("--dry-run", action="store_true", help="List companies but don't run")
    args = ap.parse_args()

    # Set up file logging
    os.makedirs("logs", exist_ok=True)
    log_path = f"logs/narrative_tracer_universe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    fh = logging.FileHandler(log_path)
    fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(fh)

    logger.info(f"=== Universe narrative tracer run ===")
    logger.info(f"Args: {vars(args)}")
    logger.info(f"Log file: {log_path}")

    companies = get_company_symbols(args.min_transcripts)
    if args.skip:
        companies = [(s, n) for s, n in companies if s not in args.skip]
    if args.limit > 0:
        companies = companies[:args.limit]

    total = len(companies)
    logger.info(f"Found {total} companies to process (min_transcripts={args.min_transcripts})")
    print(f"\nProcessing {total} companies. Log: {log_path}\n")

    if args.dry_run:
        for s, n in companies:
            print(f"  {s:<15} {n} transcripts")
        return

    success = 0
    failures: list[tuple[str, str]] = []
    total_promises = 0
    start = time.time()

    for i, (symbol, n_transcripts) in enumerate(companies, 1):
        elapsed = time.time() - start
        avg = elapsed / max(1, i - 1) if i > 1 else 0
        eta = avg * (total - i + 1)
        logger.info(
            f"[{i}/{total}] {symbol} ({n_transcripts} transcripts)  "
            f"elapsed={elapsed:.0f}s eta={eta:.0f}s"
        )
        print(
            f"[{i}/{total}] {symbol} ({n_transcripts} t)  "
            f"elapsed={elapsed:.0f}s eta={eta:.0f}s",
            flush=True,
        )
        try:
            tracer = NarrativeTracer(symbol, max_chars_per_call=args.max_chars)
            promises = tracer.trace()
            if promises:
                upserted = upsert_timeline(symbol, promises)
                total_promises += upserted
                logger.info(f"  → {upserted} promises upserted for {symbol}")
            success += 1
        except Exception as e:
            err = f"{type(e).__name__}: {e}"
            failures.append((symbol, err))
            logger.error(f"  FAILED {symbol}: {err}")
            logger.error(traceback.format_exc())

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"COMPLETE: {success}/{total} succeeded in {elapsed:.0f}s")
    print(f"Total promises written: {total_promises}")
    if failures:
        print(f"\nFailures ({len(failures)}):")
        for s, err in failures:
            print(f"  {s}: {err}")
    print(f"\nLog: {log_path}")


if __name__ == "__main__":
    main()
