import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_core.db import fetch_df
import time

def main():
    print("Fetching daily prices...")
    start = time.time()
    query = "SELECT symbol, date, open, high, low, close, volume, ema_50, ema_150, ema_200, sma_200, atr_20, vol_sma_50 FROM daily_prices"
    
    # Actually wait, maybe some columns don't exist. Let's just select the core ones required for the audit and backtest.
    # The prompt says: "The export must contain at minimum: symbol, date, open, high, low, close, volume"
    query = "SELECT symbol, date, open, high, low, close, volume FROM daily_prices"
    
    try:
        df = fetch_df(query)
    except Exception as e:
        print(f"Error fetching: {e}")
        return

    print(f"Fetched {len(df)} rows in {time.time() - start:.2f}s")
    
    print(f"Row count: {len(df)}")
    print(f"Symbol count: {df['symbol'].nunique()}")
    print(f"Minimum date: {df['date'].min()}")
    print(f"Maximum date: {df['date'].max()}")
    duplicates = df.duplicated(subset=['symbol', 'date']).sum()
    print(f"Duplicate symbol/date pairs: {duplicates}")
    
    df.to_pickle('scratch/yahoo_restored.pkl')
    print("Saved to scratch/yahoo_restored.pkl")

if __name__ == '__main__':
    main()
