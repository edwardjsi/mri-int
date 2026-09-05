import yfinance as yf
import pandas as pd
import numpy as np

symbols = {
    'MRF': ('MRF.NS', '2026-01-14', '2026-01-17'),
    'BAJFINANCE': ('BAJFINANCE.NS', '2005-07-27', '2005-07-30'),
    'BEL': ('BEL.NS', '2005-07-27', '2005-07-30'),
    'GLENMARK': ('GLENMARK.NS', '2003-04-01', '2003-04-04'),
    'CIPLA': ('CIPLA.NS', '2003-11-26', '2003-11-29'),
    'NUVAMA': ('NUVAMA.NS', '2026-01-14', '2026-01-17'),
    'AIAENG': ('AIAENG.NS', '2026-01-14', '2026-01-17'),
    'PATANJALI': ('PATANJALI.NS', '2005-07-27', '2005-07-30')
}

def analyze():
    for name, (yf_sym, start, end) in symbols.items():
        print(f"\n--- {name} ({yf_sym}) ---")
        try:
            df = yf.download(yf_sym, start=start, end=end, auto_adjust=False, actions=True, progress=False)
            if df.empty:
                print("No data.")
                continue
                
            # yfinance returns MultiIndex columns sometimes now, flatten them
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
                
            # Rename columns to standard lowercase
            df.columns = [c.lower() for c in df.columns]
            
            # Print the dataframe
            cols_to_print = [c for c in ['open', 'high', 'low', 'close', 'adj close', 'volume', 'dividends', 'stock splits'] if c in df.columns]
            print(df[cols_to_print])
            
            # Check if there is a big jump in raw close vs adj close
            if 'adj close' in df.columns:
                df['adj_ratio'] = df['adj close'] / df['close']
                print(f"Adjustment Ratios:\n{df['adj_ratio']}")
                
                # Let's reconstruct adjusted OHLC
                df['adj_open'] = df['open'] * df['adj_ratio']
                df['adj_high'] = df['high'] * df['adj_ratio']
                df['adj_low'] = df['low'] * df['adj_ratio']
                
                # Calculate adjusted daily return
                df['adj_ret'] = df['adj close'].pct_change()
                df['raw_ret'] = df['close'].pct_change()
                
                print(f"Raw Returns:\n{df['raw_ret']}")
                print(f"Adjusted Returns:\n{df['adj_ret']}")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    analyze()
