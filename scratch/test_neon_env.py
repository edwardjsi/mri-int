import psycopg2
import sys
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

def test_conn():
    load_dotenv()
    database_url = os.environ.get("DATABASE_URL")
    print(f"DATABASE_URL: {database_url}")
    parsed = urlparse(database_url)
    try:
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            dbname=parsed.path.lstrip("/"),
            user=parsed.username,
            password=parsed.password,
            sslmode="require",
            connect_timeout=5
        )
        print("SUCCESS connecting to Neon!")
        
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM daily_prices;")
        print(f"daily_prices count: {cur.fetchone()[0]}")
    except Exception as e:
        print(f"FAIL: {e}")

if __name__ == '__main__':
    test_conn()
