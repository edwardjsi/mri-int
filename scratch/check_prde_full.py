import sys
sys.path.insert(0, '/home/immanuels/Desktop/mri-int')
from engine_core.db import get_connection

conn = get_connection()
cur = conn.cursor()

# What's in prde_companies?
cur.execute("SELECT * FROM prde_companies ORDER BY id")
print('prde_companies:')
for r in cur.fetchall():
    print(f'  {r["id"]}: {r["ticker"]} - {r["name"]} ({r["sector"]}/{r["industry"]}) active={r["is_active"]}')

# Check if any prde_financials_annual data exists
cur.execute("SELECT COUNT(*) FROM prde_financials_annual")
print(f'\nprde_financials_annual: {cur.fetchone()["count"]} rows')

cur.execute("SELECT COUNT(*) FROM prde_ratios_annual")
print(f'prde_ratios_annual: {cur.fetchone()["count"]} rows')

cur.execute("SELECT COUNT(*) FROM prde_feature_snapshots")
print(f'prde_feature_snapshots: {cur.fetchone()["count"]} rows')

# Watchlist distinct symbols
cur.execute("SELECT DISTINCT symbol FROM client_watchlist ORDER BY symbol")
wl_symbols = [r['symbol'] for r in cur.fetchall()]
print(f'\nWatchlist distinct symbols ({len(wl_symbols)}): {wl_symbols}')

# Check fundamental_financials for watchlist symbols
print('\nfundamental_financials for watchlist:')
for sym in wl_symbols:
    cur.execute("SELECT COUNT(*) FROM fundamental_financials WHERE symbol = %s", (sym,))
    cnt = cur.fetchone()['count']
    if cnt > 0:
        print(f'  {sym}: {cnt} years')

cur.close()
conn.close()
