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
    """Builds an exhaustive mapping of NSE Symbols to BSE Codes via ISIN."""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        # 1. Fetch NSE All-Equity List
        nse_url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        nse_res = requests.get(nse_url, headers=headers, timeout=15)
        nse_df = pd.read_csv(io.StringIO(nse_res.text))
        nse_df.columns = nse_df.columns.str.strip()

        # 2. Fetch BSE Master List (Full)
        bse_url = "https://www.bseindia.com/downloads1/List_of_companies.csv"
        bse_res = requests.get(bse_url, headers=headers, timeout=15)
        bse_df = pd.read_csv(io.StringIO(bse_res.text))
        bse_df.columns = bse_df.columns.str.strip()

        nse_map = nse_df[['SYMBOL', 'ISIN NUMBER']].rename(columns={'ISIN NUMBER': 'ISIN'})
        bse_map = bse_df[['Security Code', 'ISIN No']].rename(columns={'ISIN No': 'ISIN'})
        
        merged = pd.merge(nse_map, bse_map, on='ISIN', how='inner')
        translator = dict(zip(merged['SYMBOL'].str.strip(), merged['Security Code'].astype(str).str.strip()))
        
        # Manual Overrides for known discrepancies or formatting issues
        overrides = {
            "CIGNITITEC": "534756", 
            "LUMAXTECH": "532796",  
            "SKFINDIA": "500474",   
            "AGI": "500187"         
        }
        translator.update(overrides)
        
        logger.info(f"Built Wide-Net ISIN Bridge with {len(translator)} mappings.")
        return translator
    except Exception as e:
        logger.warning(f"Failed to build ISIN bridge: {e}")
        return {}

def fetch_bse_active_universe():
    """Fetches the official BSE master list of ALL active stocks."""
    logger.info("Fetching complete BSE Master List (All Groups)...")
    url = "https://www.bseindia.com/downloads1/List_of_companies.csv"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=30)
        df = pd.read_csv(io.StringIO(response.text))
        df.columns = df.columns.str.strip()
        
        if 'Status' in df.columns:
            df = df[df['Status'].str.strip() == 'Active']
        if 'Instrument' in df.columns:
            df = df[df['Instrument'].str.strip() == 'Equity']
            
        code_col = 'Scrip code' if 'Scrip code' in df.columns else 'Security Code'
        symbols = df[code_col].dropna().astype(int).astype(str).tolist()
        return symbols
    except Exception as e:
        logger.error(f"Failed to fetch BSE universe: {e}")
        return []

def get_client_holdings_symbols() -> list:
    """Fetch all unique symbols that clients have uploaded."""
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
    if symbol_upper.endswith(".NS") or symbol_upper.endswith(".BO"): symbol_upper = symbol_upper[:-3]
    if symbol_upper.startswith("BOM