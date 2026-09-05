import pandas as pd
import numpy as np

def run_audit():
    print("Loading restored data...")
    df = pd.read_pickle('scratch/yahoo_restored.pkl')
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    print("\n--- A. DUPLICATE SYMBOL/DATE ---")
    dups = df.duplicated(subset=['symbol', 'date']).sum()
    print(f"Duplicates: {dups}")
    
    print("\n--- B. MISSING OHLC ---")
    missing_ohlc = df[['open', 'high', 'low', 'close']].isna().sum()
    print(missing_ohlc)
    
    print("\n--- C. NEGATIVE VOLUME ---")
    neg_vol = (df['volume'] < 0).sum()
    print(f"Negative Volume: {neg_vol}")
    
    print("\n--- D. INVALID OHLC RELATIONSHIPS ---")
    invalid_high = (df['high'] < df['open']) | (df['high'] < df['close']) | (df['high'] < df['low'])
    invalid_low = (df['low'] > df['open']) | (df['low'] > df['close']) | (df['low'] > df['high'])
    print(f"Invalid High: {invalid_high.sum()}")
    print(f"Invalid Low: {invalid_low.sum()}")
    
    print("\n--- E. EXTREME DAILY RETURNS ---")
    df['prev_close'] = df.groupby('symbol')['close'].shift(1)
    df['daily_return'] = (df['close'] - df['prev_close']) / df['prev_close']
    extreme_returns = df[(df['daily_return'] > 0.5) | (df['daily_return'] < -0.5)]
    print(f"Extreme daily returns (>50% or <-50%): {len(extreme_returns)}")
    
    print("\n--- H. ABNORMAL ZERO-VOLUME ---")
    zero_vol = (df['volume'] == 0).sum()
    print(f"Zero volume days: {zero_vol}")

    print("\n--- INVESTIGATING SPECIFIC ANOMALIES ---")
    anomalies = {
        'MRF': '2026-01-15',
    }
    
    symbols_to_check = ['MRF', 'BAJFINANCE', 'HINDZINC', 'GVT&D', 'BEL', 'PATANJALI', 'GLENMARK', 'NUVAMA', 'AIAENG', 'CIPLA']
    
    for sym in symbols_to_check:
        sym_df = df[df['symbol'] == sym]
        if sym_df.empty:
            print(f"{sym}: No data found.")
            continue
            
        print(f"\n[{sym}]")
        # Find max drops or jumps
        if len(sym_df) > 1:
            sym_df = sym_df.copy()
            sym_df['ret'] = (sym_df['close'] - sym_df['close'].shift(1)) / sym_df['close'].shift(1)
            min_ret = sym_df.loc[sym_df['ret'].idxmin()] if not sym_df['ret'].isna().all() else None
            max_ret = sym_df.loc[sym_df['ret'].idxmax()] if not sym_df['ret'].isna().all() else None
            
            if min_ret is not None:
                print(f"  Max Drop: {min_ret['ret']*100:.2f}% on {min_ret['date'].date()} (Close: {min_ret['close']})")
            if max_ret is not None:
                print(f"  Max Jump: {max_ret['ret']*100:.2f}% on {max_ret['date'].date()} (Close: {max_ret['close']})")
                
        if sym in anomalies:
            date_to_check = pd.to_datetime(anomalies[sym])
            day_data = sym_df[sym_df['date'] == date_to_check]
            if not day_data.empty:
                print(f"  Specific Date ({date_to_check.date()}):")
                print(day_data[['date', 'open', 'high', 'low', 'close', 'volume', 'daily_return']])
            else:
                print(f"  Specific Date ({date_to_check.date()}): No data found.")

if __name__ == '__main__':
    run_audit()
