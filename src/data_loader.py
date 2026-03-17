import pandas as pd
import numpy as np
import yfinance as yf
import requests
import io
import logging
import time
from datetime import datetime, timedelta
from src.db import get_connection, create_tables, insert_daily_prices

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_last_date(table_name="daily_prices") -> str:
    """Queries the DB for the latest record date to allow incremental top-up."""
    from src.db import get_connection
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT MAX(date) FROM {table_name}")
        last_date = cur.fetchone()[0]
        if last_date:
            # Shift back 3 days to catch any weekend/holiday gaps or data corrections
            start_date = (last_date - timedelta(days=3)).strftime("%Y-%m-%d")
            return start_date
    except Exception:
        pass
    finally:
        cur.close()
        conn.close()
    return "2023-01-01" # Default fallback

def load_indices(period: str = None):
    """Daily pipeline entry point for index data."""
    create_tables()
    if period:
        logger.info(f"Forcing {period} index download...")
        idx_raw = yf.download("^NSEI", period=period, progress=False, auto_adjust=True)
    else:
        start_date = get_last_date("index_prices")
        logger.info(f"Fetching NIFTY 50 Index data from {start_date}...")
        idx_raw = yf.download("^NSEI", start=start_date, progress=False, auto_adjust=True)
    
    if not idx_raw.empty:
        idx_df = idx_raw.reset_index()
        idx_df.columns = [c[0].lower().replace(" ", "_") if isinstance(idx_df.columns, pd.MultiIndex) else str(c).lower().replace(" ", "_") for c in idx_df.columns]
        idx_df['symbol'] = 'NIFTY50'
        idx_df['date'] = pd.to_datetime(idx_df['date']).dt.date
        idx_df['adjusted_close'] = idx_df.get('adj_close', idx_df.get('close'))
        from src.db import insert_index_prices
        insert_index_prices(idx_df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume']].dropna().to_dict('records'))
    logger.info("✅ Index data loaded")

def build_symbol_translator() -> dict:
    """Builds a mapping of NSE symbols to BSE codes for dual-exchange fallback."""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        nse_res = requests.get("https://archives.nseindia.com/content/equities/EQUITY_L.csv", headers=headers, timeout=15)
        nse_df = pd.read_csv(io.StringIO(nse_res.text))
        bse_res = requests.get("https://www.bseindia.com/downloads1/List_of_companies.csv", headers=headers, timeout=15)
        bse_df = pd.read_csv(io.StringIO(bse_res.text))
        
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

    translator.update({
        "CIGNITITEC": "534758", "LUMAXTECH": "532796", "SKFINDIAN": "500472", 
        "AGI": "500187", "ONEGLOBAL": "514330", "SHILCTECH": "531201"
    })
    return translator

def load_stocks(symbols: list, period: str = None):
    """Daily pipeline entry point for stock data, now with batching for stability."""
    if not symbols: return
    create_tables()
    translator = build_symbol_translator()
    
    # Process in batches of 50 to avoid timeouts and show progress
    batch_size = 50
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        logger.info(f"--- Processing Batch {i//batch_size + 1}/{ (len(symbols)-1)//batch_size + 1 } ({len(batch)} symbols) ---")
        
        if period:
            logger.info(f"  Forcing {period} bulk download...")
            tickers = [f"{s}.NS" for s in batch]
            try:
                raw_data = yf.download(tickers, period=period, interval="1d", group_by='ticker', progress=False, auto_adjust=True)
            except Exception as e:
                logger.error(f"  Batch download failed: {e}")
                continue
        else:
            start_date = get_last_date("daily_prices")
            logger.info(f"  Incremental download from {start_date}...")
            tickers = [f"{s}.NS" for s in batch]
            try:
                raw_data = yf.download(tickers, start=start_date, interval="1d", group_by='ticker', progress=False, auto_adjust=True)
            except Exception as e:
                logger.error(f"  Batch download failed: {e}")
                continue
        
        all_records = []
        failed_symbols = []

        for sym in batch:
            ticker = f"{sym}.NS"
            # Handle single ticker edge case
            if len(batch) == 1:
                df = raw_data.reset_index()
            elif ticker not in raw_data.columns.levels[0]:
                failed_symbols.append(sym)
                continue
            else:
                df = raw_data[ticker].dropna(how='all').reset_index()
            
            if df.empty:
                failed_symbols.append(sym)
                continue
            
            df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
            df['symbol'] = sym
            df['date'] = pd.to_datetime(df['date']).dt.date
            df['adjusted_close'] = df.get('adj_close', df.get('close'))
            for col in ['open', 'high', 'low']: 
                if col not in df.columns: df[col] = df['close']
            
            clean_df = df[['symbol', 'date', 'open', 'high', 'low', 'close', 'adjusted_close', 'volume']].dropna(subset=['close'])
            all_records.extend(clean_df.to_dict('records'))

        if all_records:
            from src.db import insert_daily_prices
            insert_daily_prices(all_records)
            logger.info(f"  ✅ Batch: Stored {len(all_records)} records")

        # Fallback for failed/BSE symbols in this batch
        if failed_symbols:
            logger.info(f"  Processing fallback for {len(failed_symbols)} symbols...")
            for sym in failed_symbols:
                time.sleep(0.5)
                bse_code = translator.get(sym, sym)
                search_list = [f"{bse_code}.BO", f"{sym}.BO"] if bse_code.isdigit() else [f"{sym}.BO"]
                
                for ticker in search_list:
                    try:
                        if period:
                            raw = yf.download(ticker, period=period, progress=False, auto_adjust=True)
                        else:
                            start_date = get_last_date("daily_prices")
                            raw = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)
                            
                        if not raw.empty:
                            df = raw.reset_index()
                            df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
                            df['symbol'] = sym
                            df['date'] = pd.to_datetime(df['date']).dt.date
                            df['adjusted_close'] = df.get('adj_close', df.get('close'))
                            for col in ['open', 'high', 'low']: 
                                if col not in df.columns: df[col] = df['close']
                            
                            records = df[['symbol', 'date', 'open', 'high', 'low', 'close', 'adjusted_close', 'volume']].dropna(subset=['close']).to_dict('records')
                            insert_daily_prices(records)
                            logger.info(f"  ✅ Fallback: {sym} ({len(records)} days)")
                            break
                    except Exception: continue

def run():
    create_tables()
    load_indices()
    
    logger.info("Fetching Nifty 500 list from NSE...")
    try:
        url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        nifty500_df = pd.read_csv(io.StringIO(res.text))
        symbols = nifty500_df['Symbol'].tolist()
    except Exception:
        symbols = ["RELIANCE", "TCS", "INFY"]
    
    overrides = ["CIGNITITEC", "ONEGLOBAL", "SHILCTECH", "AGI", "LUMAXTECH", "SKFINDIAN"]
    symbols = list(set(symbols + overrides))
    load_stocks(symbols)

if __name__ == "__main__":
    run()