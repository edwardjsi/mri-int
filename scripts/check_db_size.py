from engine_core.db import get_connection
import os

def check_db_size():
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Total DB size
        cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
        db_size = cur.fetchone()[0]
        
        # Table sizes
        cur.execute("""
            SELECT
                relname AS "table_name",
                pg_size_pretty(pg_total_relation_size(relid)) AS "total_size",
                (SELECT reltuples FROM pg_class WHERE oid = relid)::bigint AS "row_count"
            FROM pg_catalog.pg_statio_user_tables
            ORDER BY pg_total_relation_size(relid) DESC;
        """)
        tables = cur.fetchall()
        
        print(f"Total Database Size: {db_size}")
        print("-" * 50)
        print(f"{'Table Name':<25} | {'Size':<10} | {'Rows':<10}")
        print("-" * 50)
        for table, size, rows in tables:
            print(f"{table:<25} | {size:<10} | {rows:<10}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error checking DB size: {e}")

if __name__ == "__main__":
    check_db_size()
