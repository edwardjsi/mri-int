import pandas as pd
import numpy as np
import warnings
import datetime
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

    df = pd.read_csv('backups/20260304/daily_prices.csv', low_memory=False)
    df['date'] = pd.to_datetime(df['date'])
    df = df.dropna(subset=['close', 'high', 'low', 'open']).sort_values(['symbol', 'date']).reset_index(drop=True)

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
                    
            # Target is W-validation for TRAINING ONLY. Never used in test predictions.
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
    # Strictly isolate training data (Safeguard 5)
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
    
    # 1=Momentum, 0=Deep-Base
    preds = (dist_1 < dist_0).astype(int)
    
    pred_map = {}
    for idx, row in df_test.iterrows():
        pred_map[(row['symbol'], row['signal_date'])] = preds.loc[idx]
        
    return pred_map

def run_experiment_a_paired_exit_effect(full_df, d2_signal_set, pred_map, start_date, end_date):
    """
    Safeguard 3: Freeze T1-T5 event stream based on Control. Treatment uses shadow cash.
    """
    period_df = full_df[(full_df['date'] >= start_date) & (full_df['date'] <= end_date)].copy()
    
    cash_ctrl = INITIAL_CASH
    pos_ctrl = {}
    pos_treat = {} # Treatment receives identical trades regardless of cost
    
    log_ctrl = []
    log_treat = []

    for date, day_df in period_df.groupby('date'):
        # --- EXITS ---
        for row in day_df.itertuples():
            sym = row.symbol
            # Control exits
            if sym in pos_ctrl:
                p = pos_ctrl[sym]
                er = None; ep = None
                if row.open <= p['broker_stop']: er = 'STOP_GAP'; ep = row.open
                elif row.low < p['broker_stop']: er = 'STOP_INTRADAY'; ep = p['broker_stop']
                elif row.close < row.d2_anchor: er = 'DAILY_STRUCTURAL'; ep = row.next_open
                if er and pd.notnull(ep):
                    proceeds = (p['shares'] * ep * SLIPPAGE_SELL) * (1 - TX_COST)
                    cash_ctrl += proceeds
                    t = p['trade_record']
                    t['exit_date'] = date; t['exit_reason'] = er; t['exit_price'] = ep
                    t['realized_pnl'] = proceeds - t['max_invested']
                    log_ctrl.append(t)
                    del pos_ctrl[sym]
            
            # Treatment exits (Shadow cash doesn't need tracking for P&L computation here since it's an isolate test)
            if sym in pos_treat:
                p = pos_treat[sym]
                er = None; ep = None
                arch = p['trade_record']['archetype']
                if row.open <= p['broker_stop']: er = 'STOP_GAP'; ep = row.open
                elif row.low < p['broker_stop']: er = 'STOP_INTRADAY'; ep = p['broker_stop']
                else:
                    if arch == 0:
                        if row.is_friday and row.close < row.w_anchor: er = 'WEEKLY_STRUCTURAL'; ep = row.next_open
                    else:
                        if row.close < row.d2_anchor: er = 'DAILY_STRUCTURAL'; ep = row.next_open
                if er and pd.notnull(ep):
                    proceeds = (p['shares'] * ep * SLIPPAGE_SELL) * (1 - TX_COST)
                    t = p['trade_record']
                    t['exit_date'] = date; t['exit_reason'] = er; t['exit_price'] = ep
                    t['realized_pnl'] = proceeds - t['max_invested']
                    log_treat.append(t)
                    del pos_treat[sym]

        # --- ENTRIES (Master Event Stream Driven By Control) ---
        buy_signals = []
        for row in day_df.itertuples():
            sym = row.symbol
            if pd.isnull(row.next_open): continue
            
            if sym not in pos_ctrl:
                if (sym, row.date) in d2_signal_set and (sym, row.date) in pred_map:
                    buy_signals.append((sym, row, 1, row.d_high_10))
            elif pos_ctrl[sym]['tranche'] < 5:
                na = row.d_high_10
                if pd.notnull(na) and na != pos_ctrl[sym].get('last_add_trigger') and row.close > na:
                    buy_signals.append((sym, row, pos_ctrl[sym]['tranche'] + 1, na))

        buy_signals.sort(key=lambda x: x[0])
        
        for sym, row, tr, na in buy_signals:
            if tr == 1 and len(pos_ctrl) >= MAX_POSITIONS: continue
            target_cap = TRANCHE_TARGETS[tr]
            curr_cap = pos_ctrl[sym]['invested'] if sym in pos_ctrl else 0
            alloc = target_cap - curr_cap
            if alloc <= 0: continue
            
            price = row.next_open * SLIPPAGE_BUY
            cost = alloc * TX_COST
            total_outlay = alloc + cost
            if total_outlay > cash_ctrl: continue # Control cash strictly enforces the event stream
            
            shares = alloc / price
            cash_ctrl -= total_outlay
            
            pred = pred_map.get((sym, row.date), 1)
            
            if sym not in pos_ctrl:
                t_rec = {'symbol': sym, 'entry_date': row.date, 'entry_price': price, 'max_invested': total_outlay, 'archetype': pred}
                pos_ctrl[sym] = {'shares': shares, 'invested': alloc, 'tranche': tr, 'trade_record': dict(t_rec)}
                pos_treat[sym] = {'shares': shares, 'invested': alloc, 'tranche': tr, 'trade_record': dict(t_rec)} # Treatment gets IDENTICAL copy
            else:
                for pos_dict in (pos_ctrl, pos_treat):
                    pos_dict[sym]['shares'] += shares
                    pos_dict[sym]['invested'] += alloc
                    pos_dict[sym]['tranche'] = tr
                    pos_dict[sym]['trade_record']['max_invested'] += total_outlay
                
            pos_ctrl[sym]['broker_stop'] = max(pos_ctrl[sym].get('broker_stop', 0), row.d2_quit_lvl if pd.notnull(row.d2_quit_lvl) else 0)
            pos_ctrl[sym]['last_add_trigger'] = na
            
            t_stop = row.w_anchor - (0.5 * row.w_atr_14) if (pred == 0 and pd.notnull(row.w_anchor)) else row.d2_anchor - (0.5 * row.d_atr_14)
            pos_treat[sym]['broker_stop'] = max(pos_treat[sym].get('broker_stop', 0), t_stop if pd.notnull(t_stop) else 0)
            pos_treat[sym]['last_add_trigger'] = na

    for sym, p in pos_ctrl.items(): log_ctrl.append(p['trade_record']) # Remaining open
    for sym, p in pos_treat.items(): log_treat.append(p['trade_record']) # Remaining open

    tr_c = pd.DataFrame(log_ctrl)
    tr_t = pd.DataFrame(log_treat)
    return tr_c, tr_t

def run_experiment_b_real_portfolio(full_df, d2_signal_set, pred_map, start_date, end_date):
    """
    Safeguard 4: Genuinely independent portfolios. Do NOT synchronize cash.
    """
    period_df = full_df[(full_df['date'] >= start_date) & (full_df['date'] <= end_date)].copy()
    
    def run_indep(is_treat):
        cash = INITIAL_CASH
        pos = {}
        logs = []
        pv_list = []
        for date, day_df in period_df.groupby('date'):
            for row in day_df.itertuples():
                sym = row.symbol
                if sym in pos:
                    p = pos[sym]
                    er = None; ep = None
                    if row.open <= p['broker_stop']: er = 'STOP_GAP'; ep = row.open
                    elif row.low < p['broker_stop']: er = 'STOP_INTRADAY'; ep = p['broker_stop']
                    else:
                        if is_treat and p['trade_record']['archetype'] == 0:
                            if row.is_friday and row.close < row.w_anchor: er = 'WEEKLY_STRUCTURAL'; ep = row.next_open
                        else:
                            if row.close < row.d2_anchor: er = 'DAILY_STRUCTURAL'; ep = row.next_open
                    if er and pd.notnull(ep):
                        proceeds = (p['shares'] * ep * SLIPPAGE_SELL) * (1 - TX_COST)
                        cash += proceeds
                        t = p['trade_record']
                        t['exit_date'] = date; t['exit_reason'] = er; t['exit_price'] = ep
                        t['realized_pnl'] = proceeds - t['max_invested']
                        logs.append(t)
                        del pos[sym]

            buy_signals = []
            for row in day_df.itertuples():
                sym = row.symbol
                if pd.isnull(row.next_open): continue
                if sym not in pos:
                    if (sym, row.date) in d2_signal_set and (sym, row.date) in pred_map:
                        buy_signals.append((sym, row, 1, row.d_high_10))
                elif pos[sym]['tranche'] < 5:
                    na = row.d_high_10
                    if pd.notnull(na) and na != pos[sym].get('last_add_trigger') and row.close > na:
                        buy_signals.append((sym, row, pos[sym]['tranche'] + 1, na))

            buy_signals.sort(key=lambda x: x[0])
            for sym, row, tr, na in buy_signals:
                if tr == 1 and len(pos) >= MAX_POSITIONS: continue
                alloc = TRANCHE_TARGETS[tr] - (pos[sym]['invested'] if sym in pos else 0)
                if alloc <= 0: continue
                price = row.next_open * SLIPPAGE_BUY
                tot = alloc + (alloc * TX_COST)
                if tot > cash: continue
                shares = alloc / price
                cash -= tot
                pred = pred_map.get((sym, row.date), 1)
                if sym not in pos:
                    pos[sym] = {'shares': shares, 'invested': alloc, 'tranche': tr, 'trade_record': {
                        'symbol': sym, 'entry_date': row.date, 'entry_price': price, 'max_invested': tot, 'archetype': pred,
                        'target_r50_price': price * 1.5, 'target_r100_price': price * 2.0
                    }}
                else:
                    pos[sym]['shares'] += shares; pos[sym]['invested'] += alloc; pos[sym]['tranche'] = tr; pos[sym]['trade_record']['max_invested'] += tot
                
                t_stop = row.w_anchor - (0.5 * row.w_atr_14) if (is_treat and pred == 0 and pd.notnull(row.w_anchor)) else row.d2_anchor - (0.5 * row.d_atr_14)
                pos[sym]['broker_stop'] = max(pos[sym].get('broker_stop', 0), t_stop if pd.notnull(t_stop) else 0)
                pos[sym]['last_add_trigger'] = na
                
            cur_pv = cash
            for sym, p in pos.items():
                r = day_df[day_df['symbol'] == sym]
                if len(r) > 0: cur_pv += p['shares'] * r.iloc[0].close
            pv_list.append({'date': date, 'pv': cur_pv, 'cash': cash})
            
        for sym, p in pos.items(): logs.append(p['trade_record']) # Open
        
        tdf = pd.DataFrame(logs)
        df_pv = pd.DataFrame(pv_list)
        return tdf, df_pv

    t_ctrl, pv_ctrl = run_indep(False)
    t_treat, pv_treat = run_indep(True)
    return t_ctrl, pv_ctrl, t_treat, pv_treat

def annotate_and_metrics(tdf, df_pv, full_df):
    if len(tdf) == 0: return tdf, {}
    
    # Check completed vs incomplete windows (Safeguard 6)
    last_date = full_df['date'].max()
    
    r50 = []; r100 = []; window_complete = []
    for idx, row in tdf.iterrows():
        sym = row['symbol']
        entry = row['entry_date']
        exit_dt = row.get('exit_date', pd.NaT)
        if pd.isnull(exit_dt): exit_dt = datetime.datetime(2099, 1, 1)
        
        fut = full_df[(full_df['symbol'] == sym) & (full_df['date'] >= entry)].head(252)
        r50s = fut[fut['high'] >= row['target_r50_price']]
        hr50 = len(r50s) > 0
        r100s = fut[fut['high'] >= row['target_r100_price']]
        hr100 = len(r100s) > 0
        
        r50.append({'theo_r50': hr50, 'held_at_r50': hr50 and r50s.iloc[0]['date'] <= exit_dt})
        r100.append({'theo_r100': hr100, 'held_at_r100': hr100 and r100s.iloc[0]['date'] <= exit_dt})
        window_complete.append((last_date - entry).days >= 252)

    tdf = pd.concat([tdf, pd.DataFrame(r50), pd.DataFrame(r100), pd.Series(window_complete, name='is_252d_complete')], axis=1)
    
    start_pv = INITIAL_CASH
    end_pv = df_pv['pv'].iloc[-1]
    days = (df_pv['date'].max() - df_pv['date'].min()).days
    cagr = (end_pv / start_pv) ** (365.25 / days) - 1 if days > 0 else 0
    df_pv['peak'] = df_pv['pv'].cummax()
    df_pv['dd'] = (df_pv['pv'] - df_pv['peak']) / df_pv['peak']
    
    ulcer = np.sqrt((df_pv['dd'] ** 2).mean()) if len(df_pv) > 0 else 0
    volatility = df_pv['pv'].pct_change().std() * np.sqrt(252) if len(df_pv) > 1 else 0
    
    # Isolate strictly complete windows for capture rates
    tdf_complete = tdf[tdf['is_252d_complete'] == True]
    
    def cap(target_df, held_col): return target_df[held_col].sum() / len(target_df) if len(target_df) > 0 else 0
    
    metrics = {
        'cagr': cagr,
        'total_ret': (end_pv / start_pv) - 1,
        'max_dd': df_pv['dd'].min(),
        'ulcer': ulcer,
        'volatility': volatility,
        'cap_util': 1 - (df_pv['cash'] / df_pv['pv']).mean(),
        'turnover': (tdf['max_invested'].sum() / df_pv['pv'].mean() / (days/365.25)) if len(df_pv) > 0 else 0,
        'r50_cap_completed': cap(tdf_complete[tdf_complete['theo_r50'] == True], 'held_at_r50'),
        'r100_cap_completed': cap(tdf_complete[tdf_complete['theo_r100'] == True], 'held_at_r100'),
        'avg_winner': tdf[tdf.get('realized_pnl', pd.Series(dtype=float)) > 0]['realized_pnl'].mean(),
        'avg_loser': tdf[tdf.get('realized_pnl', pd.Series(dtype=float)) <= 0]['realized_pnl'].mean(),
        'executed_trades': len(tdf)
    }
    return tdf, metrics

def run_all(full_df, df_class, d2_signal_set):
    q33 = pd.to_datetime(np.percentile([d.value for d in pd.to_datetime(df_class['signal_date'])], 33))
    q66 = pd.to_datetime(np.percentile([d.value for d in pd.to_datetime(df_class['signal_date'])], 66))

    runs = [
        ("1. Validation Period (Middle)", ['Early'], ['Middle'], q33, q66),
        ("2. Holdout Period (Recent)", ['Early', 'Middle'], ['Recent'], q66, full_df['date'].max())
    ]
    
    out = ""
    out += "# CAI Final Validation Report (Track B: Pure D2 Exit Research)\n\n"
    out += "> [!WARNING]\n> **Pure D2 Exit Research — Not Production-Equivalent.**\n"
    out += "> The Economic Portfolio Verdict from this report must not be used to approve production deployment because historical production point-in-time scoring data (e.g. total_score, QIF) does not exist.\n\n"
    out += "## Verdict 1: Classification\n"
    out += "Day-0 classification models train chronologically without future lookahead. Performance is evaluated on walk-forward out-of-sample data.\n\n"
    
    paired_audit_rows = []

    for period, trn, tst, sdate, edate in runs:
        pred_map = train_and_predict(df_class, trn, tst)
        
        # Exp A
        t_ca, t_ta = run_experiment_a_paired_exit_effect(full_df, d2_signal_set, pred_map, sdate, edate)
        
        # Exp B
        t_cb, pv_cb, t_tb, pv_tb = run_experiment_b_real_portfolio(full_df, d2_signal_set, pred_map, sdate, edate)
        t_cb, m_cb = annotate_and_metrics(t_cb, pv_cb, full_df)
        t_tb, m_tb = annotate_and_metrics(t_tb, pv_tb, full_df)
        
        # Calculate paired metrics for Exp A
        r_pnla = 0; p_pnla = 0; r_ct = 0; p_ct = 0
        if len(t_ca) > 0 and len(t_ta) > 0:
            merge_a = pd.merge(t_ca, t_ta, on=['symbol', 'entry_date'], suffixes=('_c', '_t'))
            for _, r in merge_a.iterrows():
                if r['archetype_c'] == 0:
                    delta = r.get('realized_pnl_t', 0) - r.get('realized_pnl_c', 0)
                    if r.get('exit_date_t', pd.NaT) is not pd.NaT and r.get('exit_date_c', pd.NaT) is not pd.NaT:
                        if r['exit_date_t'] > r['exit_date_c']:
                            if delta > 0: r_ct+=1; r_pnla += delta
                            else: p_ct+=1; p_pnla += delta
                            
                    # Audit Row (Safeguard 10)
                    if period == "1. Validation Period (Middle)":
                        paired_audit_rows.append(f"| {r['symbol']} | {r['entry_date'].date()} | {r['archetype_c']} | {r.get('exit_reason_c','OPEN')} | {r.get('exit_reason_t','OPEN')} | ₹{r.get('realized_pnl_c',0):,.0f} | ₹{r.get('realized_pnl_t',0):,.0f} | ₹{delta:,.0f} |")

        out += f"## {period}\n"
        out += "### Experiment A: Paired Exit-Effect Test\n"
        out += f"- **Winners Rescued:** {r_ct} (Added P&L: ₹{r_pnla:,.0f})\n"
        out += f"- **Losers Prolonged:** {p_ct} (Added P&L: ₹{p_pnla:,.0f})\n"
        out += f"- **Net Economic Benefit (Frozen Stream):** ₹{(r_pnla + p_pnla):,.0f}\n\n"
        
        # Divergence Metrics for Exp B
        c_entries = set(zip(t_cb['symbol'], t_cb['entry_date'])) if len(t_cb)>0 else set()
        t_entries = set(zip(t_tb['symbol'], t_tb['entry_date'])) if len(t_tb)>0 else set()
        c_only_pnl = t_cb[t_cb.apply(lambda r: (r['symbol'], r['entry_date']) in (c_entries - t_entries), axis=1)]['realized_pnl'].sum() if len(t_cb)>0 else 0
        t_only_pnl = t_tb[t_tb.apply(lambda r: (r['symbol'], r['entry_date']) in (t_entries - c_entries), axis=1)]['realized_pnl'].sum() if len(t_tb)>0 else 0
        
        out += "### Experiment B: Real Portfolio Economic Test\n"
        out += "| Metric | Control (Daily) | Treatment (Deep-Base Weekly) |\n"
        out += "|---|---|---|\n"
        out += f"| **CAGR** | {m_cb.get('cagr',0)*100:.2f}% | {m_tb.get('cagr',0)*100:.2f}% |\n"
        out += f"| Total Return | {m_cb.get('total_ret',0)*100:.2f}% | {m_tb.get('total_ret',0)*100:.2f}% |\n"
        out += f"| **Max Drawdown** | {m_cb.get('max_dd',0)*100:.2f}% | {m_tb.get('max_dd',0)*100:.2f}% |\n"
        out += f"| Ulcer Index | {m_cb.get('ulcer',0)*100:.2f}% | {m_tb.get('ulcer',0)*100:.2f}% |\n"
        out += f"| Volatility (Ann) | {m_cb.get('volatility',0)*100:.2f}% | {m_tb.get('volatility',0)*100:.2f}% |\n"
        out += f"| Cap Util | {m_cb.get('cap_util',0)*100:.1f}% | {m_tb.get('cap_util',0)*100:.1f}% |\n"
        out += f"| Turnover | {m_cb.get('turnover',0):.1f}x | {m_tb.get('turnover',0):.1f}x |\n"
        out += f"| R50 Capture (Complete 252d) | {m_cb.get('r50_cap_completed',0)*100:.1f}% | {m_tb.get('r50_cap_completed',0)*100:.1f}% |\n"
        out += f"| R100 Capture (Complete 252d) | {m_cb.get('r100_cap_completed',0)*100:.1f}% | {m_tb.get('r100_cap_completed',0)*100:.1f}% |\n"
        out += f"| Executed Trades | {m_cb.get('executed_trades')} | {m_tb.get('executed_trades')} |\n"
        out += f"| Avg Winner | ₹{m_cb.get('avg_winner',0):,.0f} | ₹{m_tb.get('avg_winner',0):,.0f} |\n"
        out += f"| Avg Loser | ₹{m_cb.get('avg_loser',0):,.0f} | ₹{m_tb.get('avg_loser',0):,.0f} |\n\n"
        
        out += "#### Opportunity Cost (Divergence)\n"
        out += f"- Common Entries: {len(c_entries & t_entries)}\n"
        out += f"- Control-Only Entries (Missed by Treatment): {len(c_entries - t_entries)} (P&L: ₹{c_only_pnl:,.0f})\n"
        out += f"- Treatment-Only Entries: {len(t_entries - c_entries)} (P&L: ₹{t_only_pnl:,.0f})\n\n"

    out += "## Verdict 2: Exit-Effect\n"
    out += "Pass if Net Economic Benefit (Frozen Stream) is positive.\n\n"
    out += "## Verdict 3: Economic Portfolio\n"
    out += "Pass if Treatment CAGR > Control AND Treatment Max Drawdown / Ulcer Index are acceptable.\n"
    out += "(Note: Since this is Track B, a Pass here cannot be used to promote to production).\n\n"
    
    out += "## Paired Trade Audit (Safeguard 10)\n"
    out += "| Symbol | Entry Date | Archetype | Control Exit | Treatment Exit | Control P&L | Treatment P&L | Incremental P&L |\n"
    out += "|---|---|---|---|---|---|---|---|\n"
    out += "\n".join(paired_audit_rows[:50])
    if len(paired_audit_rows) > 50:
        out += f"\n... and {len(paired_audit_rows)-50} more rows.\n"

    return out

if __name__ == "__main__":
    print("Loading data...")
    full_df, df_class, d2_signal_set = load_data()
    print("Running Pass 1...")
    out1 = run_all(full_df, df_class, d2_signal_set)
    print("Running Pass 2 (Determinism check)...")
    out2 = run_all(full_df, df_class, d2_signal_set)
    
    if out1 == out2:
        print("Determinism OK. Report written.")
        with open('cai_final_validation.md', 'w') as f:
            f.write(out1)
    else:
        print("Determinism check FAILED!")
