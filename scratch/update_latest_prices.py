import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import sys
sys.path.append('.')
from engine_core.db import get_connection

def update_prices():
    conn = get_connection()
    cur = conn.cursor()
    
    # Get all distinct symbols from daily_prices
    cur.execute("SELECT DISTINCT symbol FROM daily_prices")
    symbols = [row['symbol'] for row in cur.fetchall()]
    print(f"Found {len(symbols)} symbols to update.")
    
    START_DATE = '2026-08-27'
    END_DATE = (datetime.today() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    inserted = 0
    failed = 0
    
    # Batch download for speed
    batch_size = 100
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        yf_symbols = [f"{sym}.NS" for sym in batch]
        print(f"Downloading batch {i//batch_size + 1}...")
        
        try:
            data = yf.download(yf_symbols, start=START_DATE, end=END_DATE, progress=False, auto_adjust=True)
            if data.empty:
                continue
                
            for sym in batch:
                yf_sym = f"{sym}.NS"
                if 'Close' not in data:
                    continue
                
                # Check if multi-index
                if isinstance(data.columns, pd.MultiIndex):
                    if yf_sym not in data['Close']:
                        continue
                    close_series = data['Close'][yf_sym]
                    open_series = data['Open'][yf_sym]
                    high_series = data['High'][yf_sym]
                    low_series = data['Low'][yf_sym]
                    vol_series = data['Volume'][yf_sym]
                else:
                    close_series = data['Close']
                    open_series = data['Open']
                    high_series = data['High']
                    low_series = data['Low']
                    vol_series = data['Volume']

                for date, close_val in close_series.items():
                    if pd.isna(close_val):
                        continue
                    
                    open_val = open_series[date]
                    high_val = high_series[date]
                    low_val = low_series[date]
                    vol_val = vol_series[date]
                    
                    cur.execute('''
                        INSERT INTO daily_prices (symbol, date, open, high, low, close, volume)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (symbol, date) DO NOTHING
                    ''', (sym, date.date(), float(open_val), float(high_val), float(low_val), float(close_val), int(vol_val)))
                    inserted += 1
            
            conn.commit()
            print(f"Batch inserted. Total inserted so far: {inserted}")
            
        except Exception as e:
            print(f"Batch failed: {e}")
            failed += 1
            
    print(f"Done. Inserted {inserted} new price records.")

if __name__ == "__main__":
    update_prices()
