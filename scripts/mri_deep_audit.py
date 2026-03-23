import sys
import os
# Add parent directory to sys.path to find src module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db import get_connection

def deep_audit():
    conn = get_connection()
    cur = conn.cursor()
    print("--- 1. Tables and Sizes (Estimated) ---")
    try:
        cur.execute("""
            SELECT
                relname AS "relation",
                pg_size_pretty(pg_total_relation_size(C.oid)) AS "total_size"
            FROM pg_class C
            LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
            WHERE nspname NOT IN ('pg_catalog', 'information_schema')
              AND C.relkind <> 'i'
              AND nspname !~ '^pg_toast'
            ORDER BY pg_total_relation_size(C.oid) DESC
        """)
        rows = cur.fetchall()
        for r in rows:
            print(f"Table: {r[0]}, Total Size: {r[1]}")
    except Exception as e:
        print(f"Error checking table sizes: {e}")
        conn.rollback()

    print("\n--- 2. Database List and Sizes ---")
    try:
        cur.execute("SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database;")
        rows = cur.fetchall()
        for r in rows:
            print(f"Database: {r[0]}, Size: {r[1]}")
    except Exception as e:
        print(f"Error checking database sizes: {e}")
        conn.rollback()

    cur.close()
    conn.close()

if __name__ == "__main__":
    deep_audit()
