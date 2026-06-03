import logging
import requests
import pandas as pd
import io
from engine_core.ingestion_engine import load_indices, load_stocks
from engine_core.indicator_engine import compute_indicators_all
from engine_core.regime_engine import compute_market_regime
from engine_core.signal_generator import run_signal_generator
from engine_core.swing_execution_engine import run_stee
from engine_core.email_service import send_signal_emails, send_stee_signal_emails
from engine_core.db import get_connection
from engine_fundamental.collector import fetch_and_store_financials
from engine_fundamental.pipeline import run_quality_pipeline
from engine_core.portfolio_review_engine import update_all_breakout_candidates

logger = logging.getLogger("mri_orchestrator")

def run_full_mri_pipeline():
    """
    Executes the full MRI pipeline in sequence.
    Mirroring scripts/pipeline_cloud.sh logic in Python.
    """
    try:
        # Step 1: Ingestion
        logger.info("[1/9] Ingesting market data...")
        load_indices()

        url = 'https://archives.nseindia.com/content/indices/ind_nifty500list.csv'
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=30)
        df = pd.read_csv(io.StringIO(response.text))
        symbols = set(df['Symbol'].dropna().unique().tolist())
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute('SELECT symbol FROM universe_112co WHERE is_active = TRUE')
            symbols.update([r[0] for r in cur.fetchall()])
            cur.close()
            conn.close()
            logger.info(f'Added 112Co symbols. Universe: {len(symbols)}')
        except Exception as e:
            logger.warning(f'112Co load error: {e}')
        load_stocks(list(symbols))

        # Step 2: Indicators
        logger.info("[2/9] Running Indicator Engine...")
        compute_indicators_all()

        # Step 3: Regime + Scores
        logger.info("[3/9] Running Regime Engine...")
        compute_market_regime()

        # Step 4: Signals
        logger.info("[4/9] Generating client signals...")
        run_signal_generator()

        # Step 5: STEE Swing Execution
        logger.info("[5/9] Running STEE swing execution engine...")
        run_stee()

        # Step 6: Emails
        logger.info("[6/9] Sending signal emails...")
        try:
            send_signal_emails()
            send_stee_signal_emails()
        except Exception as e:
            logger.error(f"Email sending failed: {e}")

        # Step 7: Breakout Candidates
        logger.info("[7/9] Marking breakout candidates for Risk Audit holdings...")
        try:
            update_all_breakout_candidates()
        except Exception as e:
            logger.error(f"Breakout candidate update failed: {e}")

        # Step 8: Health (Skipping internal monitor script for now, handled by dashboard)
        logger.info("[8/9] Pipeline logic complete.")

        # Step 9: Fundamentals
        logger.info("[9/9] Running Fundamental Analysis for top candidates...")
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT symbol FROM stock_scores WHERE date = (SELECT MAX(date) FROM stock_scores) ORDER BY total_score DESC LIMIT 20")
        top_symbols = [r[0] if isinstance(r, (list, tuple)) else r['symbol'] for r in cur.fetchall()]
        conn.close()

        for sym in top_symbols:
            yf_sym = f"{sym}.NS" if not sym.endswith(".NS") and not sym.endswith(".BO") else sym
            try:
                fetch_and_store_financials(yf_sym)
                run_quality_pipeline(yf_sym)
            except Exception as e:
                logger.error(f"Failed fundamental analysis for {yf_sym}: {e}")

        logger.info("✅ Full Pipeline Orchestration Complete")
        return True
    except Exception as e:
        logger.error(f"Pipeline Orchestration FAILED: {e}")
        return False
