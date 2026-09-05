import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()
db_url = os.getenv("DATABASE_URL")

def check_symbol(symbol):
    conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    try:
        with conn.cursor() as cur:
            # Check exactly symbol
            cur.execute("SELECT COUNT(*) as c, MIN(date) as min_d, MAX(date) as max_d FROM daily_prices WHERE symbol = %s", (symbol,))
            res1 = cur.fetchone()
            
            # Check with wildcard just in case it's NSE:SYMBOL
            cur.execute("SELECT symbol, COUNT(*) as c, MIN(date) as min_d, MAX(date) as max_d FROM daily_prices WHERE symbol LIKE %s GROUP BY symbol", ('%'+symbol+'%',))
            res2 = cur.fetchall()
            
            print(f"--- SYMBOL: {symbol} ---")
            print(f"Exact match count: {res1['c']} (Min: {res1['min_d']}, Max: {res1['max_d']})")
            if res2:
                print(f"Like match results:")
                for r in res2:
                    print(f"  {r['symbol']}: count={r['c']} (Min: {r['min_d']}, Max: {r['max_d']})")
            else:
                print("No Like matches.")
    finally:
        conn.close()

if __name__ == "__main__":
    for sym in ["SHAILY", "RATEGAIN", "AZADENGG", "IPCALAB", "HSCL", "DIVISLAB"]:
        check_symbol(sym)
