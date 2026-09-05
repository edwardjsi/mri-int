import pandas as pd
import numpy as np

print("Loading events...")
events = pd.read_csv('cai_backtest_events.csv')
breakouts = events[events['event'] == 'BREAKOUT'].copy()
breakouts['signal_date'] = pd.to_datetime(breakouts['signal_date'])

print("Loading daily prices...")
prices_df = pd.read_csv('backups/20260304/daily_prices.csv', low_memory=False)
prices_df['date'] = pd.to_datetime(prices_df['date'])

# For W validation and structural invalidation, we can just use the events file or we need w_quit_lvl
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
    sdf = sdf.sort_values('date')
    sdf.set_index('date', inplace=True)
    sdf['next_open'] = sdf['open'].shift(-1)
    
    wdf = sdf.resample('W-FRI').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    wdf['w_low_4'] = wdf['low'].rolling(4).min().shift(1)
    wdf['w_ema_20'] = wdf['close'].ewm(span=20, adjust=False).mean().shift(1)
    wdf['w_ema_50'] = wdf['close'].ewm(span=50, adjust=False).mean().shift(1)
    wdf['w_atr_14'] = compute_atr(wdf, 14).shift(1)
    wdf = wdf[['w_low_4', 'w_ema_20', 'w_ema_50', 'w_atr_14']]
    
    sdf = sdf.merge(wdf, left_index=True, right_index=True, how='left')
    sdf[['w_low_4', 'w_ema_20', 'w_ema_50', 'w_atr_14']] = sdf[['w_low_4', 'w_ema_20', 'w_ema_50', 'w_atr_14']].ffill()
    sdf['w_anchor'] = sdf['w_low_4'].combine_first(sdf['w_ema_50']).combine_first(sdf['w_ema_20'])
    sdf['w_quit_lvl'] = sdf['w_anchor'] - (0.5 * sdf['w_atr_14'])
    
    # D2 invalidation for finding D2->W window
    sdf['d_ema_50'] = sdf['close'].ewm(span=50, adjust=False).mean().shift(1)
    sdf['d_ema_200'] = sdf['close'].ewm(span=200, adjust=False).mean().shift(1)
    sdf['d_atr_14'] = compute_atr(sdf, 14).shift(1)
    sdf['d2_anchor'] = sdf['d_ema_50'].combine_first(sdf['d_ema_200'])
    sdf['d2_quit_lvl'] = sdf['d2_anchor'] - (0.5 * sdf['d_atr_14'])
    
    # Pre-calculate rolling max for Opportunity Set
    rev_close = sdf['close'].iloc[::-1]
    sdf['max_close_252'] = rev_close.rolling(window=252, min_periods=1).max().iloc[::-1]
    
    sdf['symbol'] = sym
    sdf = sdf.reset_index()
    dfs.append(sdf)

df = pd.concat(dfs).sort_values('date').reset_index(drop=True)
del dfs
del prices_df

df_indexed = df.set_index(['symbol', 'date']).sort_index()

# 1. Calculate Observable Opportunity Set
# Every instance where a stock doubled in a rolling 252-session window.
# We want to count independent campaigns.
print("Calculating Observable Opportunity Set...")
opp_set_count = 0
for sym, sdf in df.groupby('symbol'):
    # Find all dates where forward 252d max >= 2.0 * next_open
    sdf = sdf.dropna(subset=['next_open', 'max_close_252'])
    hits = sdf[sdf['max_close_252'] >= 2.0 * sdf['next_open']]
    # To count campaigns (non-overlapping), we can iterate and skip forward 252 days from each hit
    last_hit_idx = -252
    for i in range(len(hits)):
        idx = hits.index[i]
        # Using iloc index in original sdf to skip
        pos = sdf.index.get_loc(idx)
        if pos >= last_hit_idx + 252:
            opp_set_count += 1
            last_hit_idx = pos

print(f"Total Observable R100 Opportunity Set (non-overlapping campaigns): {opp_set_count}")

# 2. Evaluate Signals
results = []
for _, row in breakouts.iterrows():
    sym = row['symbol']
    s_date = row['signal_date']
    st = row['strategy']
    
    try:
        # Get data from signal date onwards
        idx_loc = df_indexed.index.get_loc((sym, s_date))
        # Wait, get_loc can fail if date not exactly matching, but they should match
    except KeyError:
        continue
        
    # Get the slice of data for this symbol starting from signal date
    sym_df = df[df['symbol'] == sym]
    sym_df = sym_df[sym_df['date'] >= s_date].copy()
    if len(sym_df) < 2:
        continue
        
    sig_row = sym_df.iloc[0]
    exec_price = sig_row['next_open']
    if pd.isna(exec_price): continue
    
    # Get features for cohorts
    rs_90d = sig_row.get('rs_90d', np.nan)
    vol = sig_row.get('volume', np.nan)
    avg_vol = sig_row.get('avg_volume_20d', np.nan)
    vol_ratio = vol / avg_vol if avg_vol and avg_vol > 0 else np.nan
    ema_200_slope = sig_row.get('ema_200_slope_20', np.nan)
    ema_50 = sig_row.get('ema_50', np.nan)
    dist_ema_50 = (sig_row['close'] / ema_50) - 1 if ema_50 and ema_50 > 0 else np.nan
    
    # Look forward 126 and 252 days
    df_126 = sym_df.iloc[1:127]
    df_252 = sym_df.iloc[1:253]
    
    r50_target = exec_price * 1.50
    r100_target = exec_price * 2.00
    
    r50_hit = df_126['close'] >= r50_target
    r100_hit = df_252['close'] >= r100_target
    
    hit_r50 = r50_hit.any()
    hit_r100 = r100_hit.any()
    
    time_r50 = np.nan
    if hit_r50:
        time_r50 = (df_126[r50_hit].iloc[0]['date'] - s_date).days
        
    time_r100 = np.nan
    if hit_r100:
        time_r100 = (df_252[r100_hit].iloc[0]['date'] - s_date).days
        
    mae = df_252['low'].min() / exec_price - 1
    mfe = df_252['high'].max() / exec_price - 1
    
    is_d2_w = False
    if st == 'D2':
        # Check if D2->W
        # D2 is valid until row.close < row.d2_quit_lvl
        # Check if there is a Friday where row.close > row.w_quit_lvl before invalidation
        invalidated = False
        w_validated = False
        for _, fut_row in sym_df.iloc[1:].iterrows():
            if fut_row['close'] < fut_row['d2_quit_lvl']:
                break # Invalidated before W validation
            if fut_row['date'].weekday() == 4 and fut_row['close'] > fut_row['w_quit_lvl']:
                w_validated = True
                break
        is_d2_w = w_validated

    results.append({
        'symbol': sym,
        'strategy': st,
        'is_d2_w': is_d2_w,
        'hit_r50': hit_r50,
        'hit_r100': hit_r100,
        'time_r50': time_r50,
        'time_r100': time_r100,
        'mae': mae,
        'mfe': mfe,
        'rs_90d': rs_90d,
        'vol_ratio': vol_ratio,
        'ema_200_slope': ema_200_slope,
        'dist_ema_50': dist_ema_50
    })

res_df = pd.DataFrame(results)

# Create D2->W strategy copies
d2w_df = res_df[(res_df['strategy'] == 'D2') & (res_df['is_d2_w'] == True)].copy()
d2w_df['strategy'] = 'D2_W'
res_df = pd.concat([res_df, d2w_df])

print("\n--- PERFORMANCE BY STRATEGY ---")
summary = []
for strat in ['D2', 'W', 'D2_W']:
    sdf = res_df[res_df['strategy'] == strat]
    n = len(sdf)
    r50_count = sdf['hit_r50'].sum()
    r100_count = sdf['hit_r100'].sum()
    r50_rate = r50_count / n if n > 0 else 0
    r100_rate = r100_count / n if n > 0 else 0
    med_time_r50 = sdf['time_r50'].median()
    med_time_r100 = sdf['time_r100'].median()
    med_mae = sdf['mae'].median()
    med_mfe = sdf['mfe'].median()
    # Campaign coverage estimate: simply hits / total universe opportunities
    coverage = r100_count / opp_set_count if opp_set_count > 0 else 0
    
    summary.append({
        'Strategy': strat,
        'Signals': n,
        'R50 Hit Rate': f"{r50_rate*100:.1f}%",
        'R100 Hit Rate': f"{r100_rate*100:.1f}%",
        'Median Time R50': f"{med_time_r50:.0f}d",
        'Median Time R100': f"{med_time_r100:.0f}d",
        'Median MAE': f"{med_mae*100:.1f}%",
        'Median MFE': f"{med_mfe*100:.1f}%",
        'R100 Coverage': f"{coverage*100:.1f}%"
    })

sum_df = pd.DataFrame(summary)
print(sum_df.to_markdown(index=False))

print("\n--- D2 COHORT DESCRIPTIVES (R100 HIT RATE BY QUARTILE) ---")
d2_df = res_df[res_df['strategy'] == 'D2']
for col in ['rs_90d', 'vol_ratio', 'ema_200_slope', 'dist_ema_50']:
    print(f"\n{col} Quartiles:")
    try:
        d2_df['q'] = pd.qcut(d2_df[col], 4, labels=['Q1(Low)', 'Q2', 'Q3', 'Q4(High)'])
        grp = d2_df.groupby('q').agg(
            Signals=('hit_r100', 'count'),
            R100_Hits=('hit_r100', 'sum')
        )
        grp['Hit Rate'] = (grp['R100_Hits'] / grp['Signals'] * 100).round(1).astype(str) + '%'
        print(grp.to_markdown())
    except Exception as e:
        print(f"Error calculating quartiles for {col}: {e}")

# Save full report
with open('cai_candidate_quality_report.md', 'w') as f:
    f.write("# CAI Candidate Quality Study\n\n")
    f.write("> **Survivorship Bias Disclaimer:** The results of this study represent the **Observable Opportunity Set** within the available historical 892-symbol dataset. Because this dataset contains survivorship bias, the findings serve as observable-universe evidence of signal quality and must not be interpreted as a market-wide estimate.\n\n")
    f.write(f"**Total Observable R100 Opportunity Set (non-overlapping campaigns):** {opp_set_count}\n\n")
    f.write("## Overall Strategy Performance\n\n")
    f.write(sum_df.to_markdown(index=False) + "\n\n")
    
    f.write("## D2 Descriptive Point-in-Time Cohorts\n\n")
    for col in ['rs_90d', 'vol_ratio', 'ema_200_slope', 'dist_ema_50']:
        f.write(f"### {col}\n")
        try:
            d2_df['q'] = pd.qcut(d2_df[col], 4, labels=['Q1(Low)', 'Q2', 'Q3', 'Q4(High)'])
            grp = d2_df.groupby('q').agg(
                Signals=('hit_r100', 'count'),
                R100_Hits=('hit_r100', 'sum')
            )
            grp['Hit Rate'] = (grp['R100_Hits'] / grp['Signals'] * 100).round(1).astype(str) + '%'
            f.write(grp.to_markdown() + "\n\n")
        except Exception:
            f.write("Not enough variance for quartiles.\n\n")
