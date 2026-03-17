"""
MRI Daily Pipeline — ECS Scheduled Task version.
Runs at 4PM IST Mon-Fri via EventBridge.
"""
import os
import sys
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("pipeline")

def run_pipeline():
    logger.info(f"=== MRI Daily Pipeline — {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")

    # Step 1: Ingest today's data
    logger.info("[1/5] Ingesting today's market data...")
    try:
        import os
        import sys
        logger.info(f"DEBUG: Current Directory: {os.getcwd()}")
        logger.info(f"DEBUG: Python Path: {sys.path}")
        if os.path.exists('src'):
            logger.info(f"DEBUG: src directory contents: {os.listdir('src')}")
        else:
            logger.error("DEBUG: src directory MISSING!")

        import pandas as pd
        import requests
        import io
        from src.data_loader import load_indices, load_stocks

        load_indices()

        url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text))
        symbols = df["Symbol"].dropna().unique().tolist()
        logger.info(f"  Fetched {len(symbols)} Nifty 500 symbols")
        load_stocks(symbols)

        # Update sectors
        from src.db import get_connection as get_db_conn
        sector_conn = get_db_conn()
        sector_cur = sector_conn.cursor()
        sector_cur.execute("DELETE FROM stock_sectors;")
        from psycopg2.extras import execute_batch as eb
        sector_data = df[["Symbol", "Company Name", "Industry"]].dropna().to_dict("records")
        eb(sector_cur, """
            INSERT INTO stock_sectors (symbol, company_name, industry)
            VALUES (%(Symbol)s, %(Company Name)s, %(Industry)s)
            ON CONFLICT (symbol) DO UPDATE
            SET industry = EXCLUDED.industry, company_name = EXCLUDED.company_name, updated_at = NOW()
        """, sector_data, page_size=500)
        sector_conn.commit()
        sector_cur.close()
        sector_conn.close()
        logger.info(f"  ✅ Stock sectors updated")

    except Exception as e:
        logger.error(f"  ❌ Data ingestion failed: {e}")
        # Log precisely what failed to import
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
