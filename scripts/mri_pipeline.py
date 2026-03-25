"""
MRI Daily Pipeline — ECS Scheduled Task version.
Runs at 4PM IST Mon-Fri via EventBridge.
"""
import os
import sys
import logging
import pandas as pd
import numpy as np
import requests
import io
from datetime import datetime
from typing import List, Tuple

# Add parent directory to sys.path to find src module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.ingestion_engine import sync_universe

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("pipeline")

def get_full_symbol_list() -> Tuple[List[str], List[dict]]:
    """
    Fetches Nifty 500, User-tracked holdings, and unique BSE Group A stocks.
    Deduplicates using ISIN where possible.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # 1. Fetch Nifty 500 (NSE)
    logger.info("Fetching Nifty 500 list...")
    n500_symbols = []
    n500_isins = set()
    n500_df = pd.DataFrame()
    try:
        n500_url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
        n500_res = requests.get(n500_url, headers=headers, timeout=30)
        n500_df = pd.read_csv(io.StringIO(n500_res.text))
        n500_symbols = n500_df["Symbol"].dropna().unique().tolist()
        n500_isins = set(n500_df["ISIN Code"].dropna().unique().tolist())
        logger.info(f"  Fetched {len(n500_symbols)} Nifty 500 symbols")
    except Exception as e:
        logger.error(f"  ❌ Failed to fetch Nifty 500: {e}")

    # 2. Fetch User-tracked symbols
    from src.db import get_connection
    user_symbols = []
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT symbol FROM client_external_holdings")
        holdings = [row[0] for row in cur.fetchall()]
        cur.execute("SELECT DISTINCT symbol FROM client_watchlist")
        watchlist = [row[0] for row in cur.fetchall()]
        user_symbols = list(set(holdings + watchlist))
        cur.close()
        conn.close()
        logger.info(f"  Fetched {len(user_symbols)} user-specific symbols")
    except Exception as e:
        logger.warning(f"  ⚠️ Could not fetch user symbols: {e}")

    # 3. Fetch BSE List (Resilient Headers)
    logger.info("Fetching BSE List of Companies...")
    bse_only_symbols = []
    sector_records = []
    try:
        bse_url = "https://www.bseindia.com/downloads1/List_of_companies.csv"
        bse_res = requests.get(bse_url, headers=headers, timeout=30)
        if bse_res.status_code == 200:
            bse_df = pd.read_csv(io.StringIO(bse_res.text))
            
            # WISE SCAN: Never use [0] indices
            isin_col = next((c for c in bse_df.columns if 'ISIN' in str(c).upper()), None)
            group_col = next((c for c in bse_df.columns if 'GROUP' in str(c).upper()), None)
            sym_col = next((c for c in bse_df.columns if 'SYMBOL' in str(c).upper() or 'SCRIP ID' in str(c).upper()), None)
            name_col = next((c for c in bse_df.columns if 'SECURITY NAME' in str(c).upper() or 'SHORT NAME' in str(c).upper()), None)
            ind_col = next((c for c in bse_df.columns if 'INDUSTRY' in str(c).upper()), None)
            
            if isin_col and group_col and sym_col:
                group_a = bse_df[bse_df[group_col].astype(str).str.strip() == 'A']
                bse_only = group_a[~group_a[isin_col].astype(str).str.strip().isin(n500_isins)]
                bse_only_symbols = bse_only[sym_col].dropna().unique().tolist()
                
                # Build sectors mapping for the DB
                if name_col:
                    cols = [sym_col, name_col]
                    if ind_col: cols.append(ind_col)
                    bse_mapped = bse_only[cols].copy().rename(columns={sym_col: 'Symbol', name_col: 'Company Name'})
                    if ind_col: bse_mapped = bse_mapped.rename(columns={ind_col: 'Industry'})
                    else: bse_mapped['Industry'] = 'BSE Stocks'
                    sector_records.extend(bse_mapped.to_dict('records'))
                
                logger.info(f"  Identified {len(bse_only_symbols)} unique BSE-only Group A stocks")
    except Exception as e:
        logger.warning(f"  ⚠️ BSE Expansion bypassed: {e}")

    # 4. Final Merge & Blacklist
    all_symbols = list(set(n500_symbols + user_symbols + bse_only_symbols))
    blacklist = {"ONEGLOBAL", "FRONTSP", "ONEGLOBAL.NS", "FRONTSP.NS"}
    all_symbols = [s for s in all_symbols if s.upper().strip() not in blacklist]
    
    # Add NSE sectors
    if not n500_df.empty:
        nse_sectors = n500_df[["Symbol", "Company Name", "Industry"]].dropna().to_dict("records")
        sector_records.extend(nse_sectors)

    return all_symbols, sector_records

def run_pipeline():
    logger.info(f"=== MRI Daily Pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M UTC')} ===")

    # Step 0: Sync Universe
    try:
        sync_universe()
    except Exception as e:
        logger.warning(f"Universe sync failed: {e}")

    # Step 1: Ingest Data
    logger.info("[1/5] Ingesting market data...")
    try:
        from src.ingestion_engine import load_indices, load_stocks
        from src.db import get_connection
        from psycopg2.extras import execute_batch
        
        load_indices()
        symbols, sector_data = get_full_symbol_list()
        load_stocks(symbols)

        # Update sector data for dashboard richness
        if sector_data:
            conn = get_connection()
            cur = conn.cursor()
            execute_batch(cur, """
                INSERT INTO stock_sectors (symbol, company_name, industry)
                VALUES (%(Symbol)s, %(Company Name)s, %(Industry)s)
                ON CONFLICT (symbol) DO UPDATE SET industry = EXCLUDED.industry, updated_at = NOW()
            """, sector_data)
            conn.commit()
            cur.close()
            conn.close()
    except Exception as e:
        logger.error(f"  ❌ Ingestion failed: {e}")
        sys.exit(1)

    # Steps 2-5 (Standard MRI Engine)
    try:
        from src.indicator_engine import add_indicator_columns_if_missing, fetch_data, compute_indicators, update_db_with_indicators
        from src.regime_engine import create_market_regime_and_scores_tables, compute_market_regime, compute_stock_scores
        from src.signal_generator import run_signal_generator
        from src.email_service import send_signal_emails

        logger.info("[2/5] Indicators...")
        add_indicator_columns_if_missing()
        data_df, idx_df = fetch_data()
        update_db_with_indicators(compute_indicators(data_df, idx_df))

        logger.info("[3/5] Regime & Scores...")
        create_market_regime_and_scores_tables()
        compute_market_regime()
        compute_stock_scores()

        logger.info("[4/5] Signals...")
        run_signal_generator()

        logger.info("[5/5] Emails...")
        send_signal_emails()
        
    except Exception as e:
        logger.error(f"  ❌ Engine failed: {e}")
        sys.exit(1)

    logger.info("=== Pipeline Complete ===")

if __name__ == "__main__":
    run_pipeline()
