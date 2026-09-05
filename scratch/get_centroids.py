import pandas as pd
import numpy as np

events = pd.read_csv('cai_backtest_events.csv')
d2_events = events[events['strategy'] == 'D2'].copy()
d2_events['signal_date'] = pd.to_datetime(d2_events['signal_date'])
dates = sorted(d2_events['signal_date'].dropna())
q33 = pd.to_datetime(np.percentile([d.value for d in dates], 33))
q66 = pd.to_datetime(np.percentile([d.value for d in dates], 66))

def get_period(d):
    if d <= q33: return "Early"
    elif d <= q66: return "Middle"
    else: return "Recent"

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
    sdf = sdf.sort_values('date').copy().set_index('date')
    
    wdf = sdf.resample('W-FRI').agg({'high': 'max', 'low': 'min', 'close': 'last'})
    wdf['w_low_4'] = wdf['low'].rolling(4, min_periods=1).min().shift(1)
    wdf['w_ema_20'] = wdf['close'].ewm(span=20, adjust=False).mean().shift(1)
    wdf['w_ema_50'] = wdf['close'].ewm(span=50, adjust=False).mean().shift(1)
    wdf['w_atr_14'] = compute_atr(wdf, 14).shift(1)
    sdf = sdf.merge(wdf[['w_low_4', 'w_ema_20', 'w_ema_50', 'w_atr_14']], left_index=True, right_index=True, how='left')
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
        future_mask = sdf['date'] >= dt
        if not future_mask.any(): continue
        pos = sdf[future_mask].index[0]
        if pos >= len(sdf): continue
        sig_row = sdf.iloc[pos]
        
        rs_90d = sig_row.get('rs_90d', np.nan)
        vol = sig_row.get('volume', np.nan)
        avg_vol = sig_row.get('avg_volume_20d', np.nan)
        vol_ratio = vol / avg_vol if avg_vol and avg_vol > 0 else np.nan
        ema_50 = sig_row.get('ema_50', np.nan)
        dist_ema_50 = (sig_row['close'] / ema_50) - 1 if ema_50 and ema_50 > 0 else np.nan
        d2_anchor = sig_row.get('d2_anchor', np.nan)
        dist_anchor = (sig_row['close'] / d2_anchor) - 1 if d2_anchor and d2_anchor > 0 else np.nan
        
        fut_slice = sdf.iloc[pos+1 : pos+253]
        if len(fut_slice) == 0: continue
        
        w_validated = False
        time_to_w = np.nan
        for _, fut_row in fut_slice.iterrows():
            if pd.notna(fut_row['d2_quit_lvl']) and fut_row['close'] < fut_row['d2_quit_lvl']:
                break
            if fut_row['date'].weekday() == 4 and pd.notna(fut_row['w_quit_lvl']) and fut_row['close'] > fut_row['w_quit_lvl']:
                w_validated = True
                time_to_w = (fut_row['date'] - dt).days
                break
                
        target = 1 if (w_validated and time_to_w <= 7) else 0
        results.append({
            'period': get_period(dt),
            'target': target,
            'rs_90d': rs_90d,
            'dist_ema_50': dist_ema_50,
            'dist_anchor': dist_anchor,
            'vol_ratio': vol_ratio
        })

df = pd.DataFrame(results)
features = ['rs_90d', 'dist_ema_50', 'dist_anchor', 'vol_ratio']
df = df.dropna(subset=features)
train_df = df[df['period'].isin(['Early', 'Middle'])]

medians = train_df[features].median()
iqr = train_df[features].quantile(0.75) - train_df[features].quantile(0.25)
iqr = iqr.replace(0, 1)

cent_1 = (train_df[train_df['target'] == 1][features].median() - medians) / iqr
cent_0 = (train_df[train_df['target'] == 0][features].median() - medians) / iqr

print("MEDIANS:")
print(medians.to_dict())
print("IQR:")
print(iqr.to_dict())
print("CENT_1 (Momentum):")
print(cent_1.to_dict())
print("CENT_0 (Deep-Base):")
print(cent_0.to_dict())
