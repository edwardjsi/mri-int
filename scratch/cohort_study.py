import pandas as pd
import numpy as np

print("Loading events...")
events = pd.read_csv('cai_backtest_events.csv')
d2_events = events[events['strategy'] == 'D2'].copy()
d2_events['signal_date'] = pd.to_datetime(d2_events['signal_date'])

print("Loading daily prices...")
prices_df = pd.read_csv('backups/20260304/daily_prices.csv', low_memory=False)
prices_df['date'] = pd.to_datetime(prices_df['date'])

def compute_atr(sdf, window):
    prev_close = sdf['close'].shift(1)
    tr1 = sdf['high'] - sdf['low']
    tr2 = (sdf['high'] - prev_close).abs()
    tr3 = (sdf['low'] - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window, min_periods=1).mean()

nifty = prices_df[prices_df['symbol'] == 'NIFTY50'].copy().set_index('date')
nifty['idx_ret_90d'] = nifty['close'] / nifty['close'].shift(90) - 1.0
def get_regime(ret):
    if pd.isna(ret): return np.nan
    if ret > 0.03: return 'Positive (>3%)'
    elif ret < -0.03: return 'Negative (<-3%)'
    else: return 'Near Zero (-3% to 3%)'
nifty['nifty_regime'] = nifty['idx_ret_90d'].apply(get_regime)
nifty_regimes = nifty[['nifty_regime']].dropna()

d2_events = d2_events.merge(nifty_regimes, left_on='signal_date', right_index=True, how='left')

results = []
for sym, sdf in prices_df.groupby('symbol'):
    # Check if there are D2 signals
    sym_d2 = d2_events[d2_events['symbol'] == sym]
    if len(sym_d2) == 0: continue
    
    sdf = sdf.sort_values('date').copy()
    sdf.set_index('date', inplace=True)
    
    wdf = sdf.resample('W-FRI').agg({'high': 'max', 'low': 'min', 'close': 'last'})
    wdf['w_low_4'] = wdf['low'].rolling(4, min_periods=1).min().shift(1)
    wdf['w_ema_20'] = wdf['close'].ewm(span=20, adjust=False).mean().shift(1)
    wdf['w_ema_50'] = wdf['close'].ewm(span=50, adjust=False).mean().shift(1)
    wdf['w_atr_14'] = compute_atr(wdf, 14).shift(1)
    wdf = wdf[['w_low_4', 'w_ema_20', 'w_ema_50', 'w_atr_14']]
    
    sdf = sdf.merge(wdf, left_index=True, right_index=True, how='left')
    sdf[['w_low_4', 'w_ema_20', 'w_ema_50', 'w_atr_14']] = sdf[['w_low_4', 'w_ema_20', 'w_ema_50', 'w_atr_14']].ffill()
    sdf['w_anchor'] = sdf['w_low_4'].combine_first(sdf['w_ema_50']).combine_first(sdf['w_ema_20'])
    sdf['w_quit_lvl'] = sdf['w_anchor'] - (0.5 * sdf['w_atr_14'])
    
    sdf['d_ema_50'] = sdf['close'].ewm(span=50, adjust=False).mean().shift(1)
    sdf['d_ema_200'] = sdf['close'].ewm(span=200, adjust=False).mean().shift(1)
    sdf['d_atr_14'] = compute_atr(sdf, 14).shift(1)
    sdf['d2_anchor'] = sdf['d_ema_50'].combine_first(sdf['d_ema_200'])
    sdf['d2_quit_lvl'] = sdf['d2_anchor'] - (0.5 * sdf['d_atr_14'])
    
    sdf['next_open'] = sdf['open'].shift(-1)
    sdf = sdf.reset_index()
    
    for _, row in sym_d2.iterrows():
        dt = row['signal_date']
        regime = row['nifty_regime']
        
        future_mask = sdf['date'] >= dt
        if not future_mask.any(): continue
        pos = sdf[future_mask].index[0]
        
        if pos >= len(sdf): continue
        sig_row = sdf.iloc[pos]
        exec_price = sig_row['next_open']
        if pd.isna(exec_price): continue
        
        rs_90d = sig_row.get('rs_90d', np.nan)
        vol = sig_row.get('volume', np.nan)
        avg_vol = sig_row.get('avg_volume_20d', np.nan)
        vol_ratio = vol / avg_vol if avg_vol and avg_vol > 0 else np.nan
        ema_200_slope = sig_row.get('ema_200_slope_20', np.nan)
        ema_50 = sig_row.get('ema_50', np.nan)
        dist_ema_50 = (sig_row['close'] / ema_50) - 1 if ema_50 and ema_50 > 0 else np.nan
        
        fut_slice = sdf.iloc[pos+1 : pos+253]
        if len(fut_slice) == 0: continue
        
        df_126 = fut_slice.iloc[:126]
        df_252 = fut_slice
        
        r50_target = exec_price * 1.50
        r100_target = exec_price * 2.00
        
        r50_hit_idx = df_126.index[df_126['close'] >= r50_target].tolist()
        r100_hit_idx = df_252.index[df_252['close'] >= r100_target].tolist()
        
        hit_r50 = len(r50_hit_idx) > 0
        hit_r100 = len(r100_hit_idx) > 0
        
        time_r50 = np.nan
        if hit_r50:
            time_r50 = (df_126.loc[r50_hit_idx[0], 'date'] - dt).days
            
        time_r100 = np.nan
        if hit_r100:
            time_r100 = (df_252.loc[r100_hit_idx[0], 'date'] - dt).days
            
        mae = df_252['low'].min() / exec_price - 1
        mfe = df_252['high'].max() / exec_price - 1
        
        w_validated = False
        time_to_w = np.nan
        for _, fut_row in fut_slice.iterrows():
            if pd.notna(fut_row['d2_quit_lvl']) and fut_row['close'] < fut_row['d2_quit_lvl']:
                break
            if fut_row['date'].weekday() == 4 and pd.notna(fut_row['w_quit_lvl']) and fut_row['close'] > fut_row['w_quit_lvl']:
                w_validated = True
                time_to_w = (fut_row['date'] - dt).days
                break
                
        if hit_r100: outcome = 'R100'
        elif hit_r50: outcome = 'R50-Only'
        else: outcome = 'Failure'
        
        results.append({
            'symbol': sym,
            'regime': regime,
            'outcome': outcome,
            'rs_90d': rs_90d,
            'dist_ema_50': dist_ema_50,
            'ema_200_slope': ema_200_slope,
            'vol_ratio': vol_ratio,
            'hit_r50': hit_r50,
            'hit_r100': hit_r100,
            'time_r50': time_r50,
            'time_r100': time_r100,
            'mae': mae,
            'mfe': mfe,
            'is_d2_w': w_validated,
            'time_to_w': time_to_w
        })

res_df = pd.DataFrame(results)

def format_stats(group):
    d = {}
    d['N'] = len(group)
    d['RS90 Med'] = group['rs_90d'].median()
    d['EMA50 Dist Med'] = group['dist_ema_50'].median()
    d['EMA200 Slope Med'] = group['ema_200_slope'].median()
    d['Vol Ratio Med'] = group['vol_ratio'].median()
    d['W-Val Rate'] = group['is_d2_w'].mean() * 100
    d['W-Val Time Med (d)'] = group['time_to_w'].dropna().median()
    d['MAE Med'] = group['mae'].median()
    d['MFE Med'] = group['mfe'].median()
    if group['outcome'].iloc[0] == 'R50-Only':
        d['Time to Target Med (d)'] = group['time_r50'].median()
    elif group['outcome'].iloc[0] == 'R100':
        d['Time to Target Med (d)'] = group['time_r100'].median()
    else:
        d['Time to Target Med (d)'] = np.nan
    return pd.Series(d)

out = []
for outcome in ['Failure', 'R50-Only', 'R100']:
    g = res_df[res_df['outcome'] == outcome]
    if len(g) > 0:
        s = format_stats(g)
        s['Regime'] = 'ALL'
        s['Outcome'] = outcome
        out.append(s)

for regime in sorted(res_df['regime'].dropna().unique()):
    for outcome in ['Failure', 'R50-Only', 'R100']:
        g = res_df[(res_df['regime'] == regime) & (res_df['outcome'] == outcome)]
        if len(g) > 0:
            s = format_stats(g)
            s['Regime'] = regime
            s['Outcome'] = outcome
            out.append(s)

final_df = pd.DataFrame(out)
cols = ['Regime', 'Outcome', 'N', 'RS90 Med', 'EMA50 Dist Med', 'EMA200 Slope Med', 'Vol Ratio Med', 'W-Val Rate', 'W-Val Time Med (d)', 'MAE Med', 'MFE Med', 'Time to Target Med (d)']
final_df = final_df[cols]

with open('scratch/cohort_study_results.md', 'w') as f:
    f.write("# D2 Outcome Cohort Study\n\n")
    f.write(final_df.to_markdown(index=False, floatfmt=".3f"))

print("Analysis complete.")
