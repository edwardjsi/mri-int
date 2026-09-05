import pandas as pd
import numpy as np
import datetime
import warnings
warnings.filterwarnings('ignore')

INITIAL_CASH = 1000000.0
MAX_POSITIONS = 10
BASE_TRANCHE_TARGETS = {1: 20000, 2: 30000, 3: 50000, 4: 75000, 5: 125000}
SLIPPAGE_BUY = 1.001
SLIPPAGE_SELL = 0.999
TX_COST = 0.0015

print("Loading events...")
events = pd.read_csv('cai_backtest_events.csv')
d2_events = events[(events['strategy'] == 'D2') & (events['event'] == 'BREAKOUT')].copy()
d2_events['signal_date'] = pd.to_datetime(d2_events['signal_date'])
d2_events = d2_events[d2_events['signal_date'] >= '2013-01-01'].copy()

dates = sorted(d2_events['signal_date'].dropna())
q33 = pd.to_datetime(np.percentile([d.value for d in dates], 33))
q66 = pd.to_datetime(np.percentile([d.value for d in dates], 66))

def get_period(d):
    if d <= q33: return "Early"
    elif d <= q66: return "Middle"
    else: return "Recent"

d2_events['period'] = d2_events['signal_date'].apply(get_period)
# Make a set of (symbol, signal_date) for exact entries
d2_signal_set = set(zip(d2_events['symbol'], d2_events['signal_date']))

print("Loading daily prices...")
prices_df = pd.read_csv('backups/20260304/daily_prices.csv', low_memory=False)
prices_df['date'] = pd.to_datetime(prices_df['date'])
prices_df = prices_df[prices_df['date'] >= '2012-01-01'].dropna(subset=['close', 'high', 'low', 'open']).sort_values(['symbol', 'date']).reset_index(drop=True)

def compute_atr(sdf, window):
    prev_close = sdf['close'].shift(1)
    tr1 = sdf['high'] - sdf['low']
    tr2 = (sdf['high'] - prev_close).abs()
    tr3 = (sdf['low'] - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window, min_periods=1).mean()

print("Precomputing indicators & Classifier targets...")
dfs = []
classification_data = []

for sym, sdf in prices_df.groupby('symbol'):
    sdf = sdf.copy()
    sdf = sdf.sort_values('date')
    sdf.set_index('date', inplace=True)
    
    sdf['next_open'] = sdf['open'].shift(-1)
    sdf['d_high_10'] = sdf['high'].rolling(10).max().shift(1)
    sdf['d_ema_20'] = sdf['close'].ewm(span=20, adjust=False).mean().shift(1)
    sdf['d_ema_50'] = sdf['close'].ewm(span=50, adjust=False).mean().shift(1)
    sdf['d_ema_200'] = sdf['close'].ewm(span=200, adjust=False).mean().shift(1)
    sdf['d_atr_14'] = compute_atr(sdf, 14).shift(1)
    
    wdf = sdf.resample('W-FRI').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    wdf['w_low_4'] = wdf['low'].rolling(4, min_periods=1).min().shift(1)
    wdf['w_ema_20'] = wdf['close'].ewm(span=20, adjust=False).mean().shift(1)
    wdf['w_ema_50'] = wdf['close'].ewm(span=50, adjust=False).mean().shift(1)
    wdf['w_atr_14'] = compute_atr(wdf, 14).shift(1)
    wdf = wdf[['w_low_4', 'w_ema_20', 'w_ema_50', 'w_atr_14']]
    
    sdf = sdf.merge(wdf, left_index=True, right_index=True, how='left')
    sdf[['w_low_4', 'w_ema_20', 'w_ema_50', 'w_atr_14']] = sdf[['w_low_4', 'w_ema_20', 'w_ema_50', 'w_atr_14']].ffill()
    
    sdf['w_anchor'] = sdf['w_low_4'].combine_first(sdf['w_ema_50']).combine_first(sdf['w_ema_20'])
    sdf['w_quit_lvl'] = sdf['w_anchor'] - (0.5 * sdf['w_atr_14'])
    
    sdf['d2_anchor'] = sdf['d_ema_50'].combine_first(sdf['d_ema_200'])
    sdf['d2_quit_lvl'] = sdf['d2_anchor'] - (0.5 * sdf['d_atr_14'])
    
    sdf['symbol'] = sym
    sdf = sdf.reset_index()
    sdf['is_friday'] = sdf['date'].dt.weekday == 4
    
    sym_d2 = d2_events[d2_events['symbol'] == sym]
    if len(sym_d2) > 0:
        for _, row in sym_d2.iterrows():
            dt = row['signal_date']
            period = row['period']
            
            future_mask = sdf['date'] >= dt
            if not future_mask.any(): continue
            pos = sdf[future_mask].index[0]
            if pos >= len(sdf): continue
            sig_row = sdf.iloc[pos]
            
            rs_90d = sig_row.get('rs_90d', np.nan)
            vol = sig_row.get('volume', np.nan)
            avg_vol = sig_row.get('avg_volume_20d', np.nan)
            vol_ratio = vol / avg_vol if pd.notnull(avg_vol) and avg_vol > 0 else np.nan
            ema_50 = sig_row.get('ema_50', np.nan)
            dist_ema_50 = (sig_row['close'] / ema_50) - 1 if pd.notnull(ema_50) and ema_50 > 0 else np.nan
            d2_anchor = sig_row.get('d2_anchor', np.nan)
            dist_anchor = (sig_row['close'] / d2_anchor) - 1 if pd.notnull(d2_anchor) and d2_anchor > 0 else np.nan
            
            fut_slice = sdf.iloc[pos+1 : pos+253]
            w_validated = False
            time_to_w = np.nan
            for _, fut_row in fut_slice.iterrows():
                if pd.notnull(fut_row['d2_quit_lvl']) and fut_row['close'] < fut_row['d2_quit_lvl']:
                    break
                if fut_row['is_friday'] and pd.notnull(fut_row['w_quit_lvl']) and fut_row['close'] > fut_row['w_quit_lvl']:
                    w_validated = True
                    time_to_w = (fut_row['date'] - dt).days
                    break
                    
            target = 1 if (w_validated and time_to_w <= 7) else 0
            
            classification_data.append({
                'symbol': sym,
                'signal_date': dt,
                'period': period,
                'target': target,
                'rs_90d': rs_90d,
                'dist_ema_50': dist_ema_50,
                'dist_anchor': dist_anchor,
                'vol_ratio': vol_ratio
            })
            
    dfs.append(sdf)

full_df = pd.concat(dfs).sort_values('date').reset_index(drop=True)
del dfs
del prices_df
full_df = full_df[full_df['date'] >= '2013-01-01'].copy()

print("Training classifier and generating predictions...")
df_class = pd.DataFrame(classification_data)
features = ['rs_90d', 'dist_ema_50', 'dist_anchor', 'vol_ratio']

# To maintain consistency, any missing values are filled with the median of training set to predict out-of-sample
train_subset = df_class[df_class['period'].isin(['Early', 'Middle'])].dropna(subset=features)
medians = train_subset[features].median()
iqr = train_subset[features].quantile(0.75) - train_subset[features].quantile(0.25)
iqr = iqr.replace(0, 1)

cent_1 = (train_subset[train_subset['target'] == 1][features].median() - medians) / iqr
cent_0 = (train_subset[train_subset['target'] == 0][features].median() - medians) / iqr

# Predict for all using the frozen centroids
df_class_filled = df_class.copy()
df_class_filled[features] = df_class_filled[features].fillna(medians)

X_test = (df_class_filled[features] - medians) / iqr
dist_1 = np.sqrt(((X_test - cent_1) ** 2).sum(axis=1))
dist_0 = np.sqrt(((X_test - cent_0) ** 2).sum(axis=1))
df_class['pred'] = (dist_1 < dist_0).astype(int)

# Create mapping (symbol, signal_date) -> pred (0: Deep-Base, 1: Momentum)
pred_map = {}
for _, row in df_class.iterrows():
    pred_map[(row['symbol'], row['signal_date'])] = row['pred']

# Current Structural Policy is the control logic for Momentum
def current_structural_exit(row):
    return row.close < row.d2_anchor

def current_structural_stop(row):
    return row.d2_anchor - (0.5 * row.d_atr_14)

# Define models ONLY FOR DEEP-BASE. Momentum always uses Current_Structural
models = {
    'DeepBase_Current_Structural': {
        'struct_exit': current_structural_exit,
        'hard_stop': current_structural_stop
    },
    'DeepBase_Anchor_Minus_1_ATR': {
        'struct_exit': lambda row: row.close < (row.d2_anchor - 1.0 * row.d_atr_14),
        'hard_stop': lambda row: row.d2_anchor - (1.0 * row.d_atr_14)
    },
    'DeepBase_Anchor_Minus_1.5_ATR': {
        'struct_exit': lambda row: row.close < (row.d2_anchor - 1.5 * row.d_atr_14),
        'hard_stop': lambda row: row.d2_anchor - (1.5 * row.d_atr_14)
    },
    'DeepBase_Weekly_Structural_Exit': {
        'struct_exit': lambda row: row.is_friday and (row.close < row.w_anchor),
        'hard_stop': lambda row: row.w_anchor - (0.5 * row.w_atr_14) if pd.notnull(row.w_anchor) else row.d2_anchor - (0.5 * row.d_atr_14)
    },
    'DeepBase_Disaster_Stop_Only': {
        'struct_exit': lambda row: False,
        'hard_stop': lambda row: row.d2_anchor - (3.0 * row.d_atr_14)
    }
}

print("Running Backtests for Conditional Exit Models...")
outcomes = []

for model_name, db_rules in models.items():
    print(f"Running Policy: {model_name}")
    cash = INITIAL_CASH
    positions = {}
    daily_pv = []
    trade_logs = []
    
    db_struct_rule = db_rules['struct_exit']
    db_stop_rule = db_rules['hard_stop']
    
    for date, day_df in full_df.groupby('date'):
        # Exits
        for row in day_df.itertuples():
            sym = row.symbol
            if sym in positions:
                pos = positions[sym]
                exit_reason = None
                exit_price = None
                
                archetype = pos['trade_record']['archetype']
                # Determine active rules based on archetype (0 = Deep-Base, 1 = Momentum)
                if archetype == 1:
                    struct_rule = current_structural_exit
                    # Stop rule is updated during entries
                else:
                    struct_rule = db_struct_rule
                
                # Check broker stop first
                if row.open <= pos['broker_stop']:
                    exit_reason = 'STOP_GAP'
                    exit_price = row.open
                elif row.low < pos['broker_stop']:
                    exit_reason = 'STOP_INTRADAY'
                    exit_price = pos['broker_stop']
                # Check structural exit
                elif struct_rule(row):
                    price = row.next_open
                    if pd.notnull(price):
                        exit_reason = 'STRUCTURAL'
                        exit_price = price
                        
                if exit_reason:
                    proceeds = (pos['shares'] * exit_price * SLIPPAGE_SELL) * (1 - TX_COST)
                    cash += proceeds
                    
                    trade = pos['trade_record']
                    trade['exit_date'] = date
                    trade['realized_pnl'] = proceeds - trade['max_invested']
                    trade_logs.append(trade)
                    del positions[sym]

        # Entries
        buy_signals = []
        for row in day_df.itertuples():
            sym = row.symbol
            if pd.isnull(row.next_open): continue
            
            # Restrict new entries to exact D2 signals from the ledger
            # The signal happened on the current row's date, execution is on next_open
            if sym not in positions:
                if (sym, row.date) in d2_signal_set and len(positions) < MAX_POSITIONS:
                    pred = pred_map.get((sym, row.date), 1) # default Momentum if not found
                    buy_signals.append((sym, row, 1, row.d_high_10, pred))
            elif positions[sym]['tranche'] < 5:
                na = row.d_high_10
                if pd.notnull(na) and na != positions[sym].get('last_add_trigger') and row.close > na:
                    pred = positions[sym]['trade_record']['archetype']
                    buy_signals.append((sym, row, positions[sym]['tranche'] + 1, na, pred))
                    
        buy_signals.sort(key=lambda x: x[0])
        
        for sym, row, tr, na, pred in buy_signals:
            target_cap = BASE_TRANCHE_TARGETS[tr]
            curr_cap = positions[sym]['invested'] if sym in positions else 0
            alloc = target_cap - curr_cap
            
            if alloc <= 0 or alloc > cash: continue
            
            price = row.next_open * SLIPPAGE_BUY
            cost = alloc * TX_COST
            total_outlay = alloc + cost
            if total_outlay > cash: continue
            
            shares = alloc / price
            cash -= total_outlay
            
            if sym not in positions:
                trade_record = {
                    'symbol': sym,
                    'entry_date': row.date,
                    'max_invested': total_outlay,
                    'target_r100_price': price * 2.0,
                    'archetype': pred
                }
                positions[sym] = {'shares': shares, 'invested': alloc, 'tranche': tr, 'trade_record': trade_record}
            else:
                positions[sym]['shares'] += shares
                positions[sym]['invested'] += alloc
                positions[sym]['tranche'] = tr
                positions[sym]['trade_record']['max_invested'] += total_outlay
                
            # Update hard stop
            stop_rule = current_structural_stop if pred == 1 else db_stop_rule
            stop = stop_rule(row)
            if pd.notnull(stop):
                positions[sym]['broker_stop'] = max(positions[sym].get('broker_stop', 0), stop)
            positions[sym]['last_add_trigger'] = na

        # EOD Value
        pv = cash
        for sym, p in positions.items():
            r = day_df[day_df['symbol'] == sym]
            if len(r) > 0:
                pv += p['shares'] * r.iloc[0].close
        daily_pv.append({'date': date, 'pv': pv, 'cash': cash})
        
    df_pv = pd.DataFrame(daily_pv)
    start_pv = INITIAL_CASH
    end_pv = df_pv['pv'].iloc[-1]
    total_ret = (end_pv / start_pv) - 1
    
    days = (df_pv['date'].max() - df_pv['date'].min()).days
    cagr = (end_pv / start_pv) ** (365.25 / days) - 1 if days > 0 else 0
    
    df_pv['peak'] = df_pv['pv'].cummax()
    df_pv['dd'] = (df_pv['pv'] - df_pv['peak']) / df_pv['peak']
    max_dd = df_pv['dd'].min()
    avg_cap_util = 1 - (df_pv['cash'] / df_pv['pv']).mean()
    
    # Process trade logs
    for sym, pos in positions.items():
        t = pos['trade_record']
        t['exit_date'] = pd.NaT
        t['realized_pnl'] = 0
        trade_logs.append(t)
        
    trades_df = pd.DataFrame(trade_logs)
    r100_flags = []
    for idx, row in trades_df.iterrows():
        sym = row['symbol']
        entry_dt = row['entry_date']
        exit_dt = row['exit_date'] if pd.notnull(row['exit_date']) else datetime.datetime(2099, 1, 1)
        
        fut = full_df[(full_df['symbol'] == sym) & (full_df['date'] >= entry_dt)].head(252)
        r100_slice = fut[fut['high'] >= row['target_r100_price']]
        hit_r100 = len(r100_slice) > 0
        held_at_r100 = False
        if hit_r100:
            hit_r100_date = r100_slice.iloc[0]['date']
            if hit_r100_date <= exit_dt:
                held_at_r100 = True
                
        r100_flags.append({
            'theoretical_r100': hit_r100,
            'held_at_r100': held_at_r100
        })
        
    trades_df = pd.concat([trades_df, pd.DataFrame(r100_flags)], axis=1)
    
    # Overall metrics
    r100_winners = trades_df[trades_df['theoretical_r100'] == True]
    failures = trades_df[trades_df['theoretical_r100'] == False]
    closed_r100 = r100_winners[pd.notnull(r100_winners['exit_date'])]
    closed_fail = failures[pd.notnull(failures['exit_date'])]
    
    r100_cap_rate = (r100_winners['held_at_r100'].sum() / len(r100_winners)) if len(r100_winners) > 0 else 0
    avg_win_roi = (closed_r100['realized_pnl'] / closed_r100['max_invested']).mean() if len(closed_r100) > 0 else 0
    avg_loss_roi = (closed_fail['realized_pnl'] / closed_fail['max_invested']).mean() if len(closed_fail) > 0 else 0
    
    # Archetype metrics
    db_trades = trades_df[trades_df['archetype'] == 0]
    mom_trades = trades_df[trades_df['archetype'] == 1]
    
    db_pnl = db_trades['realized_pnl'].sum()
    mom_pnl = mom_trades['realized_pnl'].sum()
    
    outcomes.append({
        'Model': model_name,
        'CAGR': f"{cagr*100:.2f}%",
        'Total Return': f"{total_ret*100:.2f}%",
        'Max Drawdown': f"{max_dd*100:.2f}%",
        'Positions': len(trades_df),
        'Cap Util': f"{avg_cap_util*100:.1f}%",
        'R100 Capture Rate': f"{r100_cap_rate*100:.1f}%",
        'Avg Winner': f"{avg_win_roi*100:.1f}%",
        'Avg Loser': f"{avg_loss_roi*100:.1f}%",
        'Deep-Base P&L': f"₹{db_pnl:,.0f}",
        'Momentum P&L': f"₹{mom_pnl:,.0f}"
    })

res_df = pd.DataFrame(outcomes)
with open('cai_conditional_exit_study.md', 'w') as f:
    f.write("# Conditional Exit Study\n\n")
    f.write("## 1. Counterfactual Exit Models (Deep-Base Only, Momentum uses Current_Structural)\n")
    f.write(res_df.to_markdown(index=False))

print("Done.")
