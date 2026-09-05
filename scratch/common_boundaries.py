import pandas as pd
import numpy as np

print("Loading events...")
events = pd.read_csv('cai_backtest_events.csv')
d2_events = events[events['strategy'] == 'D2'].copy()
d2_events['signal_date'] = pd.to_datetime(d2_events['signal_date'])

print("Loading daily prices...")
cols = ['symbol', 'date', 'open', 'high', 'close', 'rs_90d', 'avg_volume_20d']
df = pd.read_csv('backups/20260304/daily_prices.csv', low_memory=False, usecols=cols)
df['date'] = pd.to_datetime(df['date'])

print("Processing NIFTY50...")
nifty = df[df['symbol'] == 'NIFTY50'].copy()
nifty = nifty.sort_values('date').set_index('date')
nifty['idx_ret_90d'] = nifty['close'] / nifty['close'].shift(90) - 1.0

def get_regime(ret):
    if pd.isna(ret): return np.nan
    if ret > 0.03: return 'Positive (>3%)'
    elif ret < -0.03: return 'Negative (<-3%)'
    else: return 'Near Zero (-3% to 3%)'

nifty['nifty_regime'] = nifty['idx_ret_90d'].apply(get_regime)
nifty_regimes = nifty[['nifty_regime']].dropna()

print("Calculating forward targets for all symbols...")
dfs = []
for sym, sdf in df.groupby('symbol'):
    sdf = sdf.sort_values('date')
    sdf['next_open'] = sdf['open'].shift(-1)
    
    rev_close = sdf['close'].iloc[::-1]
    sdf['max_close_126'] = rev_close.rolling(window=126, min_periods=1).max().iloc[::-1]
    sdf['max_close_252'] = rev_close.rolling(window=252, min_periods=1).max().iloc[::-1]
    
    sdf['high_10'] = sdf['high'].rolling(10).max().shift(1)
    dfs.append(sdf)

full_df = pd.concat(dfs).sort_values(['symbol', 'date']).reset_index(drop=True)
del dfs

eval_df = full_df.dropna(subset=['next_open', 'max_close_126', 'max_close_252', 'rs_90d']).copy()
eval_df = eval_df.merge(nifty_regimes, left_on='date', right_index=True, how='inner')

eval_df['r50_hit'] = eval_df['max_close_126'] >= (eval_df['next_open'] * 1.50)
eval_df['r100_hit'] = eval_df['max_close_252'] >= (eval_df['next_open'] * 2.00)

print("Establishing common RS90 quartile boundaries on Liquidity Universe...")
liq_df = eval_df[(eval_df['close'] > 10) & (eval_df['avg_volume_20d'] > 0)].copy()
rs90_quantiles = liq_df['rs_90d'].quantile([0, 0.25, 0.5, 0.75, 1.0]).values
rs90_quantiles[0] = -np.inf
rs90_quantiles[-1] = np.inf

print("Preparing D2 Signals...")
d2_data = pd.merge(d2_events, eval_df, left_on=['symbol', 'signal_date'], right_on=['symbol', 'date'], how='inner')
d2_data['q'] = pd.cut(d2_data['rs_90d'], bins=rs90_quantiles, labels=['Q1(Low)', 'Q2', 'Q3', 'Q4(High)'])

print("Preparing Generic 10-Day Breakouts...")
gen10_df = liq_df[liq_df['close'] > liq_df['high_10']].copy()
gen10_df['q'] = pd.cut(gen10_df['rs_90d'], bins=rs90_quantiles, labels=['Q1(Low)', 'Q2', 'Q3', 'Q4(High)'])

def get_stats(data, regime, q):
    sub = data[(data['nifty_regime'] == regime) & (data['q'] == q)]
    n = len(sub)
    r50 = sub['r50_hit'].sum()
    r100 = sub['r100_hit'].sum()
    hr50 = (r50 / n) if n > 0 else 0
    hr100 = (r100 / n) if n > 0 else 0
    return n, hr50, hr100

results = []
regimes = sorted(eval_df['nifty_regime'].dropna().unique())
for regime in regimes:
    for q in ['Q1(Low)', 'Q2', 'Q3', 'Q4(High)']:
        d2_n, d2_r50, d2_r100 = get_stats(d2_data, regime, q)
        gen_n, gen_r50, gen_r100 = get_stats(gen10_df, regime, q)
        
        lift_r50 = d2_r50 - gen_r50
        rel_lift_r50 = (d2_r50 / gen_r50 - 1) if gen_r50 > 0 else np.nan
        
        lift_r100 = d2_r100 - gen_r100
        rel_lift_r100 = (d2_r100 / gen_r100 - 1) if gen_r100 > 0 else np.nan
        
        results.append({
            'Regime': regime,
            'RS90 Q (Common)': q,
            'D2_N': d2_n,
            'D2_R50': f"{d2_r50*100:.1f}%",
            'D2_R100': f"{d2_r100*100:.1f}%",
            'Gen_N': gen_n,
            'Gen_R50': f"{gen_r50*100:.1f}%",
            'Gen_R100': f"{gen_r100*100:.1f}%",
            'Abs Lift R50': f"{lift_r50*100:+.1f}%",
            'Rel Lift R50': f"{rel_lift_r50*100:+.1f}%" if not pd.isna(rel_lift_r50) else "N/A",
            'Abs Lift R100': f"{lift_r100*100:+.1f}%",
            'Rel Lift R100': f"{rel_lift_r100*100:+.1f}%" if not pd.isna(rel_lift_r100) else "N/A",
        })

df_res = pd.DataFrame(results)
with open('scratch/common_boundaries_results.md', 'w') as f:
    f.write("# Common Boundaries RS90 Analysis\n\n")
    f.write(df_res.to_markdown(index=False))

print("Analysis complete. Results written to scratch/common_boundaries_results.md")

