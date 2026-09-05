import os
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=RealDictCursor)
cur = conn.cursor()

# 1. Actual MRI-managed portfolio symbols
# Let's check 'client_portfolio' or 'holdings'
cur.execute("SELECT DISTINCT symbol FROM client_portfolio")
mri_portfolio_symbols = {row['symbol'] for row in cur.fetchall()}
print(f"MRI Portfolio: {mri_portfolio_symbols}")

# 2. Actual Zerodha holdings
# Wait, let's check what tables are available for Zerodha holdings
cur.execute("SELECT DISTINCT symbol FROM holdings")
zerodha_holdings_symbols = {row['symbol'] for row in cur.fetchall()}
print(f"Zerodha Holdings (from 'holdings' table): {zerodha_holdings_symbols}")

# 3. Current cai_positions
cur.execute("SELECT DISTINCT symbol FROM cai_positions WHERE status='ACTIVE'")
cai_positions_symbols = {row['symbol'] for row in cur.fetchall()}
print(f"CAI Positions: {cai_positions_symbols}")

# 4. Current cai_alert_config_versions
cur.execute("SELECT DISTINCT symbol FROM cai_alert_config_versions")
cai_configs_symbols = {row['symbol'] for row in cur.fetchall()}
print(f"CAI Configs: {cai_configs_symbols}")

conn.close()
