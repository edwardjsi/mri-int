import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_fundamental.quarterly_collector import fetch_and_store_quarterly
from engine_core.db import fetch_df

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_quarterly_backfill(limit=None):
    """
    Backfill quarterly financials for the entire active universe.
    This is required for the AAE V3 Structural Delta engine.
    """
    # Fetch symbols from the active universe
    query = "SELECT DISTINCT symbol FROM stock_scores WHERE date > NOW() - INTERVAL '30 days' ORDER BY symbol"
    if limit:
        query += f" LIMIT {limit}"
        
    symbols_df = fetch_df(query)
    
    if symbols_df is None or symbols_df.empty:
        logger.warning("No active symbols found for backfill.")
        return

    symbols = symbols_df['symbol'].tolist()
    logger.info(f"Starting AAE Quarterly Backfill for {len(symbols)} symbols...")

    success_count = 0
    fail_count = 0
    
    for i, sym in enumerate(symbols):
        try:
            res = fetch_and_store_quarterly(sym)
            if res:
                success_count += 1
            else:
                fail_count += 1
                
            if (i + 1) % 5 == 0:
                logger.info(f"Progress: {i+1}/{len(symbols)} (Success: {success_count}, Fail: {fail_count})")
                
        except Exception as e:
            logger.error(f"Critical error for {sym}: {e}")
            fail_count += 1

    logger.info(f"Backfill Complete. Success: {success_count}, Fail: {fail_count}")

if __name__ == "__main__":
    # If a limit is provided via CLI, use it
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_quarterly_backfill(limit=limit)
