"""Sync guidance tables to database."""
from api.schema import ensure_required_tables
from engine_core.db import get_connection

conn = get_connection()
ensure_required_tables(conn)
conn.close()
print("Schema synced — guidance tables created")
