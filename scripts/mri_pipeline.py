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

# Add parent directory to sys.path to find src module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("pipeline")

def get_full_symbol_list():
    """
    Fetches Nifty 500, User-tracked holdings, and unique BSE Group A stocks.
    Deduplicates using ISIN where possible.
    """
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
        # FALLBACK: If external list fails, get everything already in our universe table
        try:
             from src.db import get_connection
             conn_fb = get_connection()
             cur_fb = conn_fb.cursor()
             cur_fb.execute("SELECT DISTINCT symbol FROM universe")
             n500_symbols = [r[0] for r in cur_fb.fetchall()]
             cur_fb.close()
             conn_fb.close()
             logger.info(f"  ⚠️ FALLBACK: Using {len(n500_symbols)} symbols from DB universe")
        except:
             n500_symbols = []
        n500_isins = set()
        n500_df = pd.DataFrame()

    # 2. Fetch User-tracked symbols (Digital Twin + Watchlist)
    from src.db import get_connection
    user_symbols = []
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        # Get from Digital Twin holdings
        cur.execute("SELECT DISTINCT symbol FROM client_external_holdings")
        holdings = [row[0] for row in cur.fetchall()]
        
        # Get from Watchlist
        cur.execute("SELECT DISTINCT symbol FROM client_watchlist")
        watchlist = [row[0] for row in cur.fetchall()]
        
        user_symbols = list(set(holdings + watchlist))
        cur.close()
        conn.close()
        logger.info(f"  Fetched {len(user_symbols)} user-specific symbols (Holdings: {len(holdings)}, Watchlist: {len(watchlist)})")
    except Exception as e:
        logger.warning(f"  ⚠️ Could not fetch user symbols: {e}")

    # 3. Fetch BSE List (to identify BSE-only Group A)
    logger.info("Fetching BSE List of Companies...")
    bse_url = "https://www.bseindia.com/downloads1/List_of_companies.csv"
    bse_only_symbols = []
    bse_df = pd.DataFrame()
    try:
        bse_res = requests.get(bse_url, headers=headers, timeout=30)
        if bse_res.status_code == 200:
            bse_df = pd.read_csv(io.StringIO(bse_res.text))
            
            # Find relevant columns safely
            isin_col = next((c for c in bse_df.columns if 'ISIN' in str(c).upper()), None)
            group_col = next((c for c in bse_df.columns if 'GROUP' in str(c).upper()), None)
            sym_col = next((c for c in bse_df.columns if 'SYMBOL' in str(c).upper() or 'SCRIP ID' in str(c).upper()), None)
            
            if not isin_col or not group_col or not sym_col:
                logger.warning(f"  ⚠️ BSE CSV structure unrecognized. Columns: {list(bse_df.columns)}")
                bse_only_symbols = []
            else:
                # Filter for Group A that are NOT in Nifty 500 by ISIN
                group_a = bse_df[bse_df[group_col].astype(str).str.strip() == 'A']
                bse_only = group_a[~group_a[isin_col].astype(str).str.strip().isin(n500_isins)]
                bse_only_symbols = bse_only[sym_col].dropna().unique().tolist()
                logger.info(f"  Identified {len(bse_only_symbols)} unique BSE-only Group A stocks")
        else:
            logger.warning(f"  ⚠️ BSE List fetch returned {bse_res.status_code}. Skipping BSE expansion.")
    except Exception as e:
        logger.warning(f"  ⚠️ BSE List fetch failed: {str(e)}. Skipping BSE expansion.")

        # 5. Merge and Deduplicate
    all_symbols = list(set(n500_symbols + user_symbols + bse_only_symbols))
    logger.info(f"Total unified symbols for ingestion: {len(all_symbols)}")
    
    # 6. Build unified sector map
    sector_records = []
    if not n500_df.empty:
        n500_records = n500_df[["Symbol", "Company Name", "Industry"]].dropna().to_dict("records")
        sector_records.extend(n500_records)
    
    if bse_only_symbols and 'bse_df' in locals():
        # Map BSE columns to NSE-style keys for the DB
        bse_sym_col = [c for c in bse_df.columns if 'SYMBOL' in str(c).upper() or 'SCRIP ID' in str(c).upper()][0]
        bse_name_col = [c for c in bse_df.columns if 'SECURITY NAME' in str(c).upper()][0]
        # BSE doesn't always have 'Industry' in the simple CSV, might be 'Industry' or missing
        bse_ind_col = [c for c in bse_df.columns if 'INDUSTRY' in str(c).upper()]
        bse_ind_col = bse_ind_col[0] if bse_ind_col else None
        
        bse_mapped = bse_only[[bse_sym_col, bse_name_col] + ([bse_ind_col] if bse_ind_col else [])].copy()
        bse_mapped = bse_mapped.rename(columns={
            bse_sym_col: 'Symbol',
            bse_name_col: 'Company Name'
        })
        if bse_ind_col:
            bse_mapped = bse_mapped.rename(columns={bse_ind_col: 'Industry'})
        else:
            bse_mapped['Industry'] = 'BSE Stocks'
            
        sector_records.extend(bse_mapped.dropna(subset=['Symbol']).to_dict("records"))

    return all_symbols, sector_records

def run_pipeline():
    logger.info(f"=== MRI Daily Pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")

    # Step 1: Ingest today's data
    logger.info("[1/5] Ingesting today's market data...")
    try:
        from src.ingestion_engine import load_indices, load_stocks

        load_indices()
        
        symbols, sector_data = get_full_symbol_list()
        if not symbols:
            raise Exception("No symbols found to ingest.")
            
        load_stocks(symbols)

        # Update sectors using unified list
        if sector_data:
            from src.db import get_connection as get_db_conn
            from psycopg2.extras import execute_batch as eb
            
            sector_conn = get_db_conn()
            sector_cur = sector_conn.cursor()
            
            eb(sector_cur, """
                INSERT INTO stock_sectors (symbol, company_name, industry)
                VALUES (%(Symbol)s, %(Company Name)s, %(Industry)s)
                ON CONFLICT (symbol) DO UPDATE
                SET industry = EXCLUDED.industry, company_name = EXCLUDED.company_name, updated_at = NOW()
            """, sector_data, page_size=500)
            
            sector_conn.commit()
            sector_cur.close()
            sector_conn.close()
            logger.info(f"  ✅ Stock sectors updated ({len(sector_data)} records)")

    except Exception as e:
        logger.error(f"  ❌ Data ingestion failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

    # Step 2: Compute indicators
    logger.info("[2/5] Running Indicator Engine...")
    try:
        from src.indicator_engine import (
            add_indicator_columns_if_missing,
            fetch_data,
            compute_indicators,
            update_db_with_indicators,
        )

        add_indicator_columns_if_missing()
        data_df, idx_df = fetch_data()
        updates = compute_indicators(data_df, idx_df)
        update_db_with_indicators(updates)
        logger.info("  ✅ Indicators computed")
    except Exception as e:
        logger.error(f"  ❌ Indicator engine failed: {e}")
        sys.exit(1)

    # Step 3: Compute regime + scores
    logger.info("[3/5] Running Regime Engine...")
    try:
        from src.regime_engine import create_market_regime_and_scores_tables, compute_market_regime, compute_stock_scores

        create_market_regime_and_scores_tables()
        compute_market_regime()
        compute_stock_scores()
        logger.info("  ✅ Regime and scores computed")
    except Exception as e:
        logger.error(f"  ❌ Regime engine failed: {e}")
        sys.exit(1)

    # Step 4: Generate client signals
    logger.info("[4/5] Generating client signals...")
    try:
        from src.signal_generator import run_signal_generator
        run_signal_generator()
        logger.info("  ✅ Signals generated")
    except Exception as e:
        logger.error(f"  ❌ Signal generation failed: {e}")
        sys.exit(1)

    # Step 5: Send email notifications
    logger.info("[5/5] Sending signal emails via SES...")
    try:
        from src.email_service import send_signal_emails
        send_signal_emails()
        logger.info("  ✅ Emails sent")
    except Exception as e:
        logger.error(f"  ❌ Email sending failed: {e}")

    logger.info(f"=== Pipeline Complete — {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")

if __name__ == "__main__":
    run_pipeline()
