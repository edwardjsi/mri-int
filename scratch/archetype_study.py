import pandas as pd
import numpy as np

print("Loading events...")
events = pd.read_csv('cai_backtest_events.csv')
d2_events = events[events['strategy'] == 'D2'].copy()
d2_events['signal_date'] = pd.to_datetime(d2_events['signal_date'])
min_date = d2_events['signal_date'].min()
max_date = d2_events['signal_date'].max()

# Divide into 3 roughly equal time periods based on quantiles or just date ranges
dates = sorted(d2_events['signal_date'].dropna())
q33 = pd.to_datetime(np.percentile([d.value for d in dates], 33))
q66 = pd.to_datetime(np.percentile([d.value for d in dates], 66))

def get_period(d):
    if d <= q33: return f"Early ({min_date.year}-{q33.year})"
    elif d <= q66: return f"Middle ({q33.year}-{q66.year})"
    else: return f"Recent ({q66.year}-{max_date.year})"

print(f"Periods: Early: <= {q33.date()}, Middle: <= {q66.date()}, Recent: > {q66.date()}")

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

results = []
for sym, sdf in prices_df.groupby('symbol'):
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
        period = get_period(dt)
        
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
        
        d_atr = sig_row.get('d_atr_14', np.nan)
        atr_pct = d_atr / sig_row['close'] if d_atr and sig_row['close'] > 0 else np.nan
        
        d2_anchor = sig_row.get('d2_anchor', np.nan)
        dist_anchor = (sig_row['close'] / d2_anchor) - 1 if d2_anchor and d2_anchor > 0 else np.nan
        
        fut_slice = sdf.iloc[pos+1 : pos+253]
        if len(fut_slice) == 0: continue
        
        df_126 = fut_slice.iloc[:126]
        df_252 = fut_slice
        
        r50_target = exec_price * 1.50
        r100_target = exec_price * 2.00
        
        hit_r50 = (df_126['close'] >= r50_target).any()
        hit_r100 = (df_252['close'] >= r100_target).any()
        
        w_validated = False
        time_to_w = np.nan
        for _, fut_row in fut_slice.iterrows():
            if pd.notna(fut_row['d2_quit_lvl']) and fut_row['close'] < fut_row['d2_quit_lvl']:
                break
            if fut_row['date'].weekday() == 4 and pd.notna(fut_row['w_quit_lvl']) and fut_row['close'] > fut_row['w_quit_lvl']:
                w_validated = True
                time_to_w = (fut_row['date'] - dt).days
                break
                
        # Group A: Fast W-validation (<= 7 cal days ~ 5 trading days)
        # Group B: Delayed or never (> 7 cal days or never)
        if w_validated and time_to_w <= 7:
            archetype = 'Group A (Fast W-val)'
        else:
            archetype = 'Group B (Deep-base)'
            
        results.append({
            'period': period,
            'archetype': archetype,
            'rs_90d': rs_90d,
            'dist_ema_50': dist_ema_50,
            'ema_200_slope': ema_200_slope,
            'vol_ratio': vol_ratio,
            'atr_pct': atr_pct,
            'dist_anchor': dist_anchor,
            'hit_r50': hit_r50,
            'hit_r100': hit_r100
        })

df = pd.DataFrame(results)

def format_stats(group):
    d = {}
    d['N'] = len(group)
    d['RS90 Med'] = group['rs_90d'].median()
    v = group['dist_ema_50'].median()
    d['EMA50 Dist Med'] = f"{v*100:.1f}%" if pd.notna(v) else 'NaN'
    d['EMA200 Slope Med'] = group['ema_200_slope'].median()
    d['Vol Ratio Med'] = group['vol_ratio'].median()
    v = group['atr_pct'].median()
    d['ATR% Med'] = f"{v*100:.1f}%" if pd.notna(v) else 'NaN'
    v = group['dist_anchor'].median()
    d['Anchor Dist Med'] = f"{v*100:.1f}%" if pd.notna(v) else 'NaN'
    d['R50 Rate'] = f"{(group['hit_r50'].mean()*100):.1f}%"
    d['R100 Rate'] = f"{(group['hit_r100'].mean()*100):.1f}%"
    return pd.Series(d)

out = []
# Global
for arch in ['Group A (Fast W-val)', 'Group B (Deep-base)']:
    g = df[df['archetype'] == arch]
    if len(g) > 0:
        s = format_stats(g)
        s['Period'] = 'ALL'
        s['Archetype'] = arch
        out.append(s)

# Periods
for p in sorted(df['period'].unique()):
    for arch in ['Group A (Fast W-val)', 'Group B (Deep-base)']:
        g = df[(df['period'] == p) & (df['archetype'] == arch)]
        if len(g) > 0:
            s = format_stats(g)
            s['Period'] = p
            s['Archetype'] = arch
            out.append(s)

final_df = pd.DataFrame(out)
cols = ['Period', 'Archetype', 'N', 'RS90 Med', 'EMA50 Dist Med', 'EMA200 Slope Med', 'Vol Ratio Med', 'ATR% Med', 'Anchor Dist Med', 'R50 Rate', 'R100 Rate']
final_df = final_df[cols]

with open('scratch/archetype_study.md', 'w') as f:
    f.write(final_df.to_markdown(index=False, floatfmt=".2f"))

print("Done.")
