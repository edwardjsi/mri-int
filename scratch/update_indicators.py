#!/usr/bin/env python3
import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append('.')

from engine_core.indicator_engine import (
    fetch_data, 
    compute_indicators, 
    update_db_with_indicators,
    chunked
)
from engine_core.db import get_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Only backfill the last 5 rows to speed up
BACKFILL_ROWS = 5

def run_backfill(batch_size=50):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT symbol FROM daily_prices")
            symbols = [row["symbol"] for row in cur.fetchall()]
    finally:
        conn.close()

    if not symbols:
        return

    import engine_core.indicator_engine
    original_persist = engine_core.indicator_engine.PERSIST_ROWS
    engine_core.indicator_engine.PERSIST_ROWS = BACKFILL_ROWS

    try:
        for i, symbol_batch in enumerate(chunked(symbols, batch_size), 1):
            logger.info(f"Processing batch {i}...")
            df, idx_df = fetch_data(symbols=symbol_batch)
            if df.empty:
                continue
                
            updates = compute_indicators(df, idx_df)
            if not updates:
                continue
                
            update_db_with_indicators(updates)
    finally:
        engine_core.indicator_engine.PERSIST_ROWS = original_persist

    logger.info("=== Update Indicators Complete ===")

if __name__ == "__main__":
    run_backfill()
