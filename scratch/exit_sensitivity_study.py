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

print("Loading data...")
d2_events = pd.read_csv('cai_backtest_events.csv')
d2_events = d2_events[d2_events['strategy'] == 'D2'].copy()
d2_events['signal_date'] = pd.to_datetime(d2_events['signal_date'])
d2_events = d2_events[d2_events['signal_date'] >= '2013-01-01'].copy()

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

print("Precomputing indicators...")
dfs = []
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
    
    # W logic
    wdf = sdf.resample('W-FRI').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    wdf['w_ema_20'] = wdf['close'].ewm(span=20, adjust=False).mean().shift(1)
    wdf['w_ema_50'] = wdf['close'].ewm(span=50, adjust=False).mean().shift(1)
    wdf['w_atr_14'] = compute_atr(wdf, 14).shift(1)
    wdf = wdf[['w_ema_20', 'w_ema_50', 'w_atr_14']]
    
    sdf = sdf.merge(wdf, left_index=True, right_index=True, how='left')
    sdf[['w_ema_20', 'w_ema_50', 'w_atr_14']] = sdf[['w_ema_20', 'w_ema_50', 'w_atr_14']].ffill()
    
    sdf['w_anchor'] = sdf['w_ema_50'].combine_first(sdf['w_ema_20'])
    sdf['d2_anchor'] = sdf['d_ema_50'].combine_first(sdf['d_ema_200'])
    
    sdf['symbol'] = sym
    sdf = sdf.reset_index()
    
    # Friday flag for weekly rules
    sdf['is_friday'] = sdf['date'].dt.weekday == 4
    
    dfs.append(sdf)

full_df = pd.concat(dfs).sort_values('date').reset_index(drop=True)
del dfs
del prices_df

full_df = full_df[full_df['date'] >= '2013-01-01'].copy()

# Theoretical R100 MAE Calculation
print("Calculating MAE for theoretical R100 winners...")
r100_maes = []
for sym, sym_df in d2_events.groupby('symbol'):
    for _, row in sym_df.iterrows():
        dt = row['signal_date']
        sym_full = full_df[(full_df['symbol'] == sym) & (full_df['date'] >= dt)]
        if len(sym_full) < 2: continue
        
        entry_price = sym_full.iloc[0]['next_open'] * SLIPPAGE_BUY
        if pd.isnull(entry_price): continue
        target = entry_price * 2.0
        
        # Next 252 days
        fut = sym_full.head(252)
        r100_slice = fut[fut['high'] >= target]
        if len(r100_slice) > 0:
            hit_date = r100_slice.iloc[0]['date']
            path_to_r100 = fut[fut['date'] <= hit_date]
            mae_price = path_to_r100['low'].min()
            mae_pct = (mae_price / entry_price) - 1
            r100_maes.append(mae_pct)

if r100_maes:
    avg_mae = np.mean(r100_maes)
    med_mae = np.median(r100_maes)
    p25_mae = np.percentile(r100_maes, 25)
    print(f"MAE for R100 Winners -> Avg: {avg_mae:.1%}, Median: {med_mae:.1%}, 25th %ile: {p25_mae:.1%}")

models = {
    'Current_Structural': {
        'struct_exit': lambda row: row.close < row.d2_anchor,
        'hard_stop': lambda row: row.d2_anchor - (0.5 * row.d_atr_14)
    },
    'Anchor_Minus_1_ATR': {
        'struct_exit': lambda row: row.close < (row.d2_anchor - 1.0 * row.d_atr_14),
        'hard_stop': lambda row: row.d2_anchor - (1.0 * row.d_atr_14)
    },
    'Anchor_Minus_1.5_ATR': {
        'struct_exit': lambda row: row.close < (row.d2_anchor - 1.5 * row.d_atr_14),
        'hard_stop': lambda row: row.d2_anchor - (1.5 * row.d_atr_14)
    },
    'Weekly_Structural_Exit': {
        'struct_exit': lambda row: row.is_friday and (row.close < row.w_anchor),
        'hard_stop': lambda row: row.w_anchor - (0.5 * row.w_atr_14) if pd.notnull(row.w_anchor) else row.d2_anchor - (0.5 * row.d_atr_14)
    },
    'Disaster_Stop_Only': {
        'struct_exit': lambda row: False,
        'hard_stop': lambda row: row.d2_anchor - (3.0 * row.d_atr_14)
    }
}

print("Running Backtests for Exit Models...")
outcomes = []

for model_name, rules in models.items():
    print(f"Running Policy: {model_name}")
    cash = INITIAL_CASH
    positions = {}
    daily_pv = []
    trade_logs = []
    
    struct_rule = rules['struct_exit']
    stop_rule = rules['hard_stop']
    
    for date, day_df in full_df.groupby('date'):
        # Exits
        for row in day_df.itertuples():
            sym = row.symbol
            if sym in positions:
                pos = positions[sym]
                exit_reason = None
                exit_price = None
                
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
            
            if sym not in positions:
                if pd.notnull(row.d_high_10) and row.close > row.d_high_10 and len(positions) < MAX_POSITIONS:
                    buy_signals.append((sym, row, 1, row.d_high_10))
            elif positions[sym]['tranche'] < 5:
                na = row.d_high_10
                if pd.notnull(na) and na != positions[sym].get('last_add_trigger') and row.close > na:
                    buy_signals.append((sym, row, positions[sym]['tranche'] + 1, na))
                    
        buy_signals.sort(key=lambda x: x[0])
        
        for sym, row, tr, na in buy_signals:
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
                    'target_r100_price': price * 2.0
                }
                positions[sym] = {'shares': shares, 'invested': alloc, 'tranche': tr, 'trade_record': trade_record}
            else:
                positions[sym]['shares'] += shares
                positions[sym]['invested'] += alloc
                positions[sym]['tranche'] = tr
                positions[sym]['trade_record']['max_invested'] += total_outlay
                
            # Update hard stop
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
    
    r100_winners = trades_df[trades_df['theoretical_r100'] == True]
    failures = trades_df[trades_df['theoretical_r100'] == False]
    closed_r100 = r100_winners[pd.notnull(r100_winners['exit_date'])]
    closed_fail = failures[pd.notnull(failures['exit_date'])]
    
    r100_cap_rate = (r100_winners['held_at_r100'].sum() / len(r100_winners)) if len(r100_winners) > 0 else 0
    avg_win_roi = (closed_r100['realized_pnl'] / closed_r100['max_invested']).mean() if len(closed_r100) > 0 else 0
    avg_loss_roi = (closed_fail['realized_pnl'] / closed_fail['max_invested']).mean() if len(closed_fail) > 0 else 0
    
    outcomes.append({
        'Model': model_name,
        'CAGR': f"{cagr*100:.2f}%",
        'Total Return': f"{total_ret*100:.2f}%",
        'Max Drawdown': f"{max_dd*100:.2f}%",
        'Positions': len(trades_df),
        'Cap Util': f"{avg_cap_util*100:.1f}%",
        'R100 Capture Rate': f"{r100_cap_rate*100:.1f}%",
        'Avg Winner (R100s)': f"{avg_win_roi*100:.1f}%",
        'Avg Loser (Failures)': f"{avg_loss_roi*100:.1f}%",
    })

res_df = pd.DataFrame(outcomes)
with open('cai_exit_sensitivity_study.md', 'w') as f:
    f.write("# Exit Sensitivity & MAE Study\n\n")
    if r100_maes:
        f.write("## 1. R100 Maximum Adverse Excursion (MAE)\n")
        f.write(f"- **Average MAE**: {avg_mae:.1%}\n")
        f.write(f"- **Median MAE**: {med_mae:.1%}\n")
        f.write(f"- **75th Percentile MAE (25th lowest)**: {p25_mae:.1%}\n\n")
    
    f.write("## 2. Counterfactual Exit Models (2013-2026)\n")
    f.write(res_df.to_markdown(index=False))

print("Done.")
