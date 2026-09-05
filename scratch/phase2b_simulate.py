import pandas as pd
import numpy as np
import time
import os
import sys

def main():
    print("Loading data...")
    # Load Stocks again to simulate exits
    df = pd.read_pickle('scratch/minervini_base.pkl') if os.path.exists('scratch/minervini_base.pkl') else pd.read_csv('/home/immanuels/Desktop/mri-int/backups/20260304/daily_prices.csv')
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Calculate 10-day EMA and 3-day swing low for trailing stop
    df['ema_10'] = df.groupby('symbol')['close'].transform(lambda x: x.ewm(span=10, adjust=False).mean())
    df['low_rolling_3'] = df.groupby('symbol')['low'].transform(lambda x: x.rolling(3, min_periods=1).min())
    df['ema_10_shift_1'] = df.groupby('symbol')['ema_10'].shift(1)
    df['low_rolling_3_shift_1'] = df.groupby('symbol')['low_rolling_3'].shift(1)
    
    # Group by symbol for fast access
    print("Indexing price data for fast lookup...")
    grouped = df.groupby('symbol')
    price_data = {}
    for sym, group in grouped:
        price_data[sym] = group.set_index('date').sort_index()

    # Load candidates
    candidates = pd.read_pickle('scratch/phase2b_candidates.pkl')
    
    trades = []
    
    slippages = [0.0, 0.002, 0.005]
    execution_variants = ['Optimistic', 'Conservative']
    
    print("Starting trade simulation...")
    for idx, row in candidates.iterrows():
        sym = row['symbol']
        if sym not in price_data: continue
        sym_df = price_data[sym]
        
        breakout_date = row['breakout_date']
        next_day_date = row['next_day_date']
        
        if breakout_date not in sym_df.index: continue
        
        future_df = sym_df.loc[breakout_date:]
        
        for variant in execution_variants:
            if variant == 'Optimistic':
                entry_date = breakout_date
                base_entry_price = row['breakout_price']
            else: # Conservative
                if pd.isnull(next_day_date) or next_day_date not in sym_df.index:
                    continue
                entry_date = next_day_date
                base_entry_price = row['next_day_open']
                if pd.isnull(base_entry_price): continue
            
            for slippage in slippages:
                entry_price = base_entry_price * (1 + slippage)
                initial_stop = row['initial_stop']
                
                if entry_price <= initial_stop:
                    continue # Invalid setup mechanically
                    
                risk_per_share = entry_price - initial_stop
                account_risk_pct = 0.0075
                capital = 1000000
                shares = (capital * account_risk_pct) / risk_per_share
                
                # Phase 1: Target +2R or +5-7% (using 6% for 5-7%)
                # Let's strictly use +2R since R is defined mechanically
                phase1_target = entry_price + (2 * risk_per_share)
                # Phase 2: Target +3R -> Trailing Stop
                phase2_target = entry_price + (3 * risk_per_share)
                
                current_stop = initial_stop
                state = 0 # 0=Initial, 1=Phase1 (+2R hit, stop at breakeven), 2=Phase2 (+3R hit, trailing)
                
                exit_date = None
                exit_price = None
                exit_reason = ""
                
                # Iterate daily starting from entry_date
                trade_future = sym_df.loc[entry_date:]
                
                for t_date, t_row in trade_future.iterrows():
                    # Check stop loss FIRST (conservative daily bar ambiguity)
                    if t_row['low'] <= current_stop:
                        exit_date = t_date
                        # If opening gap is below stop, execute at open (worse price), else at stop price
                        exit_price = min(t_row['open'], current_stop)
                        exit_reason = "Stop Loss" if state == 0 else "Trailing Stop"
                        break
                        
                    # State transitions
                    if state == 0 and t_row['high'] >= phase1_target:
                        state = 1
                        current_stop = entry_price * (1 + slippage) # Breakeven + slippage buffer
                        
                    if state == 1 and t_row['high'] >= phase2_target:
                        state = 2
                        
                    if state == 2:
                        # Use yesterday's EMA10 and Swing Low to prevent look-ahead
                        prev_ema10 = t_row['ema_10_shift_1']
                        prev_low3 = t_row['low_rolling_3_shift_1']
                        if not pd.isnull(prev_ema10) and not pd.isnull(prev_low3):
                            new_trail = max(prev_ema10, prev_low3)
                            if new_trail > current_stop:
                                current_stop = new_trail
                                
                if exit_date is None:
                    # Still open at end of dataset
                    exit_date = trade_future.index[-1]
                    exit_price = trade_future.iloc[-1]['close']
                    exit_reason = "End of Data"
                    
                gross_r = (exit_price - entry_price) / risk_per_share
                
                trades.append({
                    'trade_id': f"{sym}_{entry_date.strftime('%Y%m%d')}_{variant[:3]}_S{int(slippage*1000)}",
                    'symbol': sym,
                    'setup_date': row['setup_date'],
                    'vcp_start': row['vcp_start'],
                    'vcp_end': row['vcp_end'],
                    'pivot_date': row['pivot_date'],
                    'pivot': row['pivot'],
                    'breakout_date': breakout_date,
                    'entry_date': entry_date,
                    'entry_price': entry_price,
                    'initial_stop': initial_stop,
                    'risk_per_share': risk_per_share,
                    'shares': shares,
                    'capital_at_entry': capital,
                    'account_risk_pct': account_risk_pct * 100,
                    'exit_date': exit_date,
                    'exit_price': exit_price,
                    'exit_reason': exit_reason,
                    'gross_R': gross_r,
                    'net_R': gross_r, # Assuming no commissions modeled, so net = gross
                    'holding_days': (exit_date - entry_date).days,
                    'contraction_count': 2, # Based on Phase 2A simplified model
                    'vdu_count': row['vdu_count'],
                    'breakout_volume_ratio': row['breakout_vol_ratio'],
                    'relative_performance_3m': row['rel_perf_3m'],
                    'relative_performance_6m': row['rel_perf_6m'],
                    'relative_performance_12m': row['rel_perf_12m'],
                    'sma200_slope_10': row['sma200_slope_10'],
                    'sma200_slope_20': row['sma200_slope_20'],
                    'sma200_slope_40': row['sma200_slope_40'],
                    'slippage_buffer_assumption': f"{slippage*100:.2f}%",
                    'execution_variant': "DAILY-BAR OPTIMISTIC EXECUTION PROXY" if variant == 'Optimistic' else "CONSERVATIVE",
                    'year': entry_date.year,
                    'rs_track': 'Track B' if (row['rel_perf_3m'] > 1.0 and row['rel_perf_6m'] > 1.0 and row['rel_perf_12m'] > 1.0) else 'Track A (Only)'
                })
                
    print("Saving trade ledger...")
    trades_df = pd.DataFrame(trades)
    
    # Label Tracks correctly
    # If a trade qualifies for Track B, it ALSO qualifies for Track A. 
    # Track A is the universe without any RS filter.
    trades_df['Track_A'] = True 
    trades_df['Track_B'] = (trades_df['relative_performance_3m'] > 1.0) & (trades_df['relative_performance_6m'] > 1.0) & (trades_df['relative_performance_12m'] > 1.0)
    
    os.makedirs('docs/research', exist_ok=True)
    trades_df.to_csv('docs/research/trade_ledger.csv', index=False)
    trades_df.to_pickle('scratch/phase2b_trades.pkl')
    print(f"Total simulated trades generated: {len(trades)}")

if __name__ == '__main__':
    main()
