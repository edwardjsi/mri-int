"""Check if BROKEN_OUT candidates are in any watchlist."""
import psycopg2
import psycopg2.extras

url = "postgresql://neondb_owner:npg_opy4B3CZtxbd@ep-bold-mud-a1zbtu4d-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
conn = psycopg2.connect(url, connect_timeout=15)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("""
    SELECT symbol FROM daily_prices
    WHERE date = (SELECT MAX(date) FROM daily_prices)
    AND close > high_10d
""")
potential = [r['symbol'] for r in cur.fetchall()]
print(f"Potential breakout stocks (close > high_10d): {len(potential)}")
for s in potential:
    print(f"  {s}")

cur.execute("SELECT DISTINCT symbol FROM client_watchlist")
watchlist = [r['symbol'] for r in cur.fetchall()]
print(f"\nWatchlist symbols ({len(watchlist)}):")
for s in watchlist:
    print(f"  {s}")

overlap = set(potential) & set(watchlist)
print(f"\nIn watchlist AND potential breakout: {len(overlap)}")
for s in sorted(overlap):
    print(f"  {s}")

conn.close()
