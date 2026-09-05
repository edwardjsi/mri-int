import os
import sys
import pandas as pd
import numpy as np
from datetime import timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from engine_core.db import get_connection

TRANSACTION_COST_BPS = 10  # 0.1% per side (0.2% round trip)

def fetch_data():
    conn = get_connection()
    try:
        # Fetch all breakouts
        print("Fetching breakouts...")
        q_breakouts = """
            SELECT symbol, date as signal_date, close as signal_close, high_10d as breakout_level, atr_14
            FROM daily_prices
            WHERE breakout_state = 'BROKEN_OUT' AND breakout_age = 0
            ORDER BY date, symbol
        """
        with conn.cursor() as cur:
            cur.execute(q_breakouts)
            df_breakouts = pd.DataFrame(cur.fetchall())
        
        # Get unique symbols that have breakouts
        symbols = tuple(df_breakouts['symbol'].unique())
        
        print("Fetching daily prices...")
        # Fetch price data for these symbols to simulate
        placeholders = ','.join(['%s'] * len(symbols))
        q_prices = f"""
            SELECT symbol, date, open, high, low, close, adjusted_close
            FROM daily_prices
            WHERE symbol IN ({placeholders})
            ORDER BY symbol, date
        """
        with conn.cursor() as cur:
            cur.execute(q_prices, symbols)
            df_prices = pd.DataFrame(cur.fetchall())
        
    finally:
        conn.close()
        
    # Adjust prices for splits/dividends
    print("Adjusting prices...")
    df_prices['close'] = df_prices['close'].astype(float)
    df_prices['adjusted_close'] = df_prices['adjusted_close'].astype(float)
    df_prices['open'] = df_prices['open'].astype(float)
    df_prices['high'] = df_prices['high'].astype(float)
    df_prices['low'] = df_prices['low'].astype(float)
    
    df_prices['adj_ratio'] = df_prices['adjusted_close'] / df_prices['close']
    df_prices['adj_open'] = df_prices['open'] * df_prices['adj_ratio']
    df_prices['adj_high'] = df_prices['high'] * df_prices['adj_ratio']
    df_prices['adj_low'] = df_prices['low'] * df_prices['adj_ratio']
    df_prices['adj_close'] = df_prices['adjusted_close']
    
    df_breakouts['breakout_level'] = df_breakouts['breakout_level'].astype(float)
    df_breakouts['atr_14'] = df_breakouts['atr_14'].astype(float)
    
    return df_breakouts, df_prices

def run_simulation():
    df_breakouts, df_prices = fetch_data()
    
    print("Preparing price lookup...")
    # Create a fast lookup dict by symbol
    price_dict = {}
    grouped = df_prices.groupby('symbol')
    for sym, group in grouped:
        # Store as array of dicts for fast iteration
        price_dict[sym] = group.sort_values('date').to_dict('records')
        
    trades = []
    
    print(f"Simulating {len(df_breakouts)} breakouts...")
    for idx, row in df_breakouts.iterrows():
        sym = row['symbol']
        signal_date = row['signal_date']
        bo_level_unadj = row['breakout_level']
        atr_14_unadj = row['atr_14']
        
        if sym not in price_dict:
            print(f"Skipping {sym} - not in price_dict")
            continue
            
        sym_data = price_dict[sym]
        
        # Find index of signal date
        signal_idx = next((i for i, d in enumerate(sym_data) if pd.Timestamp(d['date']) == pd.Timestamp(signal_date)), -1)
        if signal_idx == -1 or signal_idx + 1 >= len(sym_data):
            print(f"Skipping {sym} at {signal_date} - no future data or signal idx not found")
            # No next day data for T+1 entry
            continue
            
        # T+1 Entry
        entry_day = sym_data[signal_idx + 1]
        entry_date = entry_day['date']
        entry_price = entry_day['adj_close']  # Entry at T+1 close
        
        # We need the adjusted BO level and ATR at signal time. 
        # The ratio at signal date:
        signal_day = sym_data[signal_idx]
        adj_ratio_signal = signal_day['adj_ratio']
        bo_level = bo_level_unadj * adj_ratio_signal if pd.notnull(bo_level_unadj) else None
        atr_14 = atr_14_unadj * adj_ratio_signal if pd.notnull(atr_14_unadj) else None
        
        if bo_level is None or atr_14 is None or pd.isna(bo_level) or pd.isna(atr_14):
            print(f"Skipping {sym} at {signal_date} - missing bo_level ({bo_level}) or atr_14 ({atr_14})")
            continue
            
        # Future price slice from T+2 onwards (since we enter at T+1 close, we start tracking exits at T+2 close)
        future_data = sym_data[signal_idx + 2 :]
        
        # Define the strategies
        strategies = {
            'C_BreakoutFailure': None,
            'D_Fixed_05': {'type': 'fixed', 'pct': 0.05},
            'D_Fixed_07': {'type': 'fixed', 'pct': 0.07},
            'D_Fixed_10': {'type': 'fixed', 'pct': 0.10},
            'D_Fixed_12': {'type': 'fixed', 'pct': 0.12},
            'D_Fixed_15': {'type': 'fixed', 'pct': 0.15},
            'E_ATR_1.5': {'type': 'atr', 'mult': 1.5},
            'E_ATR_2.0': {'type': 'atr', 'mult': 2.0},
            'E_ATR_2.5': {'type': 'atr', 'mult': 2.5},
            'E_ATR_3.0': {'type': 'atr', 'mult': 3.0},
            'F_Trail_10': {'type': 'trail', 'pct': 0.10},
            'F_Trail_15': {'type': 'trail', 'pct': 0.15},
            'F_Trail_20': {'type': 'trail', 'pct': 0.20},
            'G_Hold_120': {'type': 'hold', 'days': 120}
        }
        
        # Result placeholder for this breakout
        bo_results = {k: None for k in strategies.keys()}
        
        # Simulate each strategy independently
        for strat_name, strat_params in strategies.items():
            trade_mfe_pct = 0.0
            trade_mae_pct = 0.0
            highest_close_since_entry = entry_price
            
            exit_date = None
            exit_price = None
            sessions_held = 0
            
            for f_idx, f_day in enumerate(future_data):
                sessions_held += 1
                curr_close = f_day['adj_close']
                curr_high = f_day['adj_high']
                curr_low = f_day['adj_low']
                
                # Update MFE / MAE using extreme prices (High/Low)
                mfe = (curr_high - entry_price) / entry_price
                mae = (curr_low - entry_price) / entry_price
                if mfe > trade_mfe_pct: trade_mfe_pct = mfe
                if mae < trade_mae_pct: trade_mae_pct = mae
                if curr_close > highest_close_since_entry:
                    highest_close_since_entry = curr_close
                
                triggered = False
                
                # Evaluate Exit Conditions (evaluated at close)
                if strat_name == 'C_BreakoutFailure':
                    if curr_close < bo_level:
                        triggered = True
                elif strat_name.startswith('D_Fixed'):
                    stop_px = entry_price * (1 - strat_params['pct'])
                    if curr_close < stop_px:
                        triggered = True
                elif strat_name.startswith('E_ATR'):
                    stop_px = entry_price - (atr_14 * strat_params['mult'])
                    if curr_close < stop_px:
                        triggered = True
                elif strat_name.startswith('F_Trail'):
                    stop_px = highest_close_since_entry * (1 - strat_params['pct'])
                    if curr_close < stop_px:
                        triggered = True
                elif strat_name == 'G_Hold_120':
                    if sessions_held >= 120:
                        triggered = True
                        
                if triggered:
                    # Execute T+1 Close
                    if f_idx + 1 < len(future_data):
                        exec_day = future_data[f_idx + 1]
                        exit_date = exec_day['date']
                        exit_price = exec_day['adj_close']
                        sessions_held += 1 # execution day adds 1 to held
                        # update MFE/MAE for the execution day
                        mfe_exec = (exec_day['adj_high'] - entry_price) / entry_price
                        mae_exec = (exec_day['adj_low'] - entry_price) / entry_price
                        if mfe_exec > trade_mfe_pct: trade_mfe_pct = mfe_exec
                        if mae_exec < trade_mae_pct: trade_mae_pct = mae_exec
                    else:
                        # If reached end of data, exit at current day close
                        exit_date = f_day['date']
                        exit_price = curr_close
                    break
            
            if not exit_date:
                if len(future_data) == 0:
                    print(f"Skipping {sym} at {signal_date} - empty future data")
                    continue
                # Never hit stop, still open at end of available data
                last_day = future_data[-1]
                exit_date = last_day['date']
                exit_price = last_day['adj_close']
                sessions_held = len(future_data)
                
            # Post-exit 60 day opportunity
            post_exit_max_return = 0.0
            if exit_date:
                # Find post-exit slice
                exit_idx = next((i for i, d in enumerate(sym_data) if d['date'] == exit_date), -1)
                if exit_idx != -1:
                    post_slice = sym_data[exit_idx + 1 : exit_idx + 61]
                    if post_slice:
                        max_post_price = max(d['adj_high'] for d in post_slice)
                        post_exit_max_return = (max_post_price - exit_price) / exit_price
            
            gross_ret = (exit_price - entry_price) / entry_price
            net_ret = gross_ret - (2 * (TRANSACTION_COST_BPS / 10000.0))
            
            bo_results[strat_name] = {
                'symbol': sym,
                'signal_date': signal_date,
                'entry_date': entry_date,
                'exit_date': exit_date,
                'duration': sessions_held,
                'net_return': net_ret,
                'mfe': trade_mfe_pct,
                'mae': trade_mae_pct,
                'post_exit_max_60d': post_exit_max_return
            }
            
        for s_name, res in bo_results.items():
            res['strategy'] = s_name
            trades.append(res)
            
    df_trades = pd.DataFrame(trades)
    print(f"Simulation completed. Produced {len(df_trades)} trade records.")
    
    # Save to CSV for analysis
    out_file = 'backtest_trades_v01.csv'
    df_trades.to_csv(out_file, index=False)
    print(f"Saved trades to {out_file}")

if __name__ == '__main__':
    run_simulation()
