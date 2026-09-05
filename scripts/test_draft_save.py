import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

def test():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM clients WHERE is_admin = TRUE LIMIT 1")
    admin = cur.fetchone()
    if not admin:
        print("Error: No admin")
        return
    client_id = admin["id"]
    
    symbol = "HSCL"
    payload = {
        "pullback_lower_bound": 720.0,
        "pullback_upper_bound": 730.0,
        "breakout_confirmation_price": 800.0,
        "next_add_price": 820.0,
        "structural_break_price": 670.0
    }
    
    try:
        cur.execute("DELETE FROM cai_alert_config_versions WHERE client_id = %s AND symbol = %s AND status IN ('DRAFT', 'SYNC_FAILED')", (client_id, symbol))
        
        cur.execute("""
            INSERT INTO cai_alert_config_versions 
            (client_id, symbol, status, pullback_lower_bound, pullback_upper_bound, breakout_confirmation_price, next_add_price, structural_break_price, origin, validation_status)
            VALUES (%s, %s, 'DRAFT', %s, %s, %s, %s, %s, 'HUMAN_EDITED', 'PASS')
            RETURNING *
        """, (client_id, symbol, 
              payload["pullback_lower_bound"],
              payload["pullback_upper_bound"],
              payload["breakout_confirmation_price"],
              payload["next_add_price"],
              payload["structural_break_price"]))
        
        row = cur.fetchone()
        conn.rollback() # Don't actually save it
        
        print("HTTP Status: 200 OK")
        print("Response JSON:", row)
        print("No exception raised!")
        
    except Exception as e:
        conn.rollback()
        print("HTTP Status: 500")
        print(f"Backend Exception: {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    test()
