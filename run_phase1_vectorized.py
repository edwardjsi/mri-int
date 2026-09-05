import pandas as pd
import numpy as np

print("Loading data...")
df = pd.read_csv('backups/20260304/daily_prices.csv', low_memory=False)
df['date'] = pd.to_datetime(df['date'])
df = df.dropna(subset=['close', 'high', 'low', 'open']).sort_values(['symbol', 'date']).reset_index(drop=True)

try:
    idf = pd.read_csv('backups/20260304/index_prices.csv')
    idf['date'] = pd.to_datetime(idf['date'])
    nifty = idf[idf['symbol'] == 'NIFTY50'].sort_values('date').copy()
    nifty['ema_50'] = nifty['close'].ewm(span=50, adjust=False).mean()
    nifty['ema_200'] = nifty['close'].ewm(span=200, adjust=False).mean()
    cond = [(nifty['close'] > nifty['ema_50']), (nifty['close'] < nifty['ema_200'])]
    nifty['regime'] = np.select(cond, ['Bull', 'Bear'], default='Sideways')
    regime_map = dict(zip(nifty['date'], nifty['regime']))
except:
    regime_map = {}

def get_regime(dt):
    return regime_map.get(dt, 'Sideways')

print("Processing...")
events = []

grouped = df.groupby('symbol')

def compute_atr(sdf, window):
    prev_close = sdf['close'].shift(1)
    tr1 = sdf['high'] - sdf['low']
    tr2 = (sdf['high'] - prev_close).abs()
    tr3 = (sdf['low'] - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window, min_periods=1).mean()

for sym, sdf in grouped:
    sdf = sdf.copy()
    sdf.set_index('date', inplace=True)
    
    # Returns & Daily Indicators
    sdf['next_open'] = sdf['open'].shift(-1)
    sdf['next_date'] = sdf.index.to_series().shift(-1)
    sdf['ret_5d'] = (sdf['close'].shift(-6) - sdf['next_open']) / sdf['next_open']
    sdf['ret_10d'] = (sdf['close'].shift(-11) - sdf['next_open']) / sdf['next_open']
    sdf['ret_20d'] = (sdf['close'].shift(-21) - sdf['next_open']) / sdf['next_open']
    sdf['ret_60d'] = (sdf['close'].shift(-61) - sdf['next_open']) / sdf['next_open']
    
    sdf['d_high_10'] = sdf['high'].rolling(10).max().shift(1)
    sdf['d_low_4'] = sdf['low'].rolling(4).min().shift(1)
    sdf['d_ema_20'] = sdf['close'].ewm(span=20, adjust=False).mean().shift(1)
    sdf['d_ema_50'] = sdf['close'].ewm(span=50, adjust=False).mean().shift(1)
    sdf['d_ema_200'] = sdf['close'].ewm(span=200, adjust=False).mean().shift(1)
    sdf['d_atr_14'] = compute_atr(sdf, 14).shift(1)
    
    # Strategy W logic
    wdf = sdf.resample('W-FRI').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    wdf['w_high_10'] = wdf['high'].rolling(10).max().shift(1)
    wdf['w_low_4'] = wdf['low'].rolling(4).min().shift(1)
    wdf['w_ema_20'] = wdf['close'].ewm(span=20, adjust=False).mean().shift(1)
    wdf['w_ema_50'] = wdf['close'].ewm(span=50, adjust=False).mean().shift(1)
    wdf['w_atr_14'] = compute_atr(wdf, 14).shift(1)
    
    # Merge W logic into Daily frame (forward fill)
    wdf = wdf[['w_high_10', 'w_low_4', 'w_ema_20', 'w_ema_50', 'w_atr_14']]
    # To avoid lookahead, weekly values generated on Friday apply to the NEXT week.
    # The resampled index is the Friday date.
    sdf = sdf.merge(wdf, left_index=True, right_index=True, how='left')
    sdf[['w_high_10', 'w_low_4', 'w_ema_20', 'w_ema_50', 'w_atr_14']] = sdf[['w_high_10', 'w_low_4', 'w_ema_20', 'w_ema_50', 'w_atr_14']].ffill()

    # D1 & D2 Breakout Detection
    # Breakout condition: current close > previous high_10, but yesterday's close was NOT > yesterday's previous high_10 (first cross)
    
    # Generate Events iteratively for active position management
    active_d1 = active_d2 = active_w = None
    
    for row in sdf.itertuples():
        dt = row.Index
        regime = get_regime(dt)
        
        # ACTIVE POSITIONS
        for strat, active_pos in [('W', active_w), ('D1', active_d1), ('D2', active_d2)]:
            if active_pos:
                active_pos['max_price'] = max(active_pos['max_price'], row.high)
                active_pos['min_price'] = min(active_pos['min_price'], row.low)
                
                # Broker Stop Check
                if row.low < active_pos['quit_lvl'] and not active_pos['broker_stopped']:
                    active_pos['broker_stopped'] = True
                    events.append({"symbol": sym, "strategy": strat, "event": "BROKER_STOP_OUT", "signal_date": dt, "regime": regime, "MAE": (active_pos['min_price'] - active_pos['entry_price']) / active_pos['entry_price'], "MFE": (active_pos['max_price'] - active_pos['entry_price']) / active_pos['entry_price']})
                
                # Struct Inv Check (For D1/D2, Daily Close. For W, Friday Close. We simplify W to Daily Close for struct invalidation in fast backtest or just check on Fridays)
                is_invalid = False
                if strat == 'W' and dt.weekday() == 4:
                    if row.close < active_pos['quit_lvl']: is_invalid = True
                elif strat != 'W':
                    if row.close < active_pos['quit_lvl']: is_invalid = True
                
                if is_invalid:
                    events.append({"symbol": sym, "strategy": strat, "event": "STRUCTURAL_INVALIDATION", "signal_date": dt, "regime": regime, "MAE": (active_pos['min_price'] - active_pos['entry_price']) / active_pos['entry_price'], "MFE": (active_pos['max_price'] - active_pos['entry_price']) / active_pos['entry_price']})
                    if strat == 'W': active_w = None
                    elif strat == 'D1': active_d1 = None
                    elif strat == 'D2': active_d2 = None
                    
        # BREAKOUT CHECKS
        if pd.isnull(row.next_date): continue
        
        if not active_w and pd.notnull(row.w_high_10) and row.close > row.w_high_10:
            struct = row.w_low_4 if pd.notnull(row.w_low_4) else (row.w_ema_50 if pd.notnull(row.w_ema_50) else row.w_ema_20)
            if pd.notnull(struct) and pd.notnull(row.w_atr_14):
                quit_lvl = struct - (0.5 * row.w_atr_14)
                active_w = {"entry_price": row.next_open, "max_price": row.next_open, "min_price": row.next_open, "quit_lvl": quit_lvl, "broker_stopped": False}
                events.append({"symbol": sym, "strategy": "W", "event": "BREAKOUT", "signal_date": dt, "regime": regime, "ret_5d": row.ret_5d, "ret_10d": row.ret_10d, "ret_20d": row.ret_20d, "ret_60d": row.ret_60d})
                
        if not active_d1 and pd.notnull(row.d_high_10) and row.close > row.d_high_10:
            struct = row.d_low_4 if pd.notnull(row.d_low_4) else (row.d_ema_50 if pd.notnull(row.d_ema_50) else row.d_ema_20)
            if pd.notnull(struct) and pd.notnull(row.d_atr_14):
                quit_lvl = struct - (0.5 * row.d_atr_14)
                active_d1 = {"entry_price": row.next_open, "max_price": row.next_open, "min_price": row.next_open, "quit_lvl": quit_lvl, "broker_stopped": False}
                events.append({"symbol": sym, "strategy": "D1", "event": "BREAKOUT", "signal_date": dt, "regime": regime, "ret_5d": row.ret_5d, "ret_10d": row.ret_10d, "ret_20d": row.ret_20d, "ret_60d": row.ret_60d})

        if not active_d2 and pd.notnull(row.d_high_10) and row.close > row.d_high_10:
            struct = row.d_ema_50 if pd.notnull(row.d_ema_50) else row.d_ema_200
            if pd.notnull(struct) and pd.notnull(row.d_atr_14):
                quit_lvl = struct - (0.5 * row.d_atr_14)
                active_d2 = {"entry_price": row.next_open, "max_price": row.next_open, "min_price": row.next_open, "quit_lvl": quit_lvl, "broker_stopped": False}
                events.append({"symbol": sym, "strategy": "D2", "event": "BREAKOUT", "signal_date": dt, "regime": regime, "ret_5d": row.ret_5d, "ret_10d": row.ret_10d, "ret_20d": row.ret_20d, "ret_60d": row.ret_60d})

events_df = pd.DataFrame(events)
events_df.to_csv("cai_backtest_events.csv", index=False)

# Summary
summary_data = []
for s in ['W', 'D1', 'D2']:
    sdf = events_df[events_df['strategy'] == s]
    breakouts = sdf[sdf['event'] == 'BREAKOUT']
    broker_stops = sdf[sdf['event'] == 'BROKER_STOP_OUT']
    struct_invs = sdf[sdf['event'] == 'STRUCTURAL_INVALIDATION']
    for r in ['Bull', 'Sideways', 'Bear', 'ALL']:
        b_df = breakouts if r == 'ALL' else breakouts[breakouts['regime'] == r]
        bs_df = broker_stops if r == 'ALL' else broker_stops[broker_stops['regime'] == r]
        si_df = struct_invs if r == 'ALL' else struct_invs[struct_invs['regime'] == r]
        summary_data.append({
            "Strategy": s,
            "Regime": r,
            "Breakouts": len(b_df),
            "False Breakouts (10d < 0)": round(len(b_df[b_df['ret_10d'] < 0]) / max(len(b_df), 1), 3),
            "Avg 5d Ret": round(b_df['ret_5d'].mean(), 3),
            "Avg 10d Ret": round(b_df['ret_10d'].mean(), 3),
            "Avg 20d Ret": round(b_df['ret_20d'].mean(), 3),
            "Avg 60d Ret": round(b_df['ret_60d'].mean(), 3),
            "Broker Stops": len(bs_df),
            "Struct Invalids": len(si_df),
            "Avg MAE (Inv)": round(si_df['MAE'].mean(), 3) if len(si_df) > 0 else 0,
            "Avg MFE (Inv)": round(si_df['MFE'].mean(), 3) if len(si_df) > 0 else 0,
        })

summary_df = pd.DataFrame(summary_data)
with open('cai_backtest_phase1_report.md', 'w') as f:
    f.write("# CAI Phase 1 Structural Backtest Report\n\n")
    f.write("Dataset: `backups/20260304/daily_prices.csv`\n")
    f.write(f"Cutoff Date: {df['date'].max().date()}\n")
    f.write("Market Cap Breakdown: Not Available in CSV schema\n\n")
    f.write("## Overall Metrics (All Regimes)\n")
    f.write(summary_df[summary_df['Regime'] == 'ALL'].to_markdown(index=False) + "\n\n")
    f.write("## Metrics by Market Regime\n")
    f.write(summary_df[summary_df['Regime'] != 'ALL'].to_markdown(index=False) + "\n")
print("Done!")
