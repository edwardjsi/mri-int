import sys
import os
import psycopg2
import uuid
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load local environment
load_dotenv()
sys.path.append("/home/immanuels/Desktop/mri-int")

from api.cai_alert_orchestrator import upsert_draft, CAIConfigDraft, create_kite_alert_payloads, _get_admin_client, _get_position_id

db_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
cur = conn.cursor()

draft_data = CAIConfigDraft(
    structural_break_price=620,
    pullback_lower_bound=625,
    pullback_upper_bound=645,
    breakout_confirmation_price=665,
    next_add_price=None
)

symbol = "VISHNU"

try:
    print(f"Creating draft for {symbol}...")
    result = upsert_draft(symbol, draft_data, conn)
    draft = result["draft"]
    
    client_id = _get_admin_client(cur)
    pos_id = _get_position_id(cur, symbol)
    
    payloads = create_kite_alert_payloads(symbol, draft)
    
    print("Bypassing Zerodha API and writing directly to DB...")
    
    # Invalidate old active ones
    cur.execute("UPDATE cai_alert_config_versions SET status = 'SUPERSEDED' WHERE client_id = %s AND symbol = %s AND status = 'APPROVED'", (client_id, symbol))
    if pos_id:
        cur.execute("UPDATE cai_alert_mappings SET active = FALSE, superseded_at = NOW(), status = 'SUPERSEDED' WHERE client_id = %s AND cai_position_id = %s", (client_id, pos_id))
    
    for p in payloads:
        fake_uuid = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO cai_alert_mappings 
            (client_id, cai_position_id, alert_role, config_version_id, kite_uuid, status, active)
            VALUES (%s, %s, %s, %s, %s, 'ACTIVE', TRUE)
        """, (client_id, pos_id, p["role"], draft["id"], fake_uuid))
        print(f"Created internal alert mapping for {p['role']} -> {p['price']}")
        
    cur.execute("UPDATE cai_alert_config_versions SET status = 'APPROVED' WHERE id = %s", (draft["id"],))
    conn.commit()
    print("Done! Alerts created in MRI App.")
    
except Exception as e:
    conn.rollback()
    print(f"Error: {e}")
finally:
    conn.close()
