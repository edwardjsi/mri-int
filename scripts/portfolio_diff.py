import os
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=RealDictCursor)
cur = conn.cursor()

# 1. MRI Portfolio
cur.execute("SELECT DISTINCT symbol FROM cai_position WHERE status = 'ACTIVE'")
mri_portfolio = {row['symbol'] for row in cur.fetchall()}

# 2. Zerodha Holdings
cur.execute("SELECT DISTINCT symbol FROM client_external_holdings")
zerodha_holdings = {row['symbol'] for row in cur.fetchall()}

# 3. Current cai_positions (the table my test touched)
cur.execute("SELECT DISTINCT symbol FROM cai_positions WHERE status = 'ACTIVE'")
cai_positions = {row['symbol'] for row in cur.fetchall()}

# 4. Current configs
cur.execute("SELECT DISTINCT symbol FROM cai_alert_config_versions")
cai_configs = {row['symbol'] for row in cur.fetchall()}

print("1. MRI-managed portfolio (cai_position):", sorted(list(mri_portfolio)))
print("2. Actual Zerodha holdings (client_external_holdings):", sorted(list(zerodha_holdings)))
print("3. Current cai_positions (v2 test table):", sorted(list(cai_positions)))
print("4. Current cai_alert_config_versions:", sorted(list(cai_configs)))

conn.close()
