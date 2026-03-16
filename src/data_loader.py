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

INDICES = {
    "NIFTY50":    "^NSEI",
    "NIFTYMID":   "^NSEMDCP50",
    "NIFTYSMALL": "^CNXSC",
}

def get_last_date(table, fallback=START_DATE):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT MAX(date) FROM {table}")
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row and row[0]:
            return (row[0] - timedelta(days=5)).strftime("%Y-%m-%d")
    except Exception: pass
    return fallback

def build_symbol_translator() -> dict:
    """Exhaustive ISIN Bridge with built-in overrides for broker-specific tickers."""
    headers = {"User-Agent": "Mozilla/5.0"}
    translator = {}
    try:
        # NSE Master
        nse_res = requests.get("https://archives.nseindia.com/content/equities/EQUITY_L.csv", headers=headers, timeout=15)
        nse_df = pd.read_csv(io.StringIO(nse_res.text))
        nse_df.columns = nse_df.columns.str.strip()

        # BSE Master
        bse_res = requests.get("https://www.bseindia.com/downloads1/List_of_companies.csv", headers=headers, timeout=15)
        bse_df = pd.read_csv(io.StringIO(bse_res.text))
        bse_df.columns = bse_df.columns.str.strip()

        merged = pd.merge(
            nse_df[['SYMBOL', 'ISIN NUMBER']].rename(columns={'ISIN NUMBER': 'ISIN'}),
            bse_df[['Security Code', 'ISIN No']].rename(columns={'ISIN No': 'ISIN'}),
            on='ISIN', how='inner'
        )
        translator = dict(zip(merged['SYMBOL'].str.strip(), merged['Security Code'].astype(str).str.strip()))
        
        # Wholesome Overrides for common broker export discrepancies
        translator.update({
            "CIGNITITEC": "534756", "LUMAXTECH": "532796", 
            "ONEGLOBAL": "512527", "SHILCTECH": "532888",
            "AGI": "500187", "SKFINDIA": "500474",
            "AGIGREEN": "500187", "CIGNITI": "534756"
        })
        logger.info(f"Translator ready with {len(translator)} mappings.")
    except Exception as e:
        logger.warning(f"Bridge build failed, using empty map: {e}")
    return translator

def fetch_stock_history_yfinance(user_symbol: str, start: str, end: str, translator: dict) -> pd.DataFrame:
    import yfinance as yf
    sym = user_symbol.upper().strip().split('.')[0].replace("BOM", "")
    
    # Priority 1: ISIN Bridge Numeric (.BO)
    # Priority 2: Direct NSE (.NS)
    # Priority 3: Direct BSE (.BO)
    codes_to_try = []
    if sym in translator:
        codes_to_try = [f"{translator[sym]}.BO", f"{sym}.NS", f"{sym}.BO"]
    else:
        codes_to_try = [f"{sym}.NS", f"{sym}.BO"]

    df = pd.DataFrame()
    for ticker in codes_to_try:
        try:
            raw = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False, multi_level_index=False)
            if raw is not None and not raw.empty:
                df = raw
                break
        except Exception: continue
            
    if df.empty: return pd.DataFrame()

    df = df.reset_index()
    if isinstance(df.columns, pd.MultiIndex): df.columns = [col[0] for col in df.columns]
    df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
    df["symbol"] = user_symbol
    if "adj_close" in df.columns and "close" not in df.columns: df["close"] = df["adj_close"]
    df["adjusted_close"] = df.get("close")
    df = df.rename(columns={"date": "date"})
    for col in ["open", "high", "low", "volume"]:
        if col not in df.columns: df[col] = 0.0
    return df[["symbol", "date", "open", "high", "low", "close", "adjusted_close", "volume"]].dropna(subset=["close"])

def run():
    create_tables()
    translator = build_symbol_translator()
    
    # Load Indices
    start = get_last_date("index_prices")
    for name, ticker in INDICES.items():
        import yfinance as yf
        idx_raw = yf.download(ticker, start=start, end=END_DATE, auto_adjust=True, progress=False)
        if not idx_raw.empty:
            idx_raw = idx_raw.reset_index()
            idx_raw.columns = [c.lower().replace(" ", "_") for c in idx_raw.columns]
            idx_raw["symbol"] = name
            insert_index_prices(idx_raw.to_dict("records"))

    # Load All Known Stocks
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT DISTINCT symbol FROM client_external_holdings")
    symbols = [r[0] for r in cur.fetchall()]
    conn.close()
    
    # Add Nifty 500
    headers = {"User-Agent": "Mozilla/5.0"}
    n500 = pd.read_csv(io.StringIO(requests.get("https://archives.nseindia.com/content/indices/ind_nifty500list.csv", headers=headers).text))
    symbols = list(set(symbols + n500['Symbol'].tolist()))

    load_start = get_last_date("daily_prices")
    for sym in tqdm(symbols, desc="Updating Daily Prices"):
        df = fetch_stock_history_yfinance(sym, load_start, END_DATE, translator)
        if not df.empty:
            insert_daily_prices(df.to_dict("records"))
        time.sleep(0.1)
    run_quality_checks()

if __name__ == "__main__":
    run()