"""Quick DB check for breakout states."""
import psycopg2
import psycopg2.extras

url = "postgresql://neondb_owner:npg_opy4B3CZtxbd@ep-bold-mud-a1zbtu4d-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
conn = psycopg2.connect(url, connect_timeout=15)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# 1. Latest date
cur.execute("SELECT MAX(date) FROM daily_prices")
latest = cur.fetchone()["max"]
print(f"Latest date: {latest}")

# 2. Column check
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='daily_prices' AND column_name IN ('breakout_state','condition_breakout_10d')")
for c in cur.fetchall():
    print(f"COL: {c['column_name']} = {c['data_type']}")

# 3. Breakout state counts (all dates)
cur.execute("SELECT breakout_state, COUNT(*) as cnt FROM daily_prices GROUP BY breakout_state ORDER BY cnt DESC")
print("\n--- All-time breakout states ---")
for s in cur.fetchall():
    print(f"  {s['breakout_state']}: {s['cnt']}")

# 4. Breakout state counts (latest date only)
cur.execute("SELECT breakout_state, COUNT(*) as cnt FROM daily_prices WHERE date = %s GROUP BY breakout_state ORDER BY cnt DESC", (latest,))
print(f"\n--- Breakout states on {latest} ---")
for s in cur.fetchall():
    print(f"  {s['breakout_state']}: {s['cnt']}")

# 5. condition_breakout_10d on latest date
cur.execute("SELECT COUNT(*) FILTER (WHERE condition_breakout_10d IS TRUE) as t, COUNT(*) FILTER (WHERE condition_breakout_10d IS FALSE) as f, COUNT(*) FILTER (WHERE condition_breakout_10d IS NULL) as n FROM daily_prices WHERE date = %s", (latest,))
r = cur.fetchone()
print(f"\ncondition_breakout_10d: True={r['t']}, False={r['f']}, NULL={r['n']}")

# 6. Sample rows
cur.execute("""
    SELECT symbol, close, ema_50, ema_200, high_10d, condition_breakout_10d, 
           breakout_state, rolling_high_6m, volume, avg_volume_20d
    FROM daily_prices WHERE date = %s LIMIT 5
""", (latest,))
print("\n--- Sample rows ---")
for r in cur.fetchall():
    proximity = None
    if r['rolling_high_6m'] and r['close'] and r['rolling_high_6m'] > 0:
        proximity = round((r['rolling_high_6m'] - r['close']) / r['rolling_high_6m'], 4)
    print(f"  {r['symbol']}: close={r['close']}, ema50={r['ema_50']}, ema200={r['ema_200']}, high_10d={r['high_10d']}, rolling_6m={r['rolling_high_6m']}, proximity={proximity}, cond_break10d={r['condition_breakout_10d']}, breakout={r['breakout_state']}")

# 7. Watchlist/portfolio
cur.execute("SELECT COUNT(*) FROM client_watchlist")
print(f"\nwatchlist rows: {cur.fetchone()['count']}")
cur.execute("SELECT COUNT(*) FROM client_portfolio WHERE is_open=true")
print(f"open portfolio: {cur.fetchone()['count']}")

# 8. Total symbols
cur.execute("SELECT COUNT(DISTINCT symbol) FROM daily_prices WHERE date = %s", (latest,))
total = cur.fetchone()["count"]
print(f"total symbols: {total}")

# 9. How many stocks have close > ema_50 > ema_200?
cur.execute("SELECT COUNT(*) FROM daily_prices WHERE date = %s AND close > ema_50 AND ema_50 >= ema_200", (latest,))
print(f"stocks with close>ema50>=ema200: {cur.fetchone()['count']}")

conn.close()
