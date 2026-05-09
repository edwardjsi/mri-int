import os
import psycopg2
from psycopg2.extras import RealDictCursor

def check_email_logs():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not set")
        return

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM email_log ORDER BY date DESC, id DESC LIMIT 10")
        rows = cur.fetchall()
        print("Latest email logs:")
        for row in rows:
            print(row)
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_email_logs()
