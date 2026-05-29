import sys
sys.path.insert(0, '/home/immanuels/Desktop/mri-int')
from engine_core.db import get_connection

conn = get_connection()
cur = conn.cursor()

# fundamental_financials schema
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='fundamental_financials' ORDER BY ordinal_position")
print('fundamental_financials columns:')
for r in cur.fetchall():
    print(f'  {r["column_name"]} ({r["data_type"]})')

# prde_financials_annual schema
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='prde_financials_annual' ORDER BY ordinal_position")
print('\nprde_financials_annual columns:')
for r in cur.fetchall():
    print(f'  {r["column_name"]} ({r["data_type"]})')

# prde_ratios_annual schema
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='prde_ratios_annual' ORDER BY ordinal_position")
print('\nprde_ratios_annual columns:')
for r in cur.fetchall():
    print(f'  {r["column_name"]} ({r["data_type"]})')

# Sample fundamental_financials row for TCS
cur.execute("SELECT * FROM fundamental_financials WHERE symbol='TCS' LIMIT 1")
row = cur.fetchone()
if row:
    print(f'\nSample fundamental_financials (TCS): {dict(row)}')

# Sample prde_financials_annual row for TCS
cur.execute("SELECT f.* FROM prde_financials_annual f JOIN prde_companies c ON c.id = f.company_id WHERE c.ticker = 'TCS' LIMIT 1")
row = cur.fetchone()
if row:
    print(f'\nSample prde_financials_annual (TCS): {dict(row)}')

cur.close()
conn.close()
