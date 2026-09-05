import pandas as pd
df = pd.read_csv('backups/20260304/daily_prices.csv', usecols=['symbol', 'date'], low_memory=False)
df['date'] = pd.to_datetime(df['date'])
end_dates = df.groupby('symbol')['date'].max()
years = end_dates.dt.year.value_counts().sort_index()
print(years)
