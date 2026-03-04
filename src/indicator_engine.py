import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_batch
from scipy.stats import linregress
import logging
from src.db import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_indicator_columns_if_missing():
    conn = get_connection()
    cur = conn.cursor()
    columns_to_add = [
        ("ema_50", "NUMERIC(12,4)"),
        ("ema_200", "NUMERIC(12,4)"),
        ("ema_200_slope_20", "NUMERIC(12,4)"),
        ("rolling_high_6m", "NUMERIC(12,4)"),
        ("avg_volume_20d", "BIGINT"),
        ("rs_90d", "NUMERIC(12,4)")
    ]
    for col_name, col_type in columns_to_add:
        cur.execute(f"""
            ALTER TABLE daily_prices 
            ADD COLUMN IF NOT EXISTS {col_name} {col_type};
        """)
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Indicator columns added/verified in daily_prices.")

def fetch_data():
    """Fetch daily prices. In incremental mode, identifies which rows need computation."""
    conn = get_connection()

    # Count how many rows need indicators
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM daily_prices WHERE ema_50 IS NULL")
    null_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM daily_prices")
    total_count = cur.fetchone()[0]
    cur.close()

    logger.info(f"Total rows: {total_count:,} | Need indicators: {null_count:,} | Already computed: {total_count - null_count:,}")

    if null_count == 0:
        logger.info("All rows already have indicators. Skipping computation.")
        conn.close()
        return None, None

    # We always need full history for correct EMA computation (EMA depends on all prior values)
    # But we'll only UPDATE new rows in the write step
    logger.info("Fetching daily prices for indicator computation...")
    df = pd.read_sql("SELECT id, symbol, date, high, close, volume, ema_50 FROM daily_prices ORDER BY symbol, date", conn)
    
    logger.info("Fetching index prices for Relative Strength...")
    idx_df = pd.read_sql("SELECT date, close as index_close FROM index_prices WHERE symbol = 'NIFTY50' ORDER BY date", conn)
    conn.close()
    return df, idx_df

def calc_slope(s):
    """Calculate 20-day linear regression slope."""
    result = np.full(len(s), np.nan)
    s_values = s.values
    x = np.arange(20)
    for i in range(19, len(s)):
        y = s_values[i-19:i+1]
        if not np.isnan(y).any():
            slope, _, _, _, _ = linregress(x, y)
            result[i] = slope
    return pd.Series(result, index=s.index)

def compute_indicators(df, idx_df):
    """Compute indicators for all rows. Returns only rows that need DB update."""
    if df is None:
        return []

    logger.info("Computing indicators...")
    
    # Track which rows need updating (ema_50 was NULL in the DB)
    needs_update = df['ema_50'].isna()
    logger.info(f"Rows needing update: {needs_update.sum():,}")

    # Drop the DB ema_50 column before computing fresh values
    df.drop(columns=['ema_50'], inplace=True)

    # Calculate index return over 90 trading days for Relative Strength comparison
    idx_df.sort_values('date', inplace=True)
    idx_df['index_return_90d'] = idx_df['index_close'].pct_change(periods=90)
    
    # Merge index data
    df = pd.merge(df, idx_df[['date', 'index_return_90d']], on='date', how='left')
    df.sort_values(by=['symbol', 'date'], inplace=True)
    
    # Computations per symbol
    logger.info("Calculating EMAs and Rolling values per stock...")
    
    # 50 and 200 EMA
    gp = df.groupby('symbol')
    df['ema_50'] = gp['close'].transform(lambda x: x.ewm(span=50, adjust=False).mean())
    df['ema_200'] = gp['close'].transform(lambda x: x.ewm(span=200, adjust=False).mean())
    df['ema_200'].replace(0, np.nan, inplace=True)
    
    # 20-day slope of 200 EMA
    logger.info("Calculating 20-day regression slope of 200 EMA...")
    df['ema_200_slope_20'] = gp['ema_200'].transform(calc_slope)
    
    # 6-month rolling high (approx 126 trading days)
    df['rolling_high_6m'] = gp['high'].transform(lambda x: x.rolling(window=126, min_periods=1).max())
    
    # 20-day average volume
    df['avg_volume_20d'] = gp['volume'].transform(lambda x: x.rolling(window=20, min_periods=1).mean())
    
    # 90-day stock return vs 90-day index return (Relative Strength)
    df['stock_return_90d'] = gp['close'].transform(lambda x: x.pct_change(periods=90))
    df['rs_90d'] = df['stock_return_90d'] - df['index_return_90d']
    
    # Prepare data for DB update — ONLY rows that need it
    df.replace({np.nan: None}, inplace=True)
    
    # Filter to only rows that had NULL indicators
    df_to_update = df[needs_update]
    logger.info(f"Computed all indicators. Writing {len(df_to_update):,} new rows (skipping {len(df) - len(df_to_update):,} already-computed rows).")
    
    update_data = df_to_update[['ema_50', 'ema_200', 'ema_200_slope_20', 'rolling_high_6m', 'avg_volume_20d', 'rs_90d', 'id']].to_dict('records')
    return update_data

def update_db_with_indicators(update_data):
    if not update_data:
        logger.info("No rows to update. Database is current.")
        return

    total = len(update_data)
    logger.info(f"Updating database with indicators for {total:,} rows (chunked)...")

    CHUNK_SIZE = 50_000
    sql = """
        UPDATE daily_prices
        SET ema_50 = %(ema_50)s,
            ema_200 = %(ema_200)s,
            ema_200_slope_20 = %(ema_200_slope_20)s,
            rolling_high_6m = %(rolling_high_6m)s,
            avg_volume_20d = %(avg_volume_20d)s,
            rs_90d = %(rs_90d)s
        WHERE id = %(id)s
    """

    conn = get_connection()
    cur = conn.cursor()
    done = 0

    for i in range(0, total, CHUNK_SIZE):
        chunk = update_data[i:i + CHUNK_SIZE]
        retries = 3
        for attempt in range(retries):
            try:
                execute_batch(cur, sql, chunk, page_size=2000)
                conn.commit()
                done += len(chunk)
                logger.info(f"  Progress: {done:,}/{total:,} rows ({done * 100 // total}%)")
                break
            except Exception as e:
                logger.warning(f"  Chunk {i // CHUNK_SIZE + 1} failed (attempt {attempt + 1}): {e}")
                try:
                    cur.close()
                    conn.close()
                except Exception:
                    pass
                import time
                time.sleep(5)
                conn = get_connection()
                cur = conn.cursor()
                if attempt == retries - 1:
                    raise

    cur.close()
    conn.close()
    logger.info("Database update complete!")

if __name__ == "__main__":
    add_indicator_columns_if_missing()
    df, idx_df = fetch_data()
    updates = compute_indicators(df, idx_df)
    update_db_with_indicators(updates)
