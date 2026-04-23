
import os, sys
# Ensure we can import from engine_core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from engine_core.db import get_connection
from psycopg2.extras import execute_batch

def force_sync():
    print('🚀 Starting Manual Force Sync...')
    try:
        conn = get_connection()
    except Exception as e:
        print(f'❌ Connection Failed: {e}')
        print('Ensure your DATABASE_URL is set and correct.')
        return
    
    # 1. Fetch ALL index data
    with conn.cursor() as cur:
        cur.execute('SELECT date, close FROM public.market_index_prices WHERE symbol = \'NIFTY50\' ORDER BY date')
        rows = cur.fetchall()
    
    if not rows:
        print('❌ No index data found in DB. Run ingestion first.')
        conn.close()
        return

    # Handle both tuple and dict rows
    if rows and not isinstance(rows[0], dict):
        data = [{'date': r[0], 'close': r[1]} for r in rows]
    else:
        data = [dict(r) for r in rows]
        
    df = pd.DataFrame(data)
    df['close'] = pd.to_numeric(df['close'])
    
    # 2. Compute Regime
    df['sma_200'] = df['close'].rolling(window=200, min_periods=1).mean()
    df['sma_200_slope_20'] = df['sma_200'].diff(20)
    
    def classify(row):
        if pd.isna(row['sma_200']) or pd.isna(row['sma_200_slope_20']): return 'NEUTRAL'
        close = float(row['close'])
        sma = float(row['sma_200'])
        slope = float(row['sma_200_slope_20'])
        if close > sma and slope > 0: return 'BULL'
        if close < sma and slope < 0: return 'BEAR'
        return 'NEUTRAL'
        
    df['classification'] = df.apply(classify, axis=1)
    update_data = df[['date', 'sma_200', 'sma_200_slope_20', 'classification']].replace({np.nan: None}).to_dict('records')

    # 3. Write to DB
    with conn.cursor() as cur:
        sql = '''
            INSERT INTO public.market_regime (date, sma_200, sma_200_slope_20, classification)
            VALUES (%(date)s, %(sma_200)s, %(sma_200_slope_20)s, %(classification)s)
            ON CONFLICT (date) DO UPDATE SET 
                sma_200 = EXCLUDED.sma_200,
                sma_200_slope_20 = EXCLUDED.sma_200_slope_20,
                classification = EXCLUDED.classification;
        '''
        execute_batch(cur, sql, update_data)
        conn.commit()
    
    print(f'✅ Successfully synced {len(update_data)} days of regime data.')
    print(f'📊 Latest Date: {df["date"].max()} -> {df["classification"].iloc[-1]}')
    conn.close()

if __name__ == '__main__':
    force_sync()
