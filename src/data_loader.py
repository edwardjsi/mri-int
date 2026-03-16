# src/data_loader.py
import pandas as pd
import requests
import io
import time
import logging
from datetime import datetime, date, timedelta
from tqdm import tqdm
from src.db import create_tables, insert_daily_prices, insert_index_prices, run_quality_checks, get_connection
from src.config import START_DATE, END_DATE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NSE indices to track
INDICES = {
    "NIFTY50":    "^NSEI",
    "NIFTYMID":   "^NSEMDCP50",
    "NIFTYSMALL": "^CNXSC",
}

def get_last_date(table, fallback=START_DATE):
    """Get the latest date in a table. Returns a start date for incremental fetch."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT MAX(date) FROM {table}")
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row and row[0]:
            start = row[0] - timedelta(days=5)
            return start.strftime("%Y-%m-%d")
    except Exception:
        pass
    return fallback

def build_symbol_translator() -> dict:
    """
    Builds an in-memory dictionary mapping NSE Symbols to BSE Numeric Codes
    using the ISIN as the bridge. e.g., {'M&M': '500520', 'TCS': '532540'}
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        # 1. Fetch NSE Master List
        nse_url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        nse_res = requests.get(nse_url, headers=headers, timeout=15)
        nse_df = pd.read_csv(io.StringIO(nse_res.text))
        nse_df.columns = nse_df.columns.str.strip()
        nse_map = nse_df[['SYMBOL', 'ISIN NUMBER']].rename(columns={'ISIN NUMBER': 'ISIN'})

        # 2. Fetch BSE Master List
        bse_url = "https://www.bseindia.com/downloads1/List_of_companies.csv"
        bse_res = requests.get(bse_url, headers=headers, timeout=15)
        bse_df = pd.read_csv(io.StringIO(bse_res.text))
        bse_df.columns = bse_df.columns.str.strip()
        bse_map = bse_df[['Security Code', 'ISIN No']].rename(columns={'ISIN No': 'ISIN'})

        # 3. Zip them together on ISIN
        merged = pd.merge(nse_map, bse_map, on='ISIN', how='inner')
        
        # 4. Create the translation dictionary
        translator = dict(zip(merged['SYMBOL'].str.strip(), merged['Security Code'].astype(str).str.strip()))
        logger.info(f"Built ISIN Bridge: Successfully mapped {len(translator)} NSE symbols to BSE codes.")
        return translator
    except Exception as e:
        logger.warning(f"Failed to build ISIN bridge: {e}")
        return {}

def fetch_nifty500_stock_list():
    """Fallback function: Fetch current Nifty 500 list from NSE."""
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text))
        return df["Symbol"].dropna().unique().tolist()
    except Exception as e:
        logger.error(f"Failed to fetch Nifty 500 fallback: {e}")
        return []

def fetch_bse_active_universe():
    """Fetches the official BSE master list of active, liquid stocks (Groups A & B)."""
    logger.info("Fetching official BSE Master List...")
    url = "https://www.bseindia.com/downloads1/List_of_companies.csv"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            return fetch_nifty500_stock_list()
            
        df = pd.read_csv(io.StringIO(response.text))
        df.columns = df.columns.str.strip()
        
        if 'Status' in df.columns:
            df = df[df['Status'].str.strip() == 'Active']
        if 'Instrument' in df.columns:
            df = df[df['Instrument'].str.strip() == 'Equity']
        if 'Group' in df.columns:
            df = df[df['Group'].str.strip().isin(['A', 'B'])]
            
        code_col = 'Scrip code' if 'Scrip code' in df.columns else 'Security Code'
        symbols = df[code_col].dropna().astype(int).astype(str).tolist()
        
        logger.info(f"Successfully fetched {len(symbols)} liquid BSE numeric codes.")
        return symbols
    except Exception as e:
        logger.error(f"Failed to fetch BSE universe: {e}")
        return fetch_nifty500_stock_list()

def get_client_holdings_symbols() -> list:
    """Fetch all unique symbols that clients have uploaded for Risk Audit monitoring."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'client_external_holdings');")
        if not cur.fetchone()[0]:
            return []

        cur.execute("SELECT DISTINCT symbol FROM client_external_holdings")
        symbols = [r[0] for r in cur.fetchall() if r[0]]
        cur.close()
        conn.close()
        return symbols
    except Exception:
        return []

def fetch_stock_history_yfinance(user_symbol: str, start: str, end: str, translator: dict) -> pd.DataFrame:
    """Fetches data using the ISIN bridge, but saves under the original user symbol."""
    import yfinance as yf
    
    symbol_upper = user_symbol.upper().strip()
    if symbol_upper.endswith(".NS") or symbol_upper.endswith(".BO"):
        symbol_upper = symbol_upper[:-3]
    if symbol_upper.startswith("BOM") and symbol_upper[3:].isdigit():
        symbol_upper = symbol_upper[3:]
        
    # Translate using ISIN Bridge
    safe_search_term = translator.get(symbol_upper, symbol_upper)
    df = pd.DataFrame()
    
    if safe_search_term.isdigit():
        primary_suffix, fallback_suffix = ".BO", ".NS"
    else:
        primary_suffix, fallback_suffix = ".NS", ".BO"
        
    try:
        ticker_primary = f"{safe_search_term}{primary_suffix}"
        raw = yf.download(ticker_primary, start=start, end=end, auto_adjust=True, progress=False, multi_level_index=False)
        if raw is not None and not raw.empty:
            df = raw
    except Exception:
        pass
        
    if df.empty:
        try:
            ticker_fallback = f"{safe_search_term}{fallback_suffix}"
            raw = yf.download(ticker_fallback, start=start, end=end, auto_adjust=True, progress=False, multi_level_index=False)
            if raw is not None and not raw.empty:
                df = raw
        except Exception:
            pass
            
    if df.empty:
        return pd.DataFrame()

    try:
        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
            
        df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
        
        # CRITICAL: Save using the original user symbol so the UI matches
        df["symbol"] = symbol_upper
        
        if "adj_close" in df.columns and "close" not in df.columns:
             df["close"] = df["adj_close"]
             
        if "close" not in df.columns:
             return pd.DataFrame()

        df["adjusted_close"] = df["close"]
        df = df.rename(columns={"date": "date"})
        
        for col in ["open", "high", "low", "volume"]:
            if col not in df.columns:
                df[col] = 0.0 if col != "volume" else 0
                
        df = df[["symbol", "date", "open", "high", "low", "close", "adjusted_close", "volume"]]
        df = df.dropna(subset=["close"])
        return df
    except Exception:
        return pd.DataFrame()

def fetch_index_history_yfinance(symbol: str, yahoo_ticker: str, start: str, end: str) -> pd.DataFrame:
    """Fetch index historical data from Yahoo Finance."""
    import yfinance as yf
    try:
        df = yf.download(yahoo_ticker, start=start, end=end, auto_adjust=True, progress=False, multi_level_index=False)
        if df.empty: return pd.DataFrame()
        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex): df.columns = [col[0] for col in df.columns]
        df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
        df["symbol"] = symbol
        df = df.rename(columns={"date": "date"})
        if "adj_close" in df.columns and "close" not in df.columns: df["close"] = df["adj_close"]
        for col in ["open", "high", "low", "volume"]:
            if col not in df.columns: df[col] = 0.0 if col != "volume" else 0
        df = df[["symbol", "date", "open", "high", "low", "close", "volume"]]
        return df.dropna(subset=["close"])
    except Exception: return pd.DataFrame()

def load_indices():
    logger.info("Loading index data...")
    incremental_start = get_last_date("index_prices")
    for name, ticker in INDICES.items():
        df = fetch_index_history_yfinance(name, ticker, incremental_start, END_DATE)
        if not df.empty:
            insert_index_prices(df.to_dict("records"))

def load_stocks(symbols: list, translator: dict, batch_size: int = 50):
    incremental_start = get_last_date("daily_prices")
    logger.info(f"Loading stock data for {len(symbols)} symbols from {incremental_start}...")
    failed = []

    for i in tqdm(range(0, len(symbols), batch_size), desc="Loading stocks"):
        batch = symbols[i:i + batch_size]
        for symbol in batch:
            df = fetch_stock_history_yfinance(symbol, incremental_start, END_DATE, translator)
            if df.empty:
                failed.append(symbol)
                continue
            insert_daily_prices(df.to_dict("records"))
            time.sleep(0.1)

    logger.info(f"Stock data load complete. Failed: {len(failed)} symbols.")
    return failed

def run():
    logger.info("=== MRI Data Loader Starting ===")
    create_tables()
    load_indices()

    logger.info("Building ISIN Translator Bridge...")
    translator = build_symbol_translator()

    logger.info("Fetching BSE Universe & Client Custom Lists...")
    bse_symbols = fetch_bse_active_universe()
    client_custom_symbols = get_client_holdings_symbols()

    symbols = list(set(bse_symbols + client_custom_symbols))
    if not symbols:
        logger.error("No symbols fetched. Check connectivity.")
        return

    logger.info(f"Loading {len(symbols)} robust symbols...")
    load_stocks(symbols, translator)

    logger.info("Running data quality checks...")
    run_quality_checks()
    logger.info("=== Data Load Complete ===")

if __name__ == "__main__":
    run()