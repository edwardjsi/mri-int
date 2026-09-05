import pandas as pd
import os

file_path = '/home/immanuels/Desktop/mri-int/benchmarks/NSE500TRI.csv'

if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    exit(1)

size = os.path.getsize(file_path)
df = pd.read_csv(file_path)

print(f"File: {file_path}")
print(f"Format: CSV")
print(f"Size: {size/1024:.2f} KB")
print(f"Rows: {len(df)}")
print(f"Columns: {list(df.columns)}")

try:
    df['Date'] = pd.to_datetime(df['Date'])
    print(f"Earliest Date: {df['Date'].min().strftime('%Y-%m-%d')}")
    print(f"Latest Date: {df['Date'].max().strftime('%Y-%m-%d')}")
    print(f"Unique Trading Dates: {df['Date'].nunique()}")
except:
    print("Could not parse dates.")

print(f"Unique Symbols: {df['IndexName'].nunique() if 'IndexName' in df.columns else 'N/A'}")
if 'IndexName' in df.columns:
    print(df['IndexName'].unique())

