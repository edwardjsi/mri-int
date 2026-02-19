import boto3, json, psycopg2, pandas as pd, requests, io

client = boto3.client('secretsmanager', region_name='ap-south-1')
secret = json.loads(client.get_secret_value(
    SecretId='arn:aws:secretsmanager:ap-south-1:251876202726:secret:mri-dev-db-credentials-doP9bL'
)['SecretString'])
conn = psycopg2.connect(host='localhost', port=5433, dbname=secret['dbname'],
                        user=secret['username'], password=secret['password'])
cur = conn.cursor()

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

urls = [
    ('SMALLCAP', 'https://archives.nseindia.com/content/indices/ind_niftysmallcap250list.csv'),
    ('MIDCAP',   'https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv'),
    ('LARGECAP', 'https://archives.nseindia.com/content/indices/ind_nifty500list.csv'),
]

cur.execute("TRUNCATE universe")
conn.commit()

# Build master dict — later entries override segment (LARGECAP wins)
master = {}
for segment, url in urls:
    try:
        r = requests.get(url, headers=headers, timeout=10)
        df = pd.read_csv(io.StringIO(r.text))
        for _, row in df.iterrows():
            symbol = str(row['Symbol']).strip() + '.NS'
            master[symbol] = {
                'company_name': str(row['Company Name']).strip(),
                'sector':       str(row['Industry']).strip(),
                'segment':      segment
            }
        print(f"  ✅ {segment}: {len(df)} stocks fetched")
    except Exception as e:
        print(f"  ❌ {segment}: {e}")

# Insert all unique stocks
for symbol, data in master.items():
    cur.execute('''
        INSERT INTO universe (symbol, company_name, sector, segment)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (symbol) DO NOTHING
    ''', (symbol, data['company_name'], data['sector'], data['segment']))

conn.commit()

cur.execute("SELECT COUNT(*) FROM universe")
print(f"\n🎉 Total unique stocks: {cur.fetchone()[0]}")

cur.execute("SELECT segment, COUNT(*) FROM universe GROUP BY segment ORDER BY segment")
print("📊 Segment breakdown:")
for r in cur.fetchall():
    print(f"   {r[0]}: {r[1]} stocks")

cur.close()
conn.close()
