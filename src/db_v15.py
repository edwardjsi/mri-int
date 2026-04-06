import psycopg2
from psycopg2.extras import execute_batch
import logging
import os

# TRACING: Version 15 (ISOLATION)
print(f"DEBUG: LOADING src/db_v15.py from {os.path.abspath(__file__)}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_connection():
    from src.config import get_db_credentials, DB_SSL
    creds = get_db_credentials()
    connect_kwargs = dict(
        host=creds["host"], port=creds.get("port", 5432),
        dbname=creds["dbname"], user=creds["username"],
        password=creds["password"], connect_timeout=30,
    )
    if DB_SSL: connect_kwargs["sslmode"] = "require"
    return psycopg2.connect(**connect_kwargs)

def initialize_core_schema_v15():
    """Nuclear Schema Migration (Version 15.0 - ISOLATION)."""
    logger.info("🛠️ [src/db_v15.py] INITIALIZING SCHEMA")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE IF NOT EXISTS public.market_index_prices (id SERIAL PRIMARY KEY, symbol VARCHAR(20), date DATE, open NUMERIC, high NUMERIC, low NUMERIC, close NUMERIC, volume BIGINT, created_at TIMESTAMPTZ DEFAULT NOW(), UNIQUE(symbol, date));")
            conn.commit()
    finally:
        conn.close()

def insert_index_prices(records):
    if not records: return
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            execute_batch(cur, "INSERT INTO market_index_prices (symbol, date, open, high, low, close, volume) VALUES (%(symbol)s, %(date)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s) ON CONFLICT (symbol, date) DO NOTHING;", records)
            conn.commit()
    finally:
        conn.close()

def insert_daily_prices(records):
    if not records: return
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            execute_batch(cur, "INSERT INTO daily_prices (symbol, date, open, high, low, close, volume) VALUES (%(symbol)s, %(date)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s) ON CONFLICT (symbol, date) DO NOTHING;", records)
            conn.commit()
    finally:
        conn.close()
