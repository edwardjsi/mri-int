import sys
import os
# Add parent directory to sys.path to find src module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db import get_connection

conn = get_connection()
cur = conn.cursor()

print("--- Table Row Counts ---")
tables = ['daily_prices', 'index_prices', 'market_regime', 'stock_scores', 'stock_sectors']
for t in tables:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"{t}: {cur.fetchone()[0]}")
    except Exception as e:
        print(f"{t}: Error {e}")
        conn.rollback()

print("\n--- Column List (daily_prices) ---")
try:
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'daily_prices'")
    columns = [r[0] for r in cur.fetchall()]
    print(", ".join(columns))
except Exception as e:
    print(f"Error fetching columns: {e}")
    conn.rollback()

cur.close()
conn.close()
