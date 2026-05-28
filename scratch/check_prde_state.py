import os, sys
sys.path.insert(0, '/home/immanuels/Desktop/mri-int')
from engine_core.db import get_connection

conn = get_connection()
cur = conn.cursor()

cur.execute('SELECT symbol FROM watchlist LIMIT 20')
watchlist = [r[0] for r in cur.fetchall()]
print(f'Watchlist symbols ({len(watchlist)}): {watchlist}')

cur.execute('SELECT COUNT(*) FROM prde_companies')
print(f'prde_companies rows: {cur.fetchone()[0]}')

if watchlist:
    ph = ','.join(['%s'] * len(watchlist))
    cur.execute(f'SELECT symbol, COUNT(*) FROM fundamental_financials WHERE symbol IN ({ph}) GROUP BY symbol', watchlist)
    print('fundamental_financials coverage:')
    for sym, cnt in cur.fetchall():
        print(f'  {sym}: {cnt} years')
    cur.execute(f'SELECT symbol, company_name, industry FROM stock_sectors WHERE symbol IN ({ph})', watchlist)
    print('stock_sectors:')
    for sym, name, ind in cur.fetchall():
        print(f'  {sym}: {name} ({ind})')

cur.execute('SELECT COUNT(DISTINCT symbol), COUNT(*) FROM fundamental_financials')
u, t = cur.fetchone()
print(f'\nfundamental_financials: {u} symbols, {t} rows')

cur.execute('SELECT COUNT(*) FROM prde_feature_snapshots')
print(f'prde_feature_snapshots: {cur.fetchone()[0]} rows')

cur.close()
conn.close()
