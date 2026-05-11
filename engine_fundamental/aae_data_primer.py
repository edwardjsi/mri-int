"""
AAE Data Primer — Background task to backfill quarterly financials
and governance data for a symbol so the AAE V3 scan produces
meaningful scores instead of defaults.

Triggered automatically when a stock is added to Watchlist or Digital Twin.
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def prime_aae_data(symbol: str):
    """
    Backfill AAE-required data layers for a single symbol:
      1. Quarterly financials  → aae_quarterly_financials
      2. Governance metrics    → aae_governance_metrics

    Safe to call multiple times (all INSERTs are ON CONFLICT upserts).
    Designed to run as a FastAPI BackgroundTask.
    """
    base = symbol.replace(".NS", "").replace(".BO", "").upper().strip()
    logger.info(f"[AAE-PRIMER] Starting data prime for {base}")

    # ── Layer 1: Quarterly Financials ──────────────────────────────
    try:
        from engine_fundamental.quarterly_collector import fetch_and_store_quarterly
        quarters_saved = fetch_and_store_quarterly(base)
        if quarters_saved:
            logger.info(f"[AAE-PRIMER] Stored {quarters_saved} quarters for {base}")
        else:
            logger.warning(f"[AAE-PRIMER] No quarterly data found for {base}")
    except Exception as e:
        logger.error(f"[AAE-PRIMER] Quarterly backfill failed for {base}: {e}")

    # ── Layer 0: Governance Metrics ────────────────────────────────
    try:
        from engine_fundamental.governance_engine import GovernanceEngine
        gov = GovernanceEngine(base)
        gov_data = gov.fetch_governance_data()
        if gov_data:
            now = datetime.now()
            year = now.year
            quarter = (now.month - 1) // 3 + 1
            gov.store_governance(gov_data, year, quarter)
            logger.info(f"[AAE-PRIMER] Stored governance metrics for {base} (FY{year} Q{quarter})")
        else:
            logger.warning(f"[AAE-PRIMER] No governance data returned for {base}")
    except Exception as e:
        logger.error(f"[AAE-PRIMER] Governance backfill failed for {base}: {e}")

    logger.info(f"[AAE-PRIMER] Data prime complete for {base}")


def prime_aae_data_batch(symbols: list):
    """
    Batch wrapper — primes AAE data for multiple symbols.
    Used by CSV bulk upload and daily pipeline enrichment.
    """
    for sym in symbols:
        try:
            prime_aae_data(sym)
        except Exception as e:
            logger.error(f"[AAE-PRIMER] Batch prime failed for {sym}: {e}")
            continue
