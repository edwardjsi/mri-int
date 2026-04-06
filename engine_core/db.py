import psycopg2
from psycopg2.extras import execute_batch
from engine_core.config import get_db_credentials, DB_SSL
import logging
import time
import os

# TRACING: Final Version 12
print(f"DEBUG: LOADING src/db.py from {os.path.abspath(__file__)}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_connection(retries=3, delay=5):
    creds = get_db_credentials()
    connect_kwargs = dict(
        host=creds["host"], port=creds.get("port", 5432),
        dbname=creds["dbname"], user=creds["username"],
        password=creds["password"], connect_timeout=30,
    )
    if DB_SSL: connect_kwargs["sslmode"] = "require"
    for attempt in range(retries):
        try:
            return psycopg2.connect(**connect_kwargs)
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay)
            else: raise


from psycopg2 import sql

def initialize_core_schema_v12():
    """Create the fresh market_index_prices relation (Version 12)."""
    logger.info("🛠️ [src/db.py] INITIALIZING SCHEMA (Version 12 - Mandatory Rename)")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public.daily_prices (
                    id              BIGSERIAL PRIMARY KEY,
                    symbol          VARCHAR(20)  NOT NULL,
                    date            DATE         NOT NULL,
                    open            NUMERIC(12,4),
                    high            NUMERIC(12,4),
                    low             NUMERIC(12,4),
                    close           NUMERIC(12,4),
                    adjusted_close  NUMERIC(12,4),
                    volume          BIGINT,
                    created_at      TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(symbol, date)
                );
                CREATE TABLE IF NOT EXISTS public.market_index_prices (
                    id          BIGSERIAL PRIMARY KEY,
                    symbol      VARCHAR(20)  NOT NULL,
                    date        DATE         NOT NULL,
                    open        NUMERIC(12,4),
                    high        NUMERIC(12,4),
                    low         NUMERIC(12,4),
                    close       NUMERIC(12,4),
                    volume      BIGINT,
                    created_at  TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(symbol, date)
                );
            """)
            conn.commit()
            logger.info("Tables checked/created successfully.")
    except Exception as e:
        logger.error(f"Error during initialize_core_schema_v12: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def insert_index_prices(records):
    """Bulk insert index price records into market_index_prices."""
    if not records: return
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql_query = """
                INSERT INTO market_index_prices
                    (symbol, date, open, high, low, close, volume)
                VALUES
                    (%(symbol)s, %(date)s, %(open)s, %(high)s,
                     %(low)s, %(close)s, %(volume)s)
                ON CONFLICT (symbol, date) DO NOTHING;
            """
            execute_batch(cur, sql_query, records, page_size=1000)
            conn.commit()
    except Exception as e:
        logger.error(f"Error inserting index prices: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def insert_daily_prices(records):
    """Bulk insert daily prices."""
    if not records: return
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql_query = """
                INSERT INTO daily_prices
                    (symbol, date, open, high, low, close, adjusted_close, volume)
                VALUES
                    (%(symbol)s, %(date)s, %(open)s, %(high)s,
                     %(low)s, %(close)s, %(adjusted_close)s, %(volume)s)
                ON CONFLICT (symbol, date) DO UPDATE SET
                    close = EXCLUDED.close, volume = EXCLUDED.volume;
            """
            execute_batch(cur, sql_query, records, page_size=1000)
            conn.commit()
    except Exception as e:
        logger.error(f"Error inserting daily prices: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def run_quality_checks():
    """Basic checks."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            checks = {}
            cur.execute("SELECT COUNT(*) FROM daily_prices;")
            checks["total_stock_rows"] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM market_index_prices;")
            checks["total_index_rows"] = cur.fetchone()[0]
            print(f"REPORT: {checks}")
            return checks
    except Exception as e:
        logger.error(f"Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
