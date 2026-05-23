"""Verify the breakout fix produces results."""
import sys
sys.path.insert(0, '/home/immanuels/Desktop/mri-int')

from engine_core.indicator_engine import (
    compute_indicators, fetch_data, fetch_symbols_needing_repair
)

symbols = ['APOLLOHOSP', 'POWERINDIA', 'TRITURBINE', 'GVT&D',
           'ADANIGREEN', 'TIMKEN', 'KEI', 'NAVINFLUOR']

df, idx_df = fetch_data(symbols)
updates = compute_indicators(df, idx_df)

latest = max(u['date'] for u in updates)
print(f"Latest date: {latest}\n")
for u in updates:
    if u['date'] == latest:
        print(f"{u['symbol']:15s} breakout={u['breakout_state']:20s} cond_brk10d={u['condition_breakout_10d']}")
