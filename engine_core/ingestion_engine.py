import logging
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from engine_core.db import get_connection, insert_index_prices, initialize_core_schema_v100

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_indices():
    """Ingest Index Data (v100.4)."""
    logger.info("📡 [engine_core] Ingesting Index Data...")
    initialize_core_schema_v100()
    tickers = ["^NSEI", "^BSESN"]
    for ticker in tickers:
        try:
            df = yf.download(ticker, period="300d", auto_adjust=True, progress=False).reset_index()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
            # yfinance sometimes emits duplicate column names (e.g., adj close). Deduplicate to avoid pandas warning.
            df = df.loc[:, ~df.columns.duplicated()]
            df['symbol'] = 'NIFTY50' if ticker == "^NSEI" else 'SENSEX'
            records = df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']].dropna().to_dict('records')
            insert_index_prices(records)
            logger.info(f"  ✅ {df['symbol'].iloc[0]} synced.")
        except Exception as e:
            logger.error(f"  ❌ {ticker} failed: {e}")

def load_stocks(symbols):
    """Full Stock Ingestion for CSV list (v100.4)."""
    if not symbols: return
    logger.info(f"📡 [engine_core] Processing {len(symbols)} stocks (CSV list)...")
    
    def fetch_stock(symbol):
        try:
            # Suffix handle for NSE
            ticker = symbol if symbol.endswith(".NS") or symbol.endswith(".BO") or "^" in symbol else f"{symbol}.NS"
            df = yf.download(ticker, period="300d", auto_adjust=True, progress=False).reset_index()
            if df.empty: return False
            
            # Flatten columns for yfinance v1.2.0 compatibility
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            
            df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
            df = df.loc[:, ~df.columns.duplicated()]
            df['symbol'] = symbol
            
            records = df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']].dropna().to_dict('records')
            
            # Use dedicated stock insertion
            conn = get_connection()
            with conn.cursor() as cur:
                # Target 'daily_prices' as per original schema
                from psycopg2.extras import execute_batch
                execute_batch(cur, "INSERT INTO daily_prices (symbol, date, open, high, low, close, volume) VALUES (%(symbol)s, %(date)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s) ON CONFLICT (symbol, date) DO NOTHING;", records)
                conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"  ❌ {symbol} failed: {e}")
            return False

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(fetch_stock, symbols))
    
    success_count = sum(results)
    logger.info(f"✅ CSV Ingestion Complete: {success_count}/{len(symbols)} symbols synced.")
