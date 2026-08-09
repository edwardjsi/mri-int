import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from api.zerodha_adapter import KiteAlertAdapter
from api.cai_alert_orchestrator import create_kite_alert_payloads

def investigate():
    print("🔍 Starting HSCL Investigation...\n")
    conn = psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    # Get Admin ID for authentication
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
    
    print("=== PART 1: CAI MAPPINGS FOR HSCL ===")
    query = """
    SELECT
        m.id,
        p.symbol,
        m.kite_uuid,
        m.active,
        m.status,
        m.created_at,
        m.config_version_id
    FROM cai_alert_mappings m
    JOIN cai_position p ON m.cai_position_id = p.id
    WHERE p.symbol = 'HSCL'
    ORDER BY m.created_at DESC;
    """
    cur.execute(query)
    mappings = cur.fetchall()
    
    if not mappings:
        print("No HSCL mappings found in DB!")
    
    config_id = None
    for m in mappings:
        print(f"Mapping ID: {m['id']}")
        print(f"  Symbol: {m['symbol']}")
        print(f"  Kite UUID: {m['kite_uuid']}")
        print(f"  Active: {m['active']}")
        print(f"  Status: {m['status']}")
        print(f"  Created At: {m['created_at']}")
        print(f"  Config ID: {m['config_version_id']}")
        print("-" * 40)
        if config_id is None and m['active']:
            config_id = m['config_version_id']

    print("\n=== PART 2: RETRIEVE FROM KITE ===")
    for m in mappings:
        if m['active']:
            uuid = m['kite_uuid']
            print(f"Retrieving UUID {uuid} from Zerodha...")
            alert = adapter.retrieve_alert(uuid)
            if alert:
                print(f"  ✅ FOUND IN ZERODHA: {alert.get('name')} | {alert.get('lhs_tradingsymbol')} {alert.get('operator')} {alert.get('rhs_constant')}")
            else:
                print(f"  ❌ NOT FOUND IN ZERODHA (Returned None/404)")
    
    print("\n=== PART 3: EXACT PAYLOADS SENT TO CREATE_ALERT ===")
    if config_id:
        cur.execute("SELECT * FROM cai_alert_config_versions WHERE id = %s", (config_id,))
        config = cur.fetchone()
        if config:
            payloads = create_kite_alert_payloads("HSCL", config)
            for p in payloads:
                print(f"Role: {p['role']}")
                print(f"  Name: {p['name']}")
                print(f"  Condition: {p['condition']}")
                print(f"  Price: {p['price']}")
                print("-" * 40)
        else:
            print("❌ Config not found in DB")
    else:
        print("❌ No active config ID found to determine payloads")

if __name__ == "__main__":
    investigate()
