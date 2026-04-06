import os
import sys
import psycopg2

# 🛠️ Absolute Path Injection (FINAL FIX)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_core.config import get_db_credentials, DB_SSL

# TRACING: Database Integrity Check (v100.6)
print(f"DEBUG: LOADING scripts/db_check.py")

def check_db():
    creds = get_db_credentials()
    conn = psycopg2.connect(
        host=creds["host"], port=5432,
        dbname=creds["dbname"], user=creds["username"],
        password=creds["password"], sslmode="require"
    )
    try:
        with conn.cursor() as cur:
            # 1. Total Rows
            cur.execute("SELECT COUNT(*) FROM client_external_holdings;")
            holdings = cur.fetchone()[0]
            print(f"📊 [TOTAL HOLDINGS]: {holdings}")
            
            # 2. Check market_index_prices
            cur.execute("SELECT COUNT(*) FROM market_index_prices;")
            indices = cur.fetchone()[0]
            print(f"📈 [MARKET INDICES]: {indices}")
            
    finally:
        conn.close()

if __name__ == "__main__":
    check_db()
