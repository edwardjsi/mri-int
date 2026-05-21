from engine_core.db import get_connection
conn = get_connection()
cur = conn.cursor()

cur.execute("SELECT date, classification FROM market_regime ORDER BY date DESC LIMIT 1")
regime = cur.fetchone()
print("Regime:", regime)

cur.execute("""
    SELECT ss.symbol, ss.total_score, (dp.avg_volume_20d * dp.close) as adtv
    FROM stock_scores ss
    JOIN daily_prices dp ON dp.symbol = ss.symbol AND dp.date = ss.date
    WHERE ss.date = (SELECT MAX(date) FROM stock_scores)
    ORDER BY ss.total_score DESC LIMIT 10
""")
scores = cur.fetchall()
print("\nTop Scores:")
for row in scores:
    print(row)

cur.execute("SELECT COUNT(*) FROM clients WHERE is_active = true")
print("\nActive clients:", cur.fetchone())

cur.execute("SELECT COUNT(*) FROM client_signals")
print("\nTotal client_signals:", cur.fetchone())

