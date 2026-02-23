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
    logger.info("Fetching daily prices (this may take a minute for 1.6M rows)...")
    conn = get_connection()
    df = pd.read_sql("SELECT id, symbol, date, high, close, volume FROM daily_prices ORDER BY symbol, date", conn)
    
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
    logger.info("Computing indicators...")
    
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
    df['ema_200'].replace(0, np.nan, inplace=True) # Exclude extreme anomalies if any
    
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
    
    # Prepare data for DB update
    df.replace({np.nan: None}, inplace=True)
    
    update_data = df[['ema_50', 'ema_200', 'ema_200_slope_20', 'rolling_high_6m', 'avg_volume_20d', 'rs_90d', 'id']].to_dict('records')
    return update_data

def update_db_with_indicators(update_data):
    logger.info(f"Updating database with calculated indicators for {len(update_data)} rows...")
    conn = get_connection()
    cur = conn.cursor()
    
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
    
    execute_batch(cur, sql, update_data, page_size=5000)
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Database update complete!")

if __name__ == "__main__":
    add_indicator_columns_if_missing()
    df, idx_df = fetch_data()
    updates = compute_indicators(df, idx_df)
    update_db_with_indicators(updates)
