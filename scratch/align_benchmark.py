import pandas as pd
import numpy as np

# Load benchmark
bm = pd.read_csv('/home/immanuels/Desktop/mri-int/benchmarks/NSE500TRI.csv')
bm['Date'] = pd.to_datetime(bm['Date'])
bm = bm.sort_values('Date').reset_index(drop=True)

# Load stocks
stocks = pd.read_csv('/home/immanuels/Desktop/mri-int/backups/20260304/daily_prices.csv', usecols=['symbol', 'date', 'close'])
stocks['date'] = pd.to_datetime(stocks['date'])

# Unique trading dates in stocks
stock_dates = pd.Series(stocks['date'].unique()).sort_values().reset_index(drop=True)

bm_dates = set(bm['Date'])
st_dates = set(stock_dates)

missing_in_bm = st_dates - bm_dates
missing_in_st = bm_dates - st_dates

print(f"Benchmark Earliest Date: {bm['Date'].min().strftime('%Y-%m-%d')}")
print(f"Benchmark Latest Date: {bm['Date'].max().strftime('%Y-%m-%d')}")
print(f"Stocks Earliest Date: {stock_dates.min().strftime('%Y-%m-%d')}")
print(f"Stocks Latest Date: {stock_dates.max().strftime('%Y-%m-%d')}")

overlap_start = max(bm['Date'].min(), stock_dates.min())
overlap_end = min(bm['Date'].max(), stock_dates.max())
print(f"Overlap Period: {overlap_start.strftime('%Y-%m-%d')} to {overlap_end.strftime('%Y-%m-%d')}")

overlap_st_dates = set([d for d in st_dates if overlap_start <= d <= overlap_end])
overlap_bm_dates = set([d for d in bm_dates if overlap_start <= d <= overlap_end])

missing = overlap_st_dates - overlap_bm_dates
print(f"Number of overlapping stock trading dates: {len(overlap_st_dates)}")
print(f"Number of overlapping stock dates missing from benchmark: {len(missing)}")

if len(missing) > 0:
    print("Sample missing dates in benchmark:")
    print(sorted(list(missing))[:10])
