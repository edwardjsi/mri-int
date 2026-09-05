import pandas as pd
import numpy as np

print("Loading events...")
events = pd.read_csv('cai_backtest_events.csv')
d2 = events[events['strategy'] == 'D2'].copy()
d2['signal_date'] = pd.to_datetime(d2['signal_date'])

print("Loading daily prices...")
prices = pd.read_csv('backups/20260304/daily_prices.csv', low_memory=False, usecols=['symbol', 'date', 'open', 'close', 'rs_90d'])
prices['date'] = pd.to_datetime(prices['date'])

print("Processing NIFTY50...")
nifty = prices[prices['symbol'] == 'NIFTY50'].copy()
nifty = nifty.sort_values('date').set_index('date')
nifty['idx_ret_90d'] = nifty['close'] / nifty['close'].shift(90) - 1.0

print("Merging data...")
d2 = d2.merge(nifty['idx_ret_90d'], left_on='signal_date', right_index=True, how='left')

stock_rs90 = prices[['symbol', 'date', 'rs_90d']].dropna(subset=['rs_90d'])
d2 = d2.merge(stock_rs90, left_on=['symbol', 'signal_date'], right_on=['symbol', 'date'], how='left')

print("Calculating max_close_252 for opportunity set...")
# Instead of doing it for all prices, we can just check the future 252 days for each signal
hits = []
# Pre-index prices for fast lookup
prices_idx = prices.sort_values(['symbol', 'date']).set_index(['symbol', 'date'])

for _, row in d2.iterrows():
    sym = row['symbol']
    dt = row['signal_date']
    
    try:
        # Get the slice starting at dt
        sym_df = prices[(prices['symbol'] == sym) & (prices['date'] >= dt)].sort_values('date')
        if len(sym_df) < 2:
            hits.append(np.nan)
            continue
            
        next_open = sym_df.iloc[1]['open']
        # Look ahead 252 days (inclusive of the next day)
        future = sym_df.iloc[1:253]
        max_close = future['close'].max()
        
        hit = 1 if max_close >= 2.0 * next_open else 0
        hits.append(hit)
    except Exception as e:
        hits.append(np.nan)

d2['hit_r100'] = hits
d2 = d2.dropna(subset=['rs_90d', 'idx_ret_90d', 'hit_r100'])

def get_regime(ret):
    if ret > 0.03: return 'Positive (>3%)'
    elif ret < -0.03: return 'Negative (<-3%)'
    else: return 'Near Zero (-3% to 3%)'

d2['nifty_regime'] = d2['idx_ret_90d'].apply(get_regime)
d2['q'] = pd.qcut(d2['rs_90d'], 4, labels=['Q1(Low)', 'Q2', 'Q3', 'Q4(High)'])

results = []
for regime in sorted(d2['nifty_regime'].unique()):
    r_df = d2[d2['nifty_regime'] == regime]
    for q in ['Q1(Low)', 'Q2', 'Q3', 'Q4(High)']:
        q_df = r_df[r_df['q'] == q]
        n = len(q_df)
        hit_sum = q_df['hit_r100'].sum()
        hr = (hit_sum / n * 100) if n > 0 else 0
        results.append({
            'Nifty Regime': regime,
            'RS90 Quartile': q,
            'Signals': n,
            'R100_Hits': int(hit_sum),
            'Hit Rate': f"{hr:.1f}%"
        })

print("\n--- REGIME CONTROLLED RS90 HIT RATES ---")
print(pd.DataFrame(results).to_markdown(index=False))

