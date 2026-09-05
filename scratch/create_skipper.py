import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
sys.path.append("/home/immanuels/Desktop/mri-int")

from api.cai_alert_orchestrator import upsert_draft, approve_and_sync, CAIConfigDraft

db_url = os.getenv("DATABASE_URL")
conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)

targets = [
    {"symbol": "SKIPPER", "pullback": None, "breakout": 582},
]

try:
    for t in targets:
        symbol = t["symbol"]
        print(f"\n--- Processing {symbol} ---")
        draft = CAIConfigDraft(
            structural_break_price=None,
            pullback_lower_bound=None,
            pullback_upper_bound=t["pullback"],
            breakout_confirmation_price=t["breakout"],
            next_add_price=None
        )
        try:
            print(f"Creating draft for {symbol}...")
            upsert_draft(symbol, draft, conn)
            
            print(f"Syncing to Zerodha...")
            result = approve_and_sync(symbol, conn)
            print(result)
        except Exception as e:
            print(f"Error processing {symbol}: {e}")
            conn.rollback()
            
except Exception as e:
    print(f"Global Error: {e}")
finally:
    conn.close()
