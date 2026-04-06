import logging
import os
import yfinance as yf
import pandas as pd
from engine_core.db import get_connection, insert_index_prices, initialize_core_schema_v100

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_indices():
    logger.info("📡 [engine_core] Ingesting Index Data (v100.2)...")
    initialize_core_schema_v100()
    
    tickers = ["^NSEI", "^BSESN"]
    for ticker in tickers:
        try:
            # Download with multi-index bypass
            raw = yf.download(ticker, period="300d", auto_adjust=True, progress=False)
            if raw.empty: continue
            
            df = raw.reset_index()
            # DEFENSIVE: Flatten Multi-Index columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
                
            df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
            df['symbol'] = 'NIFTY50' if ticker == "^NSEI" else 'SENSEX'
            
            # Ensure required columns exist
            required = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']
            missing = [c for c in required if c not in df.columns]
            if missing:
                logger.error(f"  ❌ {ticker} missing columns: {missing}")
                continue
                
            records = df[required].dropna().to_dict('records')
            insert_index_prices(records)
            logger.info(f"  ✅ {df['symbol'].iloc[0]} synced ({len(records)} rows).")
        except Exception as e:
            logger.error(f"  ❌ {ticker} failed: {e}")
