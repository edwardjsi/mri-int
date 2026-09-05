import pandas as pd
import numpy as np

# Load events
events = pd.read_csv('cai_backtest_events.csv')
d2 = events[events['strategy'] == 'D2'].copy()
d2['signal_date'] = pd.to_datetime(d2['signal_date'])

# Load NIFTY50 prices
prices = pd.read_csv('backups/20260304/daily_prices.csv', low_memory=False)
nifty = prices[prices['symbol'] == 'NIFTY50'].copy()
nifty['date'] = pd.to_datetime(nifty['date'])
nifty = nifty.sort_values('date').set_index('date')

# Calculate NIFTY50 90-day return
nifty['idx_ret_90d'] = nifty['close'] / nifty['close'].shift(90) - 1.0

# Merge NIFTY50 90-day return into D2 events
d2 = d2.merge(nifty['idx_ret_90d'], left_on='signal_date', right_index=True, how='left')

# Load RS90 from prices (some D2 signals might not have rs_90d if they didn't exist for 90 days)
stock_rs90 = prices[['symbol', 'date', 'rs_90d']].copy()
stock_rs90['date'] = pd.to_datetime(stock_rs90['date'])
d2 = d2.merge(stock_rs90, left_on=['symbol', 'signal_date'], right_on=['symbol', 'date'], how='left')

# Calculate hit_r100 from prices (actually, maybe use the existing script logic or pre-run it? Wait, let's just use cai_quality_study.py logic)
# Actually, I can just calculate max_close_252 for the signals.
dfs = []
for sym, sdf in prices.groupby('symbol'):
    sdf = sdf.sort_values('date').set_index('date')
    sdf['next_open'] = sdf['open'].shift(-1)
    rev_close = sdf['close'].iloc[::-1]
    sdf['max_close_252'] = rev_close.rolling(window=252, min_periods=1).max().iloc[::-1]
    dfs.append(sdf[['symbol', 'next_open', 'max_close_252']])

df_indexed = pd.concat(dfs)
df_indexed = df_indexed.reset_index().set_index(['symbol', 'date'])

d2 = d2.set_index(['symbol', 'signal_date'])
d2 = d2.join(df_indexed, how='inner')
d2 = d2.reset_index()

d2['hit_r100'] = (d2['max_close_252'] >= 2.0 * d2['next_open']).astype(int)

# Filter out rows where rs_90d is null
d2 = d2.dropna(subset=['rs_90d', 'idx_ret_90d'])

# Define NIFTY50 regime
def get_regime(ret):
    if ret > 0.03: return 'Positive (>3%)'
    elif ret < -0.03: return 'Negative (<-3%)'
    else: return 'Near Zero (-3% to 3%)'

d2['nifty_regime'] = d2['idx_ret_90d'].apply(get_regime)

# Calculate quartiles within the whole dataset or within regime?
# Standard is whole dataset
d2['q'] = pd.qcut(d2['rs_90d'], 4, labels=['Q1(Low)', 'Q2', 'Q3', 'Q4(High)'])

results = []
for regime in sorted(d2['nifty_regime'].unique()):
    r_df = d2[d2['nifty_regime'] == regime]
    for q in ['Q1(Low)', 'Q2', 'Q3', 'Q4(High)']:
        q_df = r_df[r_df['q'] == q]
        n = len(q_df)
        hits = q_df['hit_r100'].sum()
        hr = (hits / n * 100) if n > 0 else 0
        results.append({
            'Nifty Regime': regime,
            'RS90 Quartile': q,
            'Signals': n,
            'R100_Hits': hits,
            'Hit Rate': f"{hr:.1f}%"
        })

print(pd.DataFrame(results).to_markdown(index=False))

