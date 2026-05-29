import sys
sys.path.insert(0, '/home/immanuels/Desktop/mri-int')
from engine_core.db import get_connection

conn = get_connection()
cur = conn.cursor()

# 1. Watchlist schema + data
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='client_watchlist'")
cols = [r['column_name'] for r in cur.fetchall()]
print(f'client_watchlist columns: {cols}')

cur.execute("SELECT * FROM client_watchlist LIMIT 15")
rows = cur.fetchall()
print(f'\nclient_watchlist rows ({len(rows)}):')
for r in rows:
    print(f'  {dict(r)}')

# 2. PRDE companies
cur.execute("SELECT COUNT(*) FROM prde_companies")
print(f'\nprde_companies: {cur.fetchone()["count"]} rows')

# 3. fundamental_financials - top symbols
cur.execute("SELECT symbol, COUNT(*) as cnt FROM fundamental_financials GROUP BY symbol ORDER BY cnt DESC LIMIT 10")
print('\nfundamental_financials top symbols:')
for r in cur.fetchall():
    print(f'  {r["symbol"]}: {r["cnt"]} years')

cur.execute("SELECT COUNT(DISTINCT symbol) FROM fundamental_financials")
print(f'\nfundamental_financials unique symbols: {cur.fetchone()["count"]}')

cur.close()
conn.close()
