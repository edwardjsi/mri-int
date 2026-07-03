#!/usr/bin/env python3
"""
Backfill `breakout_age` from existing `breakout_state` history in `daily_prices`.

Mirrors the logic in `engine_core/indicator_engine.py` lines 282-295:
- Walk each symbol's rows ordered by date ASC
- NULL when state == CONSOLIDATING
- 0 on state transition into BROKEN_OUT / READY_TO_BREAKOUT
- prev_age + 1 on continuation

Only writes rows where `breakout_state IN ('BROKEN_OUT', 'READY_TO_BREAKOUT')`
and `breakout_age IS NULL` — safe to run multiple times (idempotent).

Usage:
    python3 scripts/backfill_breakout_age.py
    python3 scripts/backfill_breakout_age.py --dry-run
"""
import argparse
import logging
import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Add project root to path so .env resolves
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("backfill_breakout_age")


def compute_age_history(rows: list[tuple]) -> list[tuple]:
    """
    rows: [(date, breakout_state), ...] ordered by date ASC.
    Returns [(date, age_or_None), ...].
    """
    prev_state = None
    prev_age = None
    out = []
    for date, state in rows:
        if state == "CONSOLIDATING" or state is None:
            age = None
            prev_age = None
        elif state == prev_state and prev_age is not None:
            age = prev_age + 1
            prev_age = age
        else:
            age = 0
            prev_age = 0
        prev_state = state
        out.append((date, age))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Compute but don't write")
    args = ap.parse_args()

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    # All symbols
    cur.execute("SELECT DISTINCT symbol FROM daily_prices ORDER BY symbol")
    symbols = [r[0] for r in cur.fetchall()]
    log.info("Found %d symbols in daily_prices", len(symbols))

    # Fetch ALL rows in one query (much faster than per-symbol)
    cur.execute(
        """
        SELECT symbol, date, breakout_state, breakout_age
        FROM daily_prices
        ORDER BY symbol ASC, date ASC
        """
    )
    all_rows = cur.fetchall()
    log.info("Loaded %d total daily_prices rows", len(all_rows))

    updates: list[tuple] = []  # (age, symbol, date)
    skipped_consolidating = 0
    skipped_already_set = 0
    computed_total = 0

    # Group rows by symbol
    by_symbol: dict[str, list[tuple]] = {}
    for sym, date, state, existing_age in all_rows:
        by_symbol.setdefault(sym, []).append((date, state, existing_age))

    for sym, history in by_symbol.items():
        # Compute full history (so prev_age carries correctly across transitions)
        computed = compute_age_history([(r[0], r[1]) for r in history])

        for (date, state, existing_age), (_, new_age) in zip(history, computed):
            if state in ("BROKEN_OUT", "READY_TO_BREAKOUT") and new_age is not None:
                # Only enqueue if the existing value differs (saves unnecessary writes)
                if existing_age != new_age:
                    updates.append((new_age, sym, date))
                    computed_total += 1
            else:
                if state in (None, "CONSOLIDATING"):
                    skipped_consolidating += 1
                elif existing_age is not None and existing_age == new_age:
                    skipped_already_set += 1

    log.info(
        "Computed %d new/updated ages; %d consolidating rows skipped; %d already correct",
        computed_total, skipped_consolidating, skipped_already_set,
    )

    if args.dry_run:
        log.info("[DRY RUN] Would write %d UPDATE rows. Exiting.", len(updates))
        conn.close()
        return

    if not updates:
        log.info("Nothing to update.")
        conn.close()
        return

    sql = """
        UPDATE daily_prices
        SET breakout_age = %s
        WHERE symbol = %s AND date = %s
    """
    psycopg2.extras.execute_batch(cur, sql, updates, page_size=2000)
    conn.commit()
    log.info("Wrote %d breakout_age updates.", len(updates))

    # Verify
    cur.execute(
        """
        SELECT breakout_state, breakout_age, COUNT(*)
        FROM daily_prices
        WHERE breakout_state IN ('BROKEN_OUT', 'READY_TO_BREAKOUT')
        GROUP BY breakout_state, breakout_age
        ORDER BY breakout_state, breakout_age
        """
    )
    log.info("Post-backfill breakout_age distribution (non-null):")
    for state, age, n in cur.fetchall():
        log.info("  %-18s age=%-4s count=%d", state, age, n)

    conn.close()


if __name__ == "__main__":
    main()
