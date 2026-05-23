"""Simulate updated /radar endpoint."""
import psycopg2
import psycopg2.extras

url = "postgresql://neondb_owner:npg_opy4B3CZtxbd@ep-bold-mud-a1zbtu4d-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
conn = psycopg2.connect(url, connect_timeout=15)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cur.execute("""
    SELECT dp.symbol, dp.close, dp.volume, dp.ema_50, dp.ema_200, dp.breakout_state,
           (SELECT COUNT(DISTINCT client_id) FROM client_watchlist WHERE symbol=dp.symbol) as watchers,
           (SELECT COUNT(DISTINCT client_id) FROM client_portfolio WHERE symbol=dp.symbol AND is_open=true) as holders
    FROM daily_prices dp
    WHERE dp.date = (SELECT MAX(date) FROM daily_prices)
      AND (EXISTS (SELECT 1 FROM client_watchlist WHERE symbol=dp.symbol)
           OR EXISTS (SELECT 1 FROM client_portfolio WHERE symbol=dp.symbol AND is_open=true))
    ORDER BY CASE dp.breakout_state WHEN 'BROKEN_OUT' THEN 1 WHEN 'READY_TO_BREAKOUT' THEN 2 ELSE 3 END, dp.symbol
""")
rows = cur.fetchall()

broken = [r for r in rows if r['breakout_state'] == 'BROKEN_OUT']
ready = [r for r in rows if r['breakout_state'] == 'READY_TO_BREAKOUT']
cons = [r for r in rows if r['breakout_state'] == 'CONSOLIDATING']

print(f"Total: {len(rows)} stocks\n")
print(f"🚀 BROKEN_OUT ({len(broken)}):")
for r in broken:
    print(f"  {r['symbol']:15s} ₹{float(r['close']):>10,.0f}")

print(f"\n⚡ READY_TO_BREAKOUT ({len(ready)}):")
for r in ready:
    print(f"  {r['symbol']:15s} ₹{float(r['close']):>10,.0f}")

print(f"\n⏳ CONSOLIDATING ({len(cons)}):")
for r in cons:
    trend = "↑" if r['ema_50'] and r['ema_200'] and r['ema_50'] > r['ema_200'] else "↓"
    print(f"  {r['symbol']:15s} ₹{float(r['close']):>10,.0f}  {trend}")

conn.close()
