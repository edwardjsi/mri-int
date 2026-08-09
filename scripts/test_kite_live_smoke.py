import os
import sys
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from api.zerodha_adapter import KiteAlertAdapter

# Ensure Kite API key is set
if not os.getenv("KITE_API_KEY"):
    print("❌ Error: KITE_API_KEY environment variable is not set!")
    sys.exit(1)

def get_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ Error: DATABASE_URL environment variable is not set!")
        sys.exit(1)
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)

def run_smoke_test():
    print("🚀 Starting Kite Live Smoke Test")
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Get the admin client ID
    cur.execute("SELECT id FROM clients WHERE is_admin = TRUE LIMIT 1")
    admin = cur.fetchone()
    if not admin:
        print("❌ Error: Admin client not found in DB")
        sys.exit(1)
    admin_id = admin["id"]
    
    adapter = KiteAlertAdapter()
    
    # 1. Authenticate
    if not adapter.authenticate(admin_id, conn):
        print("❌ Error: Failed to authenticate adapter (check DB token)")
        sys.exit(1)
    print("✅ Authenticated with Kite")
    
    # 2. Create an alert
    test_name = f"SMOKE-TEST-{str(uuid.uuid4())[:8]}"
    print(f"Creating simple alert: {test_name} for RELIANCE...")
    alert_uuid = adapter.create_alert(
        symbol="RELIANCE",
        condition=">=",
        price=9999.0,
        alert_name=test_name
    )
    print(f"✅ Created alert with real UUID: {alert_uuid}")
    
    # 3. Retrieve the alert
    print(f"Retrieving alert {alert_uuid} from Kite...")
    retrieved = adapter.retrieve_alert(alert_uuid)
    if not retrieved:
        print(f"❌ Error: Could not retrieve alert {alert_uuid}")
        sys.exit(1)
    print(f"✅ Retrieved alert successfully: {retrieved['name']}")
    
    # 4. Modify the alert (PUT)
    print(f"Modifying alert {alert_uuid} price to 9998.0...")
    success = adapter.modify_alert(alert_uuid, new_condition=">=", new_price=9998.0, new_name=f"{test_name}-MOD")
    if not success:
        print(f"❌ Error: Failed to modify alert {alert_uuid}")
        sys.exit(1)
    print("✅ Modified alert successfully")
    
    # 4.5 Retrieve it again to confirm modification
    print(f"Retrieving alert {alert_uuid} again to confirm modification...")
    retrieved_mod = adapter.retrieve_alert(alert_uuid)
    if not retrieved_mod:
        print(f"❌ Error: Could not retrieve alert {alert_uuid} after modification")
        sys.exit(1)
    print(f"✅ Confirmed modification. Name is now: {retrieved_mod['name']}, Price: {retrieved_mod.get('rhs_constant', 'unknown')}")
    
    # 5. Delete the alert
    print(f"Deleting alert {alert_uuid}...")
    del_success = adapter.delete_alert(alert_uuid)
    if not del_success:
        print(f"❌ Error: Failed to delete alert {alert_uuid}")
        sys.exit(1)
    print("✅ Deleted alert successfully")
    
    print("🎉 Smoke test completed successfully!")

if __name__ == "__main__":
    run_smoke_test()
