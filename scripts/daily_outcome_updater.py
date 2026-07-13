#!/usr/bin/env python3
"""Daily EOD outcome updater (CAS V1.1b, Decision 101).

Event B of the outcome tracking architecture: after market close, walk
all open CAS recommendations and fill milestone prices at 7d / 14d /
28d / 63d / 126d elapsed trading days.

This is intentionally a SEPARATE cron from the API:
  - API CAS computation (Event A) runs whenever the user requests it.
  - Outcome updates (Event B) run once per trading day, after market close.

Per Decision 101 expert guidance, this catches Friday→Monday gap events
that weekly sampling misses.

Run manually:
    venv/bin/python scripts/daily_outcome_updater.py

Cron entry (after market close, weekdays 16:00 IST):
    0 16 * * 1-5 cd /home/immanuels/Desktop/mri-int && \
      venv/bin/python scripts/daily_outcome_updater.py >> logs/outcomes.log 2>&1
"""
import logging
import os
import sys
from datetime import date
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from engine_core.db import get_connection
from engine_core.cas_recommendations import update_cas_outcomes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_latest_trading_date() -> date:
    """Return the most recent trading date with daily_prices rows.

    Falls back to today if the DB has no data (shouldn't happen in prod).
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(date) AS d FROM daily_prices")
            row = cur.fetchone()
            if row and row["d"]:
                return row["d"]
    return date.today()


def run(today: date | None = None) -> dict:
    """Update all open CAS recommendation outcomes as of `today`.

    Args:
        today: date to update for. Defaults to MAX(date) in daily_prices.

    Returns:
        Stats dict from update_cas_outcomes().
    """
    if today is None:
        today = get_latest_trading_date()

    logger.info("Starting daily outcome update for %s", today)

    stats = update_cas_outcomes(today)

    logger.info(
        "Outcome update complete: processed=%d, milestones_filled=%d, "
        "closed_w4=%d, closed_m6=%d",
        stats["recommendations_processed"],
        stats["milestones_filled"],
        stats["closed_w4"],
        stats["closed_m6"],
    )
    return stats


if __name__ == "__main__":
    run()
