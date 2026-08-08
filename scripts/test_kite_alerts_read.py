import os
import sys
import httpx
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

def run_test():
    load_dotenv()
    
    api_key = os.getenv("KITE_API_KEY")
    if not api_key:
        print("Error: KITE_API_KEY not found in environment")
        sys.exit(1)
        
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL not found in environment")
        sys.exit(1)
        
    try:
        conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        # Get admin client
        cur.execute("SELECT id FROM clients WHERE is_active = TRUE AND is_admin = TRUE ORDER BY created_at ASC LIMIT 1")
        admin = cur.fetchone()
        if not admin:
            print("Error: No active admin client found in DB")
            sys.exit(1)
            
        client_id = admin["id"]
        
        # Get access token
        cur.execute("SELECT access_token FROM kite_credentials WHERE client_id = %s", (client_id,))
        cred = cur.fetchone()
        if not cred or not cred["access_token"]:
            print(f"Error: No Kite access token found for admin client {client_id}")
            sys.exit(1)
            
        access_token = cred["access_token"]
        
    except Exception as e:
        print(f"Database error: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()
            
    print("Successfully retrieved access_token from DB. Making zero-mutation read-only call to Kite Alerts API...")
    
    url = "https://api.kite.trade/alerts"
    headers = {
        "X-Kite-Version": "3",
        "Authorization": f"token {api_key}:{access_token}"
    }
    
    try:
        resp = httpx.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get("status") != "success":
            print(f"Kite API Error: {data}")
            sys.exit(1)
            
        alerts = data.get("data", [])
        print(f"\n--- Retrieved {len(alerts)} Alerts ---")
        
        for alert in alerts:
            # We only print non-sensitive fields
            uuid_val = alert.get("uuid")
            name = alert.get("name")
            symbol = alert.get("lhs_tradingsymbol")
            alert_type = alert.get("type")
            status = alert.get("status")
            operator = alert.get("operator")
            rhs_val = alert.get("rhs_constant") or alert.get("rhs_tradingsymbol")
            
            print(f"UUID: {uuid_val} | Name: {name} | Symbol: {symbol} | Type: {alert_type} | Status: {status} | Condition: {operator} {rhs_val}")
            
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error from Kite API: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"Error calling Kite API: {e}")

if __name__ == "__main__":
    run_test()
