"""Simulate the /api/breakout/radar endpoint query."""
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
      AND dp.breakout_state IN ('READY_TO_BREAKOUT', 'BROKEN_OUT')
    ORDER BY dp.breakout_state, dp.symbol
""")
rows = cur.fetchall()
if not rows:
    print("Radar: EMPTY")
else:
    print(f"Radar: {len(rows)} candidates\n")
    for r in rows:
        trend = "Bullish" if r['ema_50'] and r['ema_200'] and r['ema_50'] > r['ema_200'] else "Neutral"
        print(f"  {r['symbol']:15s} close={float(r['close']):>10,.0f}  vol={int(r['volume']):>10,}  {r['breakout_state']:20s}  {trend}  watchers={r['watchers']}  holders={r['holders']}")
conn.close()
