import pandas as pd

events = pd.read_csv('cai_backtest_events.csv')
breakouts = events[events['event'] == 'BREAKOUT']

for strat in ['W', 'D1', 'D2']:
    print(f"--- Strategy {strat} ---")
    strat_bo = breakouts[breakouts['strategy'] == strat]
    unique_syms = strat_bo['symbol'].nunique()
    print(f"Total Breakouts: {len(strat_bo)}")
    print(f"Unique Symbols: {unique_syms}")
    
    counts = strat_bo['symbol'].value_counts()
    print(f"Median breakouts per symbol (for symbols with >0 signals): {counts.median()}")
    print("Distribution of breakouts per symbol:")
    print(counts.describe())
    
    print(f"\nTop 20 symbols by breakout count ({strat}):")
    print(counts.head(20).to_string())
    print("\n")
