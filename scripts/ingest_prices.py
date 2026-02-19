import boto3, json, psycopg2, yfinance as yf, pandas as pd, time
from datetime import datetime, timedelta

client = boto3.client('secretsmanager', region_name='ap-south-1')
secret = json.loads(client.get_secret_value(
    SecretId='arn:aws:secretsmanager:ap-south-1:251876202726:secret:mri-dev-db-credentials-doP9bL'
)['SecretString'])
conn = psycopg2.connect(
    host='localhost', port=5433,
    dbname=secret['dbname'], user=secret['username'], password=secret['password']
)
cur = conn.cursor()

SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "TITAN.NS",
    "SUNPHARMA.NS", "WIPRO.NS", "ULTRACEMCO.NS", "BAJFINANCE.NS", "NESTLEIND.NS"
]

END_DATE   = datetime.today().strftime('%Y-%m-%d')
START_DATE = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')

inserted = 0
for symbol in SYMBOLS:
    try:
        time.sleep(2)
        df = yf.download(symbol, start=START_DATE, end=END_DATE, progress=False, auto_adjust=True)
        if df.empty:
            print(f"  ⚠ No data for {symbol}")
            continue

        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.index = pd.to_datetime(df.index)

        for date, row in df.iterrows():
            cur.execute('''
                INSERT INTO daily_prices (symbol, date, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol, date) DO NOTHING
            ''', (symbol, date.date(), float(row['Open']), float(row['High']),
                  float(row['Low']), float(row['Close']), int(row['Volume'])))
            inserted += 1
        conn.commit()
        print(f"  ✅ {symbol}: {len(df)} rows loaded")
    except Exception as e:
        print(f"  ❌ {symbol}: {e}")

print(f"\n🎉 Total rows inserted: {inserted}")
cur.close()
conn.close()
