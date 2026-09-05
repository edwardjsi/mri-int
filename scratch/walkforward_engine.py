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

def compute_atr(sdf, window):
    prev_close = sdf['close'].shift(1)
    tr1 = sdf['high'] - sdf['low']
    tr2 = (sdf['high'] - prev_close).abs()
    tr3 = (sdf['low'] - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window, min_periods=1).mean()

def load_data():
    print("Loading events...")
    events = pd.read_csv('cai_backtest_events.csv')
    d2_events = events[(events['strategy'] == 'D2') & (events['event'] == 'BREAKOUT')].copy()
    d2_events['signal_date'] = pd.to_datetime(d2_events['signal_date'])
    
    dates = sorted(d2_events['signal_date'].dropna())
    q33 = pd.to_datetime(np.percentile([d.value for d in dates], 33))
    q66 = pd.to_datetime(np.percentile([d.value for d in dates], 66))

    def get_period(d):
        if d <= q33: return "Early"
        elif d <= q66: return "Middle"
        else: return "Recent"
        
    d2_events['period'] = d2_events['signal_date'].apply(get_period)
    d2_signal_set = set(zip(d2_events['symbol'], d2_events['signal_date']))

    print("Loading daily prices...")
    df = pd.read_csv('backups/20260304/daily_prices.csv', low_memory=False)
    df['date'] = pd.to_datetime(df['date'])
    df = df.dropna(subset=['close', 'high', 'low', 'open']).sort_values(['symbol', 'date']).reset_index(drop=True)

    print("Precomputing indicators...")
    dfs = []
    classification_data = []

    for sym, sdf in df.groupby('symbol'):
        if sym not in d2_events['symbol'].values:
            continue
            
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
    df_class = pd.DataFrame(classification_data)
    
    return full_df, df_class, d2_signal_set

def train_and_predict(df_class, train_periods, test_periods):
    features = ['rs_90d', 'dist_ema_50', 'dist_anchor', 'vol_ratio']
    df_train = df_class[df_class['period'].isin(train_periods)].dropna(subset=features)
    df_test = df_class[df_class['period'].isin(test_periods)]
    
    medians = df_train[features].median()
    iqr = df_train[features].quantile(0.75) - df_train[features].quantile(0.25)
    iqr = iqr.replace(0, 1)

    cent_1 = (df_train[df_train['target'] == 1][features].median() - medians) / iqr
    cent_0 = (df_train[df_train['target'] == 0][features].median() - medians) / iqr

    df_test_filled = df_test.copy()
    df_test_filled[features] = df_test_filled[features].fillna(medians)

    X_test = (df_test_filled[features] - medians) / iqr
    dist_1 = np.sqrt(((X_test - cent_1) ** 2).sum(axis=1))
    dist_0 = np.sqrt(((X_test - cent_0) ** 2).sum(axis=1))
    
    preds = (dist_1 < dist_0).astype(int)
    
    pred_map = {}
    for idx, row in df_test.iterrows():
        pred_map[(row['symbol'], row['signal_date'])] = preds.loc[idx]
        
    return pred_map

def run_portfolio(full_df, d2_signal_set, pred_map, start_date, end_date, is_treatment=False):
    period_df = full_df[(full_df['date'] >= start_date) & (full_df['date'] <= end_date)].copy()
    cash = INITIAL_CASH
    positions = {}
    daily_pv = []
    trade_logs = []
    executed_trades = 0

    for date, day_df in period_df.groupby('date'):
        # Exits
        for row in day_df.itertuples():
            sym = row.symbol
            if sym in positions:
                pos = positions[sym]
                exit_reason = None
                exit_price = None
                
                archetype = pos['trade_record']['archetype']
                
                if row.open <= pos['broker_stop']:
                    exit_reason = 'STOP_GAP'
                    exit_price = row.open
                elif row.low < pos['broker_stop']:
                    exit_reason = 'STOP_INTRADAY'
                    exit_price = pos['broker_stop']
                else:
                    if is_treatment and archetype == 0:
                        # Deep-Base Treatment: Weekly Structural
                        if row.is_friday and row.close < row.w_anchor:
                            exit_reason = 'WEEKLY_STRUCTURAL'
                            exit_price = row.next_open
                    else:
                        # Control (All) and Momentum Treatment: Daily Structural
                        if row.close < row.d2_anchor:
                            exit_reason = 'DAILY_STRUCTURAL'
                            exit_price = row.next_open
                            
                if exit_reason and pd.notnull(exit_price):
                    proceeds = (pos['shares'] * exit_price * SLIPPAGE_SELL) * (1 - TX_COST)
                    cash += proceeds
                    
                    trade = pos['trade_record']
                    trade['exit_date'] = date
                    trade['exit_reason'] = exit_reason
                    trade['realized_pnl'] = proceeds - trade['max_invested']
                    trade_logs.append(trade)
                    del positions[sym]

        # Entries
        buy_signals = []
        for row in day_df.itertuples():
            sym = row.symbol
            if pd.isnull(row.next_open): continue
            
            if sym not in positions:
                if (sym, row.date) in d2_signal_set:
                    if (sym, row.date) in pred_map:
                        buy_signals.append((sym, row, 1, row.d_high_10))
            elif positions[sym]['tranche'] < 5:
                na = row.d_high_10
                if pd.notnull(na) and na != positions[sym].get('last_add_trigger') and row.close > na:
                    buy_signals.append((sym, row, positions[sym]['tranche'] + 1, na))

        buy_signals.sort(key=lambda x: x[0])
        
        for sym, row, tr, na in buy_signals:
            if tr == 1 and len(positions) >= MAX_POSITIONS:
                continue
                
            target_cap = TRANCHE_TARGETS[tr]
            curr_cap = positions[sym]['invested'] if sym in positions else 0
            alloc = target_cap - curr_cap
            
            if alloc <= 0: continue
            
            price = row.next_open * SLIPPAGE_BUY
            cost = alloc * TX_COST
            total_outlay = alloc + cost
            if total_outlay > cash: continue
            
            shares = alloc / price
            cash -= total_outlay
            
            if sym not in positions:
                executed_trades += 1
                pred = pred_map.get((sym, row.date), 1)
                trade_record = {
                    'symbol': sym,
                    'entry_date': row.date,
                    'entry_price': price,
                    'max_invested': total_outlay,
                    'archetype': pred,
                    'target_r50_price': price * 1.5,
                    'target_r100_price': price * 2.0,
                }
                positions[sym] = {'shares': shares, 'invested': alloc, 'tranche': tr, 'trade_record': trade_record}
            else:
                positions[sym]['shares'] += shares
                positions[sym]['invested'] += alloc
                positions[sym]['tranche'] = tr
                positions[sym]['trade_record']['max_invested'] += total_outlay
                
            pred = positions[sym]['trade_record']['archetype']
            if is_treatment and pred == 0:
                stop = row.w_anchor - (0.5 * row.w_atr_14) if pd.notnull(row.w_anchor) else row.d2_anchor - (0.5 * row.d_atr_14)
            else:
                stop = row.d2_quit_lvl
                
            if pd.notnull(stop):
                positions[sym]['broker_stop'] = max(positions[sym].get('broker_stop', 0), stop)
            positions[sym]['last_add_trigger'] = na

        pv = cash
        for sym, p in positions.items():
            r = day_df[day_df['symbol'] == sym]
            if len(r) > 0:
                pv += p['shares'] * r.iloc[0].close
        daily_pv.append({'date': date, 'pv': pv, 'cash': cash})
        
    for sym, pos in positions.items():
        trade = pos['trade_record']
        trade['exit_date'] = pd.NaT
        trade['exit_reason'] = 'OPEN'
        trade['realized_pnl'] = 0
        trade_logs.append(trade)

    df_pv = pd.DataFrame(daily_pv)
    trades_df = pd.DataFrame(trade_logs)
    
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
        if hit_r50 and r50_slice.iloc[0]['date'] <= exit_dt:
            held_at_r50 = True
                
        r100_slice = fut[fut['high'] >= row['target_r100_price']]
        hit_r100 = len(r100_slice) > 0
        held_at_r100 = False
        if hit_r100 and r100_slice.iloc[0]['date'] <= exit_dt:
            held_at_r100 = True
                
        r50_flags.append({'theo_r50': hit_r50, 'held_at_r50': held_at_r50})
        r100_flags.append({'theo_r100': hit_r100, 'held_at_r100': held_at_r100})
        
    if len(trades_df) > 0:
        trades_df = pd.concat([trades_df, pd.DataFrame(r50_flags), pd.DataFrame(r100_flags)], axis=1)
    
    start_pv = INITIAL_CASH
    end_pv = df_pv['pv'].iloc[-1]
    total_ret = (end_pv / start_pv) - 1
    days = (df_pv['date'].max() - df_pv['date'].min()).days
    cagr = (end_pv / start_pv) ** (365.25 / days) - 1 if days > 0 else 0
    df_pv['peak'] = df_pv['pv'].cummax()
    df_pv['dd'] = (df_pv['pv'] - df_pv['peak']) / df_pv['peak']
    max_dd = df_pv['dd'].min()
    avg_cap_util = 1 - (df_pv['cash'] / df_pv['pv']).mean()
    
    r50_cap_rate = 0
    r100_cap_rate = 0
    if len(trades_df) > 0:
        r50_winners = trades_df[trades_df['theo_r50'] == True]
        r100_winners = trades_df[trades_df['theo_r100'] == True]
        r50_cap_rate = (r50_winners['held_at_r50'].sum() / len(r50_winners)) if len(r50_winners) > 0 else 0
        r100_cap_rate = (r100_winners['held_at_r100'].sum() / len(r100_winners)) if len(r100_winners) > 0 else 0
    
    metrics = {
        'cagr': cagr,
        'total_ret': total_ret,
        'max_dd': max_dd,
        'cap_util': avg_cap_util,
        'r50_cap': r50_cap_rate,
        'r100_cap': r100_cap_rate,
        'executed_trades': executed_trades
    }
    return metrics, trades_df

if __name__ == "__main__":
    full_df, df_class, d2_signal_set = load_data()
    
    def run_period(name, train_periods, test_periods, start_date, end_date):
        print(f"\n--- Running {name} Period ({start_date.date()} to {end_date.date()}) ---")
        pred_map = train_and_predict(df_class, train_periods, test_periods)
        print(f"Mapped {len(pred_map)} test signals")
        
        m_ctrl, tr_ctrl = run_portfolio(full_df, d2_signal_set, pred_map, start_date, end_date, False)
        m_treat, tr_treat = run_portfolio(full_df, d2_signal_set, pred_map, start_date, end_date, True)
        
        # Trade level paired evidence
        paired_data = []
        if len(tr_ctrl) > 0 and len(tr_treat) > 0:
            merged = pd.merge(tr_ctrl, tr_treat, on=['symbol', 'entry_date'], suffixes=('_ctrl', '_treat'))
            db_merged = merged[merged['archetype_ctrl'] == 0]
            
            rescued = 0
            prolonged = 0
            rescued_pnl = 0
            prolonged_pnl = 0
            
            for _, row in db_merged.iterrows():
                # Rescued: R100 winner, failed in control, captured in treatment
                if row['theo_r100_ctrl']:
                    if not row['held_at_r100_ctrl'] and row['held_at_r100_treat']:
                        rescued += 1
                        rescued_pnl += (row['realized_pnl_treat'] - row['realized_pnl_ctrl'])
                
                # Prolonged: NOT R50/R100 winner, held longer in treatment leading to more loss or just kept alive
                if not row['theo_r50_ctrl'] and not row['theo_r100_ctrl']:
                    if row['exit_date_treat'] > row['exit_date_ctrl']:
                        prolonged += 1
                        prolonged_pnl += (row['realized_pnl_treat'] - row['realized_pnl_ctrl'])
                        
            net_benefit = rescued_pnl + prolonged_pnl
            
            pair_metrics = {
                'rescued': rescued,
                'prolonged': prolonged,
                'rescued_pnl': rescued_pnl,
                'prolonged_pnl': prolonged_pnl,
                'net_benefit': net_benefit
            }
        else:
            pair_metrics = {'rescued': 0, 'prolonged': 0, 'rescued_pnl': 0, 'prolonged_pnl': 0, 'net_benefit': 0}
            
        return m_ctrl, m_treat, pair_metrics

    # Define boundaries
    q33 = pd.to_datetime(np.percentile([d.value for d in pd.to_datetime(df_class['signal_date'])], 33))
    q66 = pd.to_datetime(np.percentile([d.value for d in pd.to_datetime(df_class['signal_date'])], 66))
    
    val_m_ctrl, val_m_treat, val_pair = run_period(
        "VALIDATION", 
        ['Early'], ['Middle'], 
        q33, q66
    )
    
    hold_m_ctrl, hold_m_treat, hold_pair = run_period(
        "HOLDOUT", 
        ['Early', 'Middle'], ['Recent'], 
        q66, full_df['date'].max()
    )

    with open('walkforward_results.md', 'w') as f:
        f.write("# Conditional Exit: Chronological Walk-Forward Validation\n\n")
        f.write("## 1. Validation Period (Middle)\n")
        f.write("| Metric | Control (Current Struct) | Treatment (Deep-Base Weekly) |\n")
        f.write("|---|---|---|\n")
        f.write(f"| CAGR | {val_m_ctrl['cagr']*100:.2f}% | {val_m_treat['cagr']*100:.2f}% |\n")
        f.write(f"| Total Return | {val_m_ctrl['total_ret']*100:.2f}% | {val_m_treat['total_ret']*100:.2f}% |\n")
        f.write(f"| Max Drawdown | {val_m_ctrl['max_dd']*100:.2f}% | {val_m_treat['max_dd']*100:.2f}% |\n")
        f.write(f"| Cap Util | {val_m_ctrl['cap_util']*100:.1f}% | {val_m_treat['cap_util']*100:.1f}% |\n")
        f.write(f"| R50 Capture | {val_m_ctrl['r50_cap']*100:.1f}% | {val_m_treat['r50_cap']*100:.1f}% |\n")
        f.write(f"| R100 Capture | {val_m_ctrl['r100_cap']*100:.1f}% | {val_m_treat['r100_cap']*100:.1f}% |\n")
        f.write(f"| Executed Trades | {val_m_ctrl['executed_trades']} | {val_m_treat['executed_trades']} |\n\n")
        
        f.write("### Validation Trade-Level Paired Evidence (Deep-Base Only)\n")
        f.write(f"- **Winners Rescued:** {val_pair['rescued']} (Added P&L: ₹{val_pair['rescued_pnl']:,.0f})\n")
        f.write(f"- **Losers Prolonged:** {val_pair['prolonged']} (Added P&L: ₹{val_pair['prolonged_pnl']:,.0f})\n")
        f.write(f"- **Net Economic Benefit:** ₹{val_pair['net_benefit']:,.0f}\n\n")

        f.write("## 2. Holdout Period (Recent)\n")
        f.write("| Metric | Control (Current Struct) | Treatment (Deep-Base Weekly) |\n")
        f.write("|---|---|---|\n")
        f.write(f"| CAGR | {hold_m_ctrl['cagr']*100:.2f}% | {hold_m_treat['cagr']*100:.2f}% |\n")
        f.write(f"| Total Return | {hold_m_ctrl['total_ret']*100:.2f}% | {hold_m_treat['total_ret']*100:.2f}% |\n")
        f.write(f"| Max Drawdown | {hold_m_ctrl['max_dd']*100:.2f}% | {hold_m_treat['max_dd']*100:.2f}% |\n")
        f.write(f"| Cap Util | {hold_m_ctrl['cap_util']*100:.1f}% | {hold_m_treat['cap_util']*100:.1f}% |\n")
        f.write(f"| R50 Capture | {hold_m_ctrl['r50_cap']*100:.1f}% | {hold_m_treat['r50_cap']*100:.1f}% |\n")
        f.write(f"| R100 Capture | {hold_m_ctrl['r100_cap']*100:.1f}% | {hold_m_treat['r100_cap']*100:.1f}% |\n")
        f.write(f"| Executed Trades | {hold_m_ctrl['executed_trades']} | {hold_m_treat['executed_trades']} |\n\n")

        f.write("### Holdout Trade-Level Paired Evidence (Deep-Base Only)\n")
        f.write(f"- **Winners Rescued:** {hold_pair['rescued']} (Added P&L: ₹{hold_pair['rescued_pnl']:,.0f})\n")
        f.write(f"- **Losers Prolonged:** {hold_pair['prolonged']} (Added P&L: ₹{hold_pair['prolonged_pnl']:,.0f})\n")
        f.write(f"- **Net Economic Benefit:** ₹{hold_pair['net_benefit']:,.0f}\n\n")
        
    print("Done!")

