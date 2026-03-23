import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extras import execute_batch
from scipy.stats import linregress
import logging
from src.db import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_market_regime_and_scores_tables():
    """Create regime and scores tables if they don't exist (preserves existing data)."""
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_regime (
            date DATE PRIMARY KEY,
            sma_200 NUMERIC(12,4),
            sma_200_slope_20 NUMERIC(12,4),
            classification VARCHAR(20)
        );

        CREATE TABLE IF NOT EXISTS stock_scores (
            date DATE,
            symbol VARCHAR(20),
            total_score INT,
            condition_ema_50_200 BOOLEAN,
            condition_ema_200_slope BOOLEAN,
            condition_6m_high BOOLEAN,
            condition_volume BOOLEAN,
            condition_rs BOOLEAN,
            PRIMARY KEY (date, symbol)
        );
        
        CREATE INDEX IF NOT EXISTS idx_stock_scores_date ON stock_scores(date);
    """)
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Market regime and stock scores tables ready.")

def calc_slope(s):
    """Calculate 20-day linear regression slope with safety for NaNs."""
    result = np.full(len(s), np.nan)
    s_values = s.values
    x = np.arange(20)
    for i in range(19, len(s)):
        y = s_values[i-19:i+1]
        # Safety: check if we have enough non-nan data for linregress
        if not np.isnan(y).any():
            slope, _, _, _, _ = linregress(x, y)
            result[i] = slope
    return pd.Series(result, index=s.index)

def compute_market_regime():
    logger.info("Computing Market Regime based on Nifty 50...")
    conn = get_connection()
    idx_df = pd.read_sql("SELECT date, close FROM index_prices WHERE symbol = 'NIFTY50' ORDER BY date", conn)
    
    if idx_df.empty:
        logger.warning("No Nifty 50 data found.")
        conn.close()
        return

    # Calculate 200 SMA and slope
    idx_df['sma_200'] = idx_df['close'].rolling(window=200, min_periods=1).mean()
    idx_df['sma_200_slope_20'] = calc_slope(idx_df['sma_200'])
    
    def classify(row):
        if pd.isna(row['sma_200_slope_20']):
            return 'NEUTRAL'
        if row['close'] > row['sma_200'] and row['sma_200_slope_20'] > 0:
            return 'BULL'
        elif row['close'] < row['sma_200'] and row['sma_200_slope_20'] < 0:
            return 'BEAR'
        else:
            return 'NEUTRAL'
            
    idx_df['classification'] = idx_df.apply(classify, axis=1)
    
    # Persist to DB
    idx_df = idx_df.replace({np.nan: None})
    update_data = idx_df[['date', 'sma_200', 'sma_200_slope_20', 'classification']].to_dict('records')

    cur = conn.cursor()
    sql = """
        INSERT INTO market_regime (date, sma_200, sma_200_slope_20, classification)
        VALUES (%(date)s, %(sma_200)s, %(sma_200_slope_20)s, %(classification)s)
        ON CONFLICT (date) DO UPDATE SET 
            sma_200 = EXCLUDED.sma_200,
            sma_200_slope_20 = EXCLUDED.sma_200_slope_20,
            classification = EXCLUDED.classification;
    """
    execute_batch(cur, sql, update_data, page_size=1000)
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Regime computation complete.")

def compute_stock_scores_for_symbols(symbols: list[str]):
    """
    Compute scores only for provided symbols. 
    FIXED: Handles float vs NoneType comparison crash.
    """
    symbols_clean = [str(s).upper().strip() for s in (symbols or []) if str(s).strip()]
    if not symbols_clean:
        return

    create_market_regime_and_scores_tables()
    conn = get_connection()
    
    try:
        # 1. Fetch data - Incremental: Only fetch last 10 days since indicators are already stored
        sql = """
            SELECT dp.symbol, dp.date, dp.close, dp.volume, dp.ema_50, dp.ema_200,
                   dp.ema_200_slope_20, dp.rolling_high_6m, dp.avg_volume_20d, dp.rs_90d
            FROM daily_prices dp
            WHERE dp.symbol = ANY(%s)
            AND dp.date >= (SELECT MAX(date) FROM daily_prices) - INTERVAL '10 days'
            ORDER BY dp.symbol, dp.date
        """
        df = pd.read_sql(sql, conn, params=(symbols_clean,))


        if df.empty:
            logger.info("No rows found for targeted scoring.")
            return

        # 2. Safety: Fill NaNs to avoid the '>=' TypeError crash
        # This replaces the 'None' values with logical fallbacks so math doesn't break
        df['rolling_high_6m'] = df['rolling_high_6m'].fillna(df['close'])
        df['ema_200'] = df['ema_200'].fillna(df['ema_50']) # Fallback trend
        df['ema_200_slope_20'] = df['ema_200_slope_20'].fillna(0)
        df['avg_volume_20d'] = df['avg_volume_20d'].fillna(df['volume'])
        df['rs_90d'] = df['rs_90d'].fillna(0)

        # 3. Calculate MRI Conditions & Weighted Scores
        df['condition_ema_50_200'] = (df['ema_50'] > df['ema_200']).astype(bool)
        df['condition_ema_200_slope'] = (df['ema_200_slope_20'] > 0).astype(bool)
        df['condition_6m_high'] = (df['close'] >= df['rolling_high_6m']).astype(bool)
        df['condition_volume'] = (df['volume'] > (1.5 * df['avg_volume_20d'])).astype(bool)
        df['condition_rs'] = (df['rs_90d'] > 0).astype(bool)

        # Apply Weights (Total = 100)
        # EMA 50/200: 25 pts, Slope: 25 pts, RS: 20 pts, 6m High: 20 pts, Volume: 10 pts
        df['total_score'] = (
            df['condition_ema_50_200'].astype(int) * 25 +
            df['condition_ema_200_slope'].astype(int) * 25 +
            df['condition_rs'].astype(int) * 20 +
            df['condition_6m_high'].astype(int) * 20 +
            df['condition_volume'].astype(int) * 10
        )

        # 4. Write back to DB
        df = df.replace({np.nan: None})
        update_data = df[['date', 'symbol', 'total_score', 'condition_ema_50_200', 
                          'condition_ema_200_slope', 'condition_6m_high', 
                          'condition_volume', 'condition_rs']].to_dict('records')

        cur = conn.cursor()
        insert_sql = """
            INSERT INTO stock_scores (date, symbol, total_score, condition_ema_50_200,
                condition_ema_200_slope, condition_6m_high, condition_volume, condition_rs
            ) VALUES (
                %(date)s, %(symbol)s, %(total_score)s, %(condition_ema_50_200)s,
                %(condition_ema_200_slope)s, %(condition_6m_high)s, %(condition_volume)s, %(condition_rs)s
            ) ON CONFLICT (date, symbol) DO UPDATE SET total_score = EXCLUDED.total_score;
        """
        execute_batch(cur, insert_sql, update_data, page_size=5000)
        conn.commit()
        cur.close()
        logger.info(f"Targeted scoring complete for {len(symbols_clean)} symbols.")

    finally:
        conn.close()

# Keep your original background bulk processing function
def compute_market_regime():
    """Calculates market regime (NIFTY 50) incrementally."""
    conn = get_connection()
    # Fetch last 255 days of Nifty to compute 200 SMA
    idx_df = pd.read_sql("SELECT date, close FROM index_prices WHERE symbol = 'NIFTY50' AND date >= (SELECT MAX(date) FROM index_prices) - INTERVAL '255 days' ORDER BY date", conn)
    
    if idx_df.empty:
        logger.warning("No index data for regime.")
        conn.close()
        return

    # SMA & Slope logic
    idx_df['sma_200'] = idx_df['close'].rolling(window=200).mean()
    idx_df['sma_200_slope_20'] = idx_df['sma_200'].diff(20)
    
    def classify(row):
        if pd.isna(row['sma_200_slope_20']): return 'NEUTRAL'
        if row['close'] > row['sma_200'] and row['sma_200_slope_20'] > 0: return 'BULL'
        elif row['close'] < row['sma_200'] and row['sma_200_slope_20'] < 0: return 'BEAR'
        else: return 'NEUTRAL'
            
    idx_df['classification'] = idx_df.apply(classify, axis=1)
    
    # Only update the latest 5 days (saves writes)
    idx_df = idx_df.tail(5).replace({np.nan: None})
    update_data = idx_df[['date', 'sma_200', 'sma_200_slope_20', 'classification']].to_dict('records')

    cur = conn.cursor()
    sql = """
        INSERT INTO market_regime (date, sma_200, sma_200_slope_20, classification)
        VALUES (%(date)s, %(sma_200)s, %(sma_200_slope_20)s, %(classification)s)
        ON CONFLICT (date) DO UPDATE SET 
            sma_200 = EXCLUDED.sma_200,
            sma_200_slope_20 = EXCLUDED.sma_200_slope_20,
            classification = EXCLUDED.classification;
    """
    execute_batch(cur, sql, update_data, page_size=100)
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Incremental regime complete.")

def compute_stock_scores():
    """Incremental scoring: only process newest dates for all symbols."""
    create_market_regime_and_scores_tables()
    conn = get_connection()
    try:
        # Detect dates needing scores (where data exists in daily_prices but not in stock_scores)
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT(date) FROM daily_prices 
            WHERE date >= (SELECT MAX(date) FROM daily_prices) - INTERVAL '10 days'
            AND date NOT IN (SELECT DISTINCT(date) FROM stock_scores)
        """)
        dates_to_process = [r[0] for r in cur.fetchall()]
        cur.close()
        
        if not dates_to_process:
            logger.info("Stock scores already up to date.")
            return

        # Fetch symbols to process
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT symbol FROM daily_prices")
        symbols = [r[0] for r in cur.fetchall()]
        cur.close()
        
        logger.info(f"Computing scores for {len(dates_to_process)} dates across {len(symbols)} symbols...")
        compute_stock_scores_for_symbols(symbols)
    finally:
        conn.close()

if __name__ == "__main__":
    create_market_regime_and_scores_tables()
    compute_market_regime()
    compute_stock_scores()