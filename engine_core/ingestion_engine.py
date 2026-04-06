import logging
import yfinance as yf
import pandas as pd
from engine_core.db import insert_index_prices, initialize_core_schema_v100

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_indices():
    logger.info("📡 [engine_core] Ingesting Index Data (v100.3)...")
    initialize_core_schema_v100()
    tickers = ["^NSEI", "^BSESN"]
    for ticker in tickers:
        try:
            # Flatten multi-index columns from new yfinance
            df = yf.download(ticker, period="300d", auto_adjust=True, progress=False).reset_index()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
                
            df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
            df['symbol'] = 'NIFTY50' if ticker == "^NSEI" else 'SENSEX'
            
            records = df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']].dropna().to_dict('records')
            insert_index_prices(records)
            logger.info(f"  ✅ {df['symbol'].iloc[0]} synced ({len(records)} rows).")
        except Exception as e:
            logger.error(f"  ❌ {ticker} failed: {e}")
