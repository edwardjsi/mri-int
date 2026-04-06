import logging
import pandas as pd
import io
import requests
from engine_core.ingestion_engine import load_stocks, load_indices

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_nifty500_symbols():
    """Fetch the current Nifty 500 symbol list from NSE."""
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    try:
        res = requests.get(url, timeout=15)
        df = pd.read_csv(io.StringIO(res.text))
        return df['Symbol'].tolist()
    except Exception as e:
        logger.error(f"Failed to fetch Nifty 500 list: {e}")
        return []

def reseed_history():
    """One-time script to pull 3 years of history for the entire Nifty 500."""
    logger.info("=== Starting One-Time 3-Year Historical Reseed ===")
    
    # 1. Reseed Index
    logger.info("[1/2] Reseeding NIFTY 50 Index (3 years)...")
    load_indices(period="3y")
    
    # 2. Reseed Stocks
    symbols = get_nifty500_symbols()
    if not symbols:
        logger.error("No symbols found. Aborting.")
        return
        
    logger.info(f"[2/2] Reseeding {len(symbols)} stocks (3 years)...")
    load_stocks(symbols, period="3y")
    
    logger.info("=== Historical Reseed Complete ===")
    logger.info("You can now run 'python scripts/check_db_size.py' to see the final usage.")

if __name__ == "__main__":
    reseed_history()
