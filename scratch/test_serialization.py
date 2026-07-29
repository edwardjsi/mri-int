import os, sys, json
sys.path.insert(0, '/home/immanuels/Desktop/mri-int')
os.environ['DATABASE_URL'] = 'postgresql://neondb_owner:npg_opy4B3CZtxbd@ep-bold-mud-a1zbtu4d-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require'
os.environ['PYTHONPATH'] = '/home/immanuels/Desktop/mri-int'

from api.breakout_status import get_trend_screen
from api.deps import get_db
from fastapi.encoders import jsonable_encoder

gen = get_db()
conn = next(gen)
try:
    result = get_trend_screen(conn=conn)
    print("Execution successful.")
    
    encoded = jsonable_encoder(result)
    print("jsonable_encoder successful.")
    
    json.dumps(encoded)
    print("json.dumps successful.")
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    gen.close()
