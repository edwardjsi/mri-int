import pandas as pd

with open('scratch/exit_sensitivity_study.py', 'r') as f:
    exit_code = f.read()

with open('scratch/conditional_exit_study.py', 'r') as f:
    cond_code = f.read()

print("--- EXIT SENSITIVITY ENTRY LOGIC ---")
print('\n'.join([line for line in exit_code.split('\n') if 'buy_signals.append' in line and 'len(positions)' in line or 'row.close > row.d_high_10' in line][0:3]))
print("\n--- CONDITIONAL EXIT ENTRY LOGIC ---")
print('\n'.join([line for line in cond_code.split('\n') if 'buy_signals.append' in line and 'len(positions)' in line or 'row.date) in d2_signal_set' in line][0:3]))

