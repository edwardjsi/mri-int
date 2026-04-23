import pandas as pd
import numpy as np
# DEBUG: VERSION 100.5 - NO PANDAS SQL
print("DEBUG: LOADING engine_core/regime_engine.py VERSION 100.5")
import psycopg2
from psycopg2.extras import execute_batch
from scipy.stats import linregress
import logging
from engine_core.db import get_connection

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
        CREATE INDEX IF NOT EXISTS idx_stock_scores_symbol_date ON stock_scores(symbol, date DESC);
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
        if not np.isnan(y).any():
            slope, _, _, _, _ = linregress(x, y)
            result[i] = slope
    return pd.Series(result, index=s.index)

def compute_market_regime():
    """Calculates market regime (NIFTY 50) incrementally."""
    logger.info("Computing Market Regime based on Nifty 50...")
    conn = get_connection()
    
    # Direct fetch to avoid pd.read_sql / RealDictCursor incompatibility
    with conn.cursor() as cur:
        cur.execute("""
            SELECT date, close 
            FROM public.market_index_prices 
            WHERE symbol = 'NIFTY50' 
            ORDER BY date
        """)
        rows = cur.fetchall()
    
    if not rows:
        logger.warning("No index data found in public.market_index_prices for NIFTY50.")
        conn.close()
        return
        
    idx_df = pd.DataFrame([dict(r) for r in rows])
    
    # Force numeric conversion for pandas
    idx_df['close'] = pd.to_numeric(idx_df['close'], errors='coerce')
    idx_df = idx_df.dropna(subset=['close'])

    # Force numeric conversion for pandas
    idx_df['close'] = pd.to_numeric(idx_df['close'], errors='coerce')
    idx_df = idx_df.dropna(subset=['close'])

    # SMA & Slope logic
    idx_df['sma_200'] = idx_df['close'].rolling(window=200, min_periods=1).mean()
    idx_df['sma_200_slope_20'] = idx_df['sma_200'].diff(20)
    
    def classify(row):
        # Safety: if SMA is missing, we can't determine a trend
        if pd.isna(row['sma_200']) or pd.isna(row['sma_200_slope_20']):
            return 'NEUTRAL'
        
        close = float(row['close'])
        sma = float(row['sma_200'])
        slope = float(row['sma_200_slope_20'])
        
        if close > sma and slope > 0: return 'BULL'
        elif close < sma and slope < 0: return 'BEAR'
        else: return 'NEUTRAL'
            
    idx_df['classification'] = idx_df.apply(classify, axis=1)
    idx_df['sma_200'] = idx_df['sma_200'].round(4)
    idx_df['sma_200_slope_20'] = idx_df['sma_200_slope_20'].round(4)
    
    # Update the entire range from the fetched data
    update_data = idx_df[['date', 'sma_200', 'sma_200_slope_20', 'classification']].replace({np.nan: None}).to_dict('records')

    if not update_data:
        logger.warning("No regime data to write.")
        return

    cur = conn.cursor()
    sql = """
        INSERT INTO public.market_regime (date, sma_200, sma_200_slope_20, classification)
        VALUES (%(date)s, %(sma_200)s, %(sma_200_slope_20)s, %(classification)s)
        ON CONFLICT (date) DO UPDATE SET 
            sma_200 = EXCLUDED.sma_200,
            sma_200_slope_20 = EXCLUDED.sma_200_slope_20,
            classification = EXCLUDED.classification;
    """
    execute_batch(cur, sql, update_data, page_size=100)
    conn.commit()
    logger.info(f"✅ Wrote {len(update_data)} rows to public.market_regime.")
    
    # Health check: log what we computed
    latest = idx_df.iloc[-1] if not idx_df.empty else None
    if latest is not None:
        logger.info(f"✅ Regime updated through {latest['date']} -> {latest['classification']}")
    
    cur.close()
    conn.close()

def compute_stock_scores_for_symbols(symbols: list[str]):
    """
    Compute scores only for provided symbols. 
    Includes health checks to detect when indicators are missing.
    """
    symbols_clean = [str(s).upper().strip() for s in (symbols or []) if str(s).strip()]
    if not symbols_clean:
        return

    create_market_regime_and_scores_tables()
    conn = get_connection()
    
    try:
        # 1. Fetch data - use a long enough window to compute ADX/RSI and score components
        sql = """
            SELECT dp.symbol, dp.date, dp.close, dp.volume, dp.ema_50, dp.ema_200,
                   dp.ema_200_slope_20, dp.rolling_high_6m, dp.avg_volume_20d, dp.rs_90d
            FROM daily_prices dp
            WHERE dp.symbol = ANY(%s)
            AND dp.date >= (SELECT MAX(date) FROM daily_prices) - INTERVAL '255 days'
            ORDER BY dp.symbol, dp.date
        """
        with conn.cursor() as cur:
            cur.execute(sql, (symbols_clean,))
            rows = cur.fetchall()
        df = pd.DataFrame([dict(r) for r in rows])

        if df.empty:
            logger.warning("⚠️ No rows found for targeted scoring.")
            return

        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        df = df[df["date"].notna()].copy()
        df["symbol"] = df["symbol"].astype(str)
        df = df[df["symbol"].str.lower() != "symbol"].copy()

        numeric_cols = [
            "high",
            "low",
            "close",
            "volume",
            "ema_50",
            "ema_200",
            "ema_200_slope_20",
            "rolling_high_6m",
            "avg_volume_20d",
            "rs_90d",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # HEALTH CHECK: Detect when indicators are mostly NULL
        # This catches the case where ingestion ran but indicators didn't compute
        latest_date = df['date'].max()
        latest_rows = df[df['date'] == latest_date]
        null_ema_count = latest_rows['ema_50'].isna().sum()
        total_latest = len(latest_rows)
        
        if total_latest > 0 and null_ema_count / total_latest > 0.5:
            logger.warning(
                f"⚠️ HEALTH CHECK: {null_ema_count}/{total_latest} symbols have NULL ema_50 "
                f"on {latest_date}. Indicators may not have been computed yet!"
            )

        # 2. Safety: Fill NaNs to avoid the '>=' TypeError crash
        df['rolling_high_6m'] = df['rolling_high_6m'].fillna(df['close'])
        df['ema_50'] = df['ema_50'].fillna(df['close'])  # Fallback to close
        df['ema_200'] = df['ema_200'].fillna(df['ema_50'])  # Fallback trend
        df['ema_200_slope_20'] = df['ema_200_slope_20'].fillna(0)
        df['avg_volume_20d'] = df['avg_volume_20d'].fillna(df['volume'])
        df['rs_90d'] = df['rs_90d'].fillna(0)

        # 3. Calculate MRI Conditions & Weighted Scores
        df['condition_ema_50_200'] = (df['ema_50'] >= df['ema_200']).astype(bool)
        df['condition_ema_200_slope'] = (df['ema_200_slope_20'] >= 0).astype(bool)
        df['condition_6m_high'] = (df['close'] >= df['rolling_high_6m'] * 0.99).astype(bool)
        df['condition_volume'] = (df['volume'] > (1.3 * df['avg_volume_20d'])).astype(bool)
        df['condition_rs'] = (df['rs_90d'] > 0).astype(bool)

        # Apply Weights (Total = 100)
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

        # Log Top 5 stocks for latest date to debug Golden Path
        latest_scored = df[df['date'] == latest_date].sort_values('total_score', ascending=False).head(10)
        logger.info(f"Top 10 scores for {latest_date}:")
        for _, r in latest_scored.iterrows():
            logger.info(f"  {r['symbol']}: {r['total_score']} (EMA:{r['condition_ema_50_200']}, Slope:{r['condition_ema_200_slope']}, RS:{r['condition_rs']}, High:{r['condition_6m_high']}, Vol:{r['condition_volume']})")

        cur = conn.cursor()
        insert_sql = """
            INSERT INTO stock_scores (date, symbol, total_score, condition_ema_50_200,
                condition_ema_200_slope, condition_6m_high, condition_volume, condition_rs
            ) VALUES (
                %(date)s, %(symbol)s, %(total_score)s, %(condition_ema_50_200)s,
                %(condition_ema_200_slope)s, %(condition_6m_high)s, %(condition_volume)s, %(condition_rs)s
            ) ON CONFLICT (date, symbol) DO UPDATE SET
                total_score = EXCLUDED.total_score,
                condition_ema_50_200 = EXCLUDED.condition_ema_50_200,
                condition_ema_200_slope = EXCLUDED.condition_ema_200_slope,
                condition_6m_high = EXCLUDED.condition_6m_high,
                condition_volume = EXCLUDED.condition_volume,
                condition_rs = EXCLUDED.condition_rs;
        """
        execute_batch(cur, insert_sql, update_data, page_size=5000)
        conn.commit()
        cur.close()
        logger.info(f"✅ Scoring complete: {len(update_data)} score rows written for {len(symbols_clean)} symbols")

    finally:
        conn.close()

def compute_stock_scores():
    """Aggressive daily scoring: ensures all symbols get graded for the newest data."""
    create_market_regime_and_scores_tables()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT symbol FROM daily_prices")
        rows = cur.fetchall()
        symbols = [r["symbol"] if isinstance(r, dict) else r[0] for r in rows]
        cur.close()
        
        if not symbols:
            logger.warning("⚠️ No symbols found in daily_prices for scoring.")
            return

        logger.info(f"📊 Computing/Refreshing scores for {len(symbols)} symbols...")
        compute_stock_scores_for_symbols(symbols)
    finally:
        conn.close()

if __name__ == "__main__":
    create_market_regime_and_scores_tables()
    compute_market_regime()
    compute_stock_scores()
