import logging
import pandas as pd
import requests
import io
import sys
import os

# Ensure project root is in path
sys.path.append(os.getcwd())

from src.ingestion_engine import load_stocks
from src.db import get_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("bse_history")

def get_bse_only_list():
    """Identifies BSE unique Group A and all Group B stocks from T+1 lists with robust column detection."""
    file_a = "BSET1A.csv"
    file_b = "BSET1B.csv"
    
    if not os.path.exists(file_a) or not os.path.exists(file_b):
        logger.error(f"❌ '{file_a}' or '{file_b}' not found!")
        return []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # 1. Fetch NSE Master Equity List to get all NSE ISINs to exclude
    logger.info("Fetching complete NSE Equity list for true BSE-exclusive deduplication...")
    nse_url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    try:
        nse_res = requests.get(nse_url, headers=headers, timeout=30)
        nse_res.raise_for_status()
        nse_df = pd.read_csv(io.StringIO(nse_res.text))
        
        # Clean columns to try and find ISIN
        nse_df.columns = [c.strip() for c in nse_df.columns]
        nse_isin_col = [c for c in nse_df.columns if 'ISIN' in c.upper()][0]
        
        nse_isins = set(nse_df[nse_isin_col].dropna().unique().tolist())
        logger.info(f"  Found {len(nse_isins)} total NSE ISINs")
    except Exception as e:
        logger.error(f"  ❌ Failed to fetch NSE Equity list: {e}")
        nse_isins = set()

    def process_file(file_path):
        try:
            # BSE CSVs often have trailing commas for empty columns, which misaligns Pandas.
            # We strip them manually first.
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Standardize by stripping newlines and trailing commas
            cleaned_lines = [line.strip().rstrip(',') for line in lines if line.strip()]
            
            df = pd.read_csv(io.StringIO('\n'.join(cleaned_lines)))
            df.columns = [str(c).strip() for c in df.columns]
            
            # Robust column identification
            def find_col(cols, patterns):
                for p in patterns:
                    for c in cols:
                        if p.upper() in c.upper():
                            return c
                return None
            
            isin_col = find_col(df.columns, ['ISIN NO', 'ISIN CODE', 'ISIN'])
            code_col = find_col(df.columns, ['SECURITY CODE', 'SCRIP CODE', 'CODE'])
            
            if not isin_col or not code_col:
                logger.error(f"  ❌ Could not find ISIN or Code columns in {file_path}")
                logger.error(f"  Available columns: {df.columns.tolist()}")
                return []
            
            # Log sample for debugging
            sample_code = df[code_col].iloc[0]
            sample_isin = df[isin_col].iloc[0]
            logger.info(f"  File: {file_path} | Detected columns: '{code_col}', '{isin_col}'")
            logger.info(f"  Sample row 1: Code={sample_code}, ISIN={sample_isin}")
            
            # Filter unique against the entire NSE Equity list
            unique_df = df[~df[isin_col].astype(str).str.strip().isin(nse_isins)]
            symbols = unique_df[code_col].astype(str).str.strip().tolist()
            return symbols
        except Exception as e:
            logger.error(f"  ❌ Error processing {file_path}: {e}")
            return []

    logger.info(f"Processing {file_a}...")
    symbols_a = process_file(file_a)
    
    logger.info(f"Processing {file_b}...")
    symbols_b = process_file(file_b)
    
    # Restrict to top 200 Group B to fit within Neon 512MB storage limit
    if len(symbols_b) > 200:
        logger.info(f"  Trunctating Group B from {len(symbols_b)} to top 200 to save DB space")
        symbols_b = symbols_b[:200]
    
    final_symbols = list(set(symbols_a + symbols_b))
    
    logger.info(f"  Unique A matches: {len(symbols_a)}")
    logger.info(f"  Unique B matches: {len(symbols_b)}")
    logger.info(f"  Total unique BSE symbols to ingest: {len(final_symbols)}")
    
    # Final sanity check: if symbols look like "A" or "B", something is wrong
    buggy_symbols = [s for s in final_symbols if not s.isdigit()]
    if len(buggy_symbols) > 5: # Allow some non-digit if they exist, but mostly should be numeric
        logger.warning(f"  ⚠️ Warning: Found {len(buggy_symbols)} non-numeric symbols (e.g., {buggy_symbols[:3]}). Check column mapping.")

    return final_symbols

if __name__ == "__main__":
    logger.info("=== BSE 3-Year Historical Ingestion Started (Unique A + Top 200 B) ===")
    
    symbols = get_bse_only_list()
    
    if not symbols:
        logger.error("No symbols identified. Exiting.")
        sys.exit(1)
        
    logger.info(f"Starting ingestion for {len(symbols)} symbols with 3y lookback...")
    # Using the existing engine's load_stocks with period='3y'
    # This will handle batching and .BO suffixing automatically
    load_stocks(symbols, period="3y")
    
    logger.info("=== BSE 3-Year Historical Ingestion Complete ===")
