import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2
from psycopg2.extras import RealDictCursor
from api.cai_alert_orchestrator import _get_admin_client, load_mri_inputs, compute_thresholds

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor(cursor_factory=RealDictCursor)
client_id = _get_admin_client(cur)

# Insert TCS APPROVED and RELIANCE UNCONFIGURED (by deleting its configs) to match test state
cur.execute("DELETE FROM cai_alert_config_versions WHERE symbol = 'RELIANCE'")
cur.execute("DELETE FROM cai_alert_config_versions WHERE symbol = 'TCS'")
cur.execute("INSERT INTO cai_alert_config_versions (client_id, symbol, status, pullback_lower_bound, pullback_upper_bound, breakout_confirmation_price, next_add_price, structural_break_price) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (client_id, "TCS", "APPROVED", 2000.0, 2050.0, 2100.0, 2150.0, 1950.0))
conn.commit()

# Now run generator logic
generated = 0
skipped_approved = 0
skipped_draft = 0

cur.execute("SELECT id, symbol FROM cai_positions WHERE status = 'ACTIVE' AND client_id = %s", (client_id,))
positions = cur.fetchall()

for pos in positions:
    symbol = pos["symbol"]
    cur.execute("SELECT status FROM cai_alert_config_versions WHERE symbol = %s AND client_id = %s ORDER BY created_at DESC LIMIT 1", (symbol, client_id))
    latest = cur.fetchone()
    if latest:
        if latest["status"] == "APPROVED":
            skipped_approved += 1
            continue
        if latest["status"] == "DRAFT":
            skipped_draft += 1
            continue

    inputs = load_mri_inputs(conn, symbol)
    if not inputs or inputs.get("current_price") is None:
        continue
    
    thresholds = compute_thresholds(inputs)
    cur.execute("""
        INSERT INTO cai_alert_config_versions 
        (client_id, symbol, status, pullback_lower_bound, pullback_upper_bound, breakout_confirmation_price, next_add_price, structural_break_price)
        VALUES (%s, %s, 'DRAFT', %s, %s, %s, %s, %s)
    """, (client_id, symbol, thresholds["pullback_lower_bound"], thresholds["pullback_upper_bound"], thresholds["breakout_confirmation_price"], thresholds["next_add_price"], thresholds["structural_break_price"]))
    generated += 1

conn.commit()
print(f"Generator run complete. Created: {generated}, Skipped DRAFT: {skipped_draft}, Skipped APPROVED: {skipped_approved}")

cur.execute("SELECT pullback_lower_bound, pullback_upper_bound, breakout_confirmation_price, next_add_price, structural_break_price FROM cai_alert_config_versions WHERE symbol = 'HSCL' ORDER BY created_at DESC LIMIT 1")
hscl_config = cur.fetchone()
print(f"HSCL Config after generation: {dict(hscl_config)}")
