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

def compute_market_regime():
    logger.info("Computing Market Regime based on Nifty 50...")
    conn = get_connection()
    idx_df = pd.read_sql("SELECT date, close FROM index_prices WHERE symbol = 'NIFTY50' ORDER BY date", conn)
    
    # Calculate 200 SMA and its 20-day slope
    idx_df['sma_200'] = idx_df['close'].rolling(window=200, min_periods=1).mean()
    idx_df['sma_200_slope_20'] = calc_slope(idx_df['sma_200'])
    
    # Classify Regime
    # BULL: Close > 200 SMA AND slope > 0
    # BEAR: Close < 200 SMA AND slope < 0
    # NEUTRAL: everything else
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
    update_data = idx_df[['date', 'sma_200', 'sma_200_slope_20', 'classification']].to_dict('records')
    idx_df.replace({np.nan: None}, inplace=True)
    update_data = [{k: (v if pd.notna(v) else None) for k, v in d.items()} for d in update_data]

    logger.info(f"Inserting {len(update_data)} Regime states...")
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
    
    bull_count = len(idx_df[idx_df['classification'] == 'BULL'])
    bear_count = len(idx_df[idx_df['classification'] == 'BEAR'])
    neutral_count = len(idx_df[idx_df['classification'] == 'NEUTRAL'])
    logger.info(f"Regime stats: BULL: {bull_count}, BEAR: {bear_count}, NEUTRAL: {neutral_count}")


def compute_stock_scores():
    """Compute 0-5 stock scores. Incremental: only processes rows not already in stock_scores."""
    read_conn = get_connection()

    # Check how many rows need scoring
    check_cur = read_conn.cursor()
    check_cur.execute("""
        SELECT COUNT(*) FROM daily_prices dp
        LEFT JOIN stock_scores ss ON dp.symbol = ss.symbol AND dp.date = ss.date
        WHERE (dp.ema_50 IS NOT NULL OR dp.rolling_high_6m IS NOT NULL)
          AND ss.date IS NULL
    """)
    pending_count = check_cur.fetchone()[0]
    check_cur.close()

    if pending_count == 0:
        logger.info("All rows already have scores. Skipping computation.")
        read_conn.close()
        return

    logger.info(f"Computing stock scores for {pending_count:,} new rows (skipping already-scored rows)...")
    
    # Only fetch rows that don't have scores yet
    sql = """
        SELECT dp.symbol, dp.date, dp.close, dp.volume, dp.ema_50, dp.ema_200, 
               dp.ema_200_slope_20, dp.rolling_high_6m, dp.avg_volume_20d, dp.rs_90d
        FROM daily_prices dp
        LEFT JOIN stock_scores ss ON dp.symbol = ss.symbol AND dp.date = ss.date
        WHERE (dp.ema_50 IS NOT NULL OR dp.rolling_high_6m IS NOT NULL)
          AND ss.date IS NULL
        ORDER BY dp.symbol, dp.date
    """
    
    cur = read_conn.cursor('cursor_scores_read')
    cur.itersize = 100000
    cur.execute(sql)
    
    columns = ['symbol', 'date', 'close', 'volume', 'ema_50', 'ema_200', 
               'ema_200_slope_20', 'rolling_high_6m', 'avg_volume_20d', 'rs_90d']
               
    total_inserted = 0
    chunk_count = 0
    
    while True:
        rows = cur.fetchmany(100000)
        if not rows:
            break
            
        chunk_count += 1
        logger.info(f"Processing chunk {chunk_count} ({len(rows)} rows)...")
        
        df = pd.DataFrame(rows, columns=columns)
        
        df['condition_ema_50_200'] = (df['ema_50'] > df['ema_200']).fillna(False).astype(bool)
        df['condition_ema_200_slope'] = (df['ema_200_slope_20'] > 0).fillna(False).astype(bool)
        df['condition_6m_high'] = (df['close'] >= df['rolling_high_6m']).fillna(False).astype(bool)
        df['condition_volume'] = (df['volume'] > (1.5 * df['avg_volume_20d'])).fillna(False).astype(bool)
        df['condition_rs'] = (df['rs_90d'] > 0).fillna(False).astype(bool)
        
        bool_cols = [
            'condition_ema_50_200', 'condition_ema_200_slope', 
            'condition_6m_high', 'condition_volume', 'condition_rs'
        ]
        df['total_score'] = df[bool_cols].sum(axis=1)

        df.replace({np.nan: None}, inplace=True)
        update_data = df[['date', 'symbol', 'total_score', 'condition_ema_50_200', 
                          'condition_ema_200_slope', 'condition_6m_high', 
                          'condition_volume', 'condition_rs']].to_dict('records')
                          
        write_conn = get_connection()
        insert_cur = write_conn.cursor()
        insert_sql = """
            INSERT INTO stock_scores (
                date, symbol, total_score, condition_ema_50_200, 
                condition_ema_200_slope, condition_6m_high, condition_volume, condition_rs
            ) VALUES (
                %(date)s, %(symbol)s, %(total_score)s, %(condition_ema_50_200)s,
                %(condition_ema_200_slope)s, %(condition_6m_high)s, %(condition_volume)s, %(condition_rs)s
            ) ON CONFLICT (date, symbol) DO NOTHING;
        """
        
        execute_batch(insert_cur, insert_sql, update_data, page_size=5000)
        write_conn.commit()
        insert_cur.close()
        write_conn.close()
        
        total_inserted += len(update_data)
        
    cur.close()
    read_conn.close()
    logger.info(f"Stock score computation complete. {total_inserted:,} new rows scored.")


def compute_stock_scores_for_symbols(symbols: list[str]):
    """
    Compute scores only for the provided symbols (fast path for on-demand portfolio grading).
    """
    symbols_clean = [str(s).upper().strip() for s in (symbols or []) if str(s).strip()]
    if not symbols_clean:
        logger.info("No symbols provided. Skipping targeted scoring.")
        return

    create_market_regime_and_scores_tables()

    conn = get_connection()
    try:
        pending_cur = conn.cursor()
        pending_cur.execute(
            """
            SELECT COUNT(*)
            FROM daily_prices dp
            LEFT JOIN stock_scores ss ON dp.symbol = ss.symbol AND dp.date = ss.date
            WHERE dp.symbol = ANY(%s)
              AND (dp.ema_50 IS NOT NULL OR dp.rolling_high_6m IS NOT NULL)
              AND ss.date IS NULL
            """,
            (symbols_clean,),
        )
        pending_count = pending_cur.fetchone()[0]
        pending_cur.close()

        if pending_count == 0:
            logger.info("All rows already have scores for provided symbols. Skipping targeted scoring.")
            return

        logger.info(f"Targeted scoring: {pending_count:,} row(s) pending for {len(symbols_clean)} symbol(s).")

        df = pd.read_sql(
            """
            SELECT dp.symbol, dp.date, dp.close, dp.volume, dp.ema_50, dp.ema_200,
                   dp.ema_200_slope_20, dp.rolling_high_6m, dp.avg_volume_20d, dp.rs_90d
            FROM daily_prices dp
            LEFT JOIN stock_scores ss ON dp.symbol = ss.symbol AND dp.date = ss.date
            WHERE dp.symbol = ANY(%s)
              AND (dp.ema_50 IS NOT NULL OR dp.rolling_high_6m IS NOT NULL)
              AND ss.date IS NULL
            ORDER BY dp.symbol, dp.date
            """,
            conn,
            params=(symbols_clean,),
        )

        if df is None or df.empty:
            logger.info("Targeted scoring query returned 0 rows. Nothing to do.")
            return

        df['condition_ema_50_200'] = (df['ema_50'] > df['ema_200']).fillna(False).astype(bool)
        df['condition_ema_200_slope'] = (df['ema_200_slope_20'] > 0).fillna(False).astype(bool)
        df['condition_6m_high'] = (df['close'] >= df['rolling_high_6m']).fillna(False).astype(bool)
        df['condition_volume'] = (df['volume'] > (1.5 * df['avg_volume_20d'])).fillna(False).astype(bool)
        df['condition_rs'] = (df['rs_90d'] > 0).fillna(False).astype(bool)

        bool_cols = [
            'condition_ema_50_200', 'condition_ema_200_slope',
            'condition_6m_high', 'condition_volume', 'condition_rs'
        ]
        df['total_score'] = df[bool_cols].sum(axis=1)

        df.replace({np.nan: None}, inplace=True)
        update_data = df[['date', 'symbol', 'total_score', 'condition_ema_50_200',
                          'condition_ema_200_slope', 'condition_6m_high',
                          'condition_volume', 'condition_rs']].to_dict('records')

        insert_cur = conn.cursor()
        insert_sql = """
            INSERT INTO stock_scores (
                date, symbol, total_score, condition_ema_50_200,
                condition_ema_200_slope, condition_6m_high, condition_volume, condition_rs
            ) VALUES (
                %(date)s, %(symbol)s, %(total_score)s, %(condition_ema_50_200)s,
                %(condition_ema_200_slope)s, %(condition_6m_high)s, %(condition_volume)s, %(condition_rs)s
            ) ON CONFLICT (date, symbol) DO NOTHING;
        """
        execute_batch(insert_cur, insert_sql, update_data, page_size=5000)
        conn.commit()
        insert_cur.close()

        logger.info(f"Targeted scoring complete. {len(update_data):,} row(s) scored.")
    finally:
        conn.close()


if __name__ == "__main__":
    create_market_regime_and_scores_tables()
    compute_market_regime()
    compute_stock_scores()
