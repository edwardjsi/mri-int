import pandas as pd
import numpy as np

print("Loading events and daily prices...")
events_df = pd.read_csv('cai_backtest_events.csv')
prices_df = pd.read_csv('backups/20260304/daily_prices.csv', usecols=['symbol', 'date', 'open', 'high', 'low', 'close'], low_memory=False)
prices_df['date'] = pd.to_datetime(prices_df['date'])
events_df['signal_date'] = pd.to_datetime(events_df['signal_date'])

# We need the execution date. The event 'date' is the breakout close date.
# Execution happens on the *next available trading day*.
prices_df = prices_df.sort_values(['symbol', 'date']).reset_index(drop=True)

# Create a mapping for fast lookup
prices_df['next_date'] = prices_df.groupby('symbol')['date'].shift(-1)
prices_df['next_open'] = prices_df.groupby('symbol')['open'].shift(-1)

print("Calculating outcome labels...")
results = []
for strat in ['W', 'D1', 'D2']:
    strat_events = events_df[(events_df['strategy'] == strat) & (events_df['event'] == 'BREAKOUT')].copy()
    
    # Merge with prices to get execution price (next_open) and execution date
    strat_events = strat_events.merge(prices_df[['symbol', 'date', 'next_date', 'next_open']], left_on=['symbol', 'signal_date'], right_on=['symbol', 'date'], how='left')
    strat_events = strat_events.dropna(subset=['next_date', 'next_open'])
    
    r50_hits = 0
    r100_hits = 0
    
    for idx, row in strat_events.iterrows():
        sym = row['symbol']
        exec_date = row['next_date']
        exec_price = row['next_open']
        
        # Future prices strictly AFTER execution date (inclusive of execution date itself since it executes at open, but high/low of that day apply)
        future_prices = prices_df[(prices_df['symbol'] == sym) & (prices_df['date'] >= exec_date)].head(252)
        
        if len(future_prices) == 0:
            continue
            
        future_prices = future_prices.reset_index(drop=True)
        future_prices['days_since'] = future_prices.index
        
        # R50 within 126 days
        fp_126 = future_prices.head(126)
        if len(fp_126) > 0:
            max_high_126 = fp_126['high'].max()
            if max_high_126 >= exec_price * 1.50:
                r50_hits += 1
                
        # R100 within 252 days
        if len(future_prices) > 0:
            max_high_252 = future_prices['high'].max()
            if max_high_252 >= exec_price * 2.00:
                r100_hits += 1
                
    results.append({
        'Strategy': strat,
        'Total Breakouts': len(strat_events),
        'R50 Hits': r50_hits,
        'R100 Hits': r100_hits,
        'R50 Hit Rate': f"{(r50_hits/len(strat_events))*100:.1f}%" if len(strat_events) > 0 else "0%",
        'R100 Hit Rate': f"{(r100_hits/len(strat_events))*100:.1f}%" if len(strat_events) > 0 else "0%"
    })

print("\n--- Outcome Label Results ---")
print(pd.DataFrame(results).to_markdown(index=False))
