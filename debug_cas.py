"""Quick diagnostic: check DB state for CAS banner."""
import os, sys
sys.path.insert(0, ".")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5433")
os.environ.setdefault("DB_NAME", "mri_db")
os.environ.setdefault("DB_USER", "mri_admin")

from api.deps import get_db

gen = get_db()
conn = next(gen)
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM daily_prices")
print(f"daily_prices rows: {cur.fetchone()[0]}")

cur.execute("SELECT MAX(date) FROM daily_prices")
print(f"Max date: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM daily_prices WHERE breakout_state IS NOT NULL")
print(f"Rows with breakout_state set: {cur.fetchone()[0]}")

cur.execute("SELECT breakout_state, COUNT(*) FROM daily_prices WHERE date = (SELECT MAX(date) FROM daily_prices) GROUP BY breakout_state")
for r in cur.fetchall():
    print(f"  breakout_state={r[0]}: {r[1]} rows")

cur.execute("SELECT COUNT(*) FROM daily_prices WHERE date = (SELECT MAX(date) FROM daily_prices)")
print(f"Total rows on latest date: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM market_regime")
print(f"market_regime rows: {cur.fetchone()[0]}")

cur.execute("SELECT classification, date FROM market_regime ORDER BY date DESC LIMIT 1")
r = cur.fetchone()
print(f"Latest regime: {r}")

cur.execute("""
    SELECT symbol, breakout_state, breakout_age, qif_score, weekly_trend_score,
           rs_90d, avg_volume_20d, rolling_high_52w
    FROM daily_prices
    WHERE date = (SELECT MAX(date) FROM daily_prices)
    LIMIT 5
""")
print("\nSample rows from latest date:")
for r in cur.fetchall():
    print(f"  {dict(r)}")

conn.close()
