import pandas as pd
import numpy as np
import os
import sys

def main():
    print("Investigating missing benchmark dates...")
    bm = pd.read_csv('/home/immanuels/Desktop/mri-int/benchmarks/NSE500TRI.csv')
    bm['Date'] = pd.to_datetime(bm['Date'])
    
    df = pd.read_pickle('scratch/minervini_base.pkl') if os.path.exists('scratch/minervini_base.pkl') else pd.read_csv('/home/immanuels/Desktop/mri-int/backups/20260304/daily_prices.csv')
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    stock_dates = pd.Series(df['date'].unique()).sort_values()
    overlap_start = max(bm['Date'].min(), stock_dates.min())
    overlap_end = min(bm['Date'].max(), stock_dates.max())
    
    st_dates_overlap = set(stock_dates[(stock_dates >= overlap_start) & (stock_dates <= overlap_end)])
    bm_dates_overlap = set(bm[(bm['Date'] >= overlap_start) & (bm['Date'] <= overlap_end)]['Date'])
    
    missing_dates = sorted(list(st_dates_overlap - bm_dates_overlap))
    
    with open('scratch/missing_dates_audit.txt', 'w') as f:
        f.write(f"Total missing dates: {len(missing_dates)}\n")
        f.write("Sample of missing dates and their day of week:\n")
        for d in missing_dates[:20]:
            f.write(f"{d.strftime('%Y-%m-%d')} ({d.day_name()})\n")
    print(f"Missing dates audited to scratch/missing_dates_audit.txt (Count: {len(missing_dates)})")

    bm_full = bm.set_index('Date')['Total Returns Index']
    bm_full = pd.to_numeric(bm_full, errors='coerce').fillna(method='ffill')
    df['bm_tri'] = df['date'].map(bm_full).fillna(method='ffill')
    
    for n in [63, 126, 252]:
        df[f'bm_tri_{n}'] = df.groupby('symbol')['bm_tri'].shift(n)
        df[f'price_{n}'] = df.groupby('symbol')['close'].shift(n)
        df[f'rel_perf_{n}m'] = (df['close'] / df[f'price_{n}']) / (df['bm_tri'] / df[f'bm_tri_{n}'])

    print("Validating VCP (Dynamic Contraction Count)...")
    
    # Calculate is_vdu
    if 'vol_sma_50' not in df.columns:
        df['vol_sma_50'] = df.groupby('symbol')['volume'].transform(lambda x: x.rolling(50).mean())
    if 'tr' not in df.columns:
        df['prev_close'] = df.groupby('symbol')['close'].shift(1)
        df['tr'] = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['prev_close']), abs(df['low'] - df['prev_close'])))
    if 'atr_20' not in df.columns:
        df['atr_20'] = df.groupby('symbol')['tr'].transform(lambda x: x.rolling(20).mean())
        
    df['is_vdu'] = (df['volume'] <= 0.5 * df['vol_sma_50']) & (df['tr'] < 0.5 * df['atr_20'])

    df['high_shift_1'] = df.groupby('symbol')['high'].shift(1)
    df['high_shift_minus_1'] = df.groupby('symbol')['high'].shift(-1)
    df['low_shift_1'] = df.groupby('symbol')['low'].shift(1)
    df['low_shift_minus_1'] = df.groupby('symbol')['low'].shift(-1)
    
    df['is_sh'] = (df['high'] > df['high_shift_1']) & (df['high'] > df['high_shift_minus_1'])
    df['is_sl'] = (df['low'] < df['low_shift_1']) & (df['low'] < df['low_shift_minus_1'])
    
    swings = df[df['is_sh'] | df['is_sl']].copy()
    grouped = swings.groupby('symbol')
    symbols = list(grouped.groups.keys())
    
    vcp_candidates = []
    
    for symbol in symbols:
        sym_swings = grouped.get_group(symbol).to_dict('records')
        if len(sym_swings) < 4: continue
        
        sym_df = df[df['symbol'] == symbol]
        
        for j in range(len(sym_swings) - 3):
            s1 = sym_swings[j]
            if not s1['is_sh']: continue
            
            seq = [s1]
            curr_is_sh = True
            for k in range(j+1, len(sym_swings)):
                expected = not curr_is_sh
                if sym_swings[k]['is_sl'] == expected:
                    seq.append(sym_swings[k])
                    curr_is_sh = expected
                elif sym_swings[k]['is_sh'] == expected:
                    seq.append(sym_swings[k])
                    curr_is_sh = expected
                else:
                    break
            
            if len(seq) % 2 != 0:
                seq = seq[:-1]
                
            if len(seq) < 4: continue
            
            if len(seq) > 8:
                seq = seq[:8]
                
            num_contractions = len(seq) // 2
            
            is_valid = True
            depths = []
            for c in range(num_contractions):
                sh = seq[c*2]
                sl = seq[c*2 + 1]
                depth = (sh['high'] - sl['low']) / sh['high']
                depths.append(depth)
                
            for c in range(1, num_contractions):
                if not (0.30 * depths[c-1] <= depths[c] <= 0.65 * depths[c-1]):
                    is_valid = False
                    break
                if seq[c*2 + 1]['low'] <= seq[(c-1)*2 + 1]['low']:
                    is_valid = False
                    break
                    
            if not is_valid: continue
            
            s_final_sl = seq[-1]
            if not s_final_sl.get('stage2', True): continue
            
            pivot = seq[-2]['high']
            
            setup_idx = sym_df.index[sym_df['date'] > s_final_sl['date']]
            if len(setup_idx) == 0: continue
            setup_date_idx = setup_idx[0]
            
            future_20 = sym_df.loc[setup_date_idx : setup_date_idx + 20]
            for idx, row in future_20.iterrows():
                if row['low'] < s_final_sl['low']:
                    break
                if row['high'] >= pivot + 0.05:
                    vcp_candidates.append({
                        'symbol': symbol,
                        'vcp_start': seq[0]['date'],
                        'vcp_end': s_final_sl['date'],
                        'setup_date': sym_df.loc[setup_date_idx, 'date'],
                        'pivot_date': seq[-2]['date'],
                        'pivot': pivot,
                        'breakout_date': row['date'],
                        'breakout_price': pivot + 0.05,
                        'breakout_open': row['open'],
                        'next_day_open': sym_df.loc[idx+1, 'open'] if idx+1 in sym_df.index else None,
                        'next_day_date': sym_df.loc[idx+1, 'date'] if idx+1 in sym_df.index else None,
                        'initial_stop': s_final_sl['low'],
                        'vdu_count': sym_df.loc[(sym_df['date'] >= seq[0]['date']) & (sym_df['date'] <= s_final_sl['date']), 'is_vdu'].sum(),
                        'breakout_vol_ratio': row['volume'] / row['vol_sma_50'] if row['vol_sma_50'] > 0 else 0,
                        'rel_perf_3m': row['rel_perf_63m'],
                        'rel_perf_6m': row['rel_perf_126m'],
                        'rel_perf_12m': row['rel_perf_252m'],
                        'contraction_count': num_contractions
                    })
                    break

    print(f"Total valid VCP proxies: {len(vcp_candidates)}")
    pd.DataFrame(vcp_candidates).to_pickle('scratch/validation_candidates.pkl')

if __name__ == '__main__':
    main()
