"""
Nifty 500 Full Universe Ingestion Script
=========================================
Downloads historical price data (2003-present) for all current Nifty 500 stocks
from yfinance and inserts into the daily_prices table in Neon DB.

This enables a survivorship-bias-aware full Nifty 500 backtest.

Usage:
    cd ~/mri-int
    source venv/bin/activate
    PYTHONPATH=. python3 src/ingest_nifty500.py

Resumes from where it left off (ON CONFLICT DO NOTHING on existing rows).
Estimated time: 30-60 minutes for 500 stocks × 22 years.
"""
import time
import logging
import io
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

from engine_core.db import get_connection, insert_daily_prices

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('outputs/nifty500_ingestion.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Fetch from 2003 to give EMA-200 warmup before 2005 backtest start
START_DATE = "2003-01-01"
END_DATE   = datetime.today().strftime("%Y-%m-%d")

# NSE Nifty 500 constituent list (current)
NIFTY500_URL = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"

# Throttle: wait between stocks to avoid yfinance rate limiting
SLEEP_BETWEEN_STOCKS = 0.5  # seconds


def fetch_nifty500_symbols() -> list[str]:
    """Download current Nifty 500 constituent list from NSE and return NSE symbols."""
    logger.info("Fetching Nifty 500 constituent list from NSE...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        response = requests.get(NIFTY500_URL, headers=headers, timeout=30)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text))
        symbols = df["Symbol"].dropna().str.strip().tolist()
        logger.info(f"Found {len(symbols)} symbols in Nifty 500 list.")
        return symbols
    except Exception as e:
        logger.error(f"Failed to fetch Nifty 500 list: {e}")
        raise


def get_already_ingested_symbols() -> set[str]:
    """Return the set of symbols that already have at least 200 rows in daily_prices."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT symbol
        FROM daily_prices
        GROUP BY symbol
        HAVING COUNT(*) >= 200
    """)
    existing = {r[0] for r in cur.fetchall()}
    cur.close()
    conn.close()
    logger.info(f"{len(existing)} symbols already have sufficient history in DB.")
    return existing


def flatten_yf_columns(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Flatten yfinance MultiIndex columns to simple lowercase names."""
    df = df.reset_index()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0].lower().replace(" ", "_") for col in df.columns]
    else:
        df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    return df


def download_stock(symbol: str) -> pd.DataFrame:
    """Download full history for a symbol, trying NSE (.NS), then BSE (.BO)."""
    for suffix in [".NS", ".BO"]:
        ticker = f"{symbol}{suffix}"
        try:
            raw = yf.download(
                ticker,
                start=START_DATE,
                end=END_DATE,
                progress=False,
                auto_adjust=True,
            )
            if raw is not None and not raw.empty:
                df = flatten_yf_columns(raw, ticker)
                if "close" in df.columns and len(df) > 50:
                    logger.info(f"  ✓ {ticker}: {len(df)} rows")
                    return df, ticker
        except Exception as e:
            logger.debug(f"  {ticker} failed: {e}")

    logger.warning(f"  ✗ {symbol}: no data on NSE or BSE")
    return pd.DataFrame(), None


def prepare_records(df: pd.DataFrame, symbol: str) -> list[dict]:
    """Convert a yfinance DataFrame to a list of dicts for insert_daily_prices."""
    if "close" not in df.columns:
        if "adj_close" in df.columns:
            df["close"] = df["adj_close"]
        else:
            return []

    for col in ["open", "high", "low"]:
        if col not in df.columns:
            df[col] = df["close"]
    if "volume" not in df.columns:
        df["volume"] = 0

    df["adjusted_close"] = df.get("adj_close", df["close"])

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.date
    else:
        return []

    df["symbol"] = symbol.upper()
    df = df[["symbol", "date", "open", "high", "low", "close", "adjusted_close", "volume"]]
    df = df.dropna(subset=["close"])
    return df.to_dict("records")


def run():
    os.makedirs("outputs", exist_ok=True)

    # Step 1: Get all target symbols
    nifty500 = fetch_nifty500_symbols()

    # Step 2: Skip symbols we already have sufficient data for
    already_done = get_already_ingested_symbols()
    to_ingest = [s for s in nifty500 if s not in already_done]

    logger.info(f"Symbols to ingest: {len(to_ingest)} (skipping {len(already_done)} already complete)")

    failed = []
    total = len(to_ingest)

    for i, symbol in enumerate(to_ingest, 1):
        logger.info(f"[{i}/{total}] Processing {symbol}...")
        try:
            df, source_ticker = download_stock(symbol)
            if df.empty:
                failed.append(symbol)
                continue

            records = prepare_records(df, symbol)
            if not records:
                logger.warning(f"  {symbol}: no usable records after cleanup.")
                failed.append(symbol)
                continue

            insert_daily_prices(records)
            logger.info(f"  Inserted {len(records)} rows for {symbol}")

        except Exception as e:
            logger.error(f"  ERROR on {symbol}: {e}")
            failed.append(symbol)

        time.sleep(SLEEP_BETWEEN_STOCKS)

    # Summary
    logger.info("=" * 60)
    logger.info("INGESTION COMPLETE")
    logger.info(f"  Attempted : {total}")
    logger.info(f"  Failed    : {len(failed)}")
    if failed:
        logger.info(f"  Failed symbols: {', '.join(failed)}")
    logger.info("=" * 60)
    logger.info("Next step: run the indicator and regime engines to compute EMAs and scores.")
    logger.info("  python3 src/indicator_engine.py")
    logger.info("  python3 src/regime_engine.py")
    logger.info("Then re-run the backtest:")
    logger.info("  python3 src/portfolio_engine.py")


if __name__ == "__main__":
    run()
