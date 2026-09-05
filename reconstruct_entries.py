import os
import pandas as pd
import numpy as np
from engine_core.db import get_connection

def calculate_mri_indicators(s_df):
    # Ensure sorted by date
    s_df = s_df.sort_values('date').reset_index(drop=True)
    
    s_df["ema_50"] = s_df["close"].ewm(span=50, adjust=False).mean()
    s_df["ema_200"] = (
        s_df["close"].ewm(span=200, adjust=False).mean()
        if len(s_df) >= 200
        else s_df["ema_50"]
    )
    
    s_df["avg_volume_20d"] = s_df["volume"].rolling(window=20).mean()
    s_df["high_10d"] = s_df["high"].rolling(window=10).max().shift(1)
    
    # Vol multiplier
    s_df['vol_multiplier'] = s_df['volume'] / s_df['avg_volume_20d']
    
    # Weekly RSI
    delta_w = s_df["close"].diff(5)
    gain_w = delta_w.where(delta_w > 0, 0).rolling(window=14).mean()
    loss_w = (-delta_w.where(delta_w < 0, 0)).rolling(window=14).mean()
    rs_w = gain_w / (loss_w + 1e-9)
    s_df["weekly_rsi_14"] = 100 - (100 / (1 + rs_w))
    
    # MACD
    ema_12 = s_df["close"].ewm(span=12, adjust=False).mean()
    ema_26 = s_df["close"].ewm(span=26, adjust=False).mean()
    macd_line = ema_12 - ema_26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    s_df["macd_hist"] = macd_line - macd_signal
    
    # Breakout condition
    s_df['condition_breakout_10d'] = s_df['close'] > s_df['high_10d']
    
    # Reconstruct classification
    def _is_broken_out(row):
        if (
            row.get('condition_breakout_10d', False)
            and row.get('vol_multiplier', 0) >= 1.3
            and row['close'] > row.get('ema_50', 0) > row.get('ema_200', 0)
            and row.get('weekly_rsi_14', 0) >= 60
            and row.get('macd_hist', 0) > 0
        ):
            return True
        return False
        
    s_df['recon_breakout'] = s_df.apply(_is_broken_out, axis=1)
    return s_df

def run_validation():
    print("Connecting to DB for Validation Gate 1...")
    conn = get_connection()
    
    # We will test on a sample of 20 symbols that have known breakouts in the DB
    query_symbols = """
        SELECT DISTINCT symbol 
        FROM daily_prices 
        WHERE breakout_state = 'BROKEN_OUT' 
        LIMIT 20
    """
    with conn.cursor() as cur:
        cur.execute(query_symbols)
        rows = cur.fetchall()
        test_symbols = [r['symbol'] for r in rows]
    
    print(f"Testing on 20 symbols: {test_symbols}")
    
    placeholders = ','.join(['%s'] * len(test_symbols))
    query_data = f"""
        SELECT symbol, date, close, high, low, volume, breakout_state, ema_50 as db_ema_50, ema_200 as db_ema_200
        FROM daily_prices
        WHERE symbol IN ({placeholders})
        ORDER BY symbol, date
    """
    
    with conn.cursor() as cur:
        cur.execute(query_data, tuple(test_symbols))
        rows = cur.fetchall()
        
    df = pd.DataFrame([dict(r) for r in rows])
    df['date'] = pd.to_datetime(df['date'])
    for col in ['close', 'high', 'low', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    print(f"Loaded {len(df)} rows. Computing indicators...")
    
    mismatches = 0
    total_db_breakouts = 0
    total_recon_breakouts = 0
    
    for symbol in test_symbols:
        s_df = df[df['symbol'] == symbol].copy()
        s_df = calculate_mri_indicators(s_df)
        
        # Only compare for dates where DB actually has computed state (since we know it only goes back ~1 year)
        # We can find the min date where breakout_state IS NOT NULL and != 'CONSOLIDATING' (or just where it's not null, though the default is CONSOLIDATING)
        # Actually, if the DB has 'BROKEN_OUT', we MUST have recon_breakout = True
        
        db_breakouts = s_df[s_df['breakout_state'] == 'BROKEN_OUT']
        recon_breakouts = s_df[s_df['recon_breakout'] == True]
        
        # Find overlap for the period > 2025-01-01 (when we know DB was active)
        period_df = s_df[s_df['date'] >= '2025-03-01']
        
        for _, row in period_df.iterrows():
            db_state = (row['breakout_state'] == 'BROKEN_OUT')
            recon_state = row['recon_breakout']
            
            if db_state: total_db_breakouts += 1
            if recon_state: total_recon_breakouts += 1
            
            if db_state != recon_state:
                mismatches += 1
                print(f"Mismatch on {symbol} at {row['date']}: DB={db_state}, Recon={recon_state}")
                print(f"Recon: close={row['close']}, high_10d={row['high_10d']}, vol_mult={row['vol_multiplier']}, ema_50={row['ema_50']}, ema_200={row['ema_200']}, rsi_14={row['weekly_rsi_14']}, macd={row['macd_hist']}")
                print(f"DB:    ema_50={row['db_ema_50']}, ema_200={row['db_ema_200']}")
                
    conn.close()
    
    print(f"\\nValidation Complete:")
    print(f"Total DB Breakouts in period: {total_db_breakouts}")
    print(f"Total Recon Breakouts in period: {total_recon_breakouts}")
    print(f"Total Mismatches: {mismatches}")
    
    if mismatches == 0:
        print("GATE 1 PASSED: 100% Agreement!")
    else:
        print("GATE 1 FAILED!")

if __name__ == '__main__':
    run_validation()
