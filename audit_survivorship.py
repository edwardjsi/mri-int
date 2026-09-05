import pandas as pd
df = pd.read_csv('backups/20260304/daily_prices.csv', usecols=['symbol', 'date'], low_memory=False)
df['date'] = pd.to_datetime(df['date'])
end_dates = df.groupby('symbol')['date'].max()
last_date = df['date'].max()
dead_stocks = end_dates[end_dates < last_date - pd.Timedelta(days=30)]
print(f"Total symbols: {len(end_dates)}")
print(f"Latest overall date: {last_date}")
print(f"Symbols with last trading date > 30 days before latest date: {len(dead_stocks)}")
print("Sample dead stocks (if any):", dead_stocks.head())
