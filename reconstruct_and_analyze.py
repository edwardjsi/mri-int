import os
import pandas as pd
import numpy as np
from engine_core.db import get_connection
import gc

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
    
    # Identify breakouts
    breakouts = (
        (s_df['close'] > s_df['high_10d']) &
        (s_df['vol_multiplier'] >= 1.3) &
        (s_df['close'] > s_df['ema_50']) &
        (s_df['ema_50'] > s_df['ema_200']) &
        (s_df['weekly_rsi_14'] >= 60) &
        (s_df['macd_hist'] > 0)
    )
    s_df['is_breakout'] = breakouts
    
    if not s_df['is_breakout'].any():
        return None
        
    # Calculate Forward Returns & MFE/MAE
    # Shift prices to simulate holding periods
    # T+1 Entry (approximate by using next day's open or close; we'll use T+1 close for conservative modeling as done before, or T+1 open)
    # The PRD said entry is T+1. We'll use T+1 close as the entry price to match previous exit logic.
    s_df['entry_price'] = s_df['close'].shift(-1)
    
    # Returns over N sessions from entry
    windows = [5, 10, 20, 60, 120]
    for w in windows:
        # Exit price is T+1+w
        exit_price = s_df['close'].shift(-(1 + w))
        s_df[f'ret_{w}'] = (exit_price - s_df['entry_price']) / s_df['entry_price']
        
        # MFE/MAE over the holding period
        # Rolling max/min of high/low over the next w days
        # We want the max high from T+1 to T+1+w
        # To vectorize this: reverse the series, use rolling, reverse back
        rev_high = s_df['high'][::-1]
        rev_low = s_df['low'][::-1]
        
        max_high = rev_high.rolling(window=w, min_periods=1).max()[::-1].shift(-1)
        min_low = rev_low.rolling(window=w, min_periods=1).min()[::-1].shift(-1)
        
        s_df[f'mfe_{w}'] = (max_high - s_df['entry_price']) / s_df['entry_price']
        s_df[f'mae_{w}'] = (min_low - s_df['entry_price']) / s_df['entry_price']
        
    # Phase 0E: Strict DATA_TERMINATION rule
    # If a trade reaches the end of the data (e.g. shift produces NaN), it remains NaN.
    # We do NOT forward fill.
    
    # Keep only breakout rows from 2005 onwards
    bo_df = s_df[s_df['is_breakout'] & (s_df['date'] >= '2005-01-01')].copy()
    
    return bo_df[['symbol', 'date', 'entry_price'] + 
                 [f'ret_{w}' for w in windows] + 
                 [f'mfe_{w}' for w in windows] + 
                 [f'mae_{w}' for w in windows]]

def run_analysis():
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
    
    all_breakouts = []
    
    # Process in batches
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
            res = calculate_mri_indicators(s_df)
            if res is not None and not res.empty:
                all_breakouts.append(res)
                
        gc.collect()
        
    conn.close()
    
    if not all_breakouts:
        print("No breakouts found.")
        return
        
    final_df = pd.concat(all_breakouts, ignore_index=True)
    final_df = final_df.merge(regime_df, on='date', how='left')
    
    final_df.to_csv('mri_v0_breakouts.csv', index=False)
    print(f"Saved {len(final_df)} historical breakouts.")
    
    # Analysis & Formatting
    windows = [5, 10, 20, 60, 120]
    
    with open('v0_analysis_report.md', 'w') as f:
        f.write("# V0.0 MRI Entry Edge Analysis\\n\\n")
        f.write(f"**Total Breakouts Analysed:** {len(final_df)} (2005 - 2026)\\n\\n")
        
        for regime in ['ALL', 'BULL', 'BEAR', 'TRANSITION']:
            if regime == 'ALL':
                r_df = final_df
            else:
                r_df = final_df[final_df['regime'] == regime]
                
            f.write(f"## Regime: {regime} (N={len(r_df)})\\n")
            
            if len(r_df) < 10:
                f.write("Not enough data.\\n\\n")
                continue
                
            results = []
            for w in windows:
                ret_col = f'ret_{w}'
                mfe_col = f'mfe_{w}'
                mae_col = f'mae_{w}'
                
                valid_ret = r_df[ret_col].dropna()
                valid_mfe = r_df[mfe_col].dropna()
                valid_mae = r_df[mae_col].dropna()
                
                if len(valid_ret) == 0: continue
                
                med_ret = valid_ret.median() * 100
                med_mfe = valid_mfe.median() * 100
                med_mae = valid_mae.median() * 100
                win_rate = (valid_ret > 0).mean() * 100
                
                pct_5 = (valid_mfe >= 0.05).mean() * 100
                pct_10 = (valid_mfe >= 0.10).mean() * 100
                pct_20 = (valid_mfe >= 0.20).mean() * 100
                pct_50 = (valid_mfe >= 0.50).mean() * 100
                
                results.append({
                    'Horizon': f"{w} Days",
                    'Trades': len(valid_ret),
                    'Win Rate (%)': f"{win_rate:.1f}",
                    'Median Ret (%)': f"{med_ret:.2f}",
                    'Median MFE (%)': f"{med_mfe:.2f}",
                    'Median MAE (%)': f"{med_mae:.2f}",
                    '>= 5% (%)': f"{pct_5:.1f}",
                    '>= 10% (%)': f"{pct_10:.1f}",
                    '>= 20% (%)': f"{pct_20:.1f}",
                    '>= 50% (%)': f"{pct_50:.1f}"
                })
                
            res_df = pd.DataFrame(results)
            f.write(res_df.to_markdown(index=False))
            f.write("\\n\\n")

if __name__ == '__main__':
    run_analysis()
