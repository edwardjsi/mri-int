import pandas as pd
import numpy as np

events_df = pd.read_csv('cai_backtest_events.csv')
prices_df = pd.read_csv('backups/20260304/daily_prices.csv', usecols=['symbol', 'date', 'open', 'high', 'low', 'close'], low_memory=False)

prices_df['date'] = pd.to_datetime(prices_df['date'])
events_df['signal_date'] = pd.to_datetime(events_df['signal_date'])
prices_df = prices_df.sort_values(['symbol', 'date']).reset_index(drop=True)

# Precompute 126-day and 252-day forward rolling max highs per symbol
# We want the max high in the NEXT 126 and 252 days, starting from the current index
# A simple way using pandas:
print("Precomputing forward rolling metrics...")
grouped = prices_df.groupby('symbol')['high']
# .shift(-1) means starting from the next day (execution day), but execution day itself is day 0 of the forward look.
# Actually, the user says: "from the CAI execution price". Execution happens at the open of the next session.
# The prices_df is sorted.
prices_df['max_high_126'] = grouped.rolling(126, min_periods=1).max().reset_index(level=0, drop=True)
# But wait, rolling is backward looking. To make it forward looking, we reverse the dataframe, roll, and reverse back.
prices_rev = prices_df.iloc[::-1].copy()
grouped_rev = prices_rev.groupby('symbol')['high']
prices_df['max_high_126_fwd'] = grouped_rev.rolling(126, min_periods=1).max().reset_index(level=0, drop=True).iloc[::-1]
prices_df['max_high_252_fwd'] = grouped_rev.rolling(252, min_periods=1).max().reset_index(level=0, drop=True).iloc[::-1]

prices_df['next_date'] = prices_df.groupby('symbol')['date'].shift(-1)
prices_df['next_open'] = prices_df.groupby('symbol')['open'].shift(-1)

print("Calculating outcome labels...")
results = []
for strat in ['W', 'D1', 'D2']:
    strat_events = events_df[(events_df['strategy'] == strat) & (events_df['event'] == 'BREAKOUT')].copy()
    
    # Merge on the event date (which is the breakout close date)
    strat_events = strat_events.merge(prices_df[['symbol', 'date', 'next_date', 'next_open', 'max_high_126_fwd', 'max_high_252_fwd']], left_on=['symbol', 'signal_date'], right_on=['symbol', 'date'], how='left')
    strat_events = strat_events.dropna(subset=['next_date', 'next_open'])
    
    # The max_high_126_fwd at the row of the execution date (next_date). So we need to shift max_high by -1.
    strat_events['exec_max_high_126'] = strat_events.groupby('symbol')['max_high_126_fwd'].shift(-1)
    
    # Actually, simpler: merge again on next_date to get the forward max highs exactly from the execution day
    temp = prices_df[['symbol', 'date', 'max_high_126_fwd', 'max_high_252_fwd']].rename(columns={'date':'exec_date', 'max_high_126_fwd':'m126', 'max_high_252_fwd':'m252'})
    strat_events = strat_events.merge(temp, left_on=['symbol', 'next_date'], right_on=['symbol', 'exec_date'], how='left')
    
    strat_events['hit_r50'] = strat_events['m126'] >= strat_events['next_open'] * 1.50
    strat_events['hit_r100'] = strat_events['m252'] >= strat_events['next_open'] * 2.00
    
    r50_hits = strat_events['hit_r50'].sum()
    r100_hits = strat_events['hit_r100'].sum()
    total = len(strat_events)
    
    results.append({
        'Strategy': strat,
        'Total Breakouts': total,
        'R50 Hits': r50_hits,
        'R100 Hits': r100_hits,
        'R50 Hit Rate': f"{(r50_hits/total)*100:.1f}%" if total > 0 else "0%",
        'R100 Hit Rate': f"{(r100_hits/total)*100:.1f}%" if total > 0 else "0%"
    })

print("\n--- Outcome Label Results ---")
print(pd.DataFrame(results).to_markdown(index=False))
