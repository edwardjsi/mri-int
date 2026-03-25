
import os
import sys
import logging
import pandas as pd
import requests
import io

# Add project root to path
sys.path.append(os.getcwd())

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_symbols")

def test_symbol_gathering():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    # 1. Fetch Nifty 500 (NSE)
    logger.info("Fetching Nifty 500 list...")
    n500_url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    try:
        n500_res = requests.get(n500_url, headers=headers, timeout=30)
        n500_res.raise_for_status()
        n500_df = pd.read_csv(io.StringIO(n500_res.text))
        n500_symbols = n500_df["Symbol"].dropna().unique().tolist()
        n500_isins = set(n500_df["ISIN Code"].dropna().unique().tolist())
        logger.info(f"  Fetched {len(n500_symbols)} Nifty 500 symbols")
    except Exception as e:
        logger.error(f"  ❌ Failed to fetch Nifty 500: {e}")
        n500_symbols = []
        n500_isins = set()

    # 2. Fetch User-tracked holdings (Digital Twin)
    from src.db import get_connection
    user_symbols = []
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT symbol FROM client_external_holdings")
        user_symbols = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        logger.info(f"  Fetched {len(user_symbols)} user-tracked symbols")
    except Exception as e:
        logger.warning(f"  ⚠️ Could not fetch user holdings: {e}")

    # 3. Fetch BSE List (to identify BSE-only Group A)
    logger.info("Fetching BSE List of Companies...")
    bse_url = "https://www.bseindia.com/downloads1/List_of_companies.csv"
    bse_only_symbols = []
    try:
        bse_res = requests.get(bse_url, headers=headers, timeout=30)
        if bse_res.status_code == 200:
            bse_df = pd.read_csv(io.StringIO(bse_res.text))
            
            # Find relevant columns (BSE headers can vary)
            isin_col = next((c for c in bse_df.columns if 'ISIN' in str(c).upper()), None)
            group_col = next((c for c in bse_df.columns if 'GROUP' in str(c).upper()), None)
            sym_col = next((c for c in bse_df.columns if 'SYMBOL' in str(c).upper() or 'SCRIP ID' in str(c).upper()), None)
            
            if isin_col and group_col and sym_col:
                # Filter for Group A that are NOT in Nifty 500 by ISIN
                bse_df[group_col] = bse_df[group_col].astype(str).str.strip()
                group_a = bse_df[bse_df[group_col] == 'A']
                bse_only = group_a[~group_a[isin_col].astype(str).str.strip().isin(n500_isins)]
                bse_only_symbols = bse_only[sym_col].dropna().unique().tolist()
                logger.info(f"  Identified {len(bse_only_symbols)} unique BSE-only Group A stocks")
                logger.info(f"  Sample BSE-only: {bse_only_symbols[:10]}")
            else:
                logger.warning(f"  ⚠️ BSE List columns not found. Headers: {list(bse_df.columns)}")
        else:
            logger.warning(f"  ⚠️ BSE List fetch returned {bse_res.status_code}.")
    except Exception as e:
        logger.warning(f"  ⚠️ BSE List fetch failed: {e}.")

    # 4. Merge and Deduplicate
    all_symbols = list(set(n500_symbols + user_symbols + bse_only_symbols))
    logger.info(f"Total unified symbols: {len(all_symbols)} (NSE: {len(n500_symbols)}, User: {len(user_symbols)}, BSE-Only: {len(bse_only_symbols)})")

if __name__ == "__main__":
    test_symbol_gathering()
