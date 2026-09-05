import pandas as pd
import numpy as np

print("Loading data...")
df = pd.read_csv('backups/20260304/daily_prices.csv', usecols=['symbol', 'date', 'close', 'high', 'low'], low_memory=False)
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values(['symbol', 'date']).reset_index(drop=True)

print("Computing rolling metrics...")
events_d1 = 0
events_d2 = 0
events_d3 = 0

for sym, sdf in df.groupby('symbol'):
    # Definition 1: 100% gain in 252 days, no 25% drawdown from max
    # We can approximate this by checking non-overlapping 252-day windows or rolling
    # A simple way: find all days where close is 100% higher than the 252-day min, and the drawdown from the 252-day max is < 25%
    sdf = sdf.set_index('date')
    
    # We just want a rough count of unique sustained moves per symbol.
    # We can use resampling for simplicity.
    wdf = sdf.resample('M').agg({'close':'last', 'high':'max', 'low':'min'}).dropna()
    
    # Approx Def 1: 12-month return >= 100%
    if len(wdf) >= 12:
        ret_12m = wdf['close'].pct_change(12)
        # To count distinct events, we only count when it crosses the threshold
        cross_12m = (ret_12m >= 1.0) & (ret_12m.shift(1) < 1.0)
        events_d1 += cross_12m.sum()
        
    # Approx Def 2: 6-month return >= 50%
    if len(wdf) >= 6:
        ret_6m = wdf['close'].pct_change(6)
        cross_6m = (ret_6m >= 0.50) & (ret_6m.shift(1) < 0.50)
        events_d2 += cross_6m.sum()
        
    # Approx Def 3: 3 consecutive positive quarters (9 months), cumulative > 40%
    if len(wdf) >= 9:
        q_close = sdf.resample('Q').last()['close'].dropna()
        if len(q_close) >= 3:
            q_ret = q_close.pct_change()
            cond = (q_ret > 0) & (q_ret.shift(1) > 0) & (q_ret.shift(2) > 0)
            cum_ret = (q_close / q_close.shift(3)) - 1
            cross_q = cond & (cum_ret >= 0.40) & ~(cond.shift(1).fillna(False))
            events_d3 += cross_q.sum()

print(f"Def 1 (12M > 100%): {events_d1}")
print(f"Def 2 (6M > 50%): {events_d2}")
print(f"Def 3 (3 Quarters Up > 40%): {events_d3}")
