import os
import psycopg2
from psycopg2.extras import RealDictCursor

def check_scores():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set")
        return

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT MAX(date) FROM stock_scores")
        max_date = cur.fetchone()['max']
        print(f"Latest date in stock_scores: {max_date}")
        
        cur.execute("SELECT COUNT(*) FROM stock_scores WHERE date = %s", (max_date,))
        count = cur.fetchone()['count']
        print(f"Count of stocks scored on {max_date}: {count}")
        
        cur.execute("SELECT symbol FROM stock_scores WHERE date = %s LIMIT 10", (max_date,))
        rows = cur.fetchall()
        print(f"Sample symbols scored on {max_date}: {[r['symbol'] for r in rows]}")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_scores()
