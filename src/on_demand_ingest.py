import pandas as pd
import yfinance as yf
import logging
from datetime import datetime
from src.db import get_connection, insert_daily_prices
from src.indicator_engine import compute_indicators_for_symbols
from src.regime_engine import compute_stock_scores_for_symbols

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ingest_missing_symbols_sync(symbols, user_id='admin', user_email=None, user_name=None):
    """
    Synchronous ingestion: Fetch -> Indicators -> Scores.
    Used for on-demand portfolio reviews.
    """
    if not symbols:
        return

    logger.info(f"[INGEST] Starting sync ingestion for: {symbols}")
    
    # 1. Fetch data from Yahoo Finance
    for sym in symbols:
        # Search priority: NSE then BSE
        for suffix in [".NS", ".BO"]:
            ticker = f"{sym}{suffix}"
            try:
                logger.info(f"[INGEST] Fetching: {ticker}")
                raw = yf.download(ticker, period="2y", progress=False, auto_adjust=True)
                
                if not raw.empty:
                    df = raw.reset_index()
                    
                    # Handle MultiIndex/Tuple columns and fix the 'df.columns' truncation
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = [c[0].lower().replace(" ", "_") for c in df.columns]
                    else:
                        df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
                    
                    df['symbol'] = sym
                    df['date'] = pd.to_datetime(df['date']).dt.date
                    df['adjusted_close'] = df.get('adj_close', df.get('close'))
                    
                    # Clean and insert
                    records = df[['symbol', 'date', 'open', 'high', 'low', 'close', 'adjusted_close', 'volume']].dropna(subset=['close']).to_dict('records')
                    insert_daily_prices(records)
                    break # Success with this suffix
            except Exception as e:
                logger.error(f"[INGEST] Failed {ticker}: {e}")

    # 2. Compute Technical Indicators
    logger.info(f"[INGEST] Computing indicators for {symbols}")
    compute_indicators_for_symbols(symbols)

    # 3. Generate MRI Scores
    logger.info(f"[INGEST] Generating scores for {symbols}")
    compute_stock_scores_for_symbols(symbols)
    
    logger.info(f"[INGEST] Completed sync ingestion for {len(symbols)} symbols.")