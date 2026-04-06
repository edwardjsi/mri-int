import pandas as pd
import numpy as np
import logging
from engine_core.db import get_connection
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_indicator_columns_if_missing():
    """Ensures all required columns exist in daily_prices."""
    conn = get_connection()
    cur = conn.cursor()
    columns = [
        ("ema_20", "NUMERIC"), 
        ("ema_50", "NUMERIC"), 
        ("ema_200", "NUMERIC"), 
        ("rsi_14", "NUMERIC"), 
        ("below_200ema", "BOOLEAN"),
        ("ema_200_slope_20", "NUMERIC"),
        ("rolling_high_6m", "NUMERIC"),
        ("avg_volume_20d", "NUMERIC"),
        ("rs_90d", "NUMERIC")
    ]
    for col_name, col_type in columns:
        cur.execute(f"""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                               WHERE table_name='daily_prices' AND column_name='{col_name}') 
                THEN 
                    ALTER TABLE daily_prices ADD COLUMN {col_name} {col_type}; 
                END IF; 
            END $$;
        """)
    conn.commit()
    cur.close()
    conn.close()

def fetch_data(symbols=None):
    """
    Incremental fetch: finds symbols with ANY NULL indicator columns in
    the recent window (last 5 days). This catches newly ingested rows
    that have prices but no computed indicators yet.
    Fetches full 255-day history for those symbols for calculation accuracy.
    """
    conn = get_connection()
    try:
        if not symbols:
            cur = conn.cursor()
            # FIX: Find symbols that have rows with NULL indicators in the
            # recent window — not just globally. This catches new daily rows.
            cur.execute("""
                SELECT DISTINCT symbol FROM daily_prices
                WHERE date >= (SELECT MAX(date) FROM daily_prices) - INTERVAL '30 days'
                  AND (ema_50 IS NULL OR ema_200 IS NULL OR rs_90d IS NULL
                       OR avg_volume_20d IS NULL OR rolling_high_6m IS NULL)
            """)
            symbols = [r[0] for r in cur.fetchall()]
            cur.close()
            
        if not symbols:
            logger.info("✅ All symbols have indicators up to date.")
            return pd.DataFrame(), pd.DataFrame()

        logger.info(f"📊 Computing indicators for {len(symbols)} symbols with missing data...")
        
        # Fetch the last 255 days for these symbols
        # (255 is enough for a stable 200 EMA and 6-month high)
        sql = """
            SELECT symbol, date, high, close, volume, ema_20, ema_50, ema_200 
            FROM daily_prices 
            WHERE symbol = ANY(%s)
            AND date >= (SELECT MAX(date) FROM daily_prices) - INTERVAL '255 days'
            ORDER BY symbol, date
        """
        df = pd.read_sql(sql, conn, params=(symbols,))
        idx_df = pd.read_sql("SELECT date, close as idx_close FROM index_prices WHERE symbol = 'NIFTY50' ORDER BY date", conn)
        return df, idx_df
    finally:
        conn.close()

def compute_indicators(df, idx_df):
    """Calculates all technical indicators including slopes and relative strength."""
    if df.empty: return []
    
    updates = []
    for symbol in df['symbol'].unique():
        s_df = df[df['symbol'] == symbol].copy().sort_values('date')
        if len(s_df) < 20: continue
        
        # 1. EMAs
        s_df['ema_20'] = s_df['close'].ewm(span=20, adjust=False).mean()
        s_df['ema_50'] = s_df['close'].ewm(span=50, adjust=False).mean()
        s_df['ema_200'] = s_df['close'].ewm(span=200, adjust=False).mean() if len(s_df) >= 200 else s_df['ema_50']
        
        # 2. EMA 200 Slope (20-day regression equivalent)
        s_df['ema_200_slope_20'] = s_df['ema_200'].diff(20)
        
        # 3. RSI
        delta = s_df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        s_df['rsi_14'] = 100 - (100 / (1 + rs))
        
        # 4. Misc indicators
        s_df['below_200ema'] = s_df['close'] < s_df['ema_200']
        s_df['rolling_high_6m'] = s_df['close'].rolling(window=126, min_periods=20).max()
        s_df['avg_volume_20d'] = s_df['volume'].rolling(window=20).mean()
        
        # 5. Relative Strength (RS_90D) - Simplified calculation
        if not idx_df.empty:
            merged = pd.merge(s_df[['date', 'close']], idx_df[['date', 'idx_close']], on='date', how='inner')
            if len(merged) > 90:
                merged['stock_ret'] = merged['close'] / merged['close'].shift(90)
                merged['idx_ret'] = merged['idx_close'] / merged['idx_close'].shift(90)
                merged['rs_90d'] = (merged['stock_ret'] / merged['idx_ret']) * 100
                s_df = pd.merge(s_df, merged[['date', 'rs_90d']], on='date', how='left')

        # Clean up NaNs for Postgres
        s_df = s_df.replace({np.nan: None})

        # FIX: Always write the latest rows. The UPDATE SQL is idempotent
        # (ON symbol+date), so writing the same correct value twice is harmless.
        # The old filter "if ema_50 is None" was wrong — it checked AFTER
        # computing, so the freshly-computed value was never None, and updates
        # were silently discarded.
        for _, row in s_df.tail(10).iterrows():
            updates.append({
                'symbol': row['symbol'], 
                'date': row['date'],
                'ema_20': row.get('ema_20'), 
                'ema_50': row.get('ema_50'), 
                'ema_200': row.get('ema_200'),
                'rsi_14': row.get('rsi_14') if row.get('rsi_14') is not None else 50,
                'below_200ema': bool(row.get('below_200ema', False)),
                'ema_200_slope_20': row.get('ema_200_slope_20'),
                'rolling_high_6m': row.get('rolling_high_6m'),
                'avg_volume_20d': row.get('avg_volume_20d'),
                'rs_90d': row.get('rs_90d')
            })
    
    logger.info(f"📊 Indicator engine prepared {len(updates)} row updates across {df['symbol'].nunique()} symbols")
    return updates

def update_db_with_indicators(updates):
    """Bulk update the daily_prices table."""
    if not updates:
        logger.info("⚠️ No indicator updates to write (0 rows). Check if ingestion produced new data.")
        return
    conn = get_connection()
    try:
        cur = conn.cursor()
        sql = """
            UPDATE daily_prices 
            SET ema_20=%(ema_20)s, ema_50=%(ema_50)s, ema_200=%(ema_200)s, 
                rsi_14=%(rsi_14)s, below_200ema=%(below_200ema)s,
                ema_200_slope_20=%(ema_200_slope_20)s, rolling_high_6m=%(rolling_high_6m)s,
                avg_volume_20d=%(avg_volume_20d)s, rs_90d=%(rs_90d)s
            WHERE symbol=%(symbol)s AND date=%(date)s
        """
        from psycopg2.extras import execute_batch
        execute_batch(cur, sql, updates, page_size=2000)
        conn.commit()
        logger.info(f"✅ Wrote {len(updates)} indicator updates to DB")
        cur.close()
    finally:
        conn.close()

def compute_indicators_for_symbols(symbols: list):
    """API Bridge function for on-demand scoring."""
    if not symbols: return
    add_indicator_columns_if_missing()
    data_df, idx_df = fetch_data(symbols)
    updates = compute_indicators(data_df, idx_df)
    update_db_with_indicators(updates)