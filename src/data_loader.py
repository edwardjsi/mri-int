import pandas as pd
import numpy as np
import yfinance as yf
import requests
import io
import logging
import time
from datetime import datetime
from src.db import get_connection, create_tables, insert_daily_prices

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def build_symbol_translator() -> dict:
    """Builds a mapping of NSE symbols to BSE codes for dual-exchange fallback."""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        nse_res = requests.get("https://archives.nseindia.com/content/equities/EQUITY_L.csv", headers=headers, timeout=15)
        nse_df = pd.read_csv(io.StringIO(nse_res.text))
        bse_res = requests.get("https://www.bseindia.com/downloads1/List_of_companies.csv", headers=headers, timeout=15)
        bse_df = pd.read_csv(io.StringIO(bse_res.text))
        
        # Fuzzy column finder
        bse_code_col = [c for c in bse_df.columns if 'Security Code' in c or 'Scrip Code' in c][0]
        bse_isin_col = [c for c in bse_df.columns if 'ISIN' in c][0]
        nse_isin_col = [c for c in nse_df.columns if 'ISIN' in c][0]

        merged = pd.merge(
            nse_df[['SYMBOL', nse_isin_col]].rename(columns={nse_isin_col: 'ISIN'}),
            bse_df[[bse_code_col, bse_isin_col]].rename(columns={bse_code_col: 'BSE_CODE', bse_isin_col: 'ISIN'}),
            on='ISIN', how='inner'
        )
        translator = dict(zip(merged['SYMBOL'].str.strip(), merged['BSE_CODE'].astype(str).str.strip()))
    except Exception as e:
        logger.error(f"Bridge build failed: {e}. Using mandatory overrides.")
        translator = {}

    # Critical overrides for your specific portfolio
    translator.update({
        "CIGNITITEC": "534758", "LUMAXTECH": "532796", "SKFINDIAN": "500472", 
        "AGI": "500187", "ONEGLOBAL": "514330", "SHILCTECH": "531201"
    })
    return translator

def load_indices():
    """Daily pipeline entry point for index data."""
    # This reuse the existing logic in run() but encapsulated
    logger.info("Fetching NIFTY 50 Index data...")
    idx_raw = yf.download("^NSEI", period="3y", progress=False, auto_adjust=True)
    if not idx_raw.empty:
        idx_df = idx_raw.reset_index()
        idx_df.columns = [c[0].lower().replace(" ", "_") if isinstance(idx_df.columns, pd.MultiIndex) else str(c).lower().replace(" ", "_") for c in idx_df.columns]
        idx_df['symbol'] = 'NIFTY50'
        idx_df['date'] = pd.to_datetime(idx_df['date']).dt.date
        idx_df['adjusted_close'] = idx_df.get('adj_close', idx_df.get('close'))
        from src.db import insert_index_prices
        insert_index_prices(idx_df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']].dropna().to_dict('records'))
    logger.info("✅ Index data loaded")

def load_stocks(symbols: list):
    """Daily pipeline entry point for bulk stock data."""
    if not symbols: return
    create_tables()
    translator = build_symbol_translator()
    
    # Using the existing per-stock logic but optimized for the pipeline call
    for sym in symbols:
        time.sleep(1.2) # Anti-Throttle
        bse_code = translator.get(sym, sym)
        search_list = [f"{bse_code}.BO", f"{sym}.NS", f"{sym}.BO"] if bse_code.isdigit() else [f"{sym}.NS", f"{sym}.BO"]
        
        df = pd.DataFrame()
        for ticker in search_list:
            try:
                raw = yf.download(ticker, period="3y", progress=False, auto_adjust=True)
                if not raw.empty:
                    df = raw.reset_index()
                    df.columns = [c[0].lower().replace(" ", "_") if isinstance(df.columns, pd.MultiIndex) else str(c).lower().replace(" ", "_") for c in df.columns]
                    break
            except Exception: continue

        if not df.empty:
            df['symbol'] = sym
            df['date'] = pd.to_datetime(df['date']).dt.date
            df['adjusted_close'] = df.get('adj_close', df.get('close'))
            for col in ['open', 'high', 'low']: 
                if col not in df.columns: df[col] = df['close']
            
            clean_df = df[['symbol', 'date', 'open', 'high', 'low', 'close', 'adjusted_close', 'volume']].dropna(subset=['close'])
            try:
                insert_daily_prices(clean_df.to_dict('records'))
                logger.info(f"✅ Stored {len(clean_df)} records for {sym}")
            except Exception as e:
                logger.error(f"DB Error for {sym}: {e}")

def run():
    create_tables()
    load_indices()
    
    # 2. Dynamic Nifty 500 List Retrieval
    logger.info("Fetching Nifty 500 list from NSE...")
    try:
        url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        nifty500_df = pd.read_csv(io.StringIO(res.text))
        symbols = nifty500_df['Symbol'].tolist()
    except Exception:
        symbols = ["RELIANCE", "TCS", "INFY"] # Emergency Fallback
    
    # Merge with overrides
    overrides = ["CIGNITITEC", "ONEGLOBAL", "SHILCTECH", "AGI", "LUMAXTECH", "SKFINDIAN"]
    symbols = list(set(symbols + overrides))
    load_stocks(symbols)

if __name__ == "__main__":
    run()