import pytest
import psycopg2
from api.schema import ensure_cai_tables

# NOTE: This test requires a running Postgres database. It will create the tables,
# insert a record, attempt to UPDATE/DELETE, and rollback the transaction.

@pytest.fixture
def db_conn():
    try:
        from db import get_connection
        conn = get_connection()
    except Exception:
        # Fallback for CI or running locally without db.py configured in path
        import os
        conn_str = os.environ.get('DATABASE_URL')
        if not conn_str:
            pytest.skip("DATABASE_URL not set, skipping DB tests.")
        conn = psycopg2.connect(conn_str)
    
    # Initialize the tables inside a transaction we can rollback
    cur = conn.cursor()
    
    # Need to ensure clients table exists for foreign keys
    cur.execute("""
        CREATE EXTENSION IF NOT EXISTS "pgcrypto";
        CREATE TABLE IF NOT EXISTS clients (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255),
            password_hash TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            is_admin BOOLEAN DEFAULT FALSE,
            initial_capital NUMERIC(15,2) DEFAULT 100000,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    cur.execute("DROP TABLE IF EXISTS cai_decision_ledger, cai_alert_events, cai_positions, cai_alert_config_versions CASCADE;")
    ensure_cai_tables(cur)
    conn.commit()
    
    yield conn
    
    cur.close()
    conn.close()

def test_decision_ledger_immutability(db_conn):
    cur = db_conn.cursor()
    
    try:
        # Clean up from any previous failed runs
        cur.execute("ALTER TABLE cai_decision_ledger DISABLE TRIGGER prevent_update_delete_cai_ledger;")
        cur.execute("DELETE FROM clients WHERE email = 'test_ledger@example.com';")
        cur.execute("ALTER TABLE cai_decision_ledger ENABLE TRIGGER prevent_update_delete_cai_ledger;")
        db_conn.commit()
        
        # Setup test data
        cur.execute("INSERT INTO clients (email, password_hash) VALUES ('test_ledger@example.com', 'dummy_hash') RETURNING id;")
        client_id = cur.fetchone()[0]
        
        cur.execute(f"INSERT INTO cai_alert_config_versions (client_id, symbol, structural_break_price) VALUES ('{client_id}', 'TEST_SYM', 100) RETURNING id;")
        config_id = cur.fetchone()[0]
        
        cur.execute(f"INSERT INTO cai_alert_events (config_id, state) VALUES ('{config_id}', 'CREATED') RETURNING id;")
        event_id = cur.fetchone()[0]
        
        # 1. Test INSERT works
        cur.execute(f"INSERT INTO cai_decision_ledger (config_id, event_id, trigger_price, user_choice, reasoning) VALUES ('{config_id}', '{event_id}', 105, 'ADD', 'Test reasoning') RETURNING id;")
        ledger_id = cur.fetchone()[0]
        db_conn.commit()
        
        # 2. Test UPDATE is rejected
        with pytest.raises(psycopg2.errors.RaiseException) as excinfo:
            cur.execute(f"UPDATE cai_decision_ledger SET reasoning = 'Hacked' WHERE id = '{ledger_id}';")
        assert "cai_decision_ledger is append-only" in str(excinfo.value)
        db_conn.rollback() # Required after failed transaction
        
        # 3. Test DELETE is rejected
        with pytest.raises(psycopg2.errors.RaiseException) as excinfo:
            cur.execute(f"DELETE FROM cai_decision_ledger WHERE id = '{ledger_id}';")
        assert "cai_decision_ledger is append-only" in str(excinfo.value)
        db_conn.rollback()
        
        # 4. Confirm event A is unchanged
        cur.execute(f"SELECT reasoning FROM cai_decision_ledger WHERE id = '{ledger_id}';")
        reasoning = cur.fetchone()[0]
        assert reasoning == 'Test reasoning'
        
    finally:
        # Cleanup
        db_conn.rollback()
        try:
            cur.execute("ALTER TABLE cai_decision_ledger DISABLE TRIGGER prevent_update_delete_cai_ledger;")
            cur.execute(f"DELETE FROM clients WHERE email = 'test_ledger@example.com';")
        finally:
            cur.execute("ALTER TABLE cai_decision_ledger ENABLE TRIGGER prevent_update_delete_cai_ledger;")
        db_conn.commit()
        cur.close()
