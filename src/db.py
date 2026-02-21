import psycopg2
from psycopg2.extras import execute_batch
from src.config import get_db_credentials
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_connection(retries=3, delay=5):
    creds = get_db_credentials()
    for attempt in range(retries):
        try:
            conn = psycopg2.connect(
                host=creds["host"],
                port=creds.get("port", 5432),
                dbname=creds["dbname"],
                user=creds["username"],
                password=creds["password"],
                connect_timeout=30  # Increased from 10 to 30 for SSM tunnel stability
            )
            return conn
        except psycopg2.OperationalError as e:
            if attempt < retries - 1:
                logger.warning(f"Database connection failed, retrying in {delay} seconds... ({e})")
                time.sleep(delay)
            else:
                logger.error("Failed to connect to the database after multiple attempts.")
                raise


def create_tables():
    """Create all required tables if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DROP TABLE IF EXISTS daily_prices CASCADE;
        
        CREATE TABLE IF NOT EXISTS daily_prices (
            id              SERIAL PRIMARY KEY,
            symbol          VARCHAR(20)  NOT NULL,
            date            DATE         NOT NULL,
            open            NUMERIC(12,4),
            high            NUMERIC(12,4),
            low             NUMERIC(12,4),
            close           NUMERIC(12,4),
            adjusted_close  NUMERIC(12,4),
            volume          BIGINT,
            created_at      TIMESTAMP DEFAULT NOW(),
            UNIQUE(symbol, date)
        );

        CREATE INDEX IF NOT EXISTS idx_daily_prices_symbol_date
            ON daily_prices(symbol, date);

        CREATE INDEX IF NOT EXISTS idx_daily_prices_date
            ON daily_prices(date);

        CREATE TABLE IF NOT EXISTS index_prices (
            id          SERIAL PRIMARY KEY,
            symbol      VARCHAR(20)  NOT NULL,
            date        DATE         NOT NULL,
            open        NUMERIC(12,4),
            high        NUMERIC(12,4),
            low         NUMERIC(12,4),
            close       NUMERIC(12,4),
            volume      BIGINT,
            created_at  TIMESTAMP DEFAULT NOW(),
            UNIQUE(symbol, date)
        );

        CREATE INDEX IF NOT EXISTS idx_index_prices_symbol_date
            ON index_prices(symbol, date);
    """)

    conn.commit()
    cur.close()
    conn.close()
    logger.info("Tables created successfully.")


def insert_daily_prices(records):
    """Bulk insert price records. Skips duplicates."""
    conn = get_connection()
    cur = conn.cursor()

    sql = """
        INSERT INTO daily_prices
            (symbol, date, open, high, low, close, adjusted_close, volume)
        VALUES
            (%(symbol)s, %(date)s, %(open)s, %(high)s,
             %(low)s, %(close)s, %(adjusted_close)s, %(volume)s)
        ON CONFLICT (symbol, date) DO NOTHING;
    """
    execute_batch(cur, sql, records, page_size=1000)
    conn.commit()
    cur.close()
    conn.close()


def insert_index_prices(records):
    """Bulk insert index price records. Skips duplicates."""
    conn = get_connection()
    cur = conn.cursor()

    sql = """
        INSERT INTO index_prices
            (symbol, date, open, high, low, close, volume)
        VALUES
            (%(symbol)s, %(date)s, %(open)s, %(high)s,
             %(low)s, %(close)s, %(volume)s)
        ON CONFLICT (symbol, date) DO NOTHING;
    """
    execute_batch(cur, sql, records, page_size=1000)
    conn.commit()
    cur.close()
    conn.close()


def run_quality_checks():
    """Run basic data quality checks and print report."""
    conn = get_connection()
    cur = conn.cursor()

    checks = {}

    # Total row counts
    cur.execute("SELECT COUNT(*) FROM daily_prices;")
    checks["total_stock_rows"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM index_prices;")
    checks["total_index_rows"] = cur.fetchone()[0]

    # Unique symbols
    cur.execute("SELECT COUNT(DISTINCT symbol) FROM daily_prices;")
    checks["unique_stocks"] = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT symbol) FROM index_prices;")
    checks["unique_indices"] = cur.fetchone()[0]

    # Date range
    cur.execute("SELECT MIN(date), MAX(date) FROM daily_prices;")
    row = cur.fetchone()
    checks["stock_date_from"] = str(row[0])
    checks["stock_date_to"]   = str(row[1])

    cur.execute("SELECT MIN(date), MAX(date) FROM index_prices;")
    row = cur.fetchone()
    checks["index_date_from"] = str(row[0])
    checks["index_date_to"]   = str(row[1])

    # Duplicate check
    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT symbol, date, COUNT(*)
            FROM daily_prices
            GROUP BY symbol, date
            HAVING COUNT(*) > 1
        ) t;
    """)
    checks["duplicate_rows"] = cur.fetchone()[0]

    # Null close prices
    cur.execute("SELECT COUNT(*) FROM daily_prices WHERE close IS NULL;")
    checks["null_close_prices"] = cur.fetchone()[0]

    cur.close()
    conn.close()

    print("\n========== DATA QUALITY REPORT ==========")
    for key, val in checks.items():
        status = "✅" if (
            (key == "duplicate_rows"    and val == 0) or
            (key == "null_close_prices" and val == 0) or
            (key == "total_stock_rows"  and val > 0)  or
            (key == "total_index_rows"  and val > 0)  or
            (key not in ["duplicate_rows", "null_close_prices",
                         "total_stock_rows", "total_index_rows"])
        ) else "❌"
        print(f"  {status}  {key}: {val}")
    print("=========================================\n")

    return checks
