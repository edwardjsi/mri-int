import pandas as pd
import numpy as np
import datetime

def compute_atr(df, window):
    prev_close = df['close'].shift(1)
    tr1 = df['high'] - df['low']
    tr2 = (df['high'] - prev_close).abs()
    tr3 = (df['low'] - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window, min_periods=1).mean()

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
    regime_map = dict(zip(nifty['date'].dt.date, nifty['regime']))
except:
    regime_map = {}

all_events = []
symbols = df['symbol'].unique()

print(f"Processing {len(symbols)} symbols...")
for idx, sym in enumerate(symbols):
    if idx % 50 == 0:
        print(f"Processed {idx}/{len(symbols)}...")
        
    sdf = df[df['symbol'] == sym].copy()
    
    # Calculate indicators
    sdf['next_open'] = sdf['open'].shift(-1)
    sdf['next_date'] = sdf['date'].shift(-1)
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
    
    # Pre-calculate W Strategy logic directly on Daily frame using shifted resampled values!
    # Instead of resampling, we can just compute weekly values and forward fill them.
    # But to be perfectly safe with W logic, we just use a fast list iteration over the daily frame.
    
    dates = sdf['date'].tolist()
    opens = sdf['open'].tolist()
    highs = sdf['high'].tolist()
    lows = sdf['low'].tolist()
    closes = sdf['close'].tolist()
    
    next_opens = sdf['next_open'].tolist()
    next_dates = sdf['next_date'].tolist()
    ret_5ds = sdf['ret_5d'].tolist()
    ret_10ds = sdf['ret_10d'].tolist()
    ret_20ds = sdf['ret_20d'].tolist()
    ret_60ds = sdf['ret_60d'].tolist()
    
    d_high_10s = sdf['d_high_10'].tolist()
    d_low_4s = sdf['d_low_4'].tolist()
    d_ema_20s = sdf['d_ema_20'].tolist()
    d_ema_50s = sdf['d_ema_50'].tolist()
    d_ema_200s = sdf['d_ema_200'].tolist()
    d_atr_14s = sdf['d_atr_14'].tolist()
    
    # Weekly aggregation state
    w_high_10_buffer = []
    w_low_4_buffer = []
    w_closes = []
    w_highs = []
    w_lows = []
    
    active_d1 = None
    active_d2 = None
    
    # D1 / D2 Simulation
    for i in range(len(dates)):
        dt = dates[i].date()
        regime = regime_map.get(dt, 'Sideways')
        
        # D1 Active Management
        if active_d1:
            active_d1['max_price'] = max(active_d1['max_price'], highs[i])
            active_d1['min_price'] = min(active_d1['min_price'], lows[i])
            if lows[i] < active_d1['quit_lvl'] and not active_d1['broker_stopped']:
                active_d1['broker_stopped'] = True
                all_events.append({"symbol": sym, "strategy": "D1", "event": "BROKER_STOP_OUT", "signal_date": dt, "regime": regime, "MAE": (active_d1['min_price'] - active_d1['entry_price']) / active_d1['entry_price'], "MFE": (active_d1['max_price'] - active_d1['entry_price']) / active_d1['entry_price']})
            if closes[i] < active_d1['quit_lvl']:
                all_events.append({"symbol": sym, "strategy": "D1", "event": "STRUCTURAL_INVALIDATION", "signal_date": dt, "regime": regime, "MAE": (active_d1['min_price'] - active_d1['entry_price']) / active_d1['entry_price'], "MFE": (active_d1['max_price'] - active_d1['entry_price']) / active_d1['entry_price']})
                active_d1 = None
                
        # D2 Active Management
        if active_d2:
            active_d2['max_price'] = max(active_d2['max_price'], highs[i])
            active_d2['min_price'] = min(active_d2['min_price'], lows[i])
            if lows[i] < active_d2['quit_lvl'] and not active_d2['broker_stopped']:
                active_d2['broker_stopped'] = True
                all_events.append({"symbol": sym, "strategy": "D2", "event": "BROKER_STOP_OUT", "signal_date": dt, "regime": regime, "MAE": (active_d2['min_price'] - active_d2['entry_price']) / active_d2['entry_price'], "MFE": (active_d2['max_price'] - active_d2['entry_price']) / active_d2['entry_price']})
            if closes[i] < active_d2['quit_lvl']:
                all_events.append({"symbol": sym, "strategy": "D2", "event": "STRUCTURAL_INVALIDATION", "signal_date": dt, "regime": regime, "MAE": (active_d2['min_price'] - active_d2['entry_price']) / active_d2['entry_price'], "MFE": (active_d2['max_price'] - active_d2['entry_price']) / active_d2['entry_price']})
                active_d2 = None

        # D1 Breakout Check
        if not active_d1 and not pd.isnull(d_high_10s[i]) and not pd.isnull(next_dates[i]):
            if closes[i] > d_high_10s[i]:
                struct = d_low_4s[i] if pd.notnull(d_low_4s[i]) else (d_ema_50s[i] if pd.notnull(d_ema_50s[i]) else d_ema_20s[i])
                if pd.notnull(struct) and pd.notnull(d_atr_14s[i]):
                    quit_lvl = struct - (0.5 * d_atr_14s[i])
                    active_d1 = {"entry_price": next_opens[i], "max_price": next_opens[i], "min_price": next_opens[i], "quit_lvl": quit_lvl, "broker_stopped": False}
                    all_events.append({"symbol": sym, "strategy": "D1", "event": "BREAKOUT", "signal_date": dt, "regime": regime, "ret_5d": ret_5ds[i], "ret_10d": ret_10ds[i], "ret_20d": ret_20ds[i], "ret_60d": ret_60ds[i]})

        # D2 Breakout Check
        if not active_d2 and not pd.isnull(d_high_10s[i]) and not pd.isnull(next_dates[i]):
            if closes[i] > d_high_10s[i]:
                struct = d_ema_50s[i] if pd.notnull(d_ema_50s[i]) else d_ema_200s[i]
                if pd.notnull(struct) and pd.notnull(d_atr_14s[i]):
                    quit_lvl = struct - (0.5 * d_atr_14s[i])
                    active_d2 = {"entry_price": next_opens[i], "max_price": next_opens[i], "min_price": next_opens[i], "quit_lvl": quit_lvl, "broker_stopped": False}
                    all_events.append({"symbol": sym, "strategy": "D2", "event": "BREAKOUT", "signal_date": dt, "regime": regime, "ret_5d": ret_5ds[i], "ret_10d": ret_10ds[i], "ret_20d": ret_20ds[i], "ret_60d": ret_60ds[i]})

print("Generating report...")
events_df = pd.DataFrame(all_events)
summary_data = []
for s in ['D1', 'D2']:
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
with open('cai_backtest_phase1_report.md', 'w') as f:
    f.write("# CAI Phase 1 Structural Backtest Report\n\n")
    f.write("Dataset: `backups/20260304/daily_prices.csv`\n")
    f.write(f"Cutoff Date: {df['date'].max().date()}\n")
    f.write("Market Cap Breakdown: Not Available in CSV schema\n\n")
    f.write("## Overall Metrics (All Regimes)\n")
    f.write(summary_df[summary_df['Regime'] == 'ALL'].to_markdown(index=False) + "\n\n")
    f.write("## Metrics by Market Regime\n")
    f.write(summary_df[summary_df['Regime'] != 'ALL'].to_markdown(index=False) + "\n")
