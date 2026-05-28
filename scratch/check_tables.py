import os, sys
sys.path.insert(0, '/home/immanuels/Desktop/mri-int')
from engine_core.db import get_connection

conn = get_connection()
cur = conn.cursor()

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE '%watch%'")
print('Watchlist:', [r['table_name'] for r in cur.fetchall()])

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE '%prde%'")
print('PRDE:', [r['table_name'] for r in cur.fetchall()])

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE '%aae%'")
print('AAE:', [r['table_name'] for r in cur.fetchall()])

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE '%fundamental%'")
print('Fund:', [r['table_name'] for r in cur.fetchall()])

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE '%sector%'")
print('Sector:', [r['table_name'] for r in cur.fetchall()])

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE '%stock%'")
print('Stock:', [r['table_name'] for r in cur.fetchall()])

cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
all_tables = sorted([r['table_name'] for r in cur.fetchall()])
print(f'\nAll ({len(all_tables)}):')
for t in all_tables:
    print(f'  {t}')

cur.close()
conn.close()
