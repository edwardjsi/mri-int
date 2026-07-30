from engine_core.db import get_connection
import psycopg2.extras

conn = get_connection()
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

print("--- DIVISLAB CAI POSITION ---")
cur.execute("SELECT * FROM cai_position WHERE symbol = 'DIVISLAB'")
for row in cur.fetchall():
    print(row)

print("\n--- DIVISLAB DAILY PRICES ---")
cur.execute("SELECT date, close FROM daily_prices WHERE symbol = 'DIVISLAB' ORDER BY date DESC LIMIT 3")
for row in cur.fetchall():
    print(row)

cur.close()
conn.close()
