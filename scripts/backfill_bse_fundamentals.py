import os
import psycopg2
import logging
from dotenv import load_dotenv
from engine_fundamental.collector import fetch_and_store_financials

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill_bse")

def backfill_missing_fundamentals():
    url = os.environ.get("DATABASE_URL")
    if not url:
        logger.error("DATABASE_URL not found")
        return

    try:
        conn = psycopg2.connect(url)
        cur = conn.cursor()

        # 1. Get all symbols in technical scores
        cur.execute("SELECT DISTINCT symbol FROM stock_scores")
        tech_symbols = {r[0] for r in cur.fetchall()}
        
        # 2. Get all symbols in fundamental financials
        cur.execute("SELECT DISTINCT symbol FROM fundamental_financials")
        fund_symbols = {r[0] for r in cur.fetchall()}
        
        # 3. Identify mismatch
        missing_fund = sorted(list(tech_symbols - fund_symbols))
        logger.info(f"Identified {len(missing_fund)} symbols missing fundamental data.")

        if not missing_fund:
            logger.info("No missing symbols found. Everything is synced.")
            return

        # 4. Fetch data for each missing symbol
        # Process all remaining symbols
        limit = 1000
        processed = 0
        success = 0
        
        for sym in missing_fund:
            if processed >= limit:
                logger.info(f"Reached batch limit of {limit}. Stopping.")
                break
                
            logger.info(f"[{processed+1}/{limit}] Processing {sym}...")
            try:
                result = fetch_and_store_financials(sym)
                if result:
                    success += 1
            except Exception as e:
                logger.error(f"Error processing {sym}: {e}")
            
            processed += 1

        logger.info(f"Batch complete. Processed: {processed}, Successfully Backfilled: {success}")
        
        conn.close()
    except Exception as e:
        logger.error(f"Backfill failed: {e}")

if __name__ == "__main__":
    backfill_missing_fundamentals()
