import sys
from engine_core.db import get_connection
from engine_core.ingestion_engine import load_stocks

def ingest_missing_112co():
    conn = get_connection()
    cur = conn.cursor()
    
    # Get active 112co symbols
    cur.execute("SELECT symbol FROM universe_112co WHERE is_active = TRUE;")
    active_symbols = [r['symbol'] for r in cur.fetchall()]
    
    # Get symbols that have some price data
    cur.execute("SELECT DISTINCT symbol FROM daily_prices;")
    has_data = {r['symbol'] for r in cur.fetchall()}
    
    # Missing symbols
    missing = [s for s in active_symbols if s not in has_data]
    
    print(f"Found {len(missing)} active 112co symbols with NO price data.")
    if missing:
        print("Ingesting now...")
        load_stocks(missing)
    else:
        print("All 112co symbols have price data.")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    ingest_missing_112co()
