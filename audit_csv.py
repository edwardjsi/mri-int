import pandas as pd
import os

df = pd.read_csv('backups/20260304/daily_prices.csv')
print("Columns:", list(df.columns))
print("Total rows:", len(df))
print("Earliest date:", df['date'].min())
print("Latest date:", df['date'].min())
print("Latest date:", df['date'].max())
print("Number of symbols:", df['symbol'].nunique())

try:
    index_df = pd.read_csv('backups/20260304/index_prices.csv')
    print("\nIndex Prices Columns:", list(index_df.columns))
    print("Indices:", index_df['symbol'].unique())
except Exception as e:
    print("Error reading index_prices.csv:", e)
