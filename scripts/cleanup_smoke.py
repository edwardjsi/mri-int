import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from api.zerodha_adapter import KiteAlertAdapter

def cleanup():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=RealDictCursor)
    cur = conn.cursor()
    cur.execute("SELECT id FROM clients WHERE is_admin = TRUE LIMIT 1")
    admin_id = cur.fetchone()["id"]
    
    adapter = KiteAlertAdapter()
    adapter.authenticate(admin_id, conn)
    
    uuid_to_delete = "d45fe8d9-41ad-4638-a478-82c806cd8935"
    print(f"Deleting leftover smoke test alert: {uuid_to_delete}...")
    success = adapter.delete_alert(uuid_to_delete)
    if success:
        print("✅ Successfully deleted leftover alert!")
    else:
        print("⚠️ Alert not found or could not be deleted.")

if __name__ == "__main__":
    cleanup()
