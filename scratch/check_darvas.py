import sys
sys.path.append('.')
from engine_core.db import get_connection

conn = get_connection()
cur = conn.cursor()
query = """
WITH latest_prices AS (
    SELECT DISTINCT ON (symbol)
        symbol, date, close, high, rolling_high_52w
    FROM daily_prices
    ORDER BY symbol, date DESC
),
latest_mcap AS (
    SELECT DISTINCT ON (symbol)
        symbol, date, market_cap_cr
    FROM market_cap_history
    ORDER BY symbol, date DESC
)
SELECT 
    lp.symbol, 
    lp.date AS price_date
FROM latest_prices lp
JOIN nifty500_universe n5 ON lp.symbol = n5.symbol AND n5.constituent_to IS NULL
LEFT JOIN latest_mcap lm ON lp.symbol = lm.symbol
WHERE lm.market_cap_cr > 800
  AND lp.close > 50
  AND lp.high >= lp.rolling_high_52w
ORDER BY lp.date ASC
LIMIT 10
"""
cur.execute(query)
rows = cur.fetchall()
print("Dates returned in Darvas scan:")
for row in rows:
    print(row['symbol'], row['price_date'])
