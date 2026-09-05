import os
import pandas as pd
import numpy as np
import gc
from engine_core.db import get_connection

def determine_regime(idx_df):
    idx_df = idx_df.sort_values('date').reset_index(drop=True)
    idx_df['ema_200'] = idx_df['idx_close'].ewm(span=200, adjust=False).mean()
    idx_df['ema_200_slope'] = idx_df['ema_200'].diff(5)
    
    def classify(row):
        if pd.isna(row['ema_200']) or pd.isna(row['ema_200_slope']):
            return 'TRANSITION'
        if row['idx_close'] > row['ema_200'] and row['ema_200_slope'] > 0:
            return 'BULL'
        elif row['idx_close'] < row['ema_200'] and row['ema_200_slope'] < 0:
            return 'BEAR'
        else:
            return 'TRANSITION'
            
    idx_df['regime'] = idx_df.apply(classify, axis=1)
    return idx_df[['date', 'regime']]

def calculate_mri_indicators(s_df):
    s_df = s_df.sort_values('date').reset_index(drop=True)
    if len(s_df) < 200:
        return None
        
    s_df["ema_50"] = s_df["close"].ewm(span=50, adjust=False).mean()
    s_df["ema_200"] = s_df["close"].ewm(span=200, adjust=False).mean()
    s_df["avg_volume_20d"] = s_df["volume"].rolling(window=20).mean()
    s_df["high_10d"] = s_df["high"].rolling(window=10).max().shift(1)
    s_df['vol_multiplier'] = s_df['volume'] / s_df["avg_volume_20d"]
    
    delta_w = s_df["close"].diff(5)
    gain_w = delta_w.where(delta_w > 0, 0).rolling(window=14).mean()
    loss_w = (-delta_w.where(delta_w < 0, 0)).rolling(window=14).mean()
    rs_w = gain_w / (loss_w + 1e-9)
    s_df["weekly_rsi_14"] = 100 - (100 / (1 + rs_w))
    
    ema_12 = s_df["close"].ewm(span=12, adjust=False).mean()
    ema_26 = s_df["close"].ewm(span=26, adjust=False).mean()
    macd_line = ema_12 - ema_26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    s_df["macd_hist"] = macd_line - macd_signal
    
    # ATR 14 calculation
    tr1 = s_df['high'] - s_df['low']
    tr2 = (s_df['high'] - s_df['close'].shift(1)).abs()
    tr3 = (s_df['low'] - s_df['close'].shift(1)).abs()
    s_df['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    s_df['atr_14'] = s_df['tr'].rolling(window=14).mean()
    
    # Breakout condition
    breakouts = (
        (s_df['close'] > s_df['high_10d']) &
        (s_df['vol_multiplier'] >= 1.3) &
        (s_df['close'] > s_df['ema_50']) &
        (s_df['ema_50'] > s_df['ema_200']) &
        (s_df['weekly_rsi_14'] >= 60) &
        (s_df['macd_hist'] > 0)
    )
    s_df['is_breakout'] = breakouts
    
    return s_df

def simulate_exits(s_df, breakouts, symbol):
    trade_results = []
    frozen_events = []
    
    breakout_indices = s_df.index[s_df['is_breakout'] & (s_df['date'] >= '2005-01-01')].tolist()
    
    for T in breakout_indices:
        if T + 1 >= len(s_df):
            continue
            
        signal_date = s_df.loc[T, 'date']
        breakout_level = s_df.loc[T, 'high_10d']
        entry_atr = s_df.loc[T, 'atr_14']
        
        entry_date = s_df.loc[T+1, 'date']
        entry_price = s_df.loc[T+1, 'close']
        
        # We need data up to T + 1 + 120 (hold) + 60 (opp cost)
        forward_slice = s_df.iloc[T+1 : T+1+180].copy().reset_index(drop=True)
        if forward_slice.empty:
            continue
            
        frozen_events.append({
            'symbol': symbol,
            'signal_date': signal_date,
            'breakout_level': breakout_level,
            'atr_14': entry_atr,
            'entry_date': entry_date,
            'entry_price': entry_price
        })
        
        # Simulating the 14 Variants
        # Variant mapping: name -> dict of params
        variants = {
            'C_BreakoutFailure': {'type': 'fixed_level', 'level': breakout_level},
            'D_Fixed_05': {'type': 'fixed_pct', 'pct': 0.05},
            'D_Fixed_07': {'type': 'fixed_pct', 'pct': 0.07},
            'D_Fixed_10': {'type': 'fixed_pct', 'pct': 0.10},
            'D_Fixed_12': {'type': 'fixed_pct', 'pct': 0.12},
            'D_Fixed_15': {'type': 'fixed_pct', 'pct': 0.15},
            'E_ATR_1.5': {'type': 'atr', 'mult': 1.5},
            'E_ATR_2.0': {'type': 'atr', 'mult': 2.0},
            'E_ATR_2.5': {'type': 'atr', 'mult': 2.5},
            'E_ATR_3.0': {'type': 'atr', 'mult': 3.0},
            'F_Trail_10': {'type': 'trail_pct', 'pct': 0.10},
            'F_Trail_15': {'type': 'trail_pct', 'pct': 0.15},
            'F_Trail_20': {'type': 'trail_pct', 'pct': 0.20},
            'G_120_Session': {'type': 'fixed_time', 'days': 120}
        }
        
        # Max horizon for active holding is 120 sessions
        max_idx = min(120, len(forward_slice)) - 1
        
        # Precompute arrays for speed
        closes = forward_slice['close'].values
        highs = forward_slice['high'].values
        lows = forward_slice['low'].values
        
        for v_name, v_params in variants.items():
            exit_idx = max_idx
            
            if v_params['type'] == 'fixed_time':
                exit_idx = max_idx
            else:
                running_max_close = entry_price
                for i in range(max_idx):
                    curr_close = closes[i]
                    if curr_close > running_max_close:
                        running_max_close = curr_close
                        
                    trigger = False
                    if v_params['type'] == 'fixed_level':
                        trigger = (curr_close < v_params['level'])
                    elif v_params['type'] == 'fixed_pct':
                        trigger = (curr_close <= entry_price * (1 - v_params['pct']))
                    elif v_params['type'] == 'atr':
                        trigger = (curr_close <= entry_price - (v_params['mult'] * entry_atr))
                    elif v_params['type'] == 'trail_pct':
                        trigger = (curr_close <= running_max_close * (1 - v_params['pct']))
                        
                    if trigger:
                        # Exit on T+1 close
                        if i + 1 <= max_idx:
                            exit_idx = i + 1
                        else:
                            exit_idx = max_idx
                        break
            
            exit_price = closes[exit_idx]
            holding_period = exit_idx + 1
            ret = (exit_price - entry_price) / entry_price
            
            # MFE/MAE during holding period
            mfe = (np.max(highs[:exit_idx+1]) - entry_price) / entry_price
            mae = (np.min(lows[:exit_idx+1]) - entry_price) / entry_price
            
            # Post-exit Opportunity Cost (Max high over next 60 sessions)
            # Available data from exit_idx + 1 to exit_idx + 61
            post_exit_highs = highs[exit_idx+1 : exit_idx+61]
            if len(post_exit_highs) > 0:
                post_exit_mfe = (np.max(post_exit_highs) - exit_price) / exit_price
            else:
                post_exit_mfe = np.nan
                
            trade_results.append({
                'symbol': symbol,
                'signal_date': signal_date,
                'strategy': v_name,
                'return': ret,
                'mfe': mfe,
                'mae': mae,
                'holding_period': holding_period,
                'post_exit_mfe': post_exit_mfe
            })
            
    return frozen_events, trade_results

def run_pipeline():
    conn = get_connection()
    
    print("Fetching index data for regimes...")
    idx_query = "SELECT date, close as idx_close FROM market_index_prices WHERE symbol='NIFTY50'"
    with conn.cursor() as cur:
        cur.execute(idx_query)
        idx_rows = cur.fetchall()
    
    idx_df = pd.DataFrame([dict(r) for r in idx_rows])
    idx_df['date'] = pd.to_datetime(idx_df['date'])
    idx_df['idx_close'] = pd.to_numeric(idx_df['idx_close'])
    regime_df = determine_regime(idx_df)
    
    print("Fetching all symbols...")
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT symbol FROM daily_prices")
        all_symbols = [r['symbol'] for r in cur.fetchall()]
        
    print(f"Total symbols: {len(all_symbols)}")
    
    all_frozen_events = []
    all_trade_results = []
    
    batch_size = 50
    for i in range(0, len(all_symbols), batch_size):
        batch = all_symbols[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1} / {len(all_symbols)//batch_size + 1}")
        
        placeholders = ','.join(['%s'] * len(batch))
        query = f"""
            SELECT symbol, date, close, high, low, volume
            FROM daily_prices
            WHERE symbol IN ({placeholders})
            ORDER BY symbol, date
        """
        with conn.cursor() as cur:
            cur.execute(query, tuple(batch))
            rows = cur.fetchall()
            
        df = pd.DataFrame([dict(r) for r in rows])
        if df.empty: continue
        
        df['date'] = pd.to_datetime(df['date'])
        for col in ['close', 'high', 'low', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        for sym, s_df in df.groupby('symbol'):
            s_df = calculate_mri_indicators(s_df)
            if s_df is None or s_df.empty:
                continue
                
            frozen_events, trade_results = simulate_exits(s_df, s_df['is_breakout'], sym)
            all_frozen_events.extend(frozen_events)
            all_trade_results.extend(trade_results)
                
        gc.collect()
        
    conn.close()
    
    frozen_df = pd.DataFrame(all_frozen_events)
    frozen_df = frozen_df.merge(regime_df, left_on='signal_date', right_on='date', how='left')
    frozen_df = frozen_df.drop(columns=['date'])
    frozen_df.to_csv('MRI_ENTRY_EVENTS_V0.0.csv', index=False)
    print(f"Frozen Dataset Saved: {len(frozen_df)} events.")
    
    trades_df = pd.DataFrame(all_trade_results)
    trades_df = trades_df.merge(regime_df, left_on='signal_date', right_on='date', how='left')
    trades_df.to_csv('MRI_PHASE1_TRADES.csv', index=False)
    
    generate_report(trades_df)

def generate_report(trades_df):
    # Hide the Test Set (2023-2026)
    train_val_df = trades_df[
        (trades_df['signal_date'] >= '2005-01-01') & 
        (trades_df['signal_date'] <= '2022-12-31')
    ].copy()
    
    train_df = trades_df[
        (trades_df['signal_date'] >= '2005-01-01') & 
        (trades_df['signal_date'] <= '2015-12-31')
    ].copy()
    
    val_df = trades_df[
        (trades_df['signal_date'] >= '2016-01-01') & 
        (trades_df['signal_date'] <= '2022-12-31')
    ].copy()
    
    def calc_metrics(df):
        if df.empty:
            return None
        
        # MFE Capture Ratio = return / MFE
        df['mfe_capture'] = np.where(df['mfe'] > 0, df['return'] / df['mfe'], np.nan)
        
        res = []
        for strat in df['strategy'].unique():
            s_df = df[df['strategy'] == strat]
            
            med_ret = s_df['return'].median() * 100
            mean_ret = s_df['return'].mean() * 100
            win_rate = (s_df['return'] > 0).mean() * 100
            med_mae = s_df['mae'].median() * 100
            med_mfe = s_df['mfe'].median() * 100
            
            med_mfe_cap = s_df['mfe_capture'].median() * 100
            med_opp_cost = s_df['post_exit_mfe'].median() * 100
            
            med_hold = s_df['holding_period'].median()
            
            gross_profits = s_df[s_df['return'] > 0]['return'].sum()
            gross_losses = abs(s_df[s_df['return'] < 0]['return'].sum())
            pf = gross_profits / gross_losses if gross_losses > 0 else np.nan
            
            # Drawdown (approximate by MAE, but max drawdown of the strategy over all trades is different. We will report Median MAE)
            
            pct_20 = (s_df['mfe'] >= 0.20).mean() * 100
            pct_50 = (s_df['mfe'] >= 0.50).mean() * 100
            
            # Stock level stats
            stock_returns = s_df.groupby('symbol')['return'].sum()
            stock_win = (stock_returns > 0).mean() * 100
            med_stock_ret = stock_returns.median() * 100
            unique_stocks = len(stock_returns)
            trades_per_stock = len(s_df) / unique_stocks if unique_stocks > 0 else 0
            
            # Top 1% and 5% contribution
            # Sort all trades by return descending
            sorted_rets = s_df['return'].sort_values(ascending=False).values
            total_net_ret = sorted_rets.sum()
            
            top_1_pct_idx = max(1, int(len(sorted_rets) * 0.01))
            top_5_pct_idx = max(1, int(len(sorted_rets) * 0.05))
            
            # If total_net_ret is negative, contribution % can be misleading.
            # We'll just calculate the gross sum of top 1% returns.
            # The prompt asks for "top 1% / 5% contribution"
            if total_net_ret > 0:
                top_1_contrib = (sorted_rets[:top_1_pct_idx].sum() / total_net_ret) * 100
                top_5_contrib = (sorted_rets[:top_5_pct_idx].sum() / total_net_ret) * 100
            else:
                top_1_contrib = np.nan
                top_5_contrib = np.nan
            
            res.append({
                'Strategy': strat,
                'WinRate(%)': f"{win_rate:.1f}",
                'Med Ret(%)': f"{med_ret:.2f}",
                'Mean Ret(%)': f"{mean_ret:.2f}",
                'PF': f"{pf:.2f}",
                'Med MFE(%)': f"{med_mfe:.2f}",
                'Med MAE(%)': f"{med_mae:.2f}",
                'MFE Cap(%)': f"{med_mfe_cap:.1f}",
                'Opp Cost(%)': f"{med_opp_cost:.1f}",
                'Hold(d)': f"{med_hold:.0f}",
                'Uniq Stk': unique_stocks,
                'Trd/Stk': f"{trades_per_stock:.1f}",
                'Stk Win(%)': f"{stock_win:.1f}",
                'Stk MedRet(%)': f"{med_stock_ret:.2f}",
                'Top 1% Ctrb(%)': f"{top_1_contrib:.1f}" if not np.isnan(top_1_contrib) else "N/A",
                'Top 5% Ctrb(%)': f"{top_5_contrib:.1f}" if not np.isnan(top_5_contrib) else "N/A"
            })
            
        return pd.DataFrame(res).sort_values('Strategy')

    with open('phase1_exit_report.md', 'w') as f:
        f.write("# Phase 1: Exit Methodology Analysis\\n\\n")
        f.write("> **Note:** The Test set (2023-2026) is strictly hidden from this report to prevent leakage during selection.\\n\\n")
        
        f.write("## 1. Combined (Training + Validation: 2005 - 2022)\\n")
        res = calc_metrics(train_val_df)
        if res is not None:
            f.write(res.to_markdown(index=False))
            f.write("\\n\\n")
            
        f.write("## 2. Training (2005 - 2015)\\n")
        res = calc_metrics(train_df)
        if res is not None:
            f.write(res.to_markdown(index=False))
            f.write("\\n\\n")
            
        f.write("## 3. Validation (2016 - 2022)\\n")
        res = calc_metrics(val_df)
        if res is not None:
            f.write(res.to_markdown(index=False))
            f.write("\\n\\n")

if __name__ == '__main__':
    run_pipeline()
