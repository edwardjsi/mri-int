"""
Market Cap Ingestion Script
===========================
Downloads current Market Cap for all active Nifty 500 constituents
from yfinance and inserts into market_cap_history.
"""
import time
import logging
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from engine_core.db import get_connection

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('outputs/market_cap_ingestion.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

SLEEP_BETWEEN_STOCKS = 0.2

def get_active_nifty500_symbols():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT symbol FROM nifty500_universe WHERE constituent_to IS NULL")
            return [r['symbol'] for r in cur.fetchall()]
    finally:
        conn.close()

def insert_market_cap(records):
    if not records:
        return
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql_query = """
                INSERT INTO market_cap_history (symbol, date, market_cap_cr, source)
                VALUES (%(symbol)s, %(date)s, %(market_cap_cr)s, %(source)s)
                ON CONFLICT (symbol, date) DO UPDATE SET
                    market_cap_cr = EXCLUDED.market_cap_cr,
                    source = EXCLUDED.source,
                    created_at = NOW();
            """
            from psycopg2.extras import execute_batch
            execute_batch(cur, sql_query, records, page_size=500)
            conn.commit()
    except Exception as e:
        logger.error(f"Error inserting market caps: {e}")
        conn.rollback()
    finally:
        conn.close()

def run():
    os.makedirs("outputs", exist_ok=True)
    symbols = get_active_nifty500_symbols()
    if not symbols:
        logger.warning("No active Nifty 500 symbols found in universe table.")
        return
    
    logger.info(f"Fetching market cap for {len(symbols)} symbols...")
    today = datetime.today().strftime("%Y-%m-%d")
    
    records = []
    failed = []
    
    for i, symbol in enumerate(symbols, 1):
        if i % 50 == 0:
            logger.info(f"Processed {i}/{len(symbols)}...")
        
        # yfinance tickers for NSE usually end in .NS
        ticker_ns = f"{symbol}.NS"
        ticker_bo = f"{symbol}.BO"
        
        mcap = None
        for ticker in [ticker_ns, ticker_bo]:
            try:
                info = yf.Ticker(ticker).info
                if info and "marketCap" in info and info["marketCap"] is not None:
                    mcap = info["marketCap"]
                    break
            except Exception:
                pass
        
        if mcap is not None:
            mcap_cr = mcap / 10000000  # Convert to Crores
            records.append({
                "symbol": symbol,
                "date": today,
                "market_cap_cr": mcap_cr,
                "source": "yahoo"
            })
        else:
            failed.append(symbol)
            
        time.sleep(SLEEP_BETWEEN_STOCKS)
        
    if records:
        insert_market_cap(records)
        logger.info(f"Inserted/Updated {len(records)} market cap records for {today}.")
    
    if failed:
        logger.warning(f"Failed to fetch market cap for {len(failed)} symbols: {failed}")

if __name__ == "__main__":
    run()
