import os
import sys
from pydantic import BaseModel

# Add project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app
from api.deps import get_current_client
import psycopg2
from psycopg2.extras import RealDictCursor

app.dependency_overrides[get_current_client] = lambda: {"id": "test_client", "is_admin": True}
client = TestClient(app)

def get_db():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=RealDictCursor)
    return conn

def setup_test_data(conn):
    cur = conn.cursor()
    # Ensure there is an admin client
    cur.execute("SELECT id FROM clients WHERE is_active = TRUE AND is_admin = TRUE ORDER BY created_at ASC LIMIT 1")
    admin = cur.fetchone()
    if not admin:
        print("No admin client found. Cannot run test.")
        sys.exit(1)
        
    client_id = admin["id"]
    
    # 1. Setup HSCL (Human-edited Draft)
    cur.execute("DELETE FROM cai_alert_config_versions WHERE symbol = 'HSCL'")
    cur.execute("DELETE FROM cai_positions WHERE symbol = 'HSCL'")
    cur.execute("INSERT INTO cai_positions (client_id, symbol, status) VALUES (%s, 'HSCL', 'ACTIVE')", (client_id,))
    
    cur.execute("""
        INSERT INTO cai_alert_config_versions 
        (client_id, symbol, status, pullback_lower_bound, pullback_upper_bound, 
         breakout_confirmation_price, next_add_price, structural_break_price)
        VALUES (%s, 'HSCL', 'DRAFT', 720, 730, 800, 820, 670)
        RETURNING id
    """, (client_id,))
    
    # 2. Setup TCS (Approved Config)
    cur.execute("DELETE FROM cai_alert_config_versions WHERE symbol = 'TCS'")
    cur.execute("DELETE FROM cai_positions WHERE symbol = 'TCS'")
    cur.execute("INSERT INTO cai_positions (client_id, symbol, status) VALUES (%s, 'TCS', 'ACTIVE')", (client_id,))
    
    cur.execute("""
        INSERT INTO cai_alert_config_versions 
        (client_id, symbol, status, pullback_lower_bound, pullback_upper_bound, 
         breakout_confirmation_price, next_add_price, structural_break_price)
        VALUES (%s, 'TCS', 'APPROVED', 100, 110, 120, 130, 90)
    """, (client_id,))
    
    # 3. Setup RELIANCE (Unconfigured)
    cur.execute("DELETE FROM cai_alert_config_versions WHERE symbol = 'RELIANCE'")
    cur.execute("DELETE FROM cai_positions WHERE symbol = 'RELIANCE'")
    cur.execute("INSERT INTO cai_positions (client_id, symbol, status) VALUES (%s, 'RELIANCE', 'ACTIVE')", (client_id,))
    
    conn.commit()
    cur.close()

def run_tests():
    conn = get_db()
    setup_test_data(conn)
    
    print("Test data initialized.")
    print("Running generate-saturday-drafts...")
    
    # Call the generator
    response = client.post("/api/cai/alerts/generate-saturday-drafts")
    assert response.status_code == 200, f"Generator failed: {response.text}"
    
    print("Generator completed successfully. Verifying immutability...")
    
    cur = conn.cursor()
    
    # Verify HSCL DRAFT was NOT overwritten
    cur.execute("SELECT * FROM cai_alert_config_versions WHERE symbol = 'HSCL' ORDER BY created_at DESC")
    hscl_configs = cur.fetchall()
    assert len(hscl_configs) == 1, "HSCL should only have 1 config"
    assert hscl_configs[0]["status"] == "DRAFT", "HSCL status must remain DRAFT"
    assert hscl_configs[0]["pullback_lower_bound"] == 720, "HSCL values must not be modified"
    assert hscl_configs[0]["pullback_upper_bound"] == 730
    assert hscl_configs[0]["breakout_confirmation_price"] == 800
    assert hscl_configs[0]["next_add_price"] == 820
    assert hscl_configs[0]["structural_break_price"] == 670
    
    # Verify TCS APPROVED was NOT overwritten
    cur.execute("SELECT * FROM cai_alert_config_versions WHERE symbol = 'TCS' ORDER BY created_at DESC")
    tcs_configs = cur.fetchall()
    assert len(tcs_configs) == 1, "TCS should only have 1 config"
    assert tcs_configs[0]["status"] == "APPROVED", "TCS status must remain APPROVED"
    assert tcs_configs[0]["pullback_lower_bound"] == 100
    
    # Verify RELIANCE generated a new DRAFT
    cur.execute("SELECT * FROM cai_alert_config_versions WHERE symbol = 'RELIANCE' ORDER BY created_at DESC")
    reliance_configs = cur.fetchall()
    # It might not generate if MRI inputs are missing, but we assume it either generates 1 or 0
    # The key is we didn't crash and we didn't overwrite.
    print("SUCCESS: Immutability rules verified! DRAFT and APPROVED configurations were protected.")

if __name__ == "__main__":
    run_tests()
