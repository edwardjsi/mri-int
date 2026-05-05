import os
import logging
import pandas as pd
import yfinance as yf
from tqdm import tqdm
from engine_core.db import get_connection, insert_index_prices
from engine_core.ingestion_engine import validate_data
from psycopg2.extras import execute_batch
import io
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_nifty500_symbols():
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(url, headers=headers, timeout=30)
        df = pd.read_csv(io.StringIO(res.text))
        return df['Symbol'].tolist()
    except Exception as e:
        logger.error(f"Failed to fetch Nifty 500 symbols: {e}")
        return []

def rebuild_indices():
    logger.info("📡 Rebuilding Indices (MAX history)...")
    tickers = {"^NSEI": "NIFTY50", "^BSESN": "SENSEX"}
    for ticker, symbol in tickers.items():
        try:
            df = yf.download(ticker, period="max", auto_adjust=True, progress=False).reset_index()
            
            # Robust flattening for yfinance multi-index
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [
                    c[0] if (isinstance(c, tuple) and c[0]) else (c[1] if isinstance(c, tuple) else c) 
                    for c in df.columns
                ]
            
            df.columns = [str(c).lower().replace(" ", "_").strip() for c in df.columns]
            if 'date' not in df.columns and 'index' in df.columns:
                df = df.rename(columns={'index': 'date'})
            
            df['symbol'] = symbol
            # Map columns safely
            col_map = {'date': 'date', 'close': 'close', 'open': 'open', 'high': 'high', 'low': 'low', 'volume': 'volume'}
            final_df = pd.DataFrame()
            final_df['symbol'] = [symbol] * len(df)
            for src, dest in col_map.items():
                if src in df.columns:
                    final_df[dest] = df[src]
            
            records = final_df.dropna(subset=['date', 'close']).to_dict('records')
            insert_index_prices(records)
            logger.info(f"  ✅ {symbol} synced: {len(records)} rows.")
        except Exception as e:
            logger.error(f"  ❌ {ticker} failed: {e}")

def rebuild_stocks(symbols):
    logger.info(f"📡 Rebuilding {len(symbols)} stocks (MAX history)...")
    
    def process_symbol(symbol):
        try:
            ticker = f"{symbol}.NS"
            df = yf.download(ticker, period="max", auto_adjust=True, progress=False).reset_index()
            
            if df.empty:
                return
                
            # Robust flattening for yfinance multi-index
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [
                    c[0] if (isinstance(c, tuple) and c[0]) else (c[1] if isinstance(c, tuple) else c) 
                    for c in df.columns
                ]

            df.columns = [str(c).lower().replace(" ", "_").strip() for c in df.columns]
            if 'date' not in df.columns and 'index' in df.columns:
                df = df.rename(columns={'index': 'date'})
            
            # Simple validation
            if 'close' not in df.columns:
                return
                
            df['symbol'] = symbol
            df['volume'] = df.get('volume', 0).fillna(0)
            
            for col in ['open', 'high', 'low']:
                if col in df.columns:
                    df[col] = df[col].fillna(df['close'])
            
            col_map = {'date': 'date', 'close': 'close', 'open': 'open', 'high': 'high', 'low': 'low', 'volume': 'volume'}
            final_df = pd.DataFrame()
            final_df['symbol'] = [symbol] * len(df)
            for src, dest in col_map.items():
                if src in df.columns:
                    final_df[dest] = df[src]

            records = final_df.dropna(subset=['date', 'close']).to_dict('records')
            
            if not records:
                return
                
            conn = get_connection()
            with conn.cursor() as cur:
                execute_batch(cur, """
                    INSERT INTO daily_prices (symbol, date, open, high, low, close, volume) 
                    VALUES (%(symbol)s, %(date)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s) 
                    ON CONFLICT (symbol, date) DO UPDATE 
                    SET open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low, 
                        close = EXCLUDED.close, volume = EXCLUDED.volume;
                """, records)
                conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"  ❌ {symbol} failed: {e}")

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=5) as executor:
        list(tqdm(executor.map(process_symbol, symbols), total=len(symbols)))

def main():
    logger.info("=== MRI Historical Rebuild Initiated ===")
    
    # 1. Rebuild Indices
    rebuild_indices()
    
    # 2. Rebuild Stocks
    symbols = fetch_nifty500_symbols()
    if not symbols:
        logger.error("No symbols found. Aborting.")
        return
        
    rebuild_stocks(symbols)
    
    logger.info("=== Historical Rebuild Complete ===")

if __name__ == "__main__":
    main()
