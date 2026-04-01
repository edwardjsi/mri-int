import psycopg2
import os
import sys
# Path setup so we can import src.db
sys.path.append(os.getcwd())

from src.db import get_connection

def check():
    print("--- Database Health Check ---")
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        tables = ['daily_prices', 'index_prices', 'market_regime', 'stock_scores']
        
        for table in tables:
            try:
                cur.execute(f"SELECT MAX(date), COUNT(*) FROM {table}")
                row = cur.fetchone()
                print(f"{table:15} | Max Date: {row[0]} | Count: {row[1]}")
            except Exception as e:
                print(f"{table:15} | Error: {e}")
                conn.rollback()
                
        cur.close()
        conn.close()
    except Exception as e:
        print(f"CRITICAL: Failed to connect or initialize DB: {e}")

if __name__ == "__main__":
    check()
