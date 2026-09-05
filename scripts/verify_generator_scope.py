import os
import psycopg2

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

# 1. Verify 24 symbols
cur.execute("""
    SELECT p.symbol 
    FROM cai_position p
    JOIN cai_portfolio port ON p.portfolio_id = port.id
    WHERE p.status = 'ACTIVE'
""")
symbols = [row[0] for row in cur.fetchall()]
print(f"Generator scope sees {len(symbols)} symbols: {sorted(symbols)}")

# 2. Verify HSCL
cur.execute("SELECT pullback_lower_bound, pullback_upper_bound, breakout_confirmation_min_price, next_add_min_price, structural_break_price, status FROM cai_alert_config_versions WHERE symbol = 'HSCL' ORDER BY created_at DESC LIMIT 1")
hscl = cur.fetchone()
if hscl:
    print(f"HSCL DRAFT: Pullback {hscl[0]}-{hscl[1]}, Breakout {hscl[2]}, Next Add {hscl[3]}, Structure {hscl[4]}, Status {hscl[5]}")
else:
    print("HSCL config not found!")

# 3. Verify INFY, TCS, RELIANCE configs don't exist
for s in ['INFY', 'TCS', 'RELIANCE']:
    cur.execute(f"SELECT COUNT(*) FROM cai_alert_config_versions WHERE symbol = '{s}'")
    count = cur.fetchone()[0]
    print(f"{s} config count: {count}")

conn.close()
