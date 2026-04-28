import requests
import io
import pandas as pd
import time
import logging
from engine_fundamental.collector import fetch_and_store_financials
from engine_fundamental.pipeline import run_quality_pipeline
from api.schema import ensure_required_tables
from engine_core.db import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_nifty500_backfill():
    logger.info("🚀 Starting Nifty 500 Quality Backfill...")
    
    # 0. Sync Schema
    conn = get_connection()
    try:
        logger.info("🛠️ Syncing database schema...")
        ensure_required_tables(conn)
        logger.info("✅ Schema synced")
    finally:
        conn.close()
    
    # 1. Fetch Nifty 500 List from NSE
    url = 'https://archives.nseindia.com/content/indices/ind_nifty500list.csv'
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        df = pd.read_csv(io.StringIO(r.text))
        symbols = [str(s).strip() + ".NS" for s in df['Symbol']]
        logger.info(f"✅ Found {len(symbols)} symbols in Nifty 500")
    except Exception as e:
        logger.error(f"❌ Failed to fetch Nifty 500 list: {e}")
        return

    # 2. Iterate and process
    success_count = 0
    fail_count = 0
    
    for i, symbol in enumerate(symbols):
        logger.info(f"[{i+1}/{len(symbols)}] Processing {symbol}...")
        
        try:
            # Fetch financials
            records = fetch_and_store_financials(symbol)
            if records:
                # Run pipeline (includes trajectory)
                verdict = run_quality_pipeline(symbol)
                if verdict:
                    success_count += 1
                else:
                    fail_count += 1
            else:
                fail_count += 1
        except Exception as e:
            logger.error(f"❌ Critical error for {symbol}: {e}")
            fail_count += 1
        
        # Rate limiting to avoid Yahoo blocks
        if (i + 1) % 5 == 0:
            time.sleep(2)
            
    logger.info(f"🏁 Backfill Complete!")
    logger.info(f"✅ Successful: {success_count}")
    logger.info(f"❌ Failed/Skipped: {fail_count}")

if __name__ == "__main__":
    run_nifty500_backfill()
