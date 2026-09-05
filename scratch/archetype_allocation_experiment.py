import pandas as pd
import numpy as np
import datetime
import warnings
warnings.filterwarnings('ignore')

print("Loading events...")
events = pd.read_csv('cai_backtest_events.csv')
d2_events = events[events['strategy'] == 'D2'].copy()
d2_events['signal_date'] = pd.to_datetime(d2_events['signal_date'])

dates = sorted(d2_events['signal_date'].dropna())
q33 = pd.to_datetime(np.percentile([d.value for d in dates], 33))
q66 = pd.to_datetime(np.percentile([d.value for d in dates], 66))

def get_period(d):
    if d <= q33: return "Early"
    elif d <= q66: return "Middle"
    else: return "Recent"

print("Loading daily prices...")
prices_df = pd.read_csv('backups/20260304/daily_prices.csv', low_memory=False)
prices_df['date'] = pd.to_datetime(prices_df['date'])
prices_df = prices_df.dropna(subset=['close', 'high', 'low', 'open']).sort_values(['symbol', 'date']).reset_index(drop=True)

def compute_atr(sdf, window):
    prev_close = sdf['close'].shift(1)
    tr1 = sdf['high'] - sdf['low']
    tr2 = (sdf['high'] - prev_close).abs()
    tr3 = (sdf['low'] - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window, min_periods=1).mean()

print("Precomputing indicators & targets...")
results = []
dfs = []
for sym, sdf in prices_df.groupby('symbol'):
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
    
    # W logic
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
    
    # Classification logic extraction
    sym_d2 = d2_events[d2_events['symbol'] == sym]
    if len(sym_d2) == 0: continue
    
    for _, row in sym_d2.iterrows():
        dt = row['signal_date']
        period = get_period(dt)
        
        future_mask = sdf['date'] >= dt
        if not future_mask.any(): continue
        pos = sdf[future_mask].index[0]
        if pos >= len(sdf): continue
        sig_row = sdf.iloc[pos]
        
        rs_90d = sig_row.get('rs_90d', np.nan)
        vol = sig_row.get('volume', np.nan)
        avg_vol = sig_row.get('avg_volume_20d', np.nan)
        vol_ratio = vol / avg_vol if avg_vol and avg_vol > 0 else np.nan
        ema_50 = sig_row.get('d_ema_50', np.nan)
        dist_ema_50 = (sig_row['close'] / ema_50) - 1 if ema_50 and ema_50 > 0 else np.nan
        d2_anchor = sig_row.get('d2_anchor', np.nan)
        dist_anchor = (sig_row['close'] / d2_anchor) - 1 if d2_anchor and d2_anchor > 0 else np.nan
        
        fut_slice = sdf.iloc[pos+1 : pos+253]
        if len(fut_slice) == 0: continue
        
        w_validated = False
        time_to_w = np.nan
        for _, fut_row in fut_slice.iterrows():
            if pd.notna(fut_row['d2_quit_lvl']) and fut_row['close'] < fut_row['d2_quit_lvl']: break
            if fut_row['date'].weekday() == 4 and pd.notna(fut_row['w_quit_lvl']) and fut_row['close'] > fut_row['w_quit_lvl']:
                w_validated = True
                time_to_w = (fut_row['date'] - dt).days
                break
                
        target = 1 if (w_validated and time_to_w <= 7) else 0
            
        results.append({
            'symbol': sym,
            'date': dt,
            'period': period,
            'target': target,
            'rs_90d': rs_90d,
            'dist_ema_50': dist_ema_50,
            'dist_anchor': dist_anchor,
            'vol_ratio': vol_ratio,
        })

df_features = pd.DataFrame(results)
features = ['rs_90d', 'dist_ema_50', 'dist_anchor', 'vol_ratio']
df_features = df_features.dropna(subset=features).copy()

print("Training classifier on Early period...")
train_early = df_features[df_features['period'] == 'Early']
medians = train_early[features].median()
iqr = train_early[features].quantile(0.75) - train_early[features].quantile(0.25)
iqr = iqr.replace(0, 1)

cent_1 = (train_early[train_early['target'] == 1][features].median() - medians) / iqr
cent_0 = (train_early[train_early['target'] == 0][features].median() - medians) / iqr

df_features['pred_class'] = 0 # 0 for deep base, 1 for momentum
X_all = (df_features[features] - medians) / iqr
dist_1 = np.sqrt(((X_all - cent_1) ** 2).sum(axis=1))
dist_0 = np.sqrt(((X_all - cent_0) ** 2).sum(axis=1))
df_features['pred_class'] = (dist_1 < dist_0).astype(int)

# Create lookup dict for quick classification in backtest
class_lookup = {}
for _, row in df_features.iterrows():
    class_lookup[(row['symbol'], row['date'])] = "MOMENTUM" if row['pred_class'] == 1 else "DEEP_BASE"

full_df = pd.concat(dfs).sort_values('date').reset_index(drop=True)
del dfs
del prices_df

# OUT OF SAMPLE ONLY - filter dataframe
print("Filtering for out of sample test period (Middle + Recent)...")
full_df = full_df[full_df['date'] > q33].copy()

INITIAL_CASH = 1000000.0
MAX_POSITIONS = 10
BASE_TRANCHE_TARGETS = {1: 20000, 2: 30000, 3: 50000, 4: 75000, 5: 125000}
SLIPPAGE_BUY = 1.001
SLIPPAGE_SELL = 0.999
TX_COST = 0.0015

policies = {
    'Equal_100_100': {'DEEP_BASE': 1.0, 'MOMENTUM': 1.0},
    'Overweight_125_75': {'DEEP_BASE': 1.25, 'MOMENTUM': 0.75},
    'Overweight_150_50': {'DEEP_BASE': 1.50, 'MOMENTUM': 0.50},
    'Momentum_Heavy_50_150': {'DEEP_BASE': 0.50, 'MOMENTUM': 1.50}
}

print("Running Backtests for Allocation Policies...")
outcomes = []

for policy_name, weights in policies.items():
    print(f"Running Policy: {policy_name}")
    cash = INITIAL_CASH
    positions = {}
    daily_pv = []
    
    for date, day_df in full_df.groupby('date'):
        # Exits
        for row in day_df.itertuples():
            sym = row.symbol
            if sym in positions:
                pos = positions[sym]
                
                # Broker stop
                if row.open <= pos['broker_stop']:
                    cash += (pos['shares'] * row.open * SLIPPAGE_SELL) * (1 - TX_COST)
                    del positions[sym]
                    continue
                elif row.low < pos['broker_stop']:
                    cash += (pos['shares'] * pos['broker_stop'] * SLIPPAGE_SELL) * (1 - TX_COST)
                    del positions[sym]
                    continue
                    
                # Structural Exit
                if row.close < row.d2_anchor:
                    price = row.next_open
                    if pd.notnull(price):
                        cash += (pos['shares'] * price * SLIPPAGE_SELL) * (1 - TX_COST)
                        del positions[sym]
                    continue

        # Entries
        buy_signals = []
        for row in day_df.itertuples():
            sym = row.symbol
            if pd.isnull(row.next_open): continue
            
            # Check if it's a D2 signal day by checking if we have it in lookup
            arch = class_lookup.get((sym, row.date), None)
            
            if sym not in positions:
                # Is it a valid D2 signal?
                if pd.notnull(row.d_high_10) and row.close > row.d_high_10 and len(positions) < MAX_POSITIONS:
                    if arch is not None:
                        buy_signals.append((sym, row, 1, row.d_high_10, arch))
            elif positions[sym]['tranche'] < 5:
                na = row.d_high_10
                if pd.notnull(na) and na != positions[sym].get('last_add_trigger') and row.close > na:
                    arch = positions[sym]['archetype']
                    buy_signals.append((sym, row, positions[sym]['tranche'] + 1, na, arch))
                    
        buy_signals.sort(key=lambda x: x[0])
        
        for sym, row, tr, na, arch in buy_signals:
            base_target = BASE_TRANCHE_TARGETS[tr]
            multiplier = weights[arch]
            target_cap = base_target * multiplier
            
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
                positions[sym] = {'shares': shares, 'invested': alloc, 'tranche': tr, 'archetype': arch}
            else:
                positions[sym]['shares'] += shares
                positions[sym]['invested'] += alloc
                positions[sym]['tranche'] = tr
                
            positions[sym]['broker_stop'] = row.d2_quit_lvl
            positions[sym]['last_add_trigger'] = na

        # EOD Value
        pv = cash
        for sym, p in positions.items():
            r = day_df[day_df['symbol'] == sym]
            if len(r) > 0:
                pv += p['shares'] * r.iloc[0].close
        daily_pv.append({'date': date, 'pv': pv})
        
    df_pv = pd.DataFrame(daily_pv)
    start_pv = INITIAL_CASH
    end_pv = df_pv['pv'].iloc[-1]
    total_ret = (end_pv / start_pv) - 1
    
    days = (df_pv['date'].max() - df_pv['date'].min()).days
    cagr = (end_pv / start_pv) ** (365.25 / days) - 1 if days > 0 else 0
    
    df_pv['peak'] = df_pv['pv'].cummax()
    df_pv['dd'] = (df_pv['pv'] - df_pv['peak']) / df_pv['peak']
    max_dd = df_pv['dd'].min()
    
    outcomes.append({
        'Policy': policy_name,
        'CAGR': f"{cagr*100:.2f}%",
        'Total Return': f"{total_ret*100:.2f}%",
        'Max Drawdown': f"{max_dd*100:.2f}%"
    })

res_df = pd.DataFrame(outcomes)
with open('cai_archetype_allocation_experiment.md', 'w') as f:
    f.write("# D2 Archetype Allocation Experiment\n\n")
    f.write("## 1. Methodology\n")
    f.write("- **Out-of-sample execution**: Classifier trained only on pre-2013 signals.\n")
    f.write("- **Test Period**: 2013 to 2026.\n")
    f.write("- **Execution**: Phase 2 mechanics, $1M starting capital.\n")
    f.write("- **Policies**:\n")
    f.write("  - Equal_100_100: 100% allocation to both.\n")
    f.write("  - Overweight_125_75: 125% to Deep-Base, 75% to Momentum.\n")
    f.write("  - Overweight_150_50: 150% to Deep-Base, 50% to Momentum.\n")
    f.write("  - Momentum_Heavy_50_150: 50% to Deep-Base, 150% to Momentum.\n\n")
    f.write("## 2. Portfolio Outcomes\n")
    f.write(res_df.to_markdown(index=False))

print("Done.")
