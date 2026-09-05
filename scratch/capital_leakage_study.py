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
events_df = pd.read_csv('cai_backtest_events.csv')
d2_events = events_df[events_df['strategy'] == 'D2'].copy()
d2_events['signal_date'] = pd.to_datetime(d2_events['signal_date'])
d2_events = d2_events[d2_events['signal_date'] >= '2013-01-01'].copy() # Out of sample test period roughly

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
    sdf['d_ema_50'] = sdf['close'].ewm(span=50, adjust=False).mean().shift(1)
    sdf['d_ema_200'] = sdf['close'].ewm(span=200, adjust=False).mean().shift(1)
    sdf['d_atr_14'] = compute_atr(sdf, 14).shift(1)
    
    sdf['d2_anchor'] = sdf['d_ema_50'].combine_first(sdf['d_ema_200'])
    sdf['d2_quit_lvl'] = sdf['d2_anchor'] - (0.5 * sdf['d_atr_14'])
    
    sdf['symbol'] = sym
    sdf = sdf.reset_index()
    dfs.append(sdf)

full_df = pd.concat(dfs).sort_values('date').reset_index(drop=True)
del dfs
del prices_df

full_df = full_df[full_df['date'] >= '2013-01-01'].copy()

print("Running Backtest and Trade Logging...")
cash = INITIAL_CASH
positions = {}
trade_logs = []

for date, day_df in full_df.groupby('date'):
    
    # 1. Exits
    for row in day_df.itertuples():
        sym = row.symbol
        if sym in positions:
            pos = positions[sym]
            exit_reason = None
            exit_price = None
            
            if row.open <= pos['broker_stop']:
                exit_reason = 'STOP_GAP'
                exit_price = row.open
            elif row.low < pos['broker_stop']:
                exit_reason = 'STOP_INTRADAY'
                exit_price = pos['broker_stop']
            elif row.close < row.d2_anchor:
                price = row.next_open
                if pd.notnull(price):
                    exit_reason = 'STRUCTURAL_D2'
                    exit_price = price
                    
            if exit_reason:
                proceeds = (pos['shares'] * exit_price * SLIPPAGE_SELL) * (1 - TX_COST)
                cash += proceeds
                
                # Finalize trade log
                trade = pos['trade_record']
                trade['exit_date'] = date
                trade['exit_reason'] = exit_reason
                trade['exit_price'] = exit_price
                trade['proceeds'] = proceeds
                trade['realized_pnl'] = proceeds - trade['max_invested']
                
                trade_logs.append(trade)
                del positions[sym]

    # 2. Entries
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
                'entry_price': price,
                'max_invested': total_outlay,
                'max_tranche': tr,
                'target_r100_price': price * 2.0
            }
            positions[sym] = {'shares': shares, 'invested': alloc, 'tranche': tr, 'trade_record': trade_record}
        else:
            positions[sym]['shares'] += shares
            positions[sym]['invested'] += alloc
            positions[sym]['tranche'] = tr
            positions[sym]['trade_record']['max_invested'] += total_outlay
            positions[sym]['trade_record']['max_tranche'] = tr
            
        positions[sym]['broker_stop'] = row.d2_quit_lvl
        positions[sym]['last_add_trigger'] = na

# Finalize open positions to prevent data loss
for sym, pos in positions.items():
    trade = pos['trade_record']
    trade['exit_date'] = pd.NaT
    trade['exit_reason'] = 'OPEN'
    trade['exit_price'] = np.nan
    trade['proceeds'] = np.nan
    trade['realized_pnl'] = np.nan
    trade_logs.append(trade)

print("Computing theoretical R100s...")
trades_df = pd.DataFrame(trade_logs)

# Determine if the stock technically hit R100 within 252 days from entry, and if it hit it BEFORE portfolio exit
r100_flags = []
for idx, row in trades_df.iterrows():
    sym = row['symbol']
    entry_dt = row['entry_date']
    exit_dt = row['exit_date'] if pd.notnull(row['exit_date']) else datetime.datetime(2099, 1, 1)
    
    # Get 252-day forward slice
    fut = full_df[(full_df['symbol'] == sym) & (full_df['date'] >= entry_dt)].head(252)
    hit_r100 = False
    hit_r100_date = pd.NaT
    
    # We define theoretical R100 using the target_r100_price (which includes slippage on entry)
    r100_slice = fut[fut['high'] >= row['target_r100_price']]
    if len(r100_slice) > 0:
        hit_r100 = True
        hit_r100_date = r100_slice.iloc[0]['date']
        
    held_at_r100 = False
    if hit_r100 and hit_r100_date <= exit_dt:
        held_at_r100 = True
        
    r100_flags.append({
        'theoretical_r100': hit_r100,
        'held_at_r100': held_at_r100
    })

trades_df = pd.concat([trades_df, pd.DataFrame(r100_flags)], axis=1)

# Metrics
tot_signals = len(trades_df)
r100_winners = trades_df[trades_df['theoretical_r100'] == True]
failures = trades_df[trades_df['theoretical_r100'] == False]

closed_r100_winners = r100_winners[r100_winners['exit_reason'] != 'OPEN']
closed_failures = failures[failures['exit_reason'] != 'OPEN']

n_r100_winners = len(r100_winners)
avg_cap_r100 = r100_winners['max_invested'].mean()
med_cap_r100 = r100_winners['max_invested'].median()

pct_reached_r100_held = (r100_winners['held_at_r100'].sum() / len(r100_winners) * 100) if len(r100_winners) > 0 else 0
pct_exited_before_r100 = 100 - pct_reached_r100_held

avg_loss_failures = (closed_failures['realized_pnl'] / closed_failures['max_invested']).mean() * 100 if len(closed_failures) > 0 else 0
avg_profit_r100 = (closed_r100_winners['realized_pnl'] / closed_r100_winners['max_invested']).mean() * 100 if len(closed_r100_winners) > 0 else 0

cap_lost_failures = closed_failures[closed_failures['realized_pnl'] < 0]['realized_pnl'].sum()

# Profit left uncaptured from winners
# theoretical profit = max_invested (since it doubled)
# uncaptured = max_invested - realized_pnl
closed_r100_winners['theoretical_profit'] = closed_r100_winners['max_invested']
closed_r100_winners['uncaptured_profit'] = closed_r100_winners['theoretical_profit'] - closed_r100_winners['realized_pnl']
profit_uncaptured = closed_r100_winners['uncaptured_profit'].sum()

# Write report
lines = [
    "# CAI Capital Leakage Study\n",
    "## 1. Portfolio Capture Analysis\n",
    "| Metric | Value |",
    "| :--- | ---: |",
    f"| D2 Portfolio Entries | {tot_signals:,} |",
    f"| Theoretical R100 Winners | {n_r100_winners:,} |",
    f"| Avg Capital in R100 Winners | ₹{avg_cap_r100:,.0f} |",
    f"| Median Capital in R100 Winners | ₹{med_cap_r100:,.0f} |",
    f"| % Reaching R100 BEFORE Portfolio Exit | {pct_reached_r100_held:.1f}% |",
    f"| % Exited BEFORE reaching R100 | {pct_exited_before_r100:.1f}% |",
    f"| Avg ROI on Theoretical Failures | {avg_loss_failures:.1f}% |",
    f"| Avg ROI on Theoretical R100 Winners | {avg_profit_r100:.1f}% |",
    f"| Total Capital Lost to Failures | ₹{cap_lost_failures:,.0f} |",
    f"| Total Profit Uncaptured from Winners | ₹{profit_uncaptured:,.0f} |",
    "\n## 2. Exit Reason Distribution (R100 Winners Exited Early)\n"
]

early_exits = closed_r100_winners[closed_r100_winners['held_at_r100'] == False]
vc = early_exits['exit_reason'].value_counts()
for reason, count in vc.items():
    pct = count / len(early_exits) * 100
    lines.append(f"- **{reason}**: {count} trades ({pct:.1f}%)")

with open('cai_capital_leakage_report.md', 'w') as f:
    f.write('\n'.join(lines))

print("Done.")
