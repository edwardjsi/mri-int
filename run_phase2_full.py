import pandas as pd
import numpy as np
import datetime
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

INITIAL_CASH = 1000000.0
MAX_POSITIONS = 10
TRANCHE_TARGETS = {1: 20000, 2: 30000, 3: 50000, 4: 75000, 5: 125000}
SLIPPAGE_BUY = 1.001
SLIPPAGE_SELL = 0.999
TX_COST = 0.0015

print("Loading daily prices...")
df = pd.read_csv('backups/20260304/daily_prices.csv', low_memory=False)
df['date'] = pd.to_datetime(df['date'])

# Only use data from 2016 onwards for speed if full 30 years takes too long, 
# but user said "30 years". The dataset has max 30 years. Let's just run it all.
# df = df[df['date'] >= '2000-01-01'] 

df = df.dropna(subset=['close', 'high', 'low', 'open']).sort_values(['symbol', 'date']).reset_index(drop=True)

def compute_atr(sdf, window):
    prev_close = sdf['close'].shift(1)
    tr1 = sdf['high'] - sdf['low']
    tr2 = (sdf['high'] - prev_close).abs()
    tr3 = (sdf['low'] - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window, min_periods=1).mean()

print("Precomputing indicators...")
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
del dfs
del df

print("Running Backtest Loop...")
cash_states = {'W': INITIAL_CASH, 'D2': INITIAL_CASH, 'D2_W': INITIAL_CASH}
positions = {'W': {}, 'D2': {}, 'D2_W': {}}
events = []
daily_portfolio_value = {'W': [], 'D2': [], 'D2_W': []}

for date, day_df in full_df.groupby('date'):
    is_friday = date.weekday() == 4
    
    # 1. Process active position exits and stops
    for row in day_df.itertuples():
        sym = row.symbol
        for st in ['W', 'D2', 'D2_W']:
            if sym in positions[st]:
                pos = positions[st][sym]
                
                # Broker stop
                if row.open <= pos['broker_stop']:
                    # SELL GAP
                    price = row.open
                    val = pos['shares'] * price
                    val_after_slip = val * SLIPPAGE_SELL
                    cost = val_after_slip * TX_COST
                    net_proceeds = val_after_slip - cost
                    cash_states[st] += net_proceeds
                    events.append({'date': row.date, 'symbol': sym, 'strategy': st, 'event': 'SELL_STOP_GAP', 'price': price, 'proceeds': net_proceeds, 'shares': pos['shares'], 'invested': pos['invested']})
                    del positions[st][sym]
                    continue
                elif row.low < pos['broker_stop']:
                    # SELL INTRADAY
                    price = pos['broker_stop']
                    val = pos['shares'] * price
                    val_after_slip = val * SLIPPAGE_SELL
                    cost = val_after_slip * TX_COST
                    net_proceeds = val_after_slip - cost
                    cash_states[st] += net_proceeds
                    events.append({'date': row.date, 'symbol': sym, 'strategy': st, 'event': 'SELL_STOP_INT', 'price': price, 'proceeds': net_proceeds, 'shares': pos['shares'], 'invested': pos['invested']})
                    del positions[st][sym]
                    continue
                    
                # Structural Exit
                if st == 'W':
                    if is_friday and row.close < row.w_anchor:
                        price = row.next_open
                        if pd.notnull(price):
                            val = pos['shares'] * price
                            val_after_slip = val * SLIPPAGE_SELL
                            cost = val_after_slip * TX_COST
                            net_proceeds = val_after_slip - cost
                            cash_states[st] += net_proceeds
                            events.append({'date': row.date, 'symbol': sym, 'strategy': st, 'event': 'SELL_STRUCT_W', 'price': price, 'proceeds': net_proceeds, 'shares': pos['shares'], 'invested': pos['invested']})
                            del positions[st][sym]
                        continue
                elif st == 'D2':
                    if row.close < row.d2_anchor:
                        price = row.next_open
                        if pd.notnull(price):
                            val = pos['shares'] * price
                            val_after_slip = val * SLIPPAGE_SELL
                            cost = val_after_slip * TX_COST
                            net_proceeds = val_after_slip - cost
                            cash_states[st] += net_proceeds
                            events.append({'date': row.date, 'symbol': sym, 'strategy': st, 'event': 'SELL_STRUCT_D2', 'price': price, 'proceeds': net_proceeds, 'shares': pos['shares'], 'invested': pos['invested']})
                            del positions[st][sym]
                        continue
                elif st == 'D2_W':
                    if pos['w_validated']:
                        if is_friday and row.close < row.w_anchor:
                            price = row.next_open
                            if pd.notnull(price):
                                val = pos['shares'] * price
                                val_after_slip = val * SLIPPAGE_SELL
                                cost = val_after_slip * TX_COST
                                net_proceeds = val_after_slip - cost
                                cash_states[st] += net_proceeds
                                events.append({'date': row.date, 'symbol': sym, 'strategy': st, 'event': 'SELL_STRUCT_W', 'price': price, 'proceeds': net_proceeds, 'shares': pos['shares'], 'invested': pos['invested']})
                                del positions[st][sym]
                    else:
                        if row.close < row.d2_anchor:
                            price = row.next_open
                            if pd.notnull(price):
                                val = pos['shares'] * price
                                val_after_slip = val * SLIPPAGE_SELL
                                cost = val_after_slip * TX_COST
                                net_proceeds = val_after_slip - cost
                                cash_states[st] += net_proceeds
                                events.append({'date': row.date, 'symbol': sym, 'strategy': st, 'event': 'SELL_STRUCT_D2', 'price': price, 'proceeds': net_proceeds, 'shares': pos['shares'], 'invested': pos['invested']})
                                del positions[st][sym]

    # 2. Entries
    buy_signals = []
    for row in day_df.itertuples():
        sym = row.symbol
        if pd.isnull(row.next_open): continue
        
        # W
        if sym not in positions['W']:
            if pd.notnull(row.w_high_10) and row.close > row.w_high_10 and len(positions['W']) < MAX_POSITIONS:
                buy_signals.append(('W', sym, row, 1, row.w_high_10))
        elif positions['W'][sym]['tranche'] < 5:
            na = row.w_high_10
            if pd.notnull(na) and na != positions['W'][sym].get('last_add_trigger') and row.close > na:
                buy_signals.append(('W', sym, row, positions['W'][sym]['tranche'] + 1, na))
                
        # D2
        if sym not in positions['D2']:
            if pd.notnull(row.d_high_10) and row.close > row.d_high_10 and len(positions['D2']) < MAX_POSITIONS:
                buy_signals.append(('D2', sym, row, 1, row.d_high_10))
        elif positions['D2'][sym]['tranche'] < 5:
            na = row.d_high_10
            if pd.notnull(na) and na != positions['D2'][sym].get('last_add_trigger') and row.close > na:
                buy_signals.append(('D2', sym, row, positions['D2'][sym]['tranche'] + 1, na))
                
        # D2_W
        if sym not in positions['D2_W']:
            if pd.notnull(row.d_high_10) and row.close > row.d_high_10 and len(positions['D2_W']) < MAX_POSITIONS:
                buy_signals.append(('D2_W', sym, row, 1, row.d_high_10))
        else:
            pos = positions['D2_W'][sym]
            if pos['tranche'] < 5:
                is_w_valid = pos['w_validated']
                if not is_w_valid and is_friday:
                    is_w_valid = pd.notnull(row.w_quit_lvl) and row.close > row.w_quit_lvl
                
                if is_w_valid:
                    if not pos['w_validated']:
                        pos['w_validated'] = True
                    na = row.w_high_10
                    if pd.notnull(na) and na != pos.get('last_add_trigger') and row.close > na:
                        buy_signals.append(('D2_W', sym, row, pos['tranche'] + 1, na))

    buy_signals.sort(key=lambda x: x[1]) # Alphanumeric tie-break
    
    for st, sym, row, tr, na in buy_signals:
        target_cap = TRANCHE_TARGETS[tr]
        curr_cap = positions[st][sym]['invested'] if sym in positions[st] else 0
        alloc = target_cap - curr_cap
        
        if alloc <= 0 or alloc > cash_states[st]: continue
        
        price = row.next_open * SLIPPAGE_BUY
        cost = alloc * TX_COST
        total_outlay = alloc + cost
        if total_outlay > cash_states[st]: continue
        
        shares = alloc / price
        cash_states[st] -= total_outlay
        
        if sym not in positions[st]:
            positions[st][sym] = {'shares': shares, 'invested': alloc, 'tranche': tr, 'w_validated': False, 'entry_date': row.date}
        else:
            positions[st][sym]['shares'] += shares
            positions[st][sym]['invested'] += alloc
            positions[st][sym]['tranche'] = tr
            
        if st == 'W': positions[st][sym]['broker_stop'] = row.w_quit_lvl
        else: positions[st][sym]['broker_stop'] = row.d2_quit_lvl
            
        positions[st][sym]['last_add_trigger'] = na
        if st == 'D2_W' and tr > 1: positions[st][sym]['w_validated'] = True
        
        events.append({'date': row.date, 'symbol': sym, 'strategy': st, 'event': f'BUY_T{tr}', 'price': price, 'alloc': alloc})

    # Record end-of-day portfolio value
    for st in ['W', 'D2', 'D2_W']:
        pv = cash_states[st]
        for sym, p in positions[st].items():
            # estimate value based on day's close
            r = day_df[day_df['symbol'] == sym]
            if len(r) > 0:
                pv += p['shares'] * r.iloc[0].close
        daily_portfolio_value[st].append({'date': date, 'pv': pv})

print("Simulation finished. Calculating Metrics...")
for st in ['W', 'D2', 'D2_W']:
    df_pv = pd.DataFrame(daily_portfolio_value[st])
    df_pv.to_csv(f'pv_{st}.csv', index=False)
    
    if len(df_pv) == 0: continue
    
    start_pv = INITIAL_CASH
    end_pv = df_pv['pv'].iloc[-1]
    total_ret = (end_pv / start_pv) - 1
    
    days = (df_pv['date'].max() - df_pv['date'].min()).days
    cagr = (end_pv / start_pv) ** (365.25 / days) - 1 if days > 0 else 0
    
    df_pv['peak'] = df_pv['pv'].cummax()
    df_pv['dd'] = (df_pv['pv'] - df_pv['peak']) / df_pv['peak']
    max_dd = df_pv['dd'].min()
    
    df_pv['ret'] = df_pv['pv'].pct_change()
    vol = df_pv['ret'].std() * np.sqrt(252)
    sharpe = (cagr - 0.05) / vol if vol > 0 else 0
    
    downside_vol = df_pv[df_pv['ret'] < 0]['ret'].std() * np.sqrt(252)
    sortino = (cagr - 0.05) / downside_vol if downside_vol > 0 else 0
    
    print(f"\n--- Strategy: {st} ---")
    print(f"Total Return: {total_ret*100:.2f}%")
    print(f"CAGR: {cagr*100:.2f}%")
    print(f"Max DD: {max_dd*100:.2f}%")
    print(f"Volatility: {vol*100:.2f}%")
    print(f"Sharpe: {sharpe:.2f}")
    print(f"Sortino: {sortino:.2f}")

# Benchmarks
try:
    idf = pd.read_csv('backups/20260304/index_prices.csv')
    idf['date'] = pd.to_datetime(idf['date'])
    for idx in ['NIFTY500', 'NIFTY500_MOMENTUM_50', 'NIFTY_MIDCAP_150']:
        tmp = idf[idf['symbol'] == idx].sort_values('date')
        if len(tmp) > 0:
            s_val = tmp['close'].iloc[0]
            e_val = tmp['close'].iloc[-1]
            days = (tmp['date'].max() - tmp['date'].min()).days
            cagr = (e_val / s_val) ** (365.25 / days) - 1 if days > 0 else 0
            
            tmp['peak'] = tmp['close'].cummax()
            dd = ((tmp['close'] - tmp['peak']) / tmp['peak']).min()
            
            print(f"\n--- Benchmark: {idx} ---")
            print(f"Total Return: {(e_val/s_val - 1)*100:.2f}%")
            print(f"CAGR: {cagr*100:.2f}%")
            print(f"Max DD: {dd*100:.2f}%")
except Exception as e:
    print(f"Error loading benchmarks: {e}")
