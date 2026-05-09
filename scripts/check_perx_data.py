import os
import psycopg2
from psycopg2.extras import RealDictCursor

def check_db():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set")
        return

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'stock_sectors')")
        exists = cur.fetchone()['exists']
        print(f"Table 'stock_sectors' exists: {exists}")
        
        if exists:
            cur.execute("SELECT COUNT(*) FROM stock_sectors")
            count = cur.fetchone()['count']
            print(f"Row count in 'stock_sectors': {count}")
            
            cur.execute("SELECT * FROM stock_sectors LIMIT 5")
            rows = cur.fetchall()
            for row in rows:
                print(row)
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
