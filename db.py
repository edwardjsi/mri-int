import psycopg2
from psycopg2.extras import execute_batch
from src.config import get_db_credentials, DB_SSL
import logging
import time
import os

# TRACING: Trace absolute paths for GitHub verification
print(f"DEBUG: LOADING root db.py from {os.path.abspath(__file__)}")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_connection(retries=3, delay=5):
    creds = get_db_credentials()
    connect_kwargs = dict(
        host=creds["host"],
        port=creds.get("port", 5432),
        dbname=creds["dbname"],
        user=creds["username"],
        password=creds["password"],
        connect_timeout=30,
    )
    if DB_SSL:
        connect_kwargs["sslmode"] = "require"
    for attempt in range(retries):
        try:
            conn = psycopg2.connect(**connect_kwargs)
            return conn
        except psycopg2.OperationalError as e:
            if attempt < retries - 1:
                logger.warning(f"Database connection failed, retrying in {delay} seconds... ({e})")
                time.sleep(delay)
            else:
                logger.error("Failed to connect to the database after multiple attempts.")
                raise


from psycopg2 import sql

def create_tables():
    """Create the fresh market_index_prices relation."""
    logger.info("🛠️ [ROOT/db.py] INITIALIZING SCHEMA (Version 11.0 - Final)")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Standard Price Table
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
                    updated_at      TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(symbol, date)
                );
            """)

            # 2. Market Index Prices (Final Renaming)
            cur.execute("""
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

            # Migration for OHLCV
            migrations = [
                "ALTER TABLE public.market_index_prices ADD COLUMN IF NOT EXISTS open NUMERIC(12,4);",
                "ALTER TABLE public.market_index_prices ADD COLUMN IF NOT EXISTS high NUMERIC(12,4);",
                "ALTER TABLE public.market_index_prices ADD COLUMN IF NOT EXISTS low NUMERIC(12,4);",
                "ALTER TABLE public.market_index_prices ADD COLUMN IF NOT EXISTS volume BIGINT;",
                "CREATE INDEX IF NOT EXISTS idx_market_index_prices_symbol_date ON public.market_index_prices(symbol, date);"
            ]
            
            for cmd in migrations:
                try:
                    cur.execute(cmd)
                    conn.commit()
                except Exception as e:
                    logger.warning(f"Note: {e}")
                    conn.rollback()

            conn.commit()
            logger.info("Tables checked/created successfully.")
    except Exception as e:
        logger.error(f"Error during create_tables: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def insert_index_prices(records):
    """Bulk insert index price records into the new market_index_prices table."""
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
    """Bulk insert price records. Skips duplicates."""
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
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    adjusted_close = EXCLUDED.adjusted_close,
                    volume = EXCLUDED.volume,
                    updated_at = NOW();
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
    """Run basic data quality checks and print report."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            checks = {}
            cur.execute("SELECT COUNT(*) FROM daily_prices;")
            checks["total_stock_rows"] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM market_index_prices;")
            checks["total_index_rows"] = cur.fetchone()[0]
            cur.execute("SELECT MIN(date), MAX(date) FROM market_index_prices;")
            row = cur.fetchone()
            checks["index_date_from"] = str(row[0])
            checks["index_date_to"]   = str(row[1])
            print("\n========== DATA QUALITY REPORT ==========")
            for key, val in checks.items():
                print(f"  {key}: {val}")
            return checks
    except Exception as e:
        logger.error(f"Error during run_quality_checks: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
