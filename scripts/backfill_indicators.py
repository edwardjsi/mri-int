#!/usr/bin/env python3
"""
Backfill script to recompute and persist historical indicators.
Writes the last 255 rows (~1 year) for ALL symbols in the database.
Usage: python3 scripts/backfill_indicators.py
"""
import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from engine_core.indicator_engine import (
    fetch_data, 
    compute_indicators, 
    update_db_with_indicators,
    chunked
)
from engine_core.db import get_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Force writing a full year of history to erase NULL gaps
BACKFILL_ROWS = 255

def run_backfill(batch_size=20):
    """Effectively recomputes and writes history for all active symbols."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT symbol FROM daily_prices")
            symbols = [row["symbol"] for row in cur.fetchall()]
    finally:
        conn.close()

    if not symbols:
        logger.error("No symbols found in daily_prices.")
        return

    logger.info(f"Starting backfill for {len(symbols)} symbols ({BACKFILL_ROWS} rows each)...")

    # Temporarily override PERSIST_ROWS in indicator_engine module
    import engine_core.indicator_engine
    original_persist = engine_core.indicator_engine.PERSIST_ROWS
    engine_core.indicator_engine.PERSIST_ROWS = BACKFILL_ROWS

    try:
        for i, symbol_batch in enumerate(chunked(symbols, batch_size), 1):
            logger.info(f"Processing batch {i} ({len(symbol_batch)} symbols)...")
            
            # 1. Fetch history
            df, idx_df = fetch_data(symbols=symbol_batch)
            if df.empty:
                continue
                
            # 2. Compute indicators
            updates = compute_indicators(df, idx_df)
            if not updates:
                continue
                
            # 3. Write to DB
            update_db_with_indicators(updates)
            
            logger.info(f"Batch {i} complete.")
    finally:
        # Restore original setting
        engine_core.indicator_engine.PERSIST_ROWS = original_persist

    logger.info("=== Backfill Complete ===")

if __name__ == "__main__":
    run_backfill()
