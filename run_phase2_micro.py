import pandas as pd
import numpy as np
import datetime
from collections import defaultdict

INITIAL_CASH = 1000000.0
MAX_POSITIONS = 10
TRANCHE_TARGETS = {1: 20000, 2: 30000, 3: 50000, 4: 75000, 5: 125000}
SLIPPAGE_BUY = 1.001
SLIPPAGE_SELL = 0.999
TX_COST = 0.0015

symbols_to_test = ['HDFCBANK', 'PATANJALI', 'SUZLON', 'TATASTEEL', 'ZOMATO', 'TCS', 'RELIANCE']

df = pd.read_csv('backups/20260304/daily_prices.csv', low_memory=False)
df['date'] = pd.to_datetime(df['date'])
df = df[(df['symbol'].isin(symbols_to_test)) & (df['date'] >= '2023-01-01')].copy()
df = df.dropna(subset=['close', 'high', 'low', 'open']).sort_values(['symbol', 'date']).reset_index(drop=True)

def compute_atr(sdf, window):
    prev_close = sdf['close'].shift(1)
    tr1 = sdf['high'] - sdf['low']
    tr2 = (sdf['high'] - prev_close).abs()
    tr3 = (sdf['low'] - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window, min_periods=1).mean()

dfs = []
for sym, sdf in df.groupby('symbol'):
    sdf = sdf.copy()
    sdf = sdf.sort_values('date')
    sdf.set_index('date', inplace=True)
    
    sdf['next_open'] = sdf['open'].shift(-1)
    sdf['d_high_10'] = sdf['high'].rolling(10).max().shift(1)
    sdf['d_low_4'] = sdf['low'].rolling(4).min().shift(1)
    sdf['d_ema_20'] = sdf['close'].ewm(span=20, adjust=False).mean().shift(1)
    sdf['d_ema_50'] = sdf['close'].ewm(span=50, adjust=False).mean().shift(1)
    sdf['d_ema_200'] = sdf['close'].ewm(span=200, adjust=False).mean().shift(1)
    sdf['d_atr_14'] = compute_atr(sdf, 14).shift(1)
    
    # Strategy W logic
    wdf = sdf.resample('W-FRI').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    wdf['w_high_10'] = wdf['high'].rolling(10, min_periods=10).max().shift(1)
    wdf['w_low_4'] = wdf['low'].rolling(4).min().shift(1)
    wdf['w_ema_20'] = wdf['close'].ewm(span=20, adjust=False).mean().shift(1)
    wdf['w_ema_50'] = wdf['close'].ewm(span=50, adjust=False).mean().shift(1)
    wdf['w_atr_14'] = compute_atr(wdf, 14).shift(1)
    
    wdf = wdf[['w_high_10', 'w_low_4', 'w_ema_20', 'w_ema_50', 'w_atr_14']]
    sdf = sdf.merge(wdf, left_index=True, right_index=True, how='left')
    sdf[['w_high_10', 'w_low_4', 'w_ema_20', 'w_ema_50', 'w_atr_14']] = sdf[['w_high_10', 'w_low_4', 'w_ema_20', 'w_ema_50', 'w_atr_14']].ffill()
    
    sdf['w_anchor'] = sdf['w_low_4'].combine_first(sdf['w_ema_50']).combine_first(sdf['w_ema_20'])
    sdf['w_quit_lvl'] = sdf['w_anchor'] - (0.5 * sdf['w_atr_14'])
    
    sdf['d2_anchor'] = sdf['d_ema_50'].combine_first(sdf['d_ema_200'])
    sdf['d2_quit_lvl'] = sdf['d2_anchor'] - (0.5 * sdf['d_atr_14'])
    
    sdf['symbol'] = sym
    sdf = sdf.reset_index()
    dfs.append(sdf)

full_df = pd.concat(dfs).sort_values('date').reset_index(drop=True)

cash = INITIAL_CASH
positions = {}
for st in ['W', 'D2', 'D2_W']:
    positions[st] = {}
events = []

def record_event(date, sym, strategy, event_type, price, tranche, cash_before, cash_after, stop, w_val, next_add, reason):
    events.append({
        'date': date, 'symbol': sym, 'strategy': strategy, 'event': event_type,
        'price': round(price, 2) if pd.notnull(price) else None,
        'tranche': tranche, 'cash_before': round(cash_before, 2), 'cash_after': round(cash_after, 2),
        'stop': round(stop, 2) if pd.notnull(stop) else None,
        'W_validation': w_val, 'next_add': round(next_add, 2) if pd.notnull(next_add) else None,
        'exit_reason': reason
    })

def execute_buy(st, sym, row, tranche, add_trigger_price):
    global cash
    target_cap = TRANCHE_TARGETS[tranche]
    
    if sym in positions[st]:
        curr_cap = positions[st][sym]['invested']
        alloc = target_cap - curr_cap
    else:
        alloc = target_cap
        
    if alloc <= 0: return
    if alloc > cash: return
    
    price = row['next_open'] * SLIPPAGE_BUY
    cost = alloc * TX_COST
    total_outlay = alloc + cost
    if total_outlay > cash: return
    
    shares = alloc / price
    cash -= total_outlay
    
    if sym not in positions[st]:
        positions[st][sym] = {'shares': shares, 'invested': alloc, 'tranche': tranche, 'broker_stop': 0, 'w_validated': False, 'entry_date': row['date']}
    else:
        positions[st][sym]['shares'] += shares
        positions[st][sym]['invested'] += alloc
        positions[st][sym]['tranche'] = tranche
        
    if st == 'W':
        positions[st][sym]['broker_stop'] = row['w_quit_lvl']
    else:
        positions[st][sym]['broker_stop'] = row['d2_quit_lvl']
        
    positions[st][sym]['last_add_trigger'] = add_trigger_price
        
    if st == 'D2_W' and tranche > 1:
        positions[st][sym]['w_validated'] = True
        
    record_event(row['date'], sym, st, f"BUY_T{tranche}", price, tranche, cash + total_outlay, cash, positions[st][sym]['broker_stop'], positions[st][sym]['w_validated'], add_trigger_price, "")

def execute_sell(st, sym, row, price, reason):
    global cash
    pos = positions[st][sym]
    val = pos['shares'] * price
    val_after_slip = val * SLIPPAGE_SELL
    cost = val_after_slip * TX_COST
    net_proceeds = val_after_slip - cost
    
    cash_before = cash
    cash += net_proceeds
    record_event(row['date'], sym, st, "SELL", price, pos['tranche'], cash_before, cash, pos['broker_stop'], pos['w_validated'], None, reason)
    del positions[st][sym]

for date, day_df in full_df.groupby('date'):
    for row in day_df.itertuples():
        sym = row.symbol
        is_friday = date.weekday() == 4
        
        for st in ['W', 'D2', 'D2_W']:
            if sym in positions[st]:
                pos = positions[st][sym]
                if row.open <= pos['broker_stop']:
                    execute_sell(st, sym, row._asdict(), row.open, "BROKER_STOP (GAP)")
                    continue
                elif row.low < pos['broker_stop']:
                    execute_sell(st, sym, row._asdict(), pos['broker_stop'], "BROKER_STOP (INTRADAY)")
                    continue
                    
                if st == 'W':
                    if is_friday and row.close < row.w_anchor:
                        execute_sell(st, sym, row._asdict(), row.next_open, "W_STRUCTURAL_EXIT")
                        continue
                elif st == 'D2':
                    if row.close < row.d2_anchor:
                        execute_sell(st, sym, row._asdict(), row.next_open, "D2_STRUCTURAL_EXIT")
                        continue
                elif st == 'D2_W':
                    if pos['w_validated']:
                        if is_friday and row.close < row.w_anchor:
                            execute_sell(st, sym, row._asdict(), row.next_open, "W_STRUCTURAL_EXIT")
                    else:
                        if row.close < row.d2_anchor:
                            execute_sell(st, sym, row._asdict(), row.next_open, "D2_STRUCTURAL_EXIT")
    
    buy_signals = []
    
    for row in day_df.itertuples():
        sym = row.symbol
        if pd.isnull(row.next_open): continue
        is_friday = date.weekday() == 4
        
        # W Baseline
        if sym not in positions['W']:
            if pd.notnull(row.w_high_10) and row.close > row.w_high_10 and len(positions['W']) < MAX_POSITIONS:
                buy_signals.append(('W', sym, row._asdict(), 1, row.w_high_10))
        elif positions['W'][sym]['tranche'] < 5:
            na = row.w_high_10
            if pd.notnull(na) and na != positions['W'][sym].get('last_add_trigger') and row.close > na:
                buy_signals.append(('W', sym, row._asdict(), positions['W'][sym]['tranche'] + 1, na))
                
        # D2 Baseline
        if sym not in positions['D2']:
            if pd.notnull(row.d_high_10) and row.close > row.d_high_10 and len(positions['D2']) < MAX_POSITIONS:
                buy_signals.append(('D2', sym, row._asdict(), 1, row.d_high_10))
        elif positions['D2'][sym]['tranche'] < 5:
            na = row.d_high_10
            if pd.notnull(na) and na != positions['D2'][sym].get('last_add_trigger') and row.close > na:
                buy_signals.append(('D2', sym, row._asdict(), positions['D2'][sym]['tranche'] + 1, na))
                
        # D2_W Architecture
        if sym not in positions['D2_W']:
            if pd.notnull(row.d_high_10) and row.close > row.d_high_10 and len(positions['D2_W']) < MAX_POSITIONS:
                buy_signals.append(('D2_W', sym, row._asdict(), 1, row.d_high_10))
        else:
            pos = positions['D2_W'][sym]
            if pos['tranche'] < 5:
                is_w_valid = pos['w_validated']
                if not is_w_valid and is_friday:
                    is_w_valid = pd.notnull(row.w_quit_lvl) and row.close > row.w_quit_lvl
                
                if is_w_valid:
                    if not pos['w_validated']:
                        pos['w_validated'] = True
                        record_event(row.date, sym, 'D2_W', 'W_VALIDATION_ACHIEVED', row.close, pos['tranche'], cash, cash, pos['broker_stop'], True, None, "")
                    
                    na = row.w_high_10
                    if pd.notnull(na) and na != pos.get('last_add_trigger') and row.close > na:
                        buy_signals.append(('D2_W', sym, row._asdict(), pos['tranche'] + 1, na))

    buy_signals.sort(key=lambda x: x[1])
    
    for st, sym, row, tr, na in buy_signals:
        execute_buy(st, sym, row, tr, na)

events_df = pd.DataFrame(events)
events_df.to_csv("micro_validation_ledger.csv", index=False)

print("\n--- Micro-Validation Summary ---")
print(f"Total Events: {len(events_df)}")
if len(events_df) > 0:
    for st in ['W', 'D2', 'D2_W']:
        st_events = events_df[events_df['strategy'] == st]
        print(f"\n{st} Overview:")
        print(st_events['event'].value_counts().to_string())
