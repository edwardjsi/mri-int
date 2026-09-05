import os
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=RealDictCursor)
cur = conn.cursor()

print("--- 1. CAI Configurations ---")
cur.execute("SELECT * FROM cai_alert_config_versions ORDER BY symbol, version DESC")
for c in cur.fetchall():
    print(c)

print("\n--- 2. Portfolio Positions ---")
cur.execute("SELECT * FROM cai_positions WHERE status = 'ACTIVE' ORDER BY symbol")
for p in cur.fetchall():
    print(p)

print("\n--- 3. CAI Alert Mappings ---")
cur.execute("""
    SELECT m.*, p.symbol 
    FROM cai_alert_mappings m 
    JOIN cai_positions p ON m.cai_position_id = p.id
""")
for m in cur.fetchall():
    print(m)

print("\n--- 4. Decision Ledger ---")
cur.execute("SELECT * FROM cai_decision_ledger WHERE recorded_at > (NOW() - INTERVAL '4 hours') ORDER BY recorded_at DESC")
for l in cur.fetchall():
    print(l)

conn.close()
