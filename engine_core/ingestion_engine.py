import logging
import os
import yfinance as yf
import pandas as pd
from engine_core.db import get_connection, insert_index_prices, initialize_core_schema_v100

# TRACING: Version 100.1
print(f"DEBUG: LOADING engine_core/ingestion_engine.py from {os.path.abspath(__file__)}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_indices():
    """Nuclear Index Loader (Version 100.1)."""
    logger.info("📡 [engine_core] Ingesting Index Data...")
    
    # Force schema bootstrap first
    initialize_core_schema_v100()
    
    tickers = ["^NSEI", "^BSESN"]
    for ticker in tickers:
        try:
            raw = yf.download(ticker, period="100d", auto_adjust=True, progress=False)
            if raw.empty: continue
            
            df = raw.reset_index()
            df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
            df['symbol'] = 'NIFTY50' if ticker == "^NSEI" else 'SENSEX'
            
            records = df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']].dropna().to_dict('records')
            insert_index_prices(records)
            logger.info(f"  ✅ {df['symbol'].iloc[0]} synced.")
        except Exception as e:
            logger.error(f"  ❌ {ticker} failed: {e}")

def load_stocks(symbols):
    # Simplified placeholder for the final push
    logger.info(f"📡 Processing {len(symbols)} stocks...")
    pass
