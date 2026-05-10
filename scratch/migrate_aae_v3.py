from api.schema import ensure_required_tables
from engine_core.db import get_connection

if __name__ == "__main__":
    conn = get_connection()
    ensure_required_tables(conn)
    conn.close()
    print("Migration complete.")
