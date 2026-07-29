"""Test the trend-screen endpoint locally."""
import os, sys, json

sys.path.insert(0, '/home/immanuels/Desktop/mri-int')
os.environ['DATABASE_URL'] = 'postgresql://neondb_owner:npg_opy4B3CZtxbd@ep-bold-mud-a1zbtu4d-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require'
os.environ['PYTHONPATH'] = '/home/immanuels/Desktop/mri-int'

from api.breakout_status import get_trend_screen
from api.deps import get_db

gen = get_db()
conn = next(gen)
try:
    result = get_trend_screen(conn=conn)
    if 'error' in result:
        print(f"ERROR: {result['error']}")
    else:
        print(f"SUCCESS - {result.get('count', 0)} stocks")
        if result.get('results'):
            r = result['results'][0]
            print(f"First: {r['symbol']} close={r['close']} mc={r.get('market_cap_cr')}")
except Exception:
    import traceback
    traceback.print_exc()
finally:
    gen.close()
