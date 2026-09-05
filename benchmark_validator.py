import pandas as pd
import numpy as np
import os

benchmark_files = {
    'Nifty 500 TRI': 'benchmarks/NSE500TRI.csv'
}

strategy_files = {
    'W': 'pv_W.csv',
    'D2': 'pv_D2.csv',
    'D2_W': 'pv_D2_W.csv'
}

def load_benchmark(name, path):
    df = pd.read_csv(path)
    tri_col = [c for c in df.columns if 'Total Returns Index' in c or 'TRI' in c.upper()][0]
    date_col = [c for c in df.columns if 'Date' in c or 'date' in c.lower()][0]
    
    df['date'] = pd.to_datetime(df[date_col], format='mixed', dayfirst=True)
    df = df.sort_values('date').reset_index(drop=True)
    raw_tri = df[tri_col].astype(str).str.replace(',', '').str.strip()
    df['close'] = pd.to_numeric(raw_tri, errors='coerce')
    return df.dropna(subset=['close'])[['date', 'close']]

def calc_metrics(series, start_val, name=""):
    if len(series) < 2: return {}
    
    days = (series['date'].max() - series['date'].min()).days
    if days == 0: return {}
    
    end_val = series['close'].iloc[-1]
    total_ret = (end_val / start_val) - 1
    cagr = (end_val / start_val) ** (365.25 / days) - 1
    
    peak = series['close'].cummax()
    dd = ((series['close'] - peak) / peak)
    max_dd = dd.min()
    
    daily_ret = series['close'].pct_change().dropna()
    vol = daily_ret.std() * np.sqrt(252)
    
    sharpe = (cagr - 0.05) / vol if vol > 0 else 0
    downside_vol = daily_ret[daily_ret < 0].std() * np.sqrt(252)
    sortino = (cagr - 0.05) / downside_vol if downside_vol > 0 else 0
    
    # Calendar year returns
    series['year'] = series['date'].dt.year
    yearly = series.groupby('year')['close'].last()
    yearly_ret = yearly.pct_change()
    first_year = series['year'].iloc[0]
    yearly_ret.loc[first_year] = (yearly.loc[first_year] / start_val) - 1
    
    return {
        'total_ret': total_ret,
        'cagr': cagr,
        'max_dd': max_dd,
        'vol': vol,
        'sharpe': sharpe,
        'sortino': sortino,
        'yearly': yearly_ret
    }

benchmarks = {name: load_benchmark(name, path) for name, path in benchmark_files.items()}

strategies = {}
for name, path in strategy_files.items():
    sdf = pd.read_csv(path)
    sdf['date'] = pd.to_datetime(sdf['date'])
    sdf = sdf.rename(columns={'pv': 'close'})
    strategies[name] = sdf

print("\n--- BENCHMARK COMPARISONS ---")
for b_name, b_df in benchmarks.items():
    for s_name, s_df in strategies.items():
        # Find maximum common period
        common_start = max(b_df['date'].min(), s_df['date'].min())
        common_end = min(b_df['date'].max(), s_df['date'].max())
        
        b_slice = b_df[(b_df['date'] >= common_start) & (b_df['date'] <= common_end)].copy()
        s_slice = s_df[(s_df['date'] >= common_start) & (s_df['date'] <= common_end)].copy()
            
        b_start_val = b_slice['close'].iloc[0]
        s_start_val = s_slice['close'].iloc[0]
        
        b_metrics = calc_metrics(b_slice, b_start_val, b_name)
        s_metrics = calc_metrics(s_slice, s_start_val, s_name)
        
        print(f"\n[{s_name} vs {b_name}] Common Period: {common_start.date()} to {common_end.date()}")
        print(f"{'Metric':<25}{s_name:<20}{b_name:<20}{'Excess':<20}")
        print("-" * 80)
        print(f"{'CAGR':<25}{s_metrics['cagr']*100:<20.2f}{b_metrics['cagr']*100:<20.2f}{(s_metrics['cagr'] - b_metrics['cagr'])*100:<20.2f}")
        print(f"{'Total Return':<25}{s_metrics['total_ret']*100:<20.2f}{b_metrics['total_ret']*100:<20.2f}{(s_metrics['total_ret'] - b_metrics['total_ret'])*100:<20.2f}")
        print(f"{'Max Drawdown':<25}{s_metrics['max_dd']*100:<20.2f}{b_metrics['max_dd']*100:<20.2f}{(s_metrics['max_dd'] - b_metrics['max_dd'])*100:<20.2f}")
        print(f"{'Volatility':<25}{s_metrics['vol']*100:<20.2f}{b_metrics['vol']*100:<20.2f}{(s_metrics['vol'] - b_metrics['vol'])*100:<20.2f}")
        print(f"{'Sharpe':<25}{s_metrics['sharpe']:<20.2f}{b_metrics['sharpe']:<20.2f}{s_metrics['sharpe'] - b_metrics['sharpe']:<20.2f}")
        print(f"{'Sortino':<25}{s_metrics['sortino']:<20.2f}{b_metrics['sortino']:<20.2f}{s_metrics['sortino'] - b_metrics['sortino']:<20.2f}")
        
        print(f"\n{s_name} Calendar Returns:")
        yearly_s = s_metrics['yearly']
        yearly_b = b_metrics['yearly']
        years = sorted(list(yearly_s.index))
        
        # Only print first 2 and last 2 years for brevity, or all? Let's just print a summary or list them
        print(", ".join([f"{y}: {yearly_s.get(y, 0)*100:.1f}%" for y in years[:5]]) + " ... " + ", ".join([f"{y}: {yearly_s.get(y, 0)*100:.1f}%" for y in years[-5:]]))

