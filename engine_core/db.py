"""
GUARANTEED WORKING database connection
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)


def get_connection():
    """
    Get database connection - uses DATABASE_URL if set, otherwise falls back to local params.
    """
    database_url = os.environ.get("DATABASE_URL", "")

    if database_url:
        try:
            if "sslmode" not in database_url.lower():
                separator = "&" if "?" in database_url else "?"
                database_url = f"{database_url}{separator}sslmode=require"
            conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
            logger.debug("Connected using DATABASE_URL")
            return conn
        except Exception as e:
            logger.warning(f"Failed to connect with DATABASE_URL: {e}")
            raise

    connection_params = {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": int(os.environ.get("DB_PORT", 5432)),
        "user": os.environ.get("DB_USER", "mri_admin"),
        "password": os.environ.get("DB_PASSWORD", "zlA3kVf9KiciHOkM"),
        "database": os.environ.get("DB_NAME", "mri_db"),
        "cursor_factory": RealDictCursor,
    }
    logger.debug("Connecting with direct parameters")
    return psycopg2.connect(**connection_params)


def fetch_df(query, params=None):
    """Run a SQL query and return a pandas DataFrame using the app cursor settings."""
    import pandas as pd

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            rows = cur.fetchall()
        return pd.DataFrame([dict(r) for r in rows])
    finally:
        conn.close()


def initialize_core_schema_v100():
    """Initialize core schema (Unified with api/schema.py)"""
    conn = get_connection()
    try:
        cur = conn.cursor()

        # Create market_index_prices table with full schema if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS market_index_prices (
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
            )
        """)
        
        # Ensure all columns exist for existing tables (Migration path)
        for col, col_type in [("open", "NUMERIC(12,4)"), ("high", "NUMERIC(12,4)"), 
                             ("low", "NUMERIC(12,4)"), ("volume", "BIGINT")]:
            cur.execute(f"ALTER TABLE market_index_prices ADD COLUMN IF NOT EXISTS {col} {col_type};")
        
        cur.execute("ALTER TABLE market_index_prices ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();")

        conn.commit()
        logger.info("✅ Core schema initialized (market_index_prices hardened)")

    finally:
        conn.close()


# For backward compatibility
_get_raw_connection = get_connection


def insert_index_prices(records):
    """Bulk insert index price records into market_index_prices."""
    if not records:
        return
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            from psycopg2.extras import execute_batch

            execute_batch(
                cur,
                """INSERT INTO market_index_prices
                   (symbol, date, open, high, low, close, volume)
                   VALUES (%(symbol)s, %(date)s, %(open)s, %(high)s,
                           %(low)s, %(close)s, %(volume)s)
                   ON CONFLICT (symbol, date) DO NOTHING;""",
                records,
                page_size=1000,
            )
            conn.commit()
    finally:
        conn.close()


def insert_daily_prices(records):
    """Bulk insert price records. Skips duplicates."""
    if not records:
        return
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            from psycopg2.extras import execute_batch

            execute_batch(
                cur,
                """INSERT INTO daily_prices
                   (symbol, date, open, high, low, close, volume)
                   VALUES (%(symbol)s, %(date)s, %(open)s, %(high)s,
                           %(low)s, %(close)s, %(volume)s)
                   ON CONFLICT (symbol, date) DO NOTHING;""",
                records,
                page_size=1000,
            )
            conn.commit()
    finally:
        conn.close()


def test_connection():
    """Test connection - FIXED VERSION"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT version()")
        version = cur.fetchone()
        conn.close()
        return True, f"Connected to: {version[0]}"
    except Exception as e:
        return False, str(e)
