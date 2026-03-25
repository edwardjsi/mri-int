import pandas as pd
import numpy as np
import yfinance as yf
import requests
import io
import logging
import time
import os
from datetime import datetime, timedelta

# SUPER DEBUG: Print exactly who is being loaded
print(f"DEBUG: LOADING ingestion_engine.py from {os.path.abspath(__file__)}")

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
    return (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d") # Default fallback 2 years

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
    translator = {}
    try:
        # NSE ISIN Fetch
        nse_res = requests.get("https://archives.nseindia.com/content/equities/EQUITY_L.csv", headers=headers, timeout=15)
        nse_df = pd.read_csv(io.StringIO(nse_res.text))
        nse_df.columns = [c.upper().strip() for c in nse_df.columns]
        
        # BSE ISIN Fetch
        bse_res = requests.get("https://www.bseindia.com/downloads1/List_of_companies.csv", headers=headers, timeout=15)
        bse_df = pd.read_csv(io.StringIO(bse_res.text))
        bse_df.columns = [c.upper().strip() for c in bse_df.columns]

        # Fuzzy Column Finder
        bse_code_col = next((c for c in bse_df.columns if 'SECURITY CODE' in c or 'SCRIP CODE' in c or 'SCRIP_CODE' in c), None)
        bse_isin_col = next((c for c in bse_df.columns if 'ISIN' in c), None)
        nse_isin_col = next((c for c in nse_df.columns if 'ISIN' in c), None)
        nse_sym_col = next((c for c in nse_df.columns if 'SYMBOL' in c), None)

        if bse_code_col and bse_isin_col and nse_isin_col and nse_sym_col:
            merged = pd.merge(
                nse_df[[nse_sym_col, nse_isin_col]].rename(columns={nse_isin_col: 'ISIN', nse_sym_col: 'SYMBOL'}),
                bse_df[[bse_code_col, bse_isin_col]].rename(columns={bse_code_col: 'BSE_CODE', bse_isin_col: 'ISIN'}),
                on='ISIN', how='inner'
            )
            translator = dict(zip(merged['SYMBOL'].str.strip(), merged['BSE_CODE'].astype(str).str.strip()))
            logger.info(f"✅ Symbol bridge built: {len(translator)} mappings linked.")
        else:
            logger.warning("⚠️ BSE/NSE headers changed. Using manual overrides.")
    except Exception as e:
        logger.error(f"Bridge build failed: {e}. Using mandatory overrides.")
    
    # BLACKLIST: Specifically remove delisted/toxic symbols that clutter logs
    blacklist = {"ONEGLOBAL", "FRONTSP", "ONEGLOBAL.NS", "FRONTSP.NS"}
    for b in blacklist:
        if b in translator: del translator[b]

    # Always include these key persistent overrides
    translator.update({
        "CIGNITITEC": "534758", "LUMAXTECH": "532796", "SKFINDIAN": "500472", 
        "AGI": "500187", "SHILCTECH": "531201"
    })
    return translator

def sync_universe():
    """Builds a master lookup table of all valid BSE/NSE symbols to avoid nonsense inputs."""
    logger.info("📡 Syncing Master Stock Universe (BSE + NSE)...")
    translator = build_symbol_translator()
    from src.db import get_connection
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("CREATE TABLE IF NOT EXISTS universe (symbol TEXT PRIMARY KEY, company_name TEXT, isin TEXT, bse_code TEXT)")
        # Clear old data (optional, but keep it fresh)
        # cur.execute("TRUNCATE universe") 
        
        # We use a greedy approach to find all active names
        headers = {"User-Agent": "Mozilla/5.0"}
        nse_res = requests.get("https://archives.nseindia.com/content/equities/EQUITY_L.csv", headers=headers, timeout=15)
        nse_df = pd.read_csv(io.StringIO(nse_res.text))
        nse_df.columns = [c.upper().strip() for c in nse_df.columns]
        
        for _, row in nse_df.iterrows():
            sym = str(row.get('SYMBOL', '')).strip().upper()
            name = str(row.get('NAME OF COMPANY', row.get('COMPANY', ''))).strip()
            isin = str(row.get('ISIN NUMBER', row.get('ISIN', ''))).strip()
            if not sym or sym == 'NAN': continue
            
            cur.execute("""
                INSERT INTO universe (symbol, company_name, isin, bse_code)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (symbol) DO UPDATE SET company_name = EXCLUDED.company_name
            """, (sym, name, isin, translator.get(sym)))
            
        conn.commit()
        logger.info(f"✅ Master Universe Synced. {len(nse_df)} NSE stocks verified.")
    except Exception as e:
        logger.error(f"Universe Sync failed: {e}")
    finally:
        cur.close()
        conn.close()

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
        
        # Nuke Blacklist right at the start
        blacklist = {"ONEGLOBAL", "FRONTSP", "ONEGLOBAL.NS", "FRONTSP.NS"}
        batch = [s for s in batch if s.upper().strip() not in blacklist]
        if not batch: continue

        def get_ticker(s):
            if s.isdigit(): return f"{s}.BO"
            if s.endswith(".BO") or s.endswith(".NS"): return s
            return f"{s}.NS"

        tickers = [get_ticker(s) for s in batch]
        
        raw_data = pd.DataFrame()
        for attempt in range(3):
            try:
                if period:
                    logger.info(f"  Forcing {period} bulk download (Attempt {attempt+1})...")
                    raw_data = yf.download(tickers, period=period, interval="1d", group_by='ticker', progress=False, auto_adjust=True, threads=False)
                else:
                    # AGGRESSIVE CATCH-UP: 7 days back to ensure we bridge weekends and missing days
                    last_date_raw = get_last_date("daily_prices")
                    start_dt = datetime.strptime(last_date_raw, "%Y-%m-%d") - timedelta(days=7)
                    start_date = start_dt.strftime("%Y-%m-%d")
                    logger.info(f"  Incremental download from {start_date} (Attempt {attempt+1})...")
                    # Silently skip missing symbols by adding threads=False (makes catching single errors easier)
                    raw_data = yf.download(tickers, start=start_date, interval="1d", group_by='ticker', progress=False, auto_adjust=True, threads=False)
                
                if not raw_data.empty:
                    break
            except Exception as e:
                logger.error(f"  Batch download attempt {attempt+1} failed: {e}")
                if attempt < 2: time.sleep(5)
        
        if raw_data.empty:
            logger.error(f"  ❌ Batch {i//batch_size + 1} failed after all retries.")
            continue
        
        all_records = []
        failed_symbols = []

        for sym in batch:
            ticker = get_ticker(sym)
            try:
                # Handle single vs multi-index download structure safely
                is_multi = isinstance(raw_data.columns, pd.MultiIndex)
                if len(batch) == 1:
                    df = raw_data.reset_index()
                elif is_multi and ticker in raw_data.columns.get_level_values(0):
                    df = raw_data[ticker].dropna(how='all').reset_index()
                elif ticker in raw_data.columns:
                    df = raw_data[ticker].dropna(how='all').reset_index()
                else:
                    logger.warning(f"  ⚠️ Symbol {sym} missing from Yahoo result batch.")
                    failed_symbols.append(sym)
                    continue
                
                if df.empty:
                    failed_symbols.append(sym)
                    continue
                
                # Standardize columns
                df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
                # Map 'date' if it came back as 'index' or 'datetime'
                if 'date' not in df.columns and 'datetime' in df.columns:
                    df = df.rename(columns={'datetime': 'date'})
                
                # Double-check we actually have a date column
                if 'date' not in df.columns:
                    logger.warning(f"  ⚠️ No date column found for {sym}. Skipping.")
                    continue

                df['symbol'] = sym
                df['date'] = pd.to_datetime(df['date']).dt.date
                df['adjusted_close'] = df.get('adj_close', df.get('close'))
                
                # Ensure OHL format is valid
                for col in ['open', 'high', 'low']: 
                    if col not in df.columns: df[col] = df['close']
                
                # Log the specific dates we're about to store
                found_dates = df['date'].unique().tolist()
                if found_dates:
                    logger.info(f"    -> {sym}: Found {len(found_dates)} new days (latest: {max(found_dates)})")

                clean_df = df[['symbol', 'date', 'open', 'high', 'low', 'close', 'adjusted_close', 'volume']].dropna(subset=['close'])
                all_records.extend(clean_df.to_dict('records'))
            except Exception as e:
                logger.error(f"  ❌ Critical error processing {sym}: {e}")
                failed_symbols.append(sym)

        if all_records:
            from src.db import insert_daily_prices
            insert_daily_prices(all_records)
            logger.info(f"  ✅ DONE: Stored {len(all_records)} records for batch {i//batch_size + 1}")

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
