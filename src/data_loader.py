import pandas as pd
import requests
import io
import time
import logging
from datetime import datetime, date
from tqdm import tqdm
from src.db import create_tables, insert_daily_prices, insert_index_prices, run_quality_checks
from src.config import START_DATE, END_DATE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NSE indices to track
INDICES = {
    "NIFTY50":    "^NSEI",
    "NIFTYMID":   "^NSEMDCP50",
    "NIFTYSMALL": "^CNXSC",
}

def fetch_nifty500_stock_list():
    """Fetch current Nifty 500 list from NSE."""
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept":     "text/html,application/xhtml+xml"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        # If the above fails, fallback to niftyindices.com
        if response.status_code != 200:
            url = "https://niftyindices.com/IndexConstituent/ind_nifty500list.csv"
            response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text))
        symbols = df["Symbol"].dropna().unique().tolist()
        logger.info(f"Fetched {len(symbols)} Nifty 500 symbols.")
        return symbols
    except Exception as e:
        logger.error(f"Failed to fetch Nifty 500 stock list: {e}")
        return []


def fetch_stock_history_yfinance(symbol: str, start: str, end: str) -> pd.DataFrame:
    """
    Fetch historical EOD data for a single NSE stock using yfinance.
    NSE symbols need .NS suffix on Yahoo Finance.
    """
    import yfinance as yf
    import pandas as pd
    ticker = f"{symbol}.NS"
    try:
        df = yf.download(ticker, start=start, end=end,
                         auto_adjust=True, progress=False, multi_level_index=False)
        if df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        
        # Flatten MultiIndex columns if present (yfinance 0.2.x behavior)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
            
        df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
        df["symbol"]         = symbol
        
        # Depending on yfinance version, 'close' might be named differently if auto_adjust is True
        # Often it comes back as just 'close' or 'adj close'
        if "adj_close" in df.columns and "close" not in df.columns:
             df["close"] = df["adj_close"]
             
        if "close" not in df.columns:
             logger.warning(f"No 'close' column found for {symbol}. Columns: {df.columns.tolist()}")
             return pd.DataFrame()

        df["adjusted_close"] = df["close"]
        df = df.rename(columns={"date": "date"})
        
        # Ensure all required columns exist, fill missing with 0 for safety
        for col in ["open", "high", "low", "volume"]:
            if col not in df.columns:
                df[col] = 0.0 if col != "volume" else 0
                
        df = df[["symbol", "date", "open", "high",
                 "low", "close", "adjusted_close", "volume"]]
        df = df.dropna(subset=["close"])
        return df
    except Exception as e:
        logger.warning(f"Failed to fetch {symbol}: {e}")
        return pd.DataFrame()


def fetch_index_history_yfinance(symbol: str,
                                  yahoo_ticker: str,
                                  start: str,
                                  end: str) -> pd.DataFrame:
    """Fetch index historical data from Yahoo Finance."""
    import yfinance as yf
    import pandas as pd
    try:
        df = yf.download(yahoo_ticker, start=start, end=end,
                         auto_adjust=True, progress=False, multi_level_index=False)
        if df.empty:
            return pd.DataFrame()
        df = df.reset_index()
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
            
        df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
        df["symbol"] = symbol
        df = df.rename(columns={"date": "date"})
        
        if "adj_close" in df.columns and "close" not in df.columns:
             df["close"] = df["adj_close"]
             
        for col in ["open", "high", "low", "volume"]:
            if col not in df.columns:
                df[col] = 0.0 if col != "volume" else 0
                
        df = df[["symbol", "date", "open", "high", "low", "close", "volume"]]
        df = df.dropna(subset=["close"])
        return df
    except Exception as e:
        logger.warning(f"Failed to fetch index {symbol}: {e}")
        return pd.DataFrame()


def load_indices():
    """Load all index historical data into index_prices table."""
    logger.info("Loading index data...")
    for name, ticker in INDICES.items():
        df = fetch_index_history_yfinance(name, ticker, START_DATE, END_DATE)
        if df.empty:
            logger.warning(f"No data for index {name}")
            continue
        records = df.to_dict("records")
        insert_index_prices(records)
        logger.info(f"  Loaded {len(records)} rows for {name}")
    logger.info("Index data load complete.")


def load_stocks(symbols: list, batch_size: int = 50):
    """
    Load historical EOD data for all NSE stocks.
    Processes in batches to avoid overwhelming the API.
    """
    logger.info(f"Loading stock data for {len(symbols)} symbols...")
    failed = []

    for i in tqdm(range(0, len(symbols), batch_size),
                  desc="Loading stocks"):
        batch = symbols[i:i + batch_size]
        for symbol in batch:
            df = fetch_stock_history_yfinance(symbol, START_DATE, END_DATE)
            if df.empty:
                failed.append(symbol)
                continue
            records = df.to_dict("records")
            insert_daily_prices(records)
            time.sleep(0.1)  # gentle rate limiting

    logger.info(f"Stock data load complete. Failed: {len(failed)} symbols.")
    if failed:
        logger.warning(f"Failed symbols: {failed[:20]}...")
    return failed


def run():
    """Main entry point for data ingestion."""
    logger.info("=== MRI Data Loader Starting ===")
    logger.info(f"Period: {START_DATE} to {END_DATE}")

    # Step 1 — Create tables
    logger.info("Step 1: Creating database tables...")
    create_tables()

    # Step 2 — Load indices first (fast)
    logger.info("Step 2: Loading index data...")
    load_indices()

    # Step 3 — Load stocks (slow — 2000+ symbols, be patient)
    logger.info("Step 3: Fetching Nifty 500 stock list...")
    symbols = fetch_nifty500_stock_list()

    if not symbols:
        logger.error("No symbols fetched. Check NSE connectivity.")
        return

    logger.info(f"Step 4: Loading {len(symbols)} stocks (this takes 2-4 hours)...")
    failed = load_stocks(symbols)

    # Step 5 — Quality checks
    logger.info("Step 5: Running data quality checks...")
    run_quality_checks()

    logger.info("=== Data Load Complete ===")


if __name__ == "__main__":
    run()
