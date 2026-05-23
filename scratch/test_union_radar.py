"""Test the UNION radar query."""
import psycopg2
import psycopg2.extras
url = "postgresql://neondb_owner:npg_opy4B3CZtxbd@ep-bold-mud-a1zbtu4d-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
conn = psycopg2.connect(url, connect_timeout=15)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
cur.execute("""
    SELECT symbol, close, volume, ema_50, ema_200, breakout_state, watchers, holders
    FROM (
        SELECT dp.symbol, dp.close, dp.volume, dp.ema_50, dp.ema_200, dp.breakout_state,
               (SELECT COUNT(DISTINCT client_id) FROM client_watchlist WHERE symbol=dp.symbol) as watchers,
               (SELECT COUNT(DISTINCT client_id) FROM client_portfolio WHERE symbol=dp.symbol AND is_open=true) as holders,
               0 as sort_grp
        FROM daily_prices dp WHERE dp.date=(SELECT MAX(date) FROM daily_prices)
          AND (EXISTS (SELECT 1 FROM client_watchlist WHERE symbol=dp.symbol)
               OR EXISTS (SELECT 1 FROM client_portfolio WHERE symbol=dp.symbol AND is_open=true))
        UNION
        SELECT dp.symbol, dp.close, dp.volume, dp.ema_50, dp.ema_200, dp.breakout_state,
               (SELECT COUNT(DISTINCT client_id) FROM client_watchlist WHERE symbol=dp.symbol) as watchers,
               (SELECT COUNT(DISTINCT client_id) FROM client_portfolio WHERE symbol=dp.symbol AND is_open=true) as holders,
               1 as sort_grp
        FROM daily_prices dp WHERE dp.date=(SELECT MAX(date) FROM daily_prices)
          AND dp.breakout_state IN ('BROKEN_OUT','READY_TO_BREAKOUT')
          AND NOT (EXISTS (SELECT 1 FROM client_watchlist WHERE symbol=dp.symbol)
                   OR EXISTS (SELECT 1 FROM client_portfolio WHERE symbol=dp.symbol AND is_open=true))
    ) combined
    ORDER BY sort_grp, CASE breakout_state WHEN 'BROKEN_OUT' THEN 1 WHEN 'READY_TO_BREAKOUT' THEN 2 ELSE 3 END, symbol
""")
rows = cur.fetchall()
broken = [r for r in rows if r['breakout_state']=='BROKEN_OUT']
ready = [r for r in rows if r['breakout_state']=='READY_TO_BREAKOUT']
cons = [r for r in rows if r['breakout_state']=='CONSOLIDATING']
print(f"Total: {len(rows)} | BROKEN: {len(broken)} | READY: {len(ready)} | CONS: {len(cons)}")
for r in broken:
    print(f"  BROKEN: {r['symbol']}")
for r in cons[:3]:
    print(f"  CONS: {r['symbol']}")
conn.close()
