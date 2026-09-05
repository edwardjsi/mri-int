import psycopg2
import sys

def test_conn():
    try:
        conn = psycopg2.connect(
            host="ep-bold-mud-a1zbtu4d-pooler.ap-southeast-1.aws.neon.tech",
            port=5432,
            dbname="neondb",
            user="mri_admin",
            password="9WP9SBQV6QeafagC",
            sslmode="require",
            connect_timeout=5
        )
        print("SUCCESS: neon mri_admin AWS secret password")
        
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM daily_prices;")
        print(f"daily_prices count: {cur.fetchone()[0]}")
        return
    except Exception as e:
        print(f"FAIL neon mri_admin: {e}")

    try:
        conn = psycopg2.connect(
            host="ep-bold-mud-a1zbtu4d-pooler.ap-southeast-1.aws.neon.tech",
            port=5432,
            dbname="neondb",
            user="neondb_owner",
            password="9WP9SBQV6QeafagC",
            sslmode="require",
            connect_timeout=5
        )
        print("SUCCESS: neon neondb_owner AWS secret password")
        
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM daily_prices;")
        print(f"daily_prices count: {cur.fetchone()[0]}")
        return
    except Exception as e:
        print(f"FAIL neon neondb_owner: {e}")

if __name__ == '__main__':
    test_conn()
