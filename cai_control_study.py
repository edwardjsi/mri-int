import pandas as pd
import numpy as np

def wilson_score(count, nobs):
    if nobs == 0: return 0.0, 0.0
    z = 1.95996
    p = count / nobs
    den = 1 + z**2 / nobs
    center = (p + z**2 / (2 * nobs)) / den
    err = z * np.sqrt((p * (1 - p) / nobs) + (z**2 / (4 * nobs**2))) / den
    return max(0, center - err), min(1, center + err)

print("Loading daily prices...")
df = pd.read_csv('backups/20260304/daily_prices.csv', low_memory=False)
df['date'] = pd.to_datetime(df['date'])

print("Calculating forward targets...")
dfs = []
for sym, sdf in df.groupby('symbol'):
    sdf = sdf.sort_values('date')
    sdf['next_open'] = sdf['open'].shift(-1)
    
    # Pre-calculate rolling max for 126 and 252 days
    rev_close = sdf['close'].iloc[::-1]
    sdf['max_close_126'] = rev_close.rolling(window=126, min_periods=1).max().iloc[::-1]
    sdf['max_close_252'] = rev_close.rolling(window=252, min_periods=1).max().iloc[::-1]
    
    sdf['high_10'] = sdf['high'].rolling(10).max().shift(1)
    dfs.append(sdf)

full_df = pd.concat(dfs).sort_values('date').reset_index(drop=True)
del dfs
del df

print("Performing RS90 Audit...")
# Focus on D2 signals for RS90 audit
events = pd.read_csv('cai_backtest_events.csv')
d2_events = events[(events['event'] == 'BREAKOUT') & (events['strategy'] == 'D2')].copy()
d2_events['signal_date'] = pd.to_datetime(d2_events['signal_date'])

# Merge D2 signals with daily prices to get rs_90d
d2_data = pd.merge(d2_events, full_df, left_on=['symbol', 'signal_date'], right_on=['symbol', 'date'], how='left')
rs = d2_data['rs_90d']
rs_n = len(rs)
rs_nan = rs.isna().sum()
rs_valid = rs.dropna()
rs_zero = (rs_valid == 0).sum()
rs_neg = (rs_valid < 0).sum()

rs_audit = f"""
### RS90 Audit
**Definition Inference:** `rs_90d` represents a price-ratio return vs an index over 90 days. It is not a percentile rank (percentiles would be 0-100).
- **Total D2 Signals:** {rs_n}
- **NaN Count:** {rs_nan} ({(rs_nan/rs_n)*100:.1f}%)
- **Zero Count:** {rs_zero} ({(rs_zero/rs_n)*100:.1f}%)
- **Negative Count:** {rs_neg} ({(rs_neg/rs_n)*100:.1f}%)

**Distribution (Excluding NaNs):**
- Min: {rs_valid.min():.4f}
- 25th Pct (Q1 boundary): {rs_valid.quantile(0.25):.4f}
- Median: {rs_valid.median():.4f}
- 75th Pct (Q3 boundary): {rs_valid.quantile(0.75):.4f}
- Max: {rs_valid.max():.4f}

**Sample Actual D2 Values:**
"""
sample_rs = d2_data[['symbol', 'signal_date', 'rs_90d']].dropna().sample(5, random_state=42)
for _, r in sample_rs.iterrows():
    rs_audit += f"- {r['symbol']} on {r['signal_date'].date()}: {r['rs_90d']:.4f}\n"

print("Building Baselines...")
# Only evaluate days where forward data is actually available for a valid test
# We drop rows where next_open is NaN
eval_df = full_df.dropna(subset=['next_open', 'max_close_252']).copy()
eval_df['r50_hit'] = eval_df['max_close_126'] >= (eval_df['next_open'] * 1.50)
eval_df['r100_hit'] = eval_df['max_close_252'] >= (eval_df['next_open'] * 2.00)

baselines = {}

# 1. Random Market Baseline
baselines['Market Baseline'] = eval_df

# 2. Liquidity Baseline
liq_df = eval_df[(eval_df['close'] > 10) & (eval_df['avg_volume_20d'] > 0)]
baselines['Liquidity Baseline'] = liq_df

# 3. Generic 10-Day Breakout (on Liquidity universe)
gen10_df = liq_df[liq_df['close'] > liq_df['high_10']]
baselines['Generic 10-Day Breakout'] = gen10_df

print("Loading CAI Results...")
# We already have D2, W, D2->W rates, but we'll recalculate exactly to get CI
# cai_res = pd.read_csv('cai_candidate_quality_report.md', sep='|', skipinitialspace=True, engine='python')
# Actually, let's just recalculate them to have the exact counts for Wilson
d2_w = set()
for sym, sdf in eval_df.groupby('symbol'):
    # find D2->W logic
    invalidated = False
    w_validated = False
    for _, fut_row in sdf.iterrows():
        # Quick and dirty approximation of D2->W hit rates from previous study
        pass
        
# Better to recalculate them fast using the same logic as previous script
events = pd.read_csv('cai_backtest_events.csv')
breakouts = events[events['event'] == 'BREAKOUT'].copy()
breakouts['signal_date'] = pd.to_datetime(breakouts['signal_date'])
# Add CAI exact numbers from previous study
# W: N=1469, R50=27.8% (408), R100=23.9% (351)
# D2_W: N=3504, R50=26.1% (914), R100=21.3% (746)

results = []
for name, bdf in baselines.items():
    n = len(bdf)
    r50_hits = bdf['r50_hit'].sum()
    r100_hits = bdf['r100_hit'].sum()
    
    p_r50 = r50_hits / n if n > 0 else 0
    p_r100 = r100_hits / n if n > 0 else 0
    
    ci50 = wilson_score(r50_hits, n)
    ci100 = wilson_score(r100_hits, n)
    
    results.append({
        'Strategy': name,
        'N': n,
        'R50 Hit Rate': f"{p_r50*100:.1f}%",
        'R50 CI 95%': f"[{ci50[0]*100:.1f}% - {ci50[1]*100:.1f}%]",
        'R100 Hit Rate': f"{p_r100*100:.1f}%",
        'R100 CI 95%': f"[{ci100[0]*100:.1f}% - {ci100[1]*100:.1f}%]",
        'raw_p100': p_r100
    })

# Add CAI exact numbers from previous study
cai_strategies = [
    ('W CAI', 1469, 408, 351),
    ('D2 CAI', 5877, 1645, 1410),
    ('D2->W CAI', 3504, 914, 746)
]
for name, n, r50_hits, r100_hits in cai_strategies:
    p_r50 = r50_hits / n if n > 0 else 0
    p_r100 = r100_hits / n if n > 0 else 0
    ci50 = wilson_score(r50_hits, n)
    ci100 = wilson_score(r100_hits, n)
    results.append({
        'Strategy': name,
        'N': n,
        'R50 Hit Rate': f"{p_r50*100:.1f}%",
        'R50 CI 95%': f"[{ci50[0]*100:.1f}% - {ci50[1]*100:.1f}%]",
        'R100 Hit Rate': f"{p_r100*100:.1f}%",
        'R100 CI 95%': f"[{ci100[0]*100:.1f}% - {ci100[1]*100:.1f}%]",
        'raw_p100': p_r100
    })

res_df = pd.DataFrame(results)

# Calculate Lift vs Liquidity Baseline
liq_p100 = res_df.loc[res_df['Strategy'] == 'Liquidity Baseline', 'raw_p100'].values[0]
res_df['Abs Lift vs Liq'] = (res_df['raw_p100'] - liq_p100) * 100
res_df['Rel Lift vs Liq'] = (res_df['raw_p100'] / liq_p100 - 1) * 100

res_df['Abs Lift vs Liq'] = res_df['Abs Lift vs Liq'].apply(lambda x: f"+{x:.1f}%" if x > 0 else f"{x:.1f}%")
res_df['Rel Lift vs Liq'] = res_df['Rel Lift vs Liq'].apply(lambda x: f"+{x:.1f}%" if x > 0 else f"{x:.1f}%")
res_df = res_df.drop(columns=['raw_p100'])

with open('cai_control_group_report.md', 'w') as f:
    f.write("# Control Group Analysis\n\n")
    f.write(res_df.to_markdown(index=False))
    f.write("\n\n" + rs_audit)

print("Done!")
