import pandas as pd
import numpy as np

events = pd.read_csv('cai_backtest_events.csv')
prices = pd.read_csv('backups/20260304/daily_prices.csv', usecols=['symbol', 'date', 'open', 'high', 'low', 'close'], low_memory=False)

prices['date'] = pd.to_datetime(prices['date'])
events['signal_date'] = pd.to_datetime(events['signal_date'])
prices = prices.sort_values(['symbol', 'date']).reset_index(drop=True)

# Precompute forward maxes and next_open
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

# Helper function to do the cross-strategy validation analysis
def analyze_campaigns(hit_col, horizon_days):
    print(f"\n--- Analysis for {hit_col.upper()} Campaigns ---")
    
    # 1. Global overarching campaigns based on ANY strategy hitting the threshold
    hit_events = strat_events[strat_events[hit_col]].sort_values(['symbol', 'signal_date']).copy()
    hit_events['global_diff'] = hit_events.groupby('symbol')['signal_date'].diff().dt.days
    hit_events['global_camp'] = ((hit_events['global_diff'].isna()) | (hit_events['global_diff'] > 252)).cumsum()
    
    d2_to_w_delays = []
    d1_to_w_delays = []
    
    # Validation bins
    d2_disc = 0
    d2_never_w = 0
    d2_val_w = 0
    d2_val_25 = 0
    d2_val_50 = 0
    d2_val_100 = 0
    
    for c_id, cdf in hit_events.groupby('global_camp'):
        w_df = cdf[cdf['strategy'] == 'W']
        d1_df = cdf[cdf['strategy'] == 'D1']
        d2_df = cdf[cdf['strategy'] == 'D2']
        
        w_min = w_df['signal_date'].min() if not w_df.empty else pd.NaT
        d1_min = d1_df['signal_date'].min() if not d1_df.empty else pd.NaT
        d2_min = d2_df['signal_date'].min() if not d2_df.empty else pd.NaT
        
        # Lead time distribution D2 -> W
        if pd.notna(d2_min) and pd.notna(w_min) and w_min >= d2_min:
            delay = (w_min - d2_min).days
            d2_to_w_delays.append(delay)
            
        # Lead time distribution D1 -> W
        if pd.notna(d1_min) and pd.notna(w_min) and w_min >= d1_min:
            delay = (w_min - d1_min).days
            d1_to_w_delays.append(delay)
            
        # D2 Discovery stats
        if pd.notna(d2_min):
            d2_disc += 1
            if pd.isna(w_min):
                d2_never_w += 1
            elif w_min >= d2_min:
                d2_val_w += 1
                
                # Check price appreciation at the exact time of W's first signal relative to D2's first signal execution price
                d2_first_row = d2_df[d2_df['signal_date'] == d2_min].iloc[0]
                d2_exec_price = d2_first_row['next_open']
                
                w_first_row = w_df[w_df['signal_date'] == w_min].iloc[0]
                w_exec_price = w_first_row['next_open']
                
                appreciation = (w_exec_price - d2_exec_price) / d2_exec_price
                
                if appreciation >= 0.25:
                    d2_val_25 += 1
                if appreciation >= 0.50:
                    d2_val_50 += 1
                if appreciation >= 1.00:
                    d2_val_100 += 1
                    
    # Print results
    d2_to_w = pd.Series(d2_to_w_delays)
    d1_to_w = pd.Series(d1_to_w_delays)
    
    print("D2 -> W Lead Time Distribution (days):")
    if not d2_to_w.empty:
        print(d2_to_w.describe().to_string())
    else:
        print("None")
        
    print("\nD1 -> W Lead Time Distribution (days):")
    if not d1_to_w.empty:
        print(d1_to_w.describe().to_string())
    else:
        print("None")
        
    print(f"\nD2 Discovery & W Validation Metrics ({hit_col}):")
    print(f"Discovered by D2: {d2_disc}")
    print(f"  - Never validated by W: {d2_never_w} ({d2_never_w/d2_disc*100:.1f}%)")
    print(f"  - Validated by W (subsequently or same day): {d2_val_w} ({d2_val_w/d2_disc*100:.1f}%)")
    if d2_val_w > 0:
        print(f"      - Validated only after +25% appreciation: {d2_val_25} ({(d2_val_25/d2_val_w)*100:.1f}% of validations)")
        print(f"      - Validated only after +50% appreciation: {d2_val_50} ({(d2_val_50/d2_val_w)*100:.1f}% of validations)")
        print(f"      - Validated only after +100% appreciation: {d2_val_100} ({(d2_val_100/d2_val_w)*100:.1f}% of validations)")

analyze_campaigns('hit_r100', 252)
analyze_campaigns('hit_r50', 126)
