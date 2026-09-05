import pandas as pd
import numpy as np
import time
import os
import sys

def main():
    print("Loading data...")
    # Load Benchmark
    bm = pd.read_csv('/home/immanuels/Desktop/mri-int/benchmarks/NSE500TRI.csv')
    bm['Date'] = pd.to_datetime(bm['Date'])
    bm = bm.sort_values('Date').reset_index(drop=True)
    
    # Forward fill benchmark for missing dates (like weekends/holidays where stocks traded)
    bm_full = bm.set_index('Date')['Total Returns Index']
    bm_full = pd.to_numeric(bm_full, errors='coerce').fillna(method='ffill')
    
    # Load Stocks
    df = pd.read_pickle('scratch/minervini_base.pkl') if os.path.exists('scratch/minervini_base.pkl') else pd.read_csv('/home/immanuels/Desktop/mri-int/backups/20260304/daily_prices.csv')
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    print("Calculating relative performance...")
    # Map benchmark to df
    df['bm_tri'] = df['date'].map(bm_full)
    df['bm_tri'] = df['bm_tri'].fillna(method='ffill') # For the 169 missing dates
    
    # Calculate NIFTY 500 RELATIVE PERFORMANCE
    for n in [63, 126, 252]:
        df[f'bm_tri_{n}'] = df.groupby('symbol')['bm_tri'].shift(n)
        df[f'price_{n}'] = df.groupby('symbol')['close'].shift(n)
        
        df[f'rel_perf_{n}m'] = (df['close'] / df[f'price_{n}']) / (df['bm_tri'] / df[f'bm_tri_{n}'])
        
    print("Validating VCP and Breakout Events (Look-ahead safe)...")
    
    # Find Swings
    df['high_shift_1'] = df.groupby('symbol')['high'].shift(1)
    df['high_shift_minus_1'] = df.groupby('symbol')['high'].shift(-1)
    df['low_shift_1'] = df.groupby('symbol')['low'].shift(1)
    df['low_shift_minus_1'] = df.groupby('symbol')['low'].shift(-1)
    
    df['is_sh'] = (df['high'] > df['high_shift_1']) & (df['high'] > df['high_shift_minus_1'])
    df['is_sl'] = (df['low'] < df['low_shift_1']) & (df['low'] < df['low_shift_minus_1'])
    
    # VDU: Volume <= 50% of 50d avg AND daily range < 50% ATR20
    if 'vol_sma_50' not in df.columns:
        df['vol_sma_50'] = df.groupby('symbol')['volume'].transform(lambda x: x.rolling(50).mean())
    if 'tr' not in df.columns:
        df['prev_close'] = df.groupby('symbol')['close'].shift(1)
        df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['prev_close']), abs(df['low'] - df['prev_close'])))
    if 'atr_20' not in df.columns:
        df['atr_20'] = df.groupby('symbol')['tr'].transform(lambda x: x.rolling(20).mean())
        
    df['is_vdu'] = (df['volume'] <= 0.5 * df['vol_sma_50']) & (df['tr'] < 0.5 * df['atr_20'])
    
    # Keep only the rows that are swings
    swings = df[df['is_sh'] | df['is_sl']].copy()
    
    vcp_candidates = []
    
    # We will iterate fast by group
    grouped = swings.groupby('symbol')
    symbols = list(grouped.groups.keys())
    
    for symbol in symbols:
        sym_swings = grouped.get_group(symbol).to_dict('records')
        if len(sym_swings) < 4: continue
        
        sym_df = df[df['symbol'] == symbol]
        
        for j in range(len(sym_swings) - 3):
            s1 = sym_swings[j]
            if not s1['is_sh']: continue
            
            s2 = next((s for s in sym_swings[j+1:] if s['is_sl']), None)
            if not s2: continue
            
            s3 = next((s for s in sym_swings[sym_swings.index(s2)+1:] if s['is_sh']), None)
            if not s3: continue
            
            s4 = next((s for s in sym_swings[sym_swings.index(s3)+1:] if s['is_sl']), None)
            if not s4: continue
            
            depth1 = (s1['high'] - s2['low']) / s1['high']
            depth2 = (s3['high'] - s4['low']) / s3['high']
            
            # Tightening: 30-65% of previous
            is_tight = 0.30 * depth1 <= depth2 <= 0.65 * depth1
            # Higher lows
            is_higher_low = s4['low'] > s2['low']
            
            if is_tight and is_higher_low:
                # Stage 2 condition must be met on s4 (SL2)
                # s4 is the last swing.
                if not s4.get('stage2', True): # default True if stage2 col is missing
                    continue
                    
                # We have a valid VCP formation known at s4 date + 1 day
                pivot = s3['high']
                setup_idx = sym_df.index[sym_df['date'] > s4['date']]
                if len(setup_idx) == 0: continue
                setup_date_idx = setup_idx[0]
                
                # Check for breakout in next 20 days
                # But it must not violate SL2 (s4['low'])
                future_20 = sym_df.loc[setup_date_idx : setup_date_idx + 20]
                
                breakout_occurred = False
                for idx, row in future_20.iterrows():
                    if row['low'] < s4['low']:
                        break # Invalidated!
                    if row['high'] >= pivot + 0.05:
                        breakout_occurred = True
                        vcp_candidates.append({
                            'symbol': symbol,
                            'vcp_start': s1['date'],
                            'vcp_end': s4['date'],
                            'pivot_date': s3['date'],
                            'setup_date': sym_df.loc[setup_date_idx, 'date'],
                            'pivot': pivot,
                            'breakout_date': row['date'],
                            'breakout_price': pivot + 0.05,
                            'breakout_open': row['open'],
                            'next_day_open': sym_df.loc[idx+1, 'open'] if idx+1 in sym_df.index else None,
                            'next_day_date': sym_df.loc[idx+1, 'date'] if idx+1 in sym_df.index else None,
                            'initial_stop': s4['low'],
                            'vdu_count': sym_df.loc[(sym_df['date'] >= s1['date']) & (sym_df['date'] <= s4['date']), 'is_vdu'].sum(),
                            'breakout_vol_ratio': row['volume'] / row['vol_sma_50'] if row['vol_sma_50'] > 0 else 0,
                            'rel_perf_3m': row['rel_perf_63m'],
                            'rel_perf_6m': row['rel_perf_126m'],
                            'rel_perf_12m': row['rel_perf_252m'],
                            'sma200_slope_10': row['sma_200'] > sym_df.loc[idx-10, 'sma_200'] if idx-10 in sym_df.index else False,
                            'sma200_slope_20': row['sma_200'] > sym_df.loc[idx-20, 'sma_200'] if idx-20 in sym_df.index else False,
                            'sma200_slope_40': row['sma_200'] > sym_df.loc[idx-40, 'sma_200'] if idx-40 in sym_df.index else False,
                        })
                        break
                        
    print(f"Total valid VCP breakout proxies found: {len(vcp_candidates)}")
    pd.DataFrame(vcp_candidates).to_pickle('scratch/phase2b_candidates.pkl')

if __name__ == '__main__':
    main()
