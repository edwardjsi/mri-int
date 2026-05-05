import logging
import pandas as pd
import numpy as np
from tqdm import tqdm
from engine_core.db import get_connection
from psycopg2.extras import execute_batch

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def compute_full_indicators():
    conn = get_connection()
    cur = conn.cursor()
    
    # 1. Fetch Nifty 50 for RS calculation
    logger.info("📡 Fetching NIFTY 50...")
    cur.execute("SELECT date, close AS idx_close FROM market_index_prices WHERE symbol = 'NIFTY50' ORDER BY date")
    idx_df = pd.DataFrame([dict(r) for r in cur.fetchall()])
    if not idx_df.empty:
        idx_df['date'] = pd.to_datetime(idx_df['date'])
        idx_df['idx_close'] = pd.to_numeric(idx_df['idx_close'], errors='coerce')
    
    # 2. Fetch all symbols
    cur.execute("SELECT DISTINCT symbol FROM daily_prices")
    symbols = [r['symbol'] for r in cur.fetchall()]
    conn.close()
    
    logger.info(f"🚀 Computing indicators for {len(symbols)} symbols (FULL HISTORY)...")
    
    def process_symbol(symbol):
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Fetch full history for symbol
            cur.execute("SELECT date, open, high, low, close, volume FROM daily_prices WHERE symbol = %s ORDER BY date", (symbol,))
            rows = cur.fetchall()
            if not rows:
                conn.close()
                return
                
            df = pd.DataFrame([dict(r) for r in rows])
            df['date'] = pd.to_datetime(df['date'])
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # EMA Calculations
            df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
            df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean()
            df["ema_200_slope_20"] = df["ema_200"].diff(20)
            
            # Momentum / RS
            df["rolling_high_6m"] = df["close"].rolling(window=126, min_periods=20).max()
            df["avg_volume_20d"] = df["volume"].rolling(window=20).mean()
            
            # Relative Strength (RS 90)
            if not idx_df.empty:
                merged = pd.merge(df[['date', 'close']], idx_df, on="date", how="inner")
                if len(merged) > 90:
                    merged["stock_ret"] = merged["close"] / merged["close"].shift(90)
                    merged["idx_ret"] = merged["idx_close"] / merged["idx_close"].shift(90)
                    merged["rs_90d"] = (merged["stock_ret"] / merged["idx_ret"]) * 100
                    df = pd.merge(df, merged[['date', 'rs_90d']], on="date", how="left")
                else:
                    df["rs_90d"] = None
            else:
                df["rs_90d"] = None

            # Prepare updates
            df = df.replace({np.nan: None})
            updates = []
            for _, row in df.iterrows():
                updates.append({
                    'symbol': symbol,
                    'date': row['date'],
                    'ema_50': row['ema_50'],
                    'ema_200': row['ema_200'],
                    'ema_200_slope_20': row['ema_200_slope_20'],
                    'rolling_high_6m': row['rolling_high_6m'],
                    'avg_volume_20d': row['avg_volume_20d'],
                    'rs_90d': row['rs_90d']
                })
            
            # Batch update
            sql = """
                UPDATE daily_prices 
                SET ema_50 = %(ema_50)s, 
                    ema_200 = %(ema_200)s, 
                    ema_200_slope_20 = %(ema_200_slope_20)s, 
                    rolling_high_6m = %(rolling_high_6m)s, 
                    avg_volume_20d = %(avg_volume_20d)s, 
                    rs_90d = %(rs_90d)s
                WHERE symbol = %(symbol)s AND date = %(date)s
            """
            execute_batch(cur, sql, updates, page_size=1000)
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"  ❌ {symbol} failed: {e}")
            if conn: conn.close()

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=5) as executor:
        list(tqdm(executor.map(process_symbol, symbols), total=len(symbols)))

if __name__ == "__main__":
    compute_full_indicators()
