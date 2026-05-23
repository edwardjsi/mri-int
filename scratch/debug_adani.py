"""Check why ADANIGREEN and others aren't READY_TO_BREAKOUT."""
import psycopg2
import psycopg2.extras
import math

url = "postgresql://neondb_owner:npg_opy4B3CZtxbd@ep-bold-mud-a1zbtu4d-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
conn = psycopg2.connect(url, connect_timeout=15)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Get latest date
cur.execute("SELECT MAX(date) FROM daily_prices")
latest = cur.fetchone()["max"]

# Get the indicator engine's computed fields that affect breakout classification
# We need: ema_50, ema_200, condition_breakout_10d, weekly_rsi_14, macd_hist,
#          proximity_to_high, price_range_5d, vol_multiplier, breakout_state
# But these live columns aren't persisted. Let me compute manually for ADANIGREEN.

# First get the recent data for ADANIGREEN
cur.execute("""
    SELECT date, close, high, low, volume, ema_50, ema_200
    FROM daily_prices
    WHERE symbol = 'ADANIGREEN'
    ORDER BY date DESC
    LIMIT 30
""")
rows = cur.fetchall()

# Print raw data
print("=== ADANIGREEN last 10 days ===")
for r in rows[:10]:
    print(f"  {r['date']}: close={r['close']}, high={r['high']}, low={r['low']}, vol={r['volume']}, ema50={r['ema_50']}, ema200={r['ema_200']}")

# Compute the 5-day price range for the latest date (5 days ending on latest)
latest_rows = rows[:5]
if len(latest_rows) >= 5:
    highs = [float(r['high']) for r in latest_rows]
    lows = [float(r['low']) for r in latest_rows]
    price_range_5d = (max(highs) - min(lows)) / min(lows)
    print(f"\nprice_range_5d (computed): {price_range_5d:.4f} (need <= 0.025)")

# Average volume over last 5 days
vols = [float(r['volume']) for r in rows[:20]]
avg_vol_20d = sum(vols) / len(vols) if vols else 0
latest_vol = float(rows[0]['volume'])
vol_mult = latest_vol / avg_vol_20d if avg_vol_20d > 0 else 0
print(f"vol_multiplier: {vol_mult:.4f} (need <= 0.85 for READY)")

# Proximity to 6-month high
cur.execute("""
    SELECT MAX(close) as high_6m FROM daily_prices
    WHERE symbol = 'ADANIGREEN' AND date >= %s::date - INTERVAL '126 days'
""", (latest,))
high_6m = float(cur.fetchone()['high_6m'])
prox = (high_6m - float(rows[0]['close'])) / high_6m
print(f"proximity_to_high: {prox:.4f} (need <= 0.03)")

# Check ema stack
close = float(rows[0]['close'])
ema50 = float(rows[0]['ema_50'])
ema200 = float(rows[0]['ema_200'])
print(f"close > ema50 > ema200: {close > ema50 > ema200} (close={close}, ema50={ema50}, ema200={ema200})")

# Now: check which condition each stock FAILS
# Let's find stocks that are closest to READY_TO_BREAKOUT
# These need: prox <= 0.03 AND close>ema50>ema200 AND price_range_5d <= 0.025 AND vol <= 0.85*avg

# First, find stocks with good proximity and trend
cur.execute("""
    SELECT symbol, close, ema_50, ema_200, rolling_high_6m,
           (rolling_high_6m - close) / NULLIF(rolling_high_6m, 0) as proximity,
           volume, avg_volume_20d,
           volume / NULLIF(avg_volume_20d, 0) as vol_multiplier
    FROM daily_prices
    WHERE date = %s
      AND close > ema_50 AND ema_50 >= ema_200
      AND rolling_high_6m > 0
      AND (rolling_high_6m - close) / rolling_high_6m <= 0.03
    ORDER BY (rolling_high_6m - close) / rolling_high_6m
    LIMIT 10
""", (latest,))

print("\n=== Stocks with good proximity + EMA stack ===")
prox_stocks = cur.fetchall()
for s in prox_stocks:
    print(f"  {s['symbol']}: prox={s['proximity']:.4f}, vol_mult={s['vol_multiplier']:.4f}, close={s['close']}, ema50={s['ema_50']}")

# Now let's also check the condition_breakout_10d computation directly:
# condition_breakout_10d = close > high_10d  
# But high_10d in the indicator engine is computed as df["high"].rolling(10).max().shift(1)
# So it's the 10-day high from the PREVIOUS row
# Let me check what high_10d values look like
cur.execute("""
    SELECT symbol, close, high_10d, close > high_10d as manual_break10d, condition_breakout_10d
    FROM daily_prices
    WHERE date = %s AND close > high_10d
    LIMIT 10
""", (latest,))

print("\n=== Stocks where close > high_10d ===")
break_stocks = cur.fetchall()
for s in break_stocks:
    print(f"  {s['symbol']}: close={s['close']}, high_10d={s['high_10d']}, manual={s['manual_break10d']}, db={s['condition_breakout_10d']}")

if not break_stocks:
    print("  NONE FOUND - no stock has close > high_10d on the latest date")

# How many pass the volume surge test?
cur.execute("""
    SELECT COUNT(*) FROM daily_prices
    WHERE date = %s 
      AND close > ema_50 AND ema_50 >= ema_200
      AND volume / NULLIF(avg_volume_20d, 0) >= 1.3
""", (latest,))
vol_surge = cur.fetchone()['count']
print(f"\nStocks with close>ema50>=ema200 AND vol_mult>=1.3: {vol_surge}")

# And how many pass volume dry-up?
cur.execute("""
    SELECT COUNT(*) FROM daily_prices
    WHERE date = %s 
      AND close > ema_50 AND ema_50 >= ema_200
      AND volume / NULLIF(avg_volume_20d, 0) <= 0.85
""", (latest,))
vol_dry = cur.fetchone()['count']
print(f"Stocks with close>ema50>=ema200 AND vol_mult<=0.85: {vol_dry}")

conn.close()
