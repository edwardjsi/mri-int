"""Debug script to check regime overlap."""
import os
import psycopg2
import pandas as pd

def get_conn():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

conn = get_conn()
c = conn.cursor()

# Fetch index prices
c.execute("SELECT date, close FROM index_prices WHERE symbol = 'NIFTY50' AND date >= '2026-02-13' ORDER BY date")
idx = pd.DataFrame(c.fetchall(), columns=['date','close'])
idx['close'] = idx['close'].astype(float)
idx['ema_50'] = idx['close'].ewm(span=50, adjust=False).mean()
idx['ema_200'] = idx['close'].ewm(span=200, adjust=False).mean()
idx['diff'] = idx['ema_50'] - idx['ema_200']
idx['band'] = (idx['close'] * 0.02).rolling(20).mean()

def regime(row):
    if pd.isna(row['ema_50']) or pd.isna(row['ema_200']):
        return 'NEUTRAL'
    diff = row['ema_50'] - row['ema_200']
    band = row['band'] if pd.notna(row['band']) else 0
    if diff > band:
        return 'BULLISH'
    elif diff < -band:
        return 'BEARISH'
    return 'NEUTRAL'

idx['regime'] = idx.apply(regime, axis=1)

# Fetch stock_scores distinct dates
c.execute("SELECT DISTINCT date FROM stock_scores WHERE date >= '2026-02-13' ORDER BY date")
ss_dates = set()
for r in c.fetchall():
    d = r['date']
    ds = d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d)
    ss_dates.add(ds)

print(f'stock_scores dates: {len(ss_dates)}')
print('All index dates in window:')
print(idx['regime'].value_counts())

idx['date_str'] = idx['date'].apply(lambda d: d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d))
idx_ss = idx[idx['date_str'].isin(ss_dates)]
print('Index dates overlapping with stock_scores:')
print(idx_ss['regime'].value_counts())

conn.close()
