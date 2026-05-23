"""Verify breakout states after engine run."""
import psycopg2
import psycopg2.extras

url = "postgresql://neondb_owner:npg_opy4B3CZtxbd@ep-bold-mud-a1zbtu4d-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
conn = psycopg2.connect(url, connect_timeout=15)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("""
    SELECT breakout_state, COUNT(*) as cnt
    FROM daily_prices
    WHERE date = (SELECT MAX(date) FROM daily_prices)
    GROUP BY breakout_state
    ORDER BY cnt DESC
""")
print("=== Breakout states (latest date) ===")
for r in cur.fetchall():
    print(f"  {r['breakout_state']}: {r['cnt']}")

cur.execute("""
    SELECT symbol, close, volume, condition_breakout_10d
    FROM daily_prices
    WHERE date = (SELECT MAX(date) FROM daily_prices)
    AND breakout_state = 'BROKEN_OUT'
    ORDER BY symbol
""")
broken = cur.fetchall()
print(f"\n=== BROKEN_OUT ({len(broken)}) ===")
for r in broken:
    print(f"  {r['symbol']}: close={r['close']}, vol={r['volume']}")

cur.execute("""
    SELECT symbol, close
    FROM daily_prices
    WHERE date = (SELECT MAX(date) FROM daily_prices)
    AND breakout_state = 'READY_TO_BREAKOUT'
    ORDER BY symbol
""")
ready = cur.fetchall()
print(f"\n=== READY_TO_BREAKOUT ({len(ready)}) ===")
for r in ready:
    print(f"  {r['symbol']}: close={r['close']}")

conn.close()
