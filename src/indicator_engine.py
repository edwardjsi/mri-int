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
    sym_tuple = tuple(symbols)
    
    # Fetch stock data
    query = "SELECT symbol, date, close FROM daily_prices WHERE symbol IN %s ORDER BY symbol, date"
    df = pd.read_sql(query, conn, params=(sym_tuple,))
    
    # Fetch Index data for relative strength
    idx_query = "SELECT date, close FROM index_prices WHERE symbol = 'NIFTY50' ORDER BY date"
    idx_df = pd.read_sql(idx_query, conn)
    
    conn.close()
    return df, idx_df

def compute_indicators(df: pd.DataFrame, idx_df: pd.DataFrame) -> list:
    """
    Adaptive Indicator Engine:
    Calculates EMAs and RSI. If 200 days of data are missing, falls back 
    to 50-day trends to ensure a score is always generated.
    """
    updates = []
    df = df.sort_values(['symbol', 'date'])
    
    # Prepare index data for RS (Relative Strength)
    idx_df = idx_df.set_index('date')
    
    for symbol, group in df.groupby('symbol'):
        if len(group) < 2:
            continue
            
        # 1. EMAs (Exponential Moving Averages)
        ema_20 = group['close'].ewm(span=20, adjust=False).mean()
        ema_50 = group['close'].ewm(span=50, adjust=False).mean()
        
        # Adaptive 200 EMA Logic
        if len(group) >= 200:
            ema_200 = group['close'].ewm(span=200, adjust=False).mean()
            current_ema_200 = float(ema_200.iloc[-1])
            is_below_200 = bool(group['close'].iloc[-1] < current_ema_200)
        else:
            # For "Young" stocks, use the 50-day trend as the long-term proxy
            current_ema_200 = float(ema_50.iloc[-1])
            is_below_200 = bool(group['close'].iloc[-1] < current_ema_200)
            logger.info(f"Symbol {symbol} is young ({len(group)} days). Using EMA50 fallback for trend.")

        # 2. RSI (Relative Strength Index)
        delta = group['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        # Avoid division by zero
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs.fillna(0)))
        
        latest_rsi = float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50.0

        updates.append({
            'symbol': symbol,
            'date': group['date'].iloc[-1],
            'ema_20': float(ema_20.iloc[-1]),
            'ema_50': float(ema_50.iloc[-1]),
            'ema_200': current_ema_200,
            'rsi_14': latest_rsi,
            'below_200ema': is_below_200
        })
        
    return updates

def update_db_with_indicators(updates: list):
    """Commits calculated indicators back to the daily_prices table."""
    conn = get_connection()
    cur = conn.cursor()
    
    sql = """
        UPDATE daily_prices 
        SET ema_20 = %(ema_20)s, 
            ema_50 = %(ema_50)s, 
            ema_200 = %(ema_200)s, 
            rsi_14 = %(rsi_14)s, 
            below_200ema = %(below_200ema)s
        WHERE symbol = %(symbol)s AND date = %(date)s
    """
    
    from psycopg2.extras import execute_batch
    execute_batch(cur, sql, updates)
    
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Successfully committed indicators for {len(updates)} records.")

def run_indicator_engine():
    """Main execution loop for the indicator engine."""
    logger.info("Starting Indicator Engine...")
    add_indicator_columns_if_missing()
    
    # Fetch all symbols that need indicators (or just fetch all for simplicity in MVP)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT symbol FROM daily_prices")
    all_symbols = [r[0] for r in cur.fetchall()]
    cur.close()
    conn.close()
    
    if not all_symbols:
        logger.warning("No price data found to process.")
        return

    df, idx_df = fetch_data_for_symbols(all_symbols)
    updates = compute_indicators(df, idx_df)
    
    if updates:
        update_db_with_indicators(updates)
        logger.info("Indicator calculation complete.")

if __name__ == "__main__":
    run_indicator_engine()