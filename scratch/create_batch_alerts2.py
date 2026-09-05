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
    {"symbol": "PREMIERENE", "pullback": 1005, "breakout": 1050},
    {"symbol": "APARINDS", "pullback": 16200, "breakout": 17200},
    {"symbol": "STLTECH", "pullback": 605, "breakout": 675},
    {"symbol": "E2E", "pullback": None, "breakout": 690}, # Pullback omitted (current 602 <= 610)
    {"symbol": "GPIL", "pullback": None, "breakout": 260}  # Pullback omitted (current 237 <= 245)
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
