import boto3, json, psycopg2, pandas as pd, pandas_ta as ta
import warnings
warnings.filterwarnings('ignore')

# --- DB connection ---
client = boto3.client('secretsmanager', region_name='ap-south-1')
secret = json.loads(client.get_secret_value(
    SecretId='arn:aws:secretsmanager:ap-south-1:251876202726:secret:mri-dev-db-credentials-doP9bL'
)['SecretString'])
conn = psycopg2.connect(host='localhost', port=5433, dbname=secret['dbname'],
                        user=secret['username'], password=secret['password'])
cur = conn.cursor()

# --- Create tables ---
cur.execute('''
    CREATE TABLE IF NOT EXISTS market_regime (
        date        DATE PRIMARY KEY,
        nifty_close NUMERIC(12,4),
        sma_200     NUMERIC(12,4),
        regime      VARCHAR(10)
    );

    CREATE TABLE IF NOT EXISTS stock_scores (
        symbol      VARCHAR(20),
        date        DATE,
        adx         NUMERIC(8,4),
        rsi         NUMERIC(8,4),
        high_52w_pct NUMERIC(8,4),
        score       INTEGER,
        PRIMARY KEY (symbol, date)
    );
''')
conn.commit()
print("✅ Tables created")

# --- Market Regime: Nifty 50 SMA 200 ---
df_nifty = pd.read_sql(
    "SELECT date, close FROM daily_prices WHERE symbol='^NSEI' ORDER BY date",
    conn, parse_dates=['date']
)
df_nifty.set_index('date', inplace=True)
df_nifty['sma_200'] = df_nifty['close'].rolling(200).mean()
df_nifty['regime']  = df_nifty.apply(
    lambda r: 'BULL' if pd.notna(r['sma_200']) and r['close'] > r['sma_200'] else 'BEAR', axis=1
)

for date, row in df_nifty.iterrows():
    if pd.isna(row['sma_200']):
        continue
    cur.execute('''
        INSERT INTO market_regime (date, nifty_close, sma_200, regime)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (date) DO UPDATE
        SET nifty_close=EXCLUDED.nifty_close, sma_200=EXCLUDED.sma_200, regime=EXCLUDED.regime
    ''', (date.date(), float(row['close']), float(row['sma_200']), row['regime']))
conn.commit()
print(f"✅ Market regime computed: {len(df_nifty.dropna())} rows")

# --- Stock Scores ---
SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS", "TITAN.NS",
    "SUNPHARMA.NS", "WIPRO.NS", "ULTRACEMCO.NS", "BAJFINANCE.NS", "NESTLEIND.NS"
]

for symbol in SYMBOLS:
    df = pd.read_sql(
        f"SELECT date, high, low, close FROM daily_prices WHERE symbol=%s ORDER BY date",
        conn, params=(symbol,), parse_dates=['date']
    )
    if len(df) < 28:
        print(f"  ⚠ {symbol}: insufficient data")
        continue

    df.set_index('date', inplace=True)
    df['adx'] = ta.adx(df['high'], df['low'], df['close'], length=14)['ADX_14']
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['high_52w'] = df['high'].rolling(252, min_periods=1).max()
    df['high_52w_pct'] = (df['close'] / df['high_52w']) * 100

    def score_row(r):
        s = 0
        if pd.notna(r['adx'])         and r['adx'] > 25:          s += 1
        if pd.notna(r['rsi'])         and 50 < r['rsi'] < 70:     s += 1
        if pd.notna(r['high_52w_pct']) and r['high_52w_pct'] > 90: s += 1
        return s

    df['score'] = df.apply(score_row, axis=1)

    rows_inserted = 0
    for date, row in df.iterrows():
        if pd.isna(row['adx']) or pd.isna(row['rsi']):
            continue
        cur.execute('''
            INSERT INTO stock_scores (symbol, date, adx, rsi, high_52w_pct, score)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, date) DO UPDATE
            SET adx=EXCLUDED.adx, rsi=EXCLUDED.rsi,
                high_52w_pct=EXCLUDED.high_52w_pct, score=EXCLUDED.score
        ''', (symbol, date.date(), float(row['adx']), float(row['rsi']),
              float(row['high_52w_pct']), int(row['score'])))
        rows_inserted += 1
    conn.commit()
    print(f"  ✅ {symbol}: {rows_inserted} scored rows")

# --- Summary ---
cur.execute("SELECT regime, COUNT(*) FROM market_regime GROUP BY regime")
print("\n📊 Market Regime Summary:")
for r in cur.fetchall():
    print(f"   {r[0]}: {r[1]} days")

cur.execute("SELECT symbol, ROUND(AVG(score),2) as avg_score FROM stock_scores GROUP BY symbol ORDER BY avg_score DESC LIMIT 5")
print("\n🏆 Top 5 Stocks by Avg Score:")
for r in cur.fetchall():
    print(f"   {r[0]}: {r[1]}")

cur.close()
conn.close()
