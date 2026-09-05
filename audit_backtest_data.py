import os
import pandas as pd
import numpy as np
import random

def run_audits():
    print("Loading data...")
    df_trades = pd.read_csv('backtest_trades_v01.csv')
    df_trades['signal_date'] = pd.to_datetime(df_trades['signal_date'])
    
    unique_dates = np.sort(df_trades['signal_date'].unique())
    n = len(unique_dates)
    train_end = unique_dates[int(n * 0.5)]
    val_end = unique_dates[int(n * 0.75)]
    
    df_train = df_trades[df_trades['signal_date'] <= train_end]
    df_val = df_trades[(df_trades['signal_date'] > train_end) & (df_trades['signal_date'] <= val_end)]
    df_test = df_trades[df_trades['signal_date'] > val_end]
    
    print("\\n=== Chronological Dates ===")
    print(f"Train: {unique_dates[0]} to {train_end}")
    print(f"Val:   {unique_dates[int(n * 0.5) + 1]} to {val_end}")
    print(f"Test:  {unique_dates[int(n * 0.75) + 1]} to {unique_dates[-1]}")
    
    print("\\n=== 1. Trade-level inspection (20 Random Test Trades for Strategy C) ===")
    test_strat_c = df_test[df_test['strategy'] == 'C_BreakoutFailure'].copy()
    
    if len(test_strat_c) > 0:
        sample_size = min(20, len(test_strat_c))
        sample = test_strat_c.sample(sample_size, random_state=42)
        cols = ['symbol', 'signal_date', 'entry_date', 'exit_date', 'duration', 'net_return', 'mfe', 'mae']
        print(sample[cols].to_markdown(index=False))
    
    print("\\n=== 2. MFE Validation (5 trades with MFE > 50%) ===")
    high_mfe = df_trades[df_trades['mfe'] > 0.5].copy()
    if len(high_mfe) > 0:
        sample_mfe = high_mfe.sample(min(5, len(high_mfe)), random_state=42)
        print(sample_mfe[['symbol', 'signal_date', 'entry_date', 'exit_date', 'duration', 'net_return', 'mfe', 'strategy']].to_markdown(index=False))
    else:
        print("No trades found with MFE > 50%")
        
    print("\\n=== 3. Entry Distribution & Forward Returns (Based on G_Hold_120 in Test set) ===")
    # G_Hold_120 gives a pure 120-session window without early exits, good for forward distribution
    test_hold = df_test[df_test['strategy'] == 'G_Hold_120'].copy()
    if len(test_hold) > 0:
        # Since we don't have entry_price directly in the CSV, we can estimate or fetch it.
        # Wait, let's just look at MFE/MAE and returns.
        print(f"Median MFE: {test_hold['mfe'].median() * 100:.2f}%")
        print(f"Median MAE: {test_hold['mae'].median() * 100:.2f}%")
        print(f"Median Net Return: {test_hold['net_return'].median() * 100:.2f}%")
        
        pct_5 = (test_hold['mfe'] >= 0.05).mean() * 100
        pct_10 = (test_hold['mfe'] >= 0.10).mean() * 100
        pct_20 = (test_hold['mfe'] >= 0.20).mean() * 100
        pct_50 = (test_hold['mfe'] >= 0.50).mean() * 100
        
        print(f"% reaching +5%: {pct_5:.1f}%")
        print(f"% reaching +10%: {pct_10:.1f}%")
        print(f"% reaching +20%: {pct_20:.1f}%")
        print(f"% reaching +50%: {pct_50:.1f}%")
        
        # Look at the raw net_returns to see why Win Rate was 0.69%
        wins = test_hold[test_hold['net_return'] > 0]
        print(f"Total Test Trades: {len(test_hold)}, Wins: {len(wins)}")
        if len(test_hold) > 0:
            print("Bottom 10 Returns:")
            print(test_hold['net_return'].sort_values().head(10).values)
            print("Top 10 Returns:")
            print(test_hold['net_return'].sort_values().tail(10).values)

if __name__ == '__main__':
    run_audits()
