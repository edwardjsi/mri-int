"""
MRI Daily Pipeline — [RESCUE HASH: 8872-FORCE-SYNC]
"""
import os
import sys
import logging
import pandas as pd
import numpy as np
import requests
import io
from datetime import datetime, timedelta
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

    # Step 0: Ensure Schema & Sync Universe
    from src.db import get_connection
    from api.schema import ensure_required_tables
    from src.ingestion_engine import get_last_date
    
    try:
        conn = get_connection()
        ensure_required_tables(conn)
        conn.close()
        logger.info("✅ Core Schema Verified")
        sync_universe()
    except Exception as e:
        logger.warning(f"Schema/Universe sync failed: {e}")

    # --- FRESHNESS CHECK ---
    # If we already have the most recent data, skip to scoring/signals
    # NOTE: We query MAX(date) directly — do NOT use get_last_date() here
    # because it subtracts 3 days as a download lookback buffer.
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT MAX(date) FROM daily_prices")
        last_stored = cur.fetchone()[0]
        cur.close()
        conn.close()
        last_stored_date = str(last_stored) if last_stored else "1970-01-01"
    except Exception:
        last_stored_date = "1970-01-01"
    
    today = datetime.now().date()
    # Subtract 1 day for 'last trading day' logic (or 3 for weekends)
    effective_today = today if today.weekday() < 5 else today - timedelta(days=(today.weekday() - 4))
    
    if last_stored_date >= str(effective_today - timedelta(days=1)):
        logger.info(f"✨ Data is likely up-to-date (Last: {last_stored_date}). Moving straight to scoring/signals.")
        skip_ingest = True
    else:
        logger.info(f"🚀 Data is stale (Last: {last_stored_date}). Starting ingestion...")
        skip_ingest = False

    # Step 1: Ingest Data
    if not skip_ingest:
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

    # ═══ PIPELINE HEALTH CHECK ═══
    # Verify data actually flowed through all stages
    try:
        from src.db import get_connection
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT MAX(date) FROM daily_prices")
        max_prices = cur.fetchone()[0]
        
        cur.execute("SELECT MAX(date) FROM stock_scores")
        max_scores = cur.fetchone()[0]
        
        cur.execute("SELECT MAX(date) FROM market_regime")
        max_regime = cur.fetchone()[0]
        
        cur.execute("SELECT MAX(date) FROM index_prices WHERE symbol = 'NIFTY50'")
        max_index = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        logger.info("═══ PIPELINE HEALTH CHECK ═══")
        logger.info(f"  daily_prices  MAX(date) = {max_prices}")
        logger.info(f"  index_prices  MAX(date) = {max_index}")
        logger.info(f"  stock_scores  MAX(date) = {max_scores}")
        logger.info(f"  market_regime MAX(date) = {max_regime}")
        
        # Check for date drift between stages
        dates = [d for d in [max_prices, max_scores, max_regime] if d is not None]
        if dates:
            spread = (max(dates) - min(dates)).days
            if spread > 3:
                logger.critical(
                    f"🚨 DATA DRIFT DETECTED: {spread}-day gap between pipeline stages! "
                    f"Prices={max_prices}, Scores={max_scores}, Regime={max_regime}. "
                    f"Dashboard will show STALE data."
                )
            else:
                logger.info(f"  ✅ All stages within {spread}-day spread — HEALTHY")
    except Exception as e:
        logger.warning(f"Health check failed: {e}")

    logger.info("=== Pipeline Complete ===")

if __name__ == "__main__":
    run_pipeline()

