import pandas as pd
import numpy as np
import time
import os
import sys

def main():
    print("Loading data...")
    df = pd.read_pickle('scratch/minervini_base.pkl') if os.path.exists('scratch/minervini_base.pkl') else pd.read_csv('/home/immanuels/Desktop/mri-int/backups/20260304/daily_prices.csv')
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Calculate 10-day EMA and 3-day swing low for trailing stop
    df['ema_10'] = df.groupby('symbol')['close'].transform(lambda x: x.ewm(span=10, adjust=False).mean())
    df['low_rolling_3'] = df.groupby('symbol')['low'].transform(lambda x: x.rolling(3, min_periods=1).min())
    df['ema_10_shift_1'] = df.groupby('symbol')['ema_10'].shift(1)
    df['low_rolling_3_shift_1'] = df.groupby('symbol')['low_rolling_3'].shift(1)
    
    print("Indexing price data for fast lookup...")
    grouped = df.groupby('symbol')
    price_data = {}
    for sym, group in grouped:
        price_data[sym] = group.set_index('date').sort_index()

    candidates = pd.read_pickle('scratch/validation_candidates.pkl')
    print(f"Loaded {len(candidates)} unique setups.")
    
    trades = []
    
    slippages = [0.0, 0.002, 0.005]
    execution_variants = ['Optimistic', 'Conservative']
    tp_variants = ['+2R_ONLY', '+2R_OR_6%']
    
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
                    continue
                    
                risk_per_share = entry_price - initial_stop
                
                for tp_variant in tp_variants:
                    if tp_variant == '+2R_OR_6%':
                        phase1_target = min(entry_price + (2 * risk_per_share), entry_price * 1.06)
                    else:
                        phase1_target = entry_price + (2 * risk_per_share)
                        
                    phase2_target = entry_price + (3 * risk_per_share)
                    
                    current_stop = initial_stop
                    state = 0 # 0=Initial, 1=Phase1, 2=Phase2
                    next_day_state = 0
                    next_day_stop = initial_stop
                    
                    exit_date = None
                    exit_price = None
                    exit_reason = ""
                    
                    trade_future = sym_df.loc[entry_date:]
                    
                    for t_date, t_row in trade_future.iterrows():
                        # State updates ALWAYS happen from the previous day's decision
                        state = next_day_state
                        current_stop = next_day_stop
                        
                        # 1. Check Stop Loss FIRST
                        if t_row['low'] <= current_stop:
                            exit_date = t_date
                            exit_price = min(t_row['open'], current_stop)
                            exit_reason = "Stop Loss" if state == 0 else "Trailing Stop"
                            break
                            
                        # 2. Check targets for NEXT DAY's state changes
                        if state == 0 and t_row['high'] >= phase1_target:
                            next_day_state = 1
                            next_day_stop = entry_price * (1 + slippage) # Breakeven
                            
                        if state == 1 and t_row['high'] >= phase2_target:
                            next_day_state = 2
                            
                        if next_day_state == 2:
                            prev_ema10 = t_row['ema_10'] # We evaluate TODAY to apply TOMORROW
                            prev_low3 = t_row['low_rolling_3']
                            if not pd.isnull(prev_ema10) and not pd.isnull(prev_low3):
                                new_trail = max(prev_ema10, prev_low3)
                                if new_trail > next_day_stop:
                                    next_day_stop = new_trail
                                    
                    if exit_date is None:
                        exit_date = trade_future.index[-1]
                        exit_price = trade_future.iloc[-1]['close']
                        exit_reason = "End of Data"
                        
                    gross_r = (exit_price - entry_price) / risk_per_share
                    
                    trades.append({
                        'trade_id': f"{sym}_{entry_date.strftime('%Y%m%d')}_{variant[:3]}_S{int(slippage*1000)}_{tp_variant}",
                        'symbol': sym,
                        'setup_date': row['setup_date'],
                        'vcp_start': row['vcp_start'],
                        'vcp_end': row['vcp_end'],
                        'pivot': row['pivot'],
                        'breakout_date': breakout_date,
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'initial_stop': initial_stop,
                        'risk_per_share': risk_per_share,
                        'exit_date': exit_date,
                        'exit_price': exit_price,
                        'exit_reason': exit_reason,
                        'net_R': gross_r,
                        'contraction_count': row['contraction_count'],
                        'vdu_count': row['vdu_count'],
                        'breakout_volume_ratio': row['breakout_vol_ratio'],
                        'relative_performance_3m': row['rel_perf_3m'],
                        'relative_performance_6m': row['rel_perf_6m'],
                        'relative_performance_12m': row['rel_perf_12m'],
                        'slippage_buffer_assumption': f"{slippage*100:.2f}%",
                        'execution_variant': "DAILY-BAR OPTIMISTIC EXECUTION PROXY" if variant == 'Optimistic' else "CONSERVATIVE",
                        'tp_variant': tp_variant,
                        'year': entry_date.year,
                        'Track_B': (row['rel_perf_3m'] > 1.0) and (row['rel_perf_6m'] > 1.0) and (row['rel_perf_12m'] > 1.0)
                    })
                
    trades_df = pd.DataFrame(trades)
    os.makedirs('scratch', exist_ok=True)
    trades_df.to_pickle('scratch/validation_scenarios.pkl')
    print(f"Total scenario simulations generated: {len(trades)}")

if __name__ == '__main__':
    main()
