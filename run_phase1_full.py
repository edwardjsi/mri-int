import pandas as pd
import numpy as np
import datetime
import os
import sys

def compute_atr(df, window):
    prev_close = df['close'].shift(1)
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - prev_close).abs()
    tr3 = (df['low'] - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window, min_periods=1).mean()

def prepare_data():
    print("Loading data...")
    df = pd.read_csv('backups/20260304/daily_prices.csv', low_memory=False)
    
    # Filter out bad data
    df['date'] = pd.to_datetime(df['date'])
    df = df.dropna(subset=['close', 'high', 'low', 'open']).copy()
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Load index and compute regime
    print("Computing market regime...")
    try:
        idf = pd.read_csv('backups/20260304/index_prices.csv')
        idf['date'] = pd.to_datetime(idf['date'])
        nifty = idf[idf['symbol'] == 'NIFTY50'].sort_values('date').copy()
        nifty['ema_50'] = nifty['close'].ewm(span=50, adjust=False).mean()
        nifty['ema_200'] = nifty['close'].ewm(span=200, adjust=False).mean()
        
        conditions = [
            (nifty['close'] > nifty['ema_50']),
            (nifty['close'] < nifty['ema_200'])
        ]
        choices = ['Bull', 'Bear']
        nifty['regime'] = np.select(conditions, choices, default='Sideways')
        regime_map = dict(zip(nifty['date'], nifty['regime']))
    except:
        regime_map = {}
        
    return df, regime_map

def run_backtest():
    df, regime_map = prepare_data()
    
    all_events = []
    symbols = df['symbol'].unique()
    
    print(f"Running backtest on {len(symbols)} symbols...")
    
    for idx, sym in enumerate(symbols):
        if idx % 50 == 0:
            print(f"Processed {idx}/{len(symbols)} symbols...")
            
        sdf = df[df['symbol'] == sym].copy()
        sdf.set_index('date', inplace=True)
        
        # Next open and returns lookup
        sdf['next_open'] = sdf['open'].shift(-1)
        sdf['next_date'] = sdf.index.to_series().shift(-1)
        sdf['ret_5d'] = (sdf['close'].shift(-6) - sdf['next_open']) / sdf['next_open']
        sdf['ret_10d'] = (sdf['close'].shift(-11) - sdf['next_open']) / sdf['next_open']
        sdf['ret_20d'] = (sdf['close'].shift(-21) - sdf['next_open']) / sdf['next_open']
        sdf['ret_60d'] = (sdf['close'].shift(-61) - sdf['next_open']) / sdf['next_open']
        
        # We must restrict forward returns if the window doesn't exist
        # Since data ends around May 2026, a 60d return from March 2026 might be NaN. Pandas shift handles this naturally.
        
        # STRATEGY W
        wdf = sdf.resample('W-FRI').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'
        }).dropna()
        
        if not wdf.empty:
            wdf['w_high_10'] = wdf['high'].rolling(10).max().shift(1)
            wdf['w_low_4'] = wdf['low'].rolling(4).min().shift(1)
            wdf['w_ema_20'] = wdf['close'].ewm(span=20, adjust=False).mean().shift(1)
            wdf['w_ema_50'] = wdf['close'].ewm(span=50, adjust=False).mean().shift(1)
            wdf['w_atr_14'] = compute_atr(wdf, 14).shift(1)
            
            # W Event Loop
            active_w_positions = []
            for row in wdf.itertuples():
                dt = row.Index
                bo = row.w_high_10
                sl_cand, ema_50, ema_20, atr = row.w_low_4, row.w_ema_50, row.w_ema_20, row.w_atr_14
                
                struct = sl_cand if pd.notnull(sl_cand) else (ema_50 if pd.notnull(ema_50) else ema_20)
                if pd.isnull(struct) or pd.isnull(atr) or pd.isnull(bo):
                    continue
                    
                quit_lvl = struct - (0.5 * atr)
                pb_lower, pb_upper = struct, struct + atr
                
                daily_after = sdf[sdf.index > dt]
                if daily_after.empty:
                    continue
                exec_date = daily_after.index[0]
                exec_price = daily_after.iloc[0]['open']
                
                # Active Position Updates (broker stop & struct invalidation & pullbacks over the past week)
                daily_in_week = sdf[(sdf.index > dt - pd.Timedelta(days=7)) & (sdf.index <= dt)]
                
                for pos in active_w_positions:
                    if pos['closed']: continue
                    
                    # Track MAE/MFE
                    pos['max_price'] = max(pos['max_price'], daily_in_week['high'].max() if not daily_in_week.empty else pos['max_price'])
                    pos['min_price'] = min(pos['min_price'], daily_in_week['low'].min() if not daily_in_week.empty else pos['min_price'])
                    
                    for d_dt, d_row in daily_in_week.iterrows():
                        if d_row['low'] < pos['quit_lvl'] and not pos['broker_stopped']:
                            pos['broker_stopped'] = True
                            all_events.append({
                                "symbol": sym, "strategy": "W", "event": "BROKER_STOP_OUT",
                                "signal_date": d_dt, "execution_date": d_row['next_date'], "execution_price": d_row['next_open'],
                                "regime": regime_map.get(d_dt, 'Sideways'),
                                "MAE": (pos['min_price'] - pos['entry_price']) / pos['entry_price'],
                                "MFE": (pos['max_price'] - pos['entry_price']) / pos['entry_price']
                            })
                            
                    # Structural invalidation for W is weekly close < quit_lvl
                    if row.close < pos['quit_lvl'] and not pos['struct_invalidated']:
                        pos['struct_invalidated'] = True
                        pos['closed'] = True
                        all_events.append({
                            "symbol": sym, "strategy": "W", "event": "STRUCTURAL_INVALIDATION",
                            "signal_date": dt, "execution_date": exec_date, "execution_price": exec_price,
                            "regime": regime_map.get(dt, 'Sideways'),
                            "MAE": (pos['min_price'] - pos['entry_price']) / pos['entry_price'],
                            "MFE": (pos['max_price'] - pos['entry_price']) / pos['entry_price']
                        })
                
                # Pullback tracking independent of position
                for d_dt, d_row in daily_in_week.iterrows():
                    if pb_lower <= d_row['low'] <= pb_upper:
                        all_events.append({
                            "symbol": sym, "strategy": "W", "event": "PULLBACK_ZONE_REACHED",
                            "signal_date": d_dt, "regime": regime_map.get(d_dt, 'Sideways')
                        })
                        
                # Check Breakout
                if row.close > bo:
                    active_w_positions.append({
                        "entry_price": exec_price, "max_price": exec_price, "min_price": exec_price,
                        "quit_lvl": quit_lvl, "broker_stopped": False, "struct_invalidated": False, "closed": False
                    })
                    all_events.append({
                        "symbol": sym, "strategy": "W", "event": "BREAKOUT", "signal_date": dt, 
                        "execution_date": exec_date, "execution_price": exec_price,
                        "breakout_level": bo, "structure_level": struct, "quit_level": quit_lvl,
                        "regime": regime_map.get(dt, 'Sideways'),
                        "ret_5d": daily_after.iloc[0]['ret_5d'], "ret_10d": daily_after.iloc[0]['ret_10d'],
                        "ret_20d": daily_after.iloc[0]['ret_20d'], "ret_60d": daily_after.iloc[0]['ret_60d']
                    })

        # STRATEGY D1 & D2
        ddf = sdf.copy()
        ddf['d_high_10'] = ddf['high'].rolling(10).max().shift(1)
        ddf['d_low_4'] = ddf['low'].rolling(4).min().shift(1)
        ddf['d_ema_20'] = ddf['close'].ewm(span=20, adjust=False).mean().shift(1)
        ddf['d_ema_50'] = ddf['close'].ewm(span=50, adjust=False).mean().shift(1)
        ddf['d_ema_200'] = ddf['close'].ewm(span=200, adjust=False).mean().shift(1)
        ddf['d_atr_14'] = compute_atr(ddf, 14).shift(1)
        
        for strategy in ['D1', 'D2']:
            active_d_positions = []
            
            for row in ddf.itertuples():
                dt = row.Index
                bo = row.d_high_10
                atr = row.d_atr_14
                
                if strategy == 'D1':
                    struct = row.d_low_4 if pd.notnull(row.d_low_4) else (row.d_ema_50 if pd.notnull(row.d_ema_50) else row.d_ema_20)
                else:
                    struct = row.d_ema_50 if pd.notnull(row.d_ema_50) else row.d_ema_200
                    
                if pd.isnull(struct) or pd.isnull(atr) or pd.isnull(bo) or pd.isnull(row.next_date):
                    continue
                    
                quit_lvl = struct - (0.5 * atr)
                pb_lower, pb_upper = struct, struct + atr
                
                exec_date = row.next_date
                exec_price = row.next_open
                regime = regime_map.get(dt, 'Sideways')
                
                # Active position updates
                for pos in active_d_positions:
                    if pos['closed']: continue
                    
                    pos['max_price'] = max(pos['max_price'], row.high)
                    pos['min_price'] = min(pos['min_price'], row.low)
                    
                    if row.low < pos['quit_lvl'] and not pos['broker_stopped']:
                        pos['broker_stopped'] = True
                        all_events.append({
                            "symbol": sym, "strategy": strategy, "event": "BROKER_STOP_OUT",
                            "signal_date": dt, "execution_date": exec_date, "execution_price": exec_price,
                            "regime": regime,
                            "MAE": (pos['min_price'] - pos['entry_price']) / pos['entry_price'],
                            "MFE": (pos['max_price'] - pos['entry_price']) / pos['entry_price']
                        })
                        
                    if row.close < pos['quit_lvl'] and not pos['struct_invalidated']:
                        pos['struct_invalidated'] = True
                        pos['closed'] = True
                        all_events.append({
                            "symbol": sym, "strategy": strategy, "event": "STRUCTURAL_INVALIDATION",
                            "signal_date": dt, "execution_date": exec_date, "execution_price": exec_price,
                            "regime": regime,
                            "MAE": (pos['min_price'] - pos['entry_price']) / pos['entry_price'],
                            "MFE": (pos['max_price'] - pos['entry_price']) / pos['entry_price']
                        })
                
                if pb_lower <= row.low <= pb_upper:
                    all_events.append({
                        "symbol": sym, "strategy": strategy, "event": "PULLBACK_ZONE_REACHED",
                        "signal_date": dt, "regime": regime
                    })
                    
                if row.close > bo:
                    active_d_positions.append({
                        "entry_price": exec_price, "max_price": exec_price, "min_price": exec_price,
                        "quit_lvl": quit_lvl, "broker_stopped": False, "struct_invalidated": False, "closed": False
                    })
                    all_events.append({
                        "symbol": sym, "strategy": strategy, "event": "BREAKOUT", "signal_date": dt, 
                        "execution_date": exec_date, "execution_price": exec_price,
                        "breakout_level": bo, "structure_level": struct, "quit_level": quit_lvl, "regime": regime,
                        "ret_5d": row.ret_5d, "ret_10d": row.ret_10d, "ret_20d": row.ret_20d, "ret_60d": row.ret_60d
                    })

    print("Backtest complete. Generating reports...")
    events_df = pd.DataFrame(all_events)
    events_df.to_csv('cai_backtest_events.csv', index=False)
    
    # Generate Phase 1 Report
    summary_data = []
    
    for s in ['W', 'D1', 'D2']:
        sdf = events_df[events_df['strategy'] == s]
        
        breakouts = sdf[sdf['event'] == 'BREAKOUT']
        broker_stops = sdf[sdf['event'] == 'BROKER_STOP_OUT']
        struct_invs = sdf[sdf['event'] == 'STRUCTURAL_INVALIDATION']
        
        for r in ['Bull', 'Sideways', 'Bear', 'ALL']:
            if r == 'ALL':
                b_df = breakouts
                bs_df = broker_stops
                si_df = struct_invs
            else:
                b_df = breakouts[breakouts['regime'] == r]
                bs_df = broker_stops[broker_stops['regime'] == r]
                si_df = struct_invs[struct_invs['regime'] == r]
                
            summary_data.append({
                "Strategy": s,
                "Regime": r,
                "Breakouts": len(b_df),
                "False Breakouts (10d < 0)": len(b_df[b_df['ret_10d'] < 0]) / max(len(b_df), 1),
                "Avg 5d Ret": b_df['ret_5d'].mean(),
                "Avg 10d Ret": b_df['ret_10d'].mean(),
                "Avg 20d Ret": b_df['ret_20d'].mean(),
                "Avg 60d Ret": b_df['ret_60d'].mean(),
                "Broker Stops": len(bs_df),
                "Struct Invalids": len(si_df),
                "Avg MAE (Inv)": si_df['MAE'].mean() if len(si_df) > 0 else 0,
                "Avg MFE (Inv)": si_df['MFE'].mean() if len(si_df) > 0 else 0,
            })
            
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv('cai_backtest_phase1_report.csv', index=False)
    
    with open('cai_backtest_phase1_report.md', 'w') as f:
        f.write("# CAI Phase 1 Structural Backtest Report\n\n")
        f.write("Dataset: `backups/20260304/daily_prices.csv`\n")
        f.write(f"Cutoff Date: {df['date'].max().date()}\n")
        f.write("Market Cap Breakdown: Not Available in CSV schema\n\n")
        
        f.write("## Overall Metrics (All Regimes)\n")
        f.write(summary_df[summary_df['Regime'] == 'ALL'].to_markdown(index=False) + "\n\n")
        
        f.write("## Metrics by Market Regime\n")
        f.write(summary_df[summary_df['Regime'] != 'ALL'].to_markdown(index=False) + "\n")

if __name__ == "__main__":
    run_backtest()
