"""
MRI Daily Pipeline — [V15 ULTIMATE ISOLATION]
"""
import os
import sys
import logging
import pandas as pd
import numpy as np
import requests
import io
from datetime import datetime, timedelta
from typing import List, Tuple

# TRACING: This is the version that uses the NEW db_v15 file
print(f"DEBUG: LOADING scripts/mri_pipeline.py V15 from {os.path.abspath(__file__)}")

# Add parent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# IMPORT FROM THE BRAND NEW FILE
from engine_core.db_v15 import initialize_core_schema_v15, insert_index_prices, insert_daily_prices

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("pipeline")

def get_full_symbol_list() -> Tuple[List[str], List[dict]]:
    from engine_core.db_v15 import get_connection
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT symbol FROM client_watchlist")
    symbols = [r[0] for r in cur.fetchall()]
    return symbols, []

def run_pipeline():
    logger.info(f"=== MRI Daily Pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M UTC')} — V15 ===")
    
    # Step 0: INITIALIZE SCHEMA USING THE NEW V15 FILE
    try:
        initialize_core_schema_v15()
    except Exception as e:
        logger.error(f"SCHEMA INITIALIZATION FAILED: {e}")

    # Step 1: Ingest Data
    logger.info("[1/5] Ingesting market data...")
    # ... Final verification logic ...
