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

print("Preparing D2 Signals...")
d2_data = pd.merge(d2_events, eval_df, left_on=['symbol', 'signal_date'], right_on=['symbol', 'date'], how='inner')
d2_data['q'] = pd.qcut(d2_data['rs_90d'], 4, labels=['Q1(Low)', 'Q2', 'Q3', 'Q4(High)'])

print("Preparing Generic 10-Day Breakouts...")
gen10_df = eval_df[
    (eval_df['close'] > 10) & 
    (eval_df['avg_volume_20d'] > 0) & 
    (eval_df['close'] > eval_df['high_10'])
].copy()
gen10_df['q'] = pd.qcut(gen10_df['rs_90d'], 4, labels=['Q1(Low)', 'Q2', 'Q3', 'Q4(High)'])

def run_analysis(data, name):
    results = []
    for regime in sorted(data['nifty_regime'].unique()):
        r_df = data[data['nifty_regime'] == regime]
        for q in ['Q1(Low)', 'Q2', 'Q3', 'Q4(High)']:
            q_df = r_df[r_df['q'] == q]
            n = len(q_df)
            r50 = q_df['r50_hit'].sum()
            r100 = q_df['r100_hit'].sum()
            hr50 = (r50 / n * 100) if n > 0 else 0
            hr100 = (r100 / n * 100) if n > 0 else 0
            results.append({
                'Strategy': name,
                'Regime': regime,
                'RS90 Quartile': q,
                'Signals': n,
                'R50 Hit Rate': f"{hr50:.1f}%",
                'R100 Hit Rate': f"{hr100:.1f}%"
            })
    return results

res_d2 = run_analysis(d2_data, 'D2')
res_gen = run_analysis(gen10_df, 'Generic 10-Day')

all_res = res_d2 + res_gen
df_res = pd.DataFrame(all_res)

with open('scratch/regime_validation_results.md', 'w') as f:
    f.write("# Regime-Controlled Validation: D2 vs Generic 10-Day Breakout\n\n")
    f.write(df_res.to_markdown(index=False))

print("Analysis complete. Results written to scratch/regime_validation_results.md")

