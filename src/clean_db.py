# src/clean_db.py
import logging
from src.db import get_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def wipe_db():
    try:
        conn = get_connection()
        conn.autocommit = True
        cur = conn.cursor()
        
        logger.info("Truncating massive tables to reclaim Neon 512MB storage...")
        # CASCADE ensures we cleanly wipe any dependent relationships
        cur.execute("TRUNCATE TABLE daily_prices, index_prices, stock_scores, market_regime CASCADE;")
        
        logger.info("✅ Database completely wiped. Storage reclaimed!")
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to wipe DB: {e}")

if __name__ == "__main__":
    wipe_db()
