import os, sys
sys.path.insert(0, '/home/immanuels/Desktop/mri-int')
os.environ['DATABASE_URL'] = 'postgresql://neondb_owner:npg_opy4B3CZtxbd@ep-bold-mud-a1zbtu4d-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require'

from api.breakout_status import get_trend_screen
from api.deps import get_db
from decimal import Decimal
import math

gen = get_db()
conn = next(gen)
result = get_trend_screen(conn=conn)

for idx, row in enumerate(result['results']):
    for k, v in row.items():
        if isinstance(v, Decimal) and v.is_nan():
            print(f"Row {idx} ({row.get('symbol')}) has Decimal NaN in {k}")
        if isinstance(v, float) and math.isnan(v):
            print(f"Row {idx} ({row.get('symbol')}) has float NaN in {k}")
