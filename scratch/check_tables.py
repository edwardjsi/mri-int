from engine_core.db import get_connection
try:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    tables = cur.fetchall()
    print("Tables in DB:")
    for t in tables:
        print(t['table_name'])
except Exception as e:
    print(f"Error connecting: {e}")
