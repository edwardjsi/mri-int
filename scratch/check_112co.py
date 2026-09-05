from engine_core.db import get_connection

conn = get_connection()
cur = conn.cursor()

cur.execute("""
    SELECT COUNT(*) FROM universe_112co WHERE is_active = TRUE;
""")
print(f"Total active 112co: {cur.fetchone()[0]}")

cur.execute("""
    SELECT MAX(date) FROM daily_prices;
""")
max_date = cur.fetchone()[0]
print(f"Max date in daily_prices: {max_date}")

cur.execute("""
    SELECT COUNT(DISTINCT u.symbol)
    FROM universe_112co u
    JOIN daily_prices dp ON dp.symbol = u.symbol
    WHERE u.is_active = TRUE AND dp.date = %s
""", (max_date,))
print(f"Companies with data on max_date: {cur.fetchone()[0]}")

cur.execute("""
    SELECT COUNT(DISTINCT symbol)
    FROM daily_prices
    WHERE symbol IN (SELECT symbol FROM universe_112co WHERE is_active = TRUE);
""")
print(f"Companies with any data at all: {cur.fetchone()[0]}")
