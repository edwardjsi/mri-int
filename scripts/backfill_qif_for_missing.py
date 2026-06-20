"""
Phase A3 of docs/INITIATIVE_DATA_RICHNESS_2026-06-19.md.

Backfill QIF (financial quality) for symbols that lack it. Discovered that
ALL 49 "missing QIF" symbols actually have NO fundamental_financials rows
at all — they need Yahoo fetch BEFORE the QIF pipeline can run.

This script:
1. Reads missing_qif.csv (49 symbols)
2. For each: fetch financials from Yahoo → store in fundamental_financials
3. Then: run_quality_pipeline() → computes QIF + persists agent_details JSONB
4. Logs progress, handles errors gracefully

Unlike the D3 re-run script, this one FETCHES fresh data from Yahoo.
Unlike backfill_nifty500_quality.py, this targets only the 49 missing symbols.

Usage:
    python scripts/backfill_qif_for_missing.py
    python scripts/backfill_qif_for_missing.py --limit 10
    python scripts/backfill_qif_for_missing.py --symbol QPOWER
"""

import argparse
import csv
import logging
import time

from engine_core.db import get_connection
from engine_fundamental.collector import fetch_and_store_financials
from engine_fundamental.pipeline import run_quality_pipeline

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_missing_symbols(csv_path='docs/data_richness_audit/missing_qif.csv'):
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        return [row['symbol'] for row in reader]


def main():
    parser = argparse.ArgumentParser(description='Phase A3: fetch + QIF for missing symbols')
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--symbol', default=None, help='Single symbol override')
    args = parser.parse_args()

    if args.symbol:
        symbols = [args.symbol.upper()]
    else:
        symbols = get_missing_symbols()
        if args.limit:
            symbols = symbols[:args.limit]

    logger.info(f'Phase A3: {len(symbols)} symbols to fetch + QIF')

    success = 0
    fail_fetch = 0
    fail_qif = 0
    t0 = time.time()

    for i, sym in enumerate(symbols):
        logger.info(f'[{i+1}/{len(symbols)}] {sym}')

        # Step 1: fetch financials from Yahoo
        fetched = fetch_and_store_financials(sym)
        if not fetched or fetched == 0:
            logger.warning(f'  ⚠️ fetch returned None/zero rows for {sym}')
            fail_fetch += 1
            continue
        logger.info(f'  📥 fetched {fetched} year(s)')

        # Step 2: run QIF pipeline
        try:
            verdict = run_quality_pipeline(sym)
            if verdict:
                ad = verdict.get('agent_details', {})
                logger.info(
                    f'  ✅ QIF score={verdict["score"]:.1f} {verdict["category"]} | '
                    f'agent_details: {len(ad.get("by_year", []))} yrs'
                )
                success += 1
            else:
                logger.warning(f'  ⚠️ pipeline returned None for {sym}')
                fail_qif += 1
        except Exception as e:
            logger.error(f'  ❌ pipeline failed for {sym}: {e}')
            fail_qif += 1

        # Rate limiting to avoid Yahoo blocks
        if (i + 1) % 5 == 0:
            time.sleep(2)

    elapsed = time.time() - t0
    logger.info('')
    logger.info(f'🏁 Phase A3 complete in {elapsed:.1f}s')
    logger.info(f'   ✅ success:  {success}')
    logger.info(f'   ⚠️ fetch fail: {fail_fetch}')
    logger.info(f'   ⚠️ QIF fail:  {fail_qif}')
    logger.info(f'   total:      {len(symbols)}')


if __name__ == '__main__':
    main()
