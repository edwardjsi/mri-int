import psycopg2, os
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
cur = conn.cursor()

symbols_to_check = ["SHAILY", "RATEGAIN", "AZADENGG", "IPCALAB", "HSCL", "DIVISLAB"]
print("Database Verification:")
print(f"{'Symbol':<15} | {'Rows':<6} | {'Min Date':<12} | {'Max Date':<12}")
print("-" * 55)

for sym in symbols_to_check:
    cur.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM daily_prices WHERE symbol = %s", (sym,))
    count, min_date, max_date = cur.fetchone()
    print(f"{sym:<15} | {count:<6} | {str(min_date):<12} | {str(max_date):<12}")

cur.close()
conn.close()
