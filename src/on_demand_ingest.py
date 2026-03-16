# src/on_demand_ingest.py
import logging
import yfinance as yf
import pandas as pd
import requests
import io
import time
from datetime import datetime, timedelta
from src.db import get_connection, insert_daily_prices
from src.indicator_engine import fetch_data_for_symbols, compute_indicators, update_db_with_indicators, add_indicator_columns_if_missing
from src.regime_engine import create_market_regime_and_scores_tables, compute_market_regime, compute_stock_scores_for_symbols
from src.portfolio_review_engine import analyze_portfolio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def build_symbol_translator() -> dict:
    """Builds exhaustive mapping of NSE symbols to BSE codes with hard-coded overrides."""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        # 1. Fetch NSE Master
        nse_res = requests.get("https://archives.nseindia.com/content/equities/EQUITY_L.csv", headers=headers, timeout=15)
        nse_df = pd.read_csv(io.StringIO(nse_res.text))
        nse_df.columns = nse_df.columns.str.strip()

        # 2. Fetch BSE Master
        bse_res = requests.get("https://www.bseindia.com/downloads1/List_of_companies.csv", headers=headers, timeout=15)
        bse_df = pd.read_csv(io.StringIO(bse_res.text))
        bse_df.columns = bse_df.columns.str.strip()

        # 3. Zip via ISIN
        merged = pd.merge(
            nse_df[['SYMBOL', 'ISIN NUMBER']].rename(columns={'ISIN NUMBER': 'ISIN'}),
            bse_df[['Security Code', 'ISIN No']].rename(columns={'ISIN No': 'ISIN'}),
            on='ISIN', how='inner'
        )
        translator = dict(zip(merged['SYMBOL'].str.strip(), merged['Security Code'].astype(str).str.strip()))
        
        # 4. Mandatory Overrides for broker-specific export strings
        overrides = {
            "CIGNITITEC": "534758", 
            "LUMAXTECH": "532796",  
            "SKFINDIAN": "500472",  
            "AGI": "500187",        
            "ONEGLOBAL": "514330",  
            "SHILCTECH": "531201"   
        }
        translator.update(overrides)
        logger.info(f"[INGEST] Translator ready with {len(translator)} mappings.")
        return translator
    except Exception as e:
        logger.error(f"[INGEST] Bridge build failed: {e}")
        return {}

def ingest_missing_symbols_sync(missing_symbols: list, original_holdings: list, client_id: str, email: str, name: str):
    """Background task: downloads, calculates, and verifies scores before emailing."""
    logger.info(f"[INGEST] Starting sync ingestion for: {missing_symbols}")
    
    translator = build_symbol_translator()
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = (datetime.today() - timedelta(days=365 * 3)).strftime('%Y-%m-%d')
    
    inserted_any = False

    for symbol in missing_symbols:
        user_sym = symbol.upper().strip().split('.')[0]
        safe_term = translator.get(user_sym, user_sym)
        
        # Tiered Search Order
        search_list = [f"{safe_term}.BO", f"{user_sym}.NS", f"{user_sym}.BO"] if safe_term.isdigit() else [f"{user_sym}.NS", f"{user_sym}.BO"]
        
        df = pd.DataFrame()
        for ticker in search_list:
            try:
                logger.info(f"[INGEST] Trying ticker: {ticker}")
                raw = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=True)
                if raw is not None and not raw.empty:
                    # Flatten multi-index if present
                    df = raw.reset_index()
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = [c[0].lower().replace(" ", "_") for c in df.columns]
                    else:
                        df.columns = [str(c).lower().replace(" ", "_") for c in df.