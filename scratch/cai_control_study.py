import pandas as pd
import numpy as np
import datetime
import warnings
warnings.filterwarnings('ignore')

INITIAL_CASH = 1000000.0
MAX_POSITIONS = 10
TRANCHE_TARGETS = {1: 20000, 2: 30000, 3: 50000, 4: 75000, 5: 125000}
SLIPPAGE_BUY = 1.001
SLIPPAGE_SELL = 0.999
TX_COST = 0.0015

def run_control_backtest():
    print("Loading events...")
    events = pd.read_csv('cai_backtest_events.csv')
    d2_events = events[(events['strategy'] == 'D2') & (events['event'] == 'BREAKOUT')].copy()
    d2_events['signal_date'] = pd.to_datetime(d2_events['signal_date'])
    # Do not filter out pre-2013 if the dataset contains them, but daily_prices only has from 2012 anyway
    d2_signal_set = set(zip(d2_events['symbol'], d2_events['signal_date']))
    total_ledger_signals = len(d2_signal_set)

    print("Loading daily prices...")
    df = pd.read_csv('backups/20260304/daily_prices.csv', low_memory=False)
    df['date'] = pd.to_datetime(df['date'])
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
        # Only process symbols that have at least one D2 signal
        if sym not in d2_events['symbol'].values:
            continue
            
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
    del df

    print("Running Backtest Loop...")
    cash = INITIAL_CASH
    positions = {}
    daily_pv = []
    
    executed_trades = 0
    rejected_max_pos = 0
    rejected_no_cash = 0
    trade_logs = []

    for date, day_df in full_df.groupby('date'):
        # 1. Exits
        for row in day_df.itertuples():
            sym = row.symbol
            if sym in positions:
                pos = positions[sym]
                exit_reason = None
                exit_price = None
                
                # Check broker stop
                if row.open <= pos['broker_stop']:
                    exit_reason = 'STOP_GAP'
                    exit_price = row.open
                elif row.low < pos['broker_stop']:
                    exit_reason = 'STOP_INTRADAY'
                    exit_price = pos['broker_stop']
                # Check structural exit
                elif row.close < row.d2_anchor:
                    price = row.next_open
                    if pd.notnull(price):
                        exit_reason = 'STRUCTURAL'
                        exit_price = price
                        
                if exit_reason:
                    proceeds = (pos['shares'] * exit_price * SLIPPAGE_SELL) * (1 - TX_COST)
                    cash += proceeds
                    
                    trade = pos['trade_record']
                    trade['exit_date'] = date
                    trade['exit_reason'] = exit_reason
                    trade['realized_pnl'] = proceeds - trade['max_invested']
                    trade_logs.append(trade)
                    del positions[sym]

        # 2. Entries
        buy_signals = []
        for row in day_df.itertuples():
            sym = row.symbol
            if pd.isnull(row.next_open): continue
            
            # T1 entries must come strictly from the ledger
            if sym not in positions:
                if (sym, row.date) in d2_signal_set:
                    buy_signals.append((sym, row, 1, row.d_high_10))
            # T2-T5 adds based on subsequent generic 10-day breakouts (per Phase-2 logic)
            elif positions[sym]['tranche'] < 5:
                na = row.d_high_10
                if pd.notnull(na) and na != positions[sym].get('last_add_trigger') and row.close > na:
                    buy_signals.append((sym, row, positions[sym]['tranche'] + 1, na))

        buy_signals.sort(key=lambda x: x[0]) # Alphanumeric tie-break (x[0] is symbol)
        
        for sym, row, tr, na in buy_signals:
            if tr == 1 and len(positions) >= MAX_POSITIONS:
                rejected_max_pos += 1
                continue
                
            target_cap = TRANCHE_TARGETS[tr]
            curr_cap = positions[sym]['invested'] if sym in positions else 0
            alloc = target_cap - curr_cap
            
            if alloc <= 0: continue
            
            price = row.next_open * SLIPPAGE_BUY
            cost = alloc * TX_COST
            total_outlay = alloc + cost
            
            if total_outlay > cash:
                if tr == 1: rejected_no_cash += 1
                continue
            
            shares = alloc / price
            cash -= total_outlay
            
            if sym not in positions:
                executed_trades += 1
                trade_record = {
                    'symbol': sym,
                    'entry_date': row.date,
                    'max_invested': total_outlay,
                    'target_r50_price': price * 1.5,
                    'target_r100_price': price * 2.0,
                }
                positions[sym] = {'shares': shares, 'invested': alloc, 'tranche': tr, 'trade_record': trade_record}
            else:
                positions[sym]['shares'] += shares
                positions[sym]['invested'] += alloc
                positions[sym]['tranche'] = tr
                positions[sym]['trade_record']['max_invested'] += total_outlay
                
            positions[sym]['broker_stop'] = max(positions[sym].get('broker_stop', 0), row.d2_quit_lvl)
            positions[sym]['last_add_trigger'] = na

        # 3. EOD Value
        pv = cash
        for sym, p in positions.items():
            r = day_df[day_df['symbol'] == sym]
            if len(r) > 0:
                pv += p['shares'] * r.iloc[0].close
        daily_pv.append({'date': date, 'pv': pv, 'cash': cash})
        
    # Flush remaining positions
    for sym, pos in positions.items():
        trade = pos['trade_record']
        trade['exit_date'] = pd.NaT
        trade['exit_reason'] = 'OPEN'
        trade['realized_pnl'] = 0
        trade_logs.append(trade)

    df_pv = pd.DataFrame(daily_pv)
    trades_df = pd.DataFrame(trade_logs)
    
    # Calculate R50/R100 outcomes using full forward price data
    print("Calculating R50/R100 theoretical outcomes...")
    r50_flags = []
    r100_flags = []
    
    for idx, row in trades_df.iterrows():
        sym = row['symbol']
        entry_dt = row['entry_date']
        exit_dt = row['exit_date'] if pd.notnull(row['exit_date']) else datetime.datetime(2099, 1, 1)
        
        fut = full_df[(full_df['symbol'] == sym) & (full_df['date'] >= entry_dt)].head(252)
        
        r50_slice = fut[fut['high'] >= row['target_r50_price']]
        hit_r50 = len(r50_slice) > 0
        held_at_r50 = False
        if hit_r50:
            if r50_slice.iloc[0]['date'] <= exit_dt:
                held_at_r50 = True
                
        r100_slice = fut[fut['high'] >= row['target_r100_price']]
        hit_r100 = len(r100_slice) > 0
        held_at_r100 = False
        if hit_r100:
            if r100_slice.iloc[0]['date'] <= exit_dt:
                held_at_r100 = True
                
        r50_flags.append({'theo_r50': hit_r50, 'held_at_r50': held_at_r50})
        r100_flags.append({'theo_r100': hit_r100, 'held_at_r100': held_at_r100})
        
    trades_df = pd.concat([trades_df, pd.DataFrame(r50_flags), pd.DataFrame(r100_flags)], axis=1)
    
    # Generate Metrics
    start_pv = INITIAL_CASH
    end_pv = df_pv['pv'].iloc[-1]
    total_ret = (end_pv / start_pv) - 1
    
    days = (df_pv['date'].max() - df_pv['date'].min()).days
    cagr = (end_pv / start_pv) ** (365.25 / days) - 1 if days > 0 else 0
    
    df_pv['peak'] = df_pv['pv'].cummax()
    df_pv['dd'] = (df_pv['pv'] - df_pv['peak']) / df_pv['peak']
    max_dd = df_pv['dd'].min()
    avg_cap_util = 1 - (df_pv['cash'] / df_pv['pv']).mean()
    
    r50_winners = trades_df[trades_df['theo_r50'] == True]
    r100_winners = trades_df[trades_df['theo_r100'] == True]
    
    r50_cap_rate = (r50_winners['held_at_r50'].sum() / len(r50_winners)) if len(r50_winners) > 0 else 0
    r100_cap_rate = (r100_winners['held_at_r100'].sum() / len(r100_winners)) if len(r100_winners) > 0 else 0
    
    metrics = {
        'total_ledger_signals': total_ledger_signals,
        'executed_trades': executed_trades,
        'rejected_max_pos': rejected_max_pos,
        'rejected_no_cash': rejected_no_cash,
        'cagr': cagr,
        'total_return': total_ret,
        'max_dd': max_dd,
        'cap_util': avg_cap_util,
        'r50_cap_rate': r50_cap_rate,
        'r100_cap_rate': r100_cap_rate,
        'final_pv': end_pv
    }
    
    return metrics, trades_df, df_pv

if __name__ == "__main__":
    print("Run 1: Generating baseline metrics...")
    m1, _, _ = run_control_backtest()
    
    print("\nRun 2: Verifying determinism...")
    m2, _, _ = run_control_backtest()
    
    print("\nDeterminism Check:")
    if m1['final_pv'] == m2['final_pv'] and m1['executed_trades'] == m2['executed_trades']:
        print("✅ PASS: The portfolio engine is perfectly deterministic.")
    else:
        print("❌ FAIL: The portfolio engine is non-deterministic!")
        print(f"Run 1 PV: {m1['final_pv']} | Run 2 PV: {m2['final_pv']}")
        
    with open('cai_control_group_report.md', 'w') as f:
        f.write("# Authoritative Phase-2 Control Group (D2)\n\n")
        f.write("This report captures the strict D2 baseline using actual production engine mechanics on the true Phase-1 event ledger.\n\n")
        f.write("### 1. Engine Event Pipeline\n")
        f.write(f"- **Total Ledger Signals (D2 Breakouts):** {m1['total_ledger_signals']:,}\n")
        f.write(f"- **Rejected (Max 10 Positions limit reached):** {m1['rejected_max_pos']:,}\n")
        f.write(f"- **Rejected (Insufficient Cash for T1):** {m1['rejected_no_cash']:,}\n")
        f.write(f"- **Executed Trades (Unique entries):** {m1['executed_trades']:,}\n\n")
        
        f.write("### 2. Portfolio Outcomes\n")
        f.write(f"- **CAGR:** {m1['cagr']*100:.2f}%\n")
        f.write(f"- **Total Return:** {m1['total_return']*100:.2f}%\n")
        f.write(f"- **Maximum Drawdown:** {m1['max_dd']*100:.2f}%\n")
        f.write(f"- **Capital Utilization:** {m1['cap_util']*100:.2f}%\n\n")
        
        f.write("### 3. Capture Efficiency\n")
        f.write(f"- **R50 Capture Rate:** {m1['r50_cap_rate']*100:.1f}%\n")
        f.write(f"- **R100 Capture Rate:** {m1['r100_cap_rate']*100:.1f}%\n")
