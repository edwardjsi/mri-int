import boto3, json, psycopg2, yfinance as yf, pandas as pd, time
from datetime import datetime, timedelta

client = boto3.client('secretsmanager', region_name='ap-south-1')
secret = json.loads(client.get_secret_value(
    SecretId='arn:aws:secretsmanager:ap-south-1:251876202726:secret:mri-dev-db-credentials-doP9bL'
)['SecretString'])
conn = psycopg2.connect(host='localhost', port=5433, dbname=secret['dbname'],
                        user=secret['username'], password=secret['password'])
cur = conn.cursor()

# Get all symbols from universe
cur.execute("SELECT symbol FROM universe WHERE active=TRUE ORDER BY symbol")
SYMBOLS = [r[0] for r in cur.fetchall()]
print(f"Total symbols to ingest: {len(SYMBOLS)}")

# --- Get already ingested symbols ---
cur.execute("SELECT DISTINCT symbol FROM daily_prices")
already_done = set(r[0] for r in cur.fetchall())
SYMBOLS = [s for s in SYMBOLS if s not in already_done]
print(f"Already ingested: {len(already_done)} | Remaining: {len(SYMBOLS)}")

END_DATE   = datetime.today().strftime('%Y-%m-%d')
START_DATE = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')

inserted = 0
skipped  = 0
failed   = 0

for i, symbol in enumerate(SYMBOLS, 1):
    try:
        time.sleep(2)
        df = yf.download(symbol, start=START_DATE, end=END_DATE,
                         progress=False, auto_adjust=True)
        if df.empty:
            print(f"  [{i}/{len(SYMBOLS)}] ⚠ No data: {symbol}")
            skipped += 1
            continue

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = pd.to_datetime(df.index)

        rows = 0
        for date, row in df.iterrows():
            cur.execute('''
                INSERT INTO daily_prices (symbol, date, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, date) DO NOTHING
            ''', (symbol, date.date(), float(row['Open']), float(row['High']),
                  float(row['Low']), float(row['Close']), int(row['Volume'])))
            rows += 1
            inserted += 1
        conn.commit()
        print(f"  [{i}/{len(SYMBOLS)}] ✅ {symbol}: {rows} rows")
    except Exception as e:
        print(f"  [{i}/{len(SYMBOLS)}] ❌ {symbol}: {e}")
        failed += 1

print(f"\n🎉 Done. Inserted: {inserted} | Skipped: {skipped} | Failed: {failed}")
cur.close()
conn.close()
