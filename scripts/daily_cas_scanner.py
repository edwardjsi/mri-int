#!/usr/bin/env python3
"""Daily CAS scanner — record recommendations for every eligible stock.

Event A of the outcome tracking architecture (CAS V1.1b, Decision 101):
iterate every symbol in daily_prices, compute CAS, and record the
recommendation (BUY/ADD/WATCH) for every eligible stock.

Per Decision 101 expert pushback: outcomes must be captured for EVERY
eligible stock, not just BUY/ADD recommendations. Otherwise calibration
analysis misses the WATCH cases (which is half the data).

This is intentionally a SEPARATE cron from the outcome updater:
  - Scanner (Event A, this script): runs after market close, records
    recommendations for all eligible stocks.
  - Outcome updater (Event B): runs after scanner, fills milestone prices
    for recommendations that have aged past their milestone windows.

Run manually:
    venv/bin/python scripts/daily_cas_scanner.py

Cron entry (after market close, weekdays 16:05 IST):
    5 16 * * 1-5 cd /home/immanuels/Desktop/mri-int && \
      venv/bin/python scripts/daily_cas_scanner.py >> logs/cas_scanner.log 2>&1
"""
import logging
import os
import sys
from datetime import date
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from engine_core.capital_allocation import load_config
from engine_core.cas_recommendations import (
    scan_and_record_eligible_recommendations,
)
from engine_core.db import get_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_latest_trading_date() -> date:
    """Return the most recent trading date with daily_prices rows."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(date) AS d FROM daily_prices")
            row = cur.fetchone()
            if row and row["d"]:
                return row["d"]
    return date.today()


def run(as_of: date | None = None, limit: int | None = None) -> dict:
    """Scan all symbols and record recommendations.

    Args:
        as_of: date to compute recommendations for. Defaults to MAX(date).
        limit: optional cap for testing (default: all symbols).

    Returns:
        Stats dict from scan_and_record_eligible_recommendations.
    """
    if as_of is None:
        as_of = get_latest_trading_date()

    config = load_config("config/capital_allocation.yaml")
    logger.info("Starting daily CAS scanner for %s (limit=%s)", as_of, limit)

    stats = scan_and_record_eligible_recommendations(as_of, config, limit=limit)

    logger.info(
        "CAS scanner complete: scanned=%d, recorded=%d "
        "(buy=%d, add=%d, watch=%d), ineligible=%d",
        stats["symbols_scanned"], stats["recommendations_recorded"],
        stats["buy_count"], stats["add_count"], stats["watch_count"],
        stats["ineligible_count"],
    )
    return stats


if __name__ == "__main__":
    # Default CLI: scan all symbols for the latest trading date.
    # Override with --limit=N for testing on a subset.
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--as-of", type=date.fromisoformat, default=None)
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()
    run(as_of=args.as_of, limit=args.limit)
