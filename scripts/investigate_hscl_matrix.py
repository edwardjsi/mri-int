import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from api.zerodha_adapter import KiteAlertAdapter

def investigate_matrix():
    print("🔍 Generating Definitive HSCL Matrix...\n")
    conn = psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM clients WHERE is_admin = TRUE LIMIT 1")
    admin = cur.fetchone()
    if not admin:
        print("❌ Error: Admin client not found in DB")
        sys.exit(1)
    admin_id = admin["id"]
    
    adapter = KiteAlertAdapter()
    if not adapter.authenticate(admin_id, conn):
        print("❌ Error: Failed to authenticate adapter (check DB token)")
        sys.exit(1)
    
    query = """
    SELECT
        m.id,
        p.symbol,
        m.alert_role,
        m.kite_uuid,
        m.active,
        m.status,
        m.created_at
    FROM cai_alert_mappings m
    JOIN cai_position p ON m.cai_position_id = p.id
    WHERE p.symbol = 'HSCL'
      AND m.active = TRUE
    ORDER BY m.created_at DESC;
    """
    cur.execute(query)
    mappings = cur.fetchall()
    
    if not mappings:
        print("No active HSCL mappings found in DB!")
        return

    print(f"{'Role':<25} | {'MRI UUID':<40} | {'Exists in Zerodha?'}")
    print("-" * 90)
    
    for m in mappings:
        role = m['alert_role']
        uuid = m['kite_uuid']
        
        # Verify in Zerodha
        try:
            alert = adapter.retrieve_alert(uuid)
            if alert:
                exists = f"YES ({alert.get('operator')} {alert.get('rhs_constant')})"
            else:
                exists = "NO"
        except Exception as e:
            exists = f"ERROR: {str(e)}"
            
        print(f"{role:<25} | {uuid:<40} | {exists}")

if __name__ == "__main__":
    investigate_matrix()
