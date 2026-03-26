import pandas as pd
import yfinance as yf
import logging
from datetime import datetime
from src.db import get_connection, insert_daily_prices
from src.indicator_engine import compute_indicators_for_symbols
from src.regime_engine import compute_stock_scores_for_symbols

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Decision 042: Definitive Scrip Mapping for Non-Standard Tickers
BSE_OVERRIDES = {
    "CIGNITITEC": "534758",
    "SKFINDIAN": "500472",
    "M&M": "500520",
    "MAHLOG": "540716",
    "ONEGLOBAL": "544136", # User mentioned "Newly listed"
}

def ingest_missing_symbols_sync(symbols, user_id='admin', user_email=None, user_name=None):
    """
    Synchronous ingestion: Bulk Fetch -> Indicators -> Scores.
    Optimized for multi-symbol portfolios (e.g., 33 stocks) to avoid 30s timeouts.
    """
    if not symbols:
        return

    # De-duplicate and cleanse
    clean_symbols = list(set([str(s).upper().strip() for s in symbols if str(s).strip()]))
    logger.info(f"[INGEST] Starting bulk sync ingestion for: {clean_symbols}")
    
    pending_symbols = clean_symbols.copy()
    successful_symbols = []

    # --- Tier 1: Bulk NSE (.NS) ---
    if pending_symbols:
        nse_tickers = [f"{s}.NS" for s in pending_symbols]
        try:
            logger.info(f"[INGEST] Strategy 1: Bulk NSE fetch for {len(nse_tickers)} symbols")
            # 2y period ensures we have enough data for EMA-200 / SMA-200
            data = yf.download(nse_tickers, period="2y", progress=False, auto_adjust=True, group_by='ticker')
            
            for sym in pending_symbols[:]:
                ticker = f"{sym}.NS"
                # If only one ticker requested, yf returns a simple DF. If multi, it returns MultiIndex.
                sym_data = data[ticker] if len(nse_tickers) > 1 else data
                
                if not sym_data.empty and sym_data.dropna(subset=['Close']).shape[0] > 0:
                    process_and_save_yf_df(sym_data, sym)
                    successful_symbols.append(sym)
                    pending_symbols.remove(sym)
        except Exception as e:
            logger.warning(f"[INGEST] Bulk NSE fetch failed: {e}")

    # --- Tier 2: Bulk BSE (.BO) for remainders ---
    if pending_symbols:
        bse_tickers = [f"{s}.BO" for s in pending_symbols]
        try:
            logger.info(f"[INGEST] Strategy 2: Bulk BSE fetch for {len(bse_tickers)} symbols")
            data = yf.download(bse_tickers, period="2y", progress=False, auto_adjust=True, group_by='ticker')
            
            for sym in pending_symbols[:]:
                ticker = f"{sym}.BO"
                sym_data = data[ticker] if len(bse_tickers) > 1 else data
                if not sym_data.empty and sym_data.dropna(subset=['Close']).shape[0] > 0:
                    process_and_save_yf_df(sym_data, sym)
                    successful_symbols.append(sym)
                    pending_symbols.remove(sym)
        except Exception as e:
            logger.warning(f"[INGEST] Bulk BSE fetch failed: {e}")

    # --- Tier 3: Individual Numeric Overrides ---
    if pending_symbols:
        for sym in pending_symbols[:]:
            numeric_code = BSE_OVERRIDES.get(sym)
            if numeric_code:
                ticker = f"{numeric_code}.BO"
                try:
                    logger.info(f"[INGEST] Strategy 3: Numeric override for {sym} -> {ticker}")
                    raw = yf.download(ticker, period="3y", progress=False, auto_adjust=True)
                    if not raw.empty:
                        process_and_save_yf_df(raw, sym)
                        successful_symbols.append(sym)
                        pending_symbols.remove(sym)
                except Exception as e:
                    logger.error(f"[INGEST] Numeric override failed for {sym}: {e}")

    # Step 2 & 3: Compute Indicators & Scores for all successful ingests
    if successful_symbols:
        logger.info(f"[INGEST] Computing indicators for successful set: {successful_symbols}")
        compute_indicators_for_symbols(successful_symbols)
        logger.info(f"[INGEST] Generating MRI scores for successful set: {successful_symbols}")
        compute_stock_scores_for_symbols(successful_symbols)
    
    if pending_symbols:
        logger.warning(f"[INGEST] Failed to resolve or fetch data for: {pending_symbols}")

    logger.info(f"[INGEST] Sync ingestion complete. Success={len(successful_symbols)}, Failed={len(pending_symbols)}")
    
    # Send Notification Email
    if user_email:
        from src.email_service import send_on_demand_risk_audit_report
        send_on_demand_risk_audit_report(user_email, user_name, successful_symbols, pending_symbols)

def process_and_save_yf_df(df, symbol):
    """Cleans a Yahoo Finance dataframe and inserts it into daily_prices."""
    if df.empty: 
        return
        
    res = df.reset_index()
    
    # Handle MultiIndex column headers from bulk yfinance calls
    if isinstance(res.columns, pd.MultiIndex):
        res.columns = [c[0].lower().replace(" ", "_").strip() for c in res.columns]
    else:
        res.columns = [str(c).lower().replace(" ", "_").strip() for c in res.columns]
    
    res['symbol'] = symbol
    # Ensure date is a python date object
    res['date'] = pd.to_datetime(res['date']).dt.date
    res['adjusted_close'] = res.get('adj_close', res.get('close'))
    
    # Filter to required columns and drop explicitly null prices
    required_cols = ['symbol', 'date', 'open', 'high', 'low', 'close', 'adjusted_close', 'volume']
    # Ensure all required columns exist (yfinance might omit some if all NaNs)
    for col in required_cols:
        if col not in res.columns:
            res[col] = None
            
    final_df = res[required_cols].dropna(subset=['close'])
    records = final_df.to_dict('records')
    
    if records:
        insert_daily_prices(records)
    else:
        logger.warning(f"[INGEST] No valid records to save for {symbol}")