import pandas as pd
import numpy as np
import yfinance as yf
import requests
import io
import logging
import time
import os
from datetime import datetime, timedelta

# SUPER DEBUG: Trace loader path
print(f"DEBUG: LOADING ingestion_engine.py from {os.path.abspath(__file__)}")

from src.db import get_connection, initialize_core_schema_v12, insert_daily_prices

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from psycopg2 import sql

def get_last_date(table_name="daily_prices") -> str:
    """Queries the DB for the latest record."""
    from src.db import get_connection
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            query = sql.SQL("SELECT MAX(date) FROM {}").format(sql.Identifier(table_name))
            cur.execute(query)
            last_date = cur.fetchone()[0]
            if last_date:
                return (last_date - timedelta(days=3)).strftime("%Y-%m-%d")
    except Exception as e:
        logger.error(f"Error fetching last date for {table_name}: {e}")
    finally:
        conn.close()
    return (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")

def load_indices(period: str = None):
    """Daily pipeline entry point for index data."""
    initialize_core_schema_v12()
    if period:
        logger.info(f"Forcing {period} index download...")
        idx_raw = yf.download("^NSEI", period=period, progress=False, auto_adjust=True)
    else:
        start_date = get_last_date("market_index_prices")
        logger.info(f"Fetching NIFTY 50 Index data since {start_date}...")
        idx_raw = yf.download("^NSEI", start=start_date, progress=False, auto_adjust=True)
    
    if idx_raw.empty:
        logger.warning("yf returned NO data for index '^NSEI'")
        return

    idx_df = idx_raw.reset_index()
    idx_df.columns = [str(c).lower().replace(" ", "_") for c in idx_df.columns]
    idx_df['symbol'] = 'NIFTY50'
    idx_df['date'] = pd.to_datetime(idx_df['date']).dt.date
    
    from src.db import insert_index_prices
    records = idx_df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']].dropna().to_dict('records')
    logger.info(f"📊 Inserting {len(records)} index rows for NIFTY50 into market_index_prices")
    insert_index_prices(records)
    logger.info("✅ Index data loaded")

def build_symbol_translator() -> dict:
    return {"NIFTY50": "NIFTY50"}

def sync_universe():
    return

def load_stocks(symbols: list, period: str = None):
    """Daily pipeline entry point for stock data."""
    if not symbols: return
    initialize_core_schema_v12()
    logger.info(f"📈 Processing {len(symbols)} symbols...")
    # ... Simplified for version check ...
