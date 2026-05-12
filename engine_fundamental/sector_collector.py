import logging
import yfinance as yf
import pandas as pd
from engine_core.db import get_connection, fetch_df

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def compute_technical_indicators(df, nsei_df=None):
    """Compute EMA 50, EMA 200, and 90-day Relative Strength."""
    if df.empty:
        return df
        
    df = df.sort_values('date').copy()
    
    # EMAs
    df['ema_50'] = df['close_price'].ewm(span=50, adjust=False).mean()
    df['ema_200'] = df['close_price'].ewm(span=200, adjust=False).mean()
    
    # 90-day RS against NSEI
    if nsei_df is not None and not nsei_df.empty:
        # Merge with NSEI to ensure aligned dates
        nsei_df_sub = nsei_df[['date', 'close_price']].rename(columns={'close_price': 'nsei_close'})
        merged = pd.merge(df, nsei_df_sub, on='date', how='left')
        
        # Forward fill any missing NSEI values temporarily for calculation
        merged['nsei_close'] = merged['nsei_close'].ffill()
        
        # Ratio = Sector Close / NSEI Close
        merged['ratio'] = merged['close_price'] / merged['nsei_close']
        # 90-trading day shift (~ 4.5 months)
        merged['ratio_90d_ago'] = merged['ratio'].shift(90)
        
        merged['relative_strength_90d'] = (merged['ratio'] / merged['ratio_90d_ago']) - 1
        
        df['relative_strength_90d'] = merged['relative_strength_90d']
    else:
        df['relative_strength_90d'] = None
        
    return df

def fetch_and_store_sector_history():
    conn = get_connection()
    if not conn:
        logger.error("Database connection failed.")
        return
        
    try:
        cur = conn.cursor()
        
        # Fetch indices
        cur.execute("SELECT sector_id, nse_ticker FROM aae_sector_indices")
        indices = cur.fetchall()
        
        if not indices:
            logger.info("No sector indices found in DB.")
            return
            
        logger.info("Fetching Nifty 50 (^NSEI) for baseline RS calculation...")
        nsei_data = yf.download('^NSEI', period='2y', interval='1d', progress=False)
        nsei_df = None
        if not nsei_data.empty:
            if isinstance(nsei_data.columns, pd.MultiIndex):
                # Flatten multi-index
                nsei_data.columns = nsei_data.columns.get_level_values(0)
            nsei_df = nsei_data.reset_index()
            nsei_df.rename(columns={'Date': 'date', 'Close': 'close_price'}, inplace=True)
            nsei_df['date'] = pd.to_datetime(nsei_df['date']).dt.date
            
        for sector_id, ticker in indices:
            logger.info(f"Fetching history for {ticker} (ID: {sector_id})")
            
            # Fetch 2 years of data to ensure valid EMA 200 and RS 90d
            data = yf.download(ticker, period='2y', interval='1d', progress=False)
            
            if data.empty:
                logger.warning(f"No data fetched for {ticker}")
                continue
                
            if isinstance(data.columns, pd.MultiIndex):
                # Flatten multi-index if fetching single ticker somehow returned it
                data.columns = data.columns.get_level_values(0)
                
            df = data.reset_index()
            df.rename(columns={'Date': 'date', 'Close': 'close_price', 'Volume': 'volume'}, inplace=True)
            df['date'] = pd.to_datetime(df['date']).dt.date
            
            # Keep only required columns
            df = df[['date', 'close_price', 'volume']]
            df.dropna(subset=['close_price'], inplace=True)
            
            # Compute indicators
            df = compute_technical_indicators(df, nsei_df)
            
            # Insert into database
            insert_query = """
                INSERT INTO aae_sector_history (sector_id, date, close_price, volume, ema_50, ema_200, relative_strength_90d)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (sector_id, date) DO UPDATE SET
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume,
                    ema_50 = EXCLUDED.ema_50,
                    ema_200 = EXCLUDED.ema_200,
                    relative_strength_90d = EXCLUDED.relative_strength_90d;
            """
            
            records = []
            for _, row in df.iterrows():
                records.append((
                    sector_id,
                    row['date'],
                    float(row['close_price']) if pd.notnull(row['close_price']) else None,
                    int(row['volume']) if pd.notnull(row['volume']) else 0,
                    float(row['ema_50']) if pd.notnull(row['ema_50']) else None,
                    float(row['ema_200']) if pd.notnull(row['ema_200']) else None,
                    float(row['relative_strength_90d']) if pd.notnull(row['relative_strength_90d']) else None
                ))
            
            from psycopg2.extras import execute_batch
            execute_batch(cur, insert_query, records, page_size=1000)
            logger.info(f"Saved {len(records)} records for {ticker}.")
            
        conn.commit()
        logger.info("Sector history ingestion complete.")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error fetching sector history: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fetch_and_store_sector_history()
