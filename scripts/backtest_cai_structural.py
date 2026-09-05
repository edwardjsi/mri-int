import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

def fetch_data(start_date="2023-01-01", limit_symbols=None):
    df_list = []
    for sym in limit_symbols:
        # Map to yfinance tickers
        yf_ticker = f"{sym}.NS"
        data = yf.download(yf_ticker, start=start_date, progress=False)
        
        # Flatten MultiIndex columns if any
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
            
        # Standardize column names
        data = data.reset_index()
        data.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in data.columns]
        
        # Rename date column
        if 'date' in data.columns:
            data['date'] = pd.to_datetime(data['date'])
        elif 'datetime' in data.columns:
            data = data.rename(columns={'datetime': 'date'})
            data['date'] = pd.to_datetime(data['date'])
        elif 'index' in data.columns:
            data = data.rename(columns={'index': 'date'})
            data['date'] = pd.to_datetime(data['date'])
            
        data['symbol'] = sym
        df_list.append(data)
        
    df = pd.concat(df_list, ignore_index=True)
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    return df

def run_gate1_validation(df):
    all_events = []
    symbols = df['symbol'].unique()
    
    for sym in symbols:
        sdf = df[df['symbol'] == sym].copy().reset_index(drop=True)
        sdf.set_index('date', inplace=True)
        
        # Next open and returns lookup
        sdf['next_open'] = sdf['open'].shift(-1)
        sdf['next_date'] = sdf.index.to_series().shift(-1)
        
        # --- STRATEGY W (Weekly) ---
        wdf = sdf.resample('W-FRI').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
        }).dropna()
        
        if not wdf.empty:
            wdf['w_high_10'] = wdf['high'].rolling(10).max().shift(1)
            
            for dt, row in wdf.iterrows():
                bo = row['w_high_10']
                if pd.isnull(bo):
                    continue
                
                # Execution Date is the NEXT date in the daily dataframe after this Friday
                daily_after = sdf[sdf.index > dt]
                if daily_after.empty:
                    continue
                exec_date = daily_after.index[0]
                exec_price = daily_after.iloc[0]['open']
                
                # Check Breakout
                if row['close'] > bo:
                    all_events.append({
                        "symbol": sym, "strategy": "W", "signal_date": dt.date(),
                        "breakout_level": round(float(bo), 2), "signal_close": round(float(row['close']), 2),
                        "execution_date": exec_date.date(), "execution_open": round(float(exec_price), 2)
                    })

        # --- STRATEGY D1 & D2 (Daily) ---
        ddf = sdf.copy()
        ddf['d_high_10'] = ddf['high'].rolling(10).max().shift(1)
        
        for strategy in ['D1', 'D2']:
            for dt, row in ddf.iterrows():
                bo = row['d_high_10']
                if pd.isnull(bo) or pd.isnull(row['next_date']):
                    continue
                
                # Check Breakout
                if row['close'] > bo:
                    all_events.append({
                        "symbol": sym, "strategy": strategy, "signal_date": dt.date(),
                        "breakout_level": round(float(bo), 2), "signal_close": round(float(row['close']), 2),
                        "execution_date": row['next_date'].date(), "execution_open": round(float(row['next_open']), 2)
                    })

    events_df = pd.DataFrame(all_events)
    
    print("\n" + "="*80)
    print("GATE 1 VALIDATION OUTPUT: BREAKOUT EVENT DATES (NO LOOK-AHEAD CHECK)")
    print("="*80)
    
    for s in ['W', 'D1', 'D2']:
        print(f"\n--- Strategy {s} ---")
        sample = events_df[events_df['strategy'] == s].head(10)
        if sample.empty:
            print("No breakouts found.")
        else:
            print(sample[['symbol', 'strategy', 'signal_date', 'breakout_level', 'signal_close', 'execution_date', 'execution_open']].to_string(index=False))

if __name__ == "__main__":
    test_symbols = ['RELIANCE', 'TCS', 'HDFCBANK']
    df = fetch_data("2023-01-01", test_symbols)
    run_gate1_validation(df)
