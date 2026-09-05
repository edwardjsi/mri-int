import pandas as pd
import numpy as np

# 1. Load Data & Compute Row-Level Labels
events = pd.read_csv('cai_backtest_events.csv')
prices = pd.read_csv('backups/20260304/daily_prices.csv', usecols=['symbol', 'date', 'open', 'high', 'low', 'close'], low_memory=False)

prices['date'] = pd.to_datetime(prices['date'])
events['signal_date'] = pd.to_datetime(events['signal_date'])
prices = prices.sort_values(['symbol', 'date']).reset_index(drop=True)

print("Precomputing outcome labels...")
prices_rev = prices.iloc[::-1].copy()
grouped_rev = prices_rev.groupby('symbol')['high']
prices['m126'] = grouped_rev.rolling(126, min_periods=1).max().reset_index(level=0, drop=True).iloc[::-1]
prices['m252'] = grouped_rev.rolling(252, min_periods=1).max().reset_index(level=0, drop=True).iloc[::-1]

prices['next_date'] = prices.groupby('symbol')['date'].shift(-1)
prices['next_open'] = prices.groupby('symbol')['open'].shift(-1)

strat_events = events[events['event'] == 'BREAKOUT'].copy()
strat_events = strat_events.merge(prices[['symbol', 'date', 'next_date', 'next_open']], left_on=['symbol', 'signal_date'], right_on=['symbol', 'date'], how='left')
strat_events = strat_events.dropna(subset=['next_date', 'next_open'])

temp = prices[['symbol', 'date', 'm126', 'm252']].rename(columns={'date':'exec_date'})
strat_events = strat_events.merge(temp, left_on=['symbol', 'next_date'], right_on=['symbol', 'exec_date'], how='left')

strat_events['hit_r50'] = strat_events['m126'] >= strat_events['next_open'] * 1.50
strat_events['hit_r100'] = strat_events['m252'] >= strat_events['next_open'] * 2.00
strat_events = strat_events.sort_values(['symbol', 'strategy', 'signal_date']).reset_index(drop=True)

# 2. Campaign Clustering (Sensitivities)
print("\n--- Sensitivity to Separation Window ---")
windows = [60, 126, 252]
for w in windows:
    # A new campaign starts if days since last signal > w
    strat_events['diff_days'] = strat_events.groupby(['symbol', 'strategy'])['signal_date'].diff().dt.days
    strat_events['new_campaign'] = (strat_events['diff_days'].isna()) | (strat_events['diff_days'] > w)
    strat_events['campaign_id'] = strat_events.groupby(['symbol', 'strategy'])['new_campaign'].cumsum()
    
    res = []
    for strat in ['W', 'D1', 'D2']:
        sdf = strat_events[strat_events['strategy'] == strat]
        c_counts = sdf.groupby(['symbol', 'campaign_id'])['hit_r100'].any().sum()
        res.append({'Strategy': strat, 'Window': w, 'R100 Campaigns': c_counts})
    print(pd.DataFrame(res).to_string(index=False))

# We will use 126 days as the primary campaign separator for reporting.
w_primary = 126
strat_events['diff_days'] = strat_events.groupby(['symbol', 'strategy'])['signal_date'].diff().dt.days
strat_events['new_campaign'] = (strat_events['diff_days'].isna()) | (strat_events['diff_days'] > w_primary)
strat_events['campaign_id'] = strat_events.groupby(['symbol', 'strategy'])['new_campaign'].cumsum()

# 3. Compile the Required Report (using w=126)
print(f"\n--- Detailed Report (using {w_primary}-day separation) ---")
metrics = []
for strat in ['W', 'D1', 'D2']:
    sdf = strat_events[strat_events['strategy'] == strat]
    raw_signals = len(sdf)
    unique_c = len(sdf.groupby(['symbol', 'campaign_id']))
    
    r50_raw = sdf['hit_r50'].sum()
    r100_raw = sdf['hit_r100'].sum()
    
    camp_r50 = sdf.groupby(['symbol', 'campaign_id'])['hit_r50'].any().sum()
    camp_r100 = sdf.groupby(['symbol', 'campaign_id'])['hit_r100'].any().sum()
    
    unique_r50_sym = sdf[sdf['hit_r50']]['symbol'].nunique()
    unique_r100_sym = sdf[sdf['hit_r100']]['symbol'].nunique()
    
    # Median successful signals per symbol (for symbols that had >0 successful signals)
    succ = sdf[sdf['hit_r100']]
    med_succ_per_sym = succ.groupby('symbol').size().median()
    
    # Top 20 symbols
    top20 = succ.groupby('symbol').size().nlargest(5).to_dict()  # Just show top 5 here for brevity, full in analysis
    
    metrics.append({
        'Strategy': strat,
        'Raw Signals': raw_signals,
        'Unique Campaigns': unique_c,
        'R50 Hits (Raw)': f"{r50_raw} ({r50_raw/raw_signals*100:.1f}%)",
        'R100 Hits (Raw)': f"{r100_raw} ({r100_raw/raw_signals*100:.1f}%)",
        'R50 Hits (Camp)': f"{camp_r50} ({camp_r50/unique_c*100:.1f}%)",
        'R100 Hits (Camp)': f"{camp_r100} ({camp_r100/unique_c*100:.1f}%)",
        'Uniq Sym R50': unique_r50_sym,
        'Uniq Sym R100': unique_r100_sym,
        'Med Succ Signals/Sym': med_succ_per_sym,
    })

print(pd.DataFrame(metrics).to_markdown(index=False))

# Show Top 20
print("\nTop 20 Symbols contributing R100 hits (Raw):")
for strat in ['W', 'D1', 'D2']:
    succ = strat_events[(strat_events['strategy'] == strat) & (strat_events['hit_r100'])]
    print(f"\n{strat}:")
    print(succ.groupby('symbol').size().nlargest(20).to_string())

# 4. First Signal Lead Time
# We group all R100 hits globally across strategies into overarching generic campaigns (using 252 day separation)
print("\n--- First Signal Lead Time (R100 Campaigns) ---")
r100_all = strat_events[strat_events['hit_r100']].sort_values(['symbol', 'signal_date']).copy()
r100_all['global_diff'] = r100_all.groupby('symbol')['signal_date'].diff().dt.days
r100_all['global_camp'] = ((r100_all['global_diff'].isna()) | (r100_all['global_diff'] > 252)).cumsum()

camp_lead_times = []
for c_id, cdf in r100_all.groupby('global_camp'):
    sym = cdf['symbol'].iloc[0]
    w_min = cdf[cdf['strategy'] == 'W']['signal_date'].min()
    d1_min = cdf[cdf['strategy'] == 'D1']['signal_date'].min()
    d2_min = cdf[cdf['strategy'] == 'D2']['signal_date'].min()
    
    first_date = cdf['signal_date'].min()
    
    # Calculate delay relative to the ABSOLUTE FIRST signal across any strategy
    w_delay = (w_min - first_date).days if not pd.isna(w_min) else None
    d1_delay = (d1_min - first_date).days if not pd.isna(d1_min) else None
    d2_delay = (d2_min - first_date).days if not pd.isna(d2_min) else None
    
    # Determine which strategy was strictly "first" (delay == 0)
    # Can be ties
    camp_lead_times.append({
        'Campaign': c_id,
        'W_delay': w_delay,
        'D1_delay': d1_delay,
        'D2_delay': d2_delay,
        'W_First': w_delay == 0,
        'D1_First': d1_delay == 0,
        'D2_First': d2_delay == 0,
        'W_Missed': pd.isna(w_min),
        'D2_Missed': pd.isna(d2_min)
    })

lead_df = pd.DataFrame(camp_lead_times)
total_camps = len(lead_df)
print(f"Total Overarching R100 Campaigns: {total_camps}")
print(f"W was FIRST (or tied): {lead_df['W_First'].sum()} ({lead_df['W_First'].sum()/total_camps*100:.1f}%)")
print(f"D1 was FIRST (or tied): {lead_df['D1_First'].sum()} ({lead_df['D1_First'].sum()/total_camps*100:.1f}%)")
print(f"D2 was FIRST (or tied): {lead_df['D2_First'].sum()} ({lead_df['D2_First'].sum()/total_camps*100:.1f}%)")

print("\nMissed Campaigns (strategy never fired during the overarching R100 run):")
print(f"W completely missed: {lead_df['W_Missed'].sum()} ({lead_df['W_Missed'].sum()/total_camps*100:.1f}%)")
print(f"D2 completely missed: {lead_df['D2_Missed'].sum()} ({lead_df['D2_Missed'].sum()/total_camps*100:.1f}%)")

print("\nMedian Delay (when not first, but did fire):")
w_delays = lead_df[~lead_df['W_Missed'] & (lead_df['W_delay'] > 0)]['W_delay']
d2_delays = lead_df[~lead_df['D2_Missed'] & (lead_df['D2_delay'] > 0)]['D2_delay']
print(f"W median delay: {w_delays.median()} days")
print(f"D2 median delay: {d2_delays.median()} days")
