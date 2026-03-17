import pandas as pd
import numpy as np
import logging
from src.db import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_indicator_columns_if_missing():
    """Ensures the daily_prices table has the required columns for our quant math."""
    conn = get_connection()
    cur = conn.cursor()
    columns = [
        ("ema_20", "NUMERIC"),
        ("ema_50", "NUMERIC"),
        ("ema_200", "NUMERIC"),
        ("rsi_14", "NUMERIC"),
        ("below_200ema", "BOOLEAN")
    ]
    for col_name, col_type in columns:
        cur.execute(f"""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name='daily_prices' AND column_name='{col_name}') THEN
                    ALTER TABLE daily_prices ADD COLUMN {col_name} {col_type};
                END IF;
            END $$;
        """)
    conn.commit()
    cur.close()
    conn.close()

def fetch_data_for_symbols(symbols: list):
    """Fetches raw price data for symbols and the NIFTY50 index for RS calculations."""
    conn = get_connection()
    sym_tuple = tuple(symbols) if len(symbols) > 1 else f"('{symbols[0]}')"
    
    query = f"SELECT symbol, date, close, volume FROM daily_prices WHERE symbol IN {sym_tuple} ORDER BY date"
    df = pd.read_sql(query, conn)
    
    idx_query = "SELECT date, close as idx_close FROM index_prices WHERE symbol = 'NIFTY50' ORDER BY date"
    idx_df = pd.read_sql(idx_query, conn)
    
    conn.close()
    return df, idx_df

def compute_indicators(df, idx_df):
    """Performs technical analysis calculations with Young Stock fallbacks."""
    updates = []
    for symbol in df['symbol'].unique():
        s_df = df[df['symbol'] == symbol].copy().sort_values('date')
        if len(s_df) < 20:
            continue

        s_df['ema_20'] = s_df['close'].ewm(span=20, adjust=False).mean()
        s_df['ema_50'] = s_df['close'].ewm(span=50, adjust=False).mean()
        
        # Fallback for Young Stocks: Use EMA50 if 200 days of data aren't available
        if len(s_df) >= 200:
            s_df['ema_200'] = s_df['close'].ewm(span=200, adjust=False).mean()
        else:
            s_df['ema_200'] = s_df['ema_50'] 

        delta = s_df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        s_df['rsi_14'] = 100 - (100 / (1 + rs))
        s_df['below_200ema'] = s_df['close'] < s_df['ema_200']

        s_df = s_df.replace({np.nan: None})
        for _, row in s_df.iterrows():
            updates.append({
                'symbol': symbol, 'date': row['date'],
                'ema_20': row['ema_20'], 'ema_50': row['ema_50'],
                'ema_200': row['ema_200'], 'rsi_14': row['rsi_14'],
                'below_200ema': row['below_200ema']
            })
    return updates

def update_db_with_indicators(updates):
    """Pushes calculated indicators back to the daily_prices table."""
    conn = get_connection()
    cur = conn.cursor()
    sql = """
        UPDATE daily_prices 
        SET ema_20 = %(ema_20)s, ema_50 = %(ema_50)s, ema_200 = %(ema_200)s, 
            rsi_14 = %(rsi_14)s, below_200ema = %(below_200ema)s
        WHERE symbol = %(symbol)s AND date = %(date)s
    """
    from psycopg2.extras import execute_batch
    execute_batch(cur, sql, updates)
    conn.commit()
    cur.close()
    conn.close()

def compute_indicators_for_symbols(symbols: list):
    """Bridge for On-Demand API requests."""
    if not symbols: return
    add_indicator_columns_if_missing()
    df, idx_df = fetch_data_for_symbols(symbols)
    if df.empty: return
    updates = compute_indicators(df, idx_df)
    if updates: update_db_with_indicators(updates)

def run_indicator_engine():
    """Bulk runner for the whole DB."""
    add_indicator_columns_if_missing()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT symbol FROM daily_prices")
    all_symbols = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    if all_symbols: compute_indicators_for_symbols(all_symbols)