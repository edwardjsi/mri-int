"""
engine_core/upstox_ingest.py
============================
Upstox V3 historical-candle adapter for MRI daily OHLCV ingestion.

Replaces yfinance/Yahoo Finance as the data source for:
  - engine_core/ingestion_engine.py  (load_indices, load_stocks)
  - engine_core/on_demand_ingest.py  (ingest_missing_symbols_sync)

Public API
----------
fetch_daily_ohlcv(symbols, lookback_calendar_days=400)
    -> dict[str, pd.DataFrame]   columns: date, open, high, low, close, volume

fetch_index_ohlcv(index_name, lookback_calendar_days=400)
    -> dict[str, pd.DataFrame]   same column set

Instrument Resolution
---------------------
Symbol -> instrument_key via the Upstox instrument master (scratch/NSE.csv).
The resolver is isolated: callers never touch instrument_key directly.

Token
-----
Read from os.environ["UPSTOX_ACCESS_TOKEN"].
NEVER logged. Raises UpstoxAuthError if missing.
"""

from __future__ import annotations

import io
import logging
import os
import random
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
import threading

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_INSTRUMENT_MASTER_LOCAL = Path(__file__).parent.parent / "scratch" / "NSE.csv"
_INSTRUMENT_MASTER_URL = (
    "https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv.gz"
)

# Instrument keys verified from scratch/NSE.csv on 2026-08-15
_INDEX_KEYS: dict[str, str] = {
    "NIFTY50":  "NSE_INDEX|Nifty 50",   # VERIFIED from scratch/NSE.csv
    "NIFTY500": "NSE_INDEX|Nifty 500",  # VERIFIED from scratch/NSE.csv
    #
    # SENSEX DEFERRED — 2026-08-15
    # SENSEX is a BSE index. The BSE instrument master CDN returns HTTP 403.
    # "BSE_INDEX|SENSEX" was never verified from any authoritative Upstox source.
    # Pattern inference is not acceptable per architect specification.
    # The MRI regime engine consumes ONLY market_index_prices.symbol='NIFTY50'.
    # SENSEX is NOT required by any current downstream MRI component.
    # Resolution: obtain the exact BSE_INDEX instrument_key from Upstox via a
    # verified API call or authoritative instrument master, then add it here.
    # "SENSEX": "BSE_INDEX|SENSEX",  # DO NOT uncomment without verification.
}

_V3_CANDLE_URL = (
    "https://api.upstox.com/v3/historical-candle"
    "/{instrument_key}/days/1/{to_date}/{from_date}"
)

# Retry configuration
_MAX_RETRIES = 4
_RETRY_BASE_SLEEP = 1.5   # seconds
_RETRY_MAX_SLEEP = 30.0   # seconds

# BSE overrides carried over from on_demand_ingest.py (Decision 042)
# Maps MRI symbol -> BSE instrument_key (verified).
# These are only used when NSE_EQ lookup fails.
_BSE_OVERRIDES: dict[str, str] = {
    "CIGNITITEC": "BSE_EQ|INE422C01022",
    "SKFINDIAN":  "BSE_EQ|INE640A01023",
    "M&M":        "BSE_EQ|INE101A01026",
    "MAHLOG":     "BSE_EQ|INE852O01025",
    "ONEGLOBAL":  "BSE_EQ|INE0RH901015",
}


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class UpstoxAuthError(RuntimeError):
    """Raised when UPSTOX_ACCESS_TOKEN is missing or rejected (401/403)."""


class UpstoxInstrumentNotFoundError(LookupError):
    """Raised when a symbol cannot be resolved to an instrument_key."""


class UpstoxIngestionError(RuntimeError):
    """Raised when ingestion fails after all retries are exhausted."""


# ---------------------------------------------------------------------------
# Token access (never logged)
# ---------------------------------------------------------------------------

def _get_token() -> str:
    token = os.environ.get("UPSTOX_ACCESS_TOKEN", "").strip()
    if not token:
        raise UpstoxAuthError(
            "UPSTOX_ACCESS_TOKEN environment variable is not set.\n"
            "Ensure the Analytics Token is configured in .env."
        )
    return token


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_get_token()}",
        "Accept": "application/json",
    }


# ---------------------------------------------------------------------------
# Instrument master — load and resolve
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InstrumentRecord:
    instrument_key: str
    tradingsymbol: str
    name: str
    instrument_type: str
    exchange: str

_instrument_master_lock = threading.Lock()

def _try_refresh_instrument_master() -> bool:
    """
    Attempt to refresh scratch/NSE.csv from Upstox CDN.
    Returns True on success, False on failure.
    The caller decides whether to abort or use the existing local copy.
    """
    try:
        logger.info("[upstox] Refreshing instrument master from Upstox CDN...")
        r = requests.get(
            _INSTRUMENT_MASTER_URL,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30,
        )
        if r.status_code != 200:
            logger.warning(
                "[upstox] Instrument master refresh returned HTTP %s — "
                "will use existing local copy.",
                r.status_code,
            )
            return False
        df = pd.read_csv(io.BytesIO(r.content), compression="gzip")
        df.to_csv(_INSTRUMENT_MASTER_LOCAL, index=False)
        logger.info(
            "[upstox] Instrument master refreshed: %d rows → %s",
            len(df),
            _INSTRUMENT_MASTER_LOCAL,
        )
        return True
    except Exception as exc:
        logger.warning(
            "[upstox] Instrument master refresh failed (%s) — "
            "will use existing local copy.",
            exc,
        )
        return False


@lru_cache(maxsize=1)
def _load_instrument_master() -> pd.DataFrame:
    """
    Load the instrument master CSV.
    Fail-safe: refresh → existing local → hard failure (no local copy).
    Result is cached in-process.
    """
    with _instrument_master_lock:
        _try_refresh_instrument_master()

        if not _INSTRUMENT_MASTER_LOCAL.exists():
            raise FileNotFoundError(
                f"Instrument master not found at {_INSTRUMENT_MASTER_LOCAL} "
                "and refresh from CDN also failed. Cannot resolve symbols."
            )

        df = pd.read_csv(_INSTRUMENT_MASTER_LOCAL, low_memory=False)
        logger.info(
            "[upstox] Instrument master loaded: %d rows from %s",
            len(df),
            _INSTRUMENT_MASTER_LOCAL,
        )
        return df


def _resolve_equity_symbol(symbol: str) -> str:
    """
    Resolve an MRI equity symbol to its Upstox instrument_key.

    Resolution order:
      1. NSE_EQ   — primary
      2. BSE explicit override list — only for known problem symbols

    Never silently falls back from NSE to BSE for arbitrary symbols.
    Raises UpstoxInstrumentNotFoundError if not found.
    """
    sym = symbol.upper().strip()

    # --- BSE explicit override (highest priority for known problem symbols) ---
    if sym in _BSE_OVERRIDES:
        key = _BSE_OVERRIDES[sym]
        logger.debug("[upstox] %s → %s (BSE override)", sym, key)
        return key

    # --- NSE_EQ lookup ---
    df = _load_instrument_master()
    nse = df[df["exchange"] == "NSE_EQ"]

    # Upstox tradingsymbol for equities is typically "SYMBOL-EQ"
    match = nse[nse["tradingsymbol"] == f"{sym}-EQ"]
    if match.empty:
        match = nse[nse["tradingsymbol"] == sym]

    if not match.empty:
        key = match.iloc[0]["instrument_key"]
        logger.debug("[upstox] %s → %s (NSE_EQ)", sym, key)
        return key

    raise UpstoxInstrumentNotFoundError(
        f"Cannot resolve '{symbol}' to an Upstox instrument_key. "
        "Check the symbol against the Upstox NSE master. "
        "If it's a BSE-only symbol, add it to _BSE_OVERRIDES in upstox_ingest.py."
    )


def _resolve_index_key(index_name: str) -> str:
    """
    Resolve a logical index name to its verified Upstox instrument_key.
    Only accepts names defined in _INDEX_KEYS — does not guess.
    """
    key = _INDEX_KEYS.get(index_name.upper())
    if key is None:
        raise UpstoxInstrumentNotFoundError(
            f"Unknown index '{index_name}'. "
            f"Known indices: {list(_INDEX_KEYS.keys())}"
        )
    return key


# ---------------------------------------------------------------------------
# HTTP call with bounded retry
# ---------------------------------------------------------------------------

def _fetch_candles_raw(
    instrument_key: str,
    from_date: date,
    to_date: date,
    symbol_label: str,
) -> list[list]:
    """
    Call the Upstox V3 historical-candle endpoint.
    Returns list of raw candle arrays: [timestamp, open, high, low, close, volume, oi]

    Error handling:
      401/403 → UpstoxAuthError (no retry)
      404     → UpstoxInstrumentNotFoundError (no retry)
      429     → exponential backoff with jitter
      5xx     → exponential backoff with jitter
      other   → UpstoxIngestionError after retries
    """
    url = _V3_CANDLE_URL.format(
        instrument_key=instrument_key,
        from_date=from_date.strftime("%Y-%m-%d"),
        to_date=to_date.strftime("%Y-%m-%d"),
    )

    attempt = 0
    while True:
        attempt += 1
        try:
            resp = requests.get(url, headers=_auth_headers(), timeout=30)
        except requests.RequestException as exc:
            if attempt >= _MAX_RETRIES:
                raise UpstoxIngestionError(
                    f"Network error after {attempt} attempts for {symbol_label}: {exc}"
                ) from exc
            _sleep_backoff(attempt)
            continue

        status = resp.status_code

        if status == 200:
            try:
                candles = resp.json().get("data", {}).get("candles", [])
                return candles
            except Exception as exc:
                raise UpstoxIngestionError(
                    f"Malformed JSON from Upstox for {symbol_label}: {exc}"
                ) from exc

        if status in (401, 403):
            raise UpstoxAuthError(
                f"Upstox authentication failed (HTTP {status}) for {symbol_label}. "
                "Check that UPSTOX_ACCESS_TOKEN is current (tokens expire at 3:30 AM IST)."
            )

        if status == 404:
            raise UpstoxInstrumentNotFoundError(
                f"Upstox returned 404 for instrument_key={instrument_key} "
                f"(symbol={symbol_label}). The instrument may be delisted."
            )

        if status == 429:
            logger.warning(
                "[upstox] Rate limit (429) on attempt %d/%d for %s — backing off.",
                attempt, _MAX_RETRIES, symbol_label,
            )
            if attempt >= _MAX_RETRIES:
                raise UpstoxIngestionError(
                    f"Rate limit persists after {attempt} attempts for {symbol_label}."
                )
            _sleep_backoff(attempt)
            continue

        if 500 <= status < 600:
            logger.warning(
                "[upstox] Server error (HTTP %s) on attempt %d/%d for %s — backing off.",
                status, attempt, _MAX_RETRIES, symbol_label,
            )
            if attempt >= _MAX_RETRIES:
                raise UpstoxIngestionError(
                    f"Upstox server error HTTP {status} after {attempt} attempts "
                    f"for {symbol_label}."
                )
            _sleep_backoff(attempt)
            continue

        # Unexpected status
        raise UpstoxIngestionError(
            f"Unexpected HTTP {status} from Upstox for {symbol_label}: "
            f"{resp.text[:200]}"
        )


def _sleep_backoff(attempt: int) -> None:
    """Bounded exponential backoff with jitter."""
    sleep = min(_RETRY_BASE_SLEEP * (2 ** (attempt - 1)), _RETRY_MAX_SLEEP)
    sleep += random.uniform(0, sleep * 0.25)
    logger.info("[upstox] Sleeping %.1fs before retry %d...", sleep, attempt + 1)
    time.sleep(sleep)


# ---------------------------------------------------------------------------
# Candle normalization
# ---------------------------------------------------------------------------

def _candles_to_dataframe(candles: list[list], symbol: str) -> Optional[pd.DataFrame]:
    """
    Convert Upstox raw candle list to a normalized DataFrame.

    Upstox candle format:
        [timestamp, open, high, low, close, volume, oi]

    Output columns:
        date (python date), open, high, low, close, volume
    """
    if not candles:
        return None

    df = pd.DataFrame(
        candles,
        columns=["timestamp", "open", "high", "low", "close", "volume", "oi"],
    )
    df["date"] = pd.to_datetime(df["timestamp"]).dt.date
    df = df[["date", "open", "high", "low", "close", "volume"]].copy()
    df = df.dropna(subset=["close"])
    df = df[df["close"] > 0]
    df = df.sort_values("date").reset_index(drop=True)
    return df if not df.empty else None


# ---------------------------------------------------------------------------
# Date chunking (Upstox V3 limits ~10 years per call)
# ---------------------------------------------------------------------------

def _date_chunks(
    from_date: date,
    to_date: date,
    chunk_days: int = 365 * 9,
) -> list[tuple[date, date]]:
    """Split a date range into chunks for the Upstox API."""
    chunks = []
    curr = from_date
    while curr < to_date:
        end = min(curr + timedelta(days=chunk_days), to_date)
        chunks.append((curr, end))
        curr = end + timedelta(days=1)
    return chunks


# ---------------------------------------------------------------------------
# Core fetch helpers
# ---------------------------------------------------------------------------

def _fetch_symbol_ohlcv(
    symbol: str,
    instrument_key: str,
    from_date: date,
    to_date: date,
) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV for a single symbol across chunked date ranges.
    Returns a normalized DataFrame or None on failure.
    Logs a structured ingestion record per the spec.
    """
    all_candles: list[list] = []

    for chunk_from, chunk_to in _date_chunks(from_date, to_date):
        try:
            candles = _fetch_candles_raw(
                instrument_key, chunk_from, chunk_to, symbol
            )
            all_candles.extend(candles)
        except (UpstoxAuthError, UpstoxInstrumentNotFoundError):
            raise   # propagate — no point retrying different date chunks
        except UpstoxIngestionError as exc:
            logger.error(
                "source=UPSTOX_V3 symbol=%s instrument=%s from=%s to=%s "
                "status=FAILED reason=%s",
                symbol, instrument_key, chunk_from, chunk_to, exc,
            )
            return None

    df = _candles_to_dataframe(all_candles, symbol)
    if df is None or df.empty:
        logger.warning(
            "source=UPSTOX_V3 symbol=%s instrument=%s from=%s to=%s "
            "rows=0 status=EMPTY_RESPONSE",
            symbol, instrument_key, from_date, to_date,
        )
        return None

    latest_date = df["date"].max()
    logger.info(
        "source=UPSTOX_V3 symbol=%s instrument=%s from=%s to=%s "
        "rows=%d latest=%s status=SUCCESS",
        symbol, instrument_key, from_date, to_date, len(df), latest_date,
    )
    return df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_daily_ohlcv(
    symbols: list[str],
    lookback_calendar_days: int = 400,
) -> dict[str, pd.DataFrame]:
    """
    Fetch daily OHLCV for a list of equity symbols via Upstox V3.

    Parameters
    ----------
    symbols : list[str]
        MRI symbol names (e.g. ['RELIANCE', 'TCS', 'INFY'])
    lookback_calendar_days : int
        Calendar days of history to fetch (default 400 to cover 200-day EMA warmup).

    Returns
    -------
    dict[str, pd.DataFrame]
        Keyed by symbol. Each DataFrame has columns:
        date (date), open, high, low, close, volume

    Notes
    -----
    - Symbols that fail to resolve or fetch are excluded from the result.
    - Auth failures raise UpstoxAuthError immediately (abort the batch).
    """
    if not symbols:
        return {}

    to_date = date.today()
    from_date = to_date - timedelta(days=lookback_calendar_days)

    result: dict[str, pd.DataFrame] = {}

    for symbol in symbols:
        sym = symbol.upper().strip()
        try:
            instrument_key = _resolve_equity_symbol(sym)
        except UpstoxInstrumentNotFoundError as exc:
            logger.error(
                "source=UPSTOX_V3 symbol=%s status=FAILED reason=INSTRUMENT_NOT_FOUND detail=%s",
                sym, exc,
            )
            continue

        try:
            df = _fetch_symbol_ohlcv(sym, instrument_key, from_date, to_date)
        except UpstoxAuthError:
            raise   # propagate — entire batch must stop
        except Exception as exc:
            logger.error(
                "source=UPSTOX_V3 symbol=%s instrument=%s status=FAILED reason=%s",
                sym, instrument_key, exc,
            )
            continue

        if df is not None:
            result[sym] = df

    return result


def fetch_index_ohlcv(
    index_name: str,
    lookback_calendar_days: int = 400,
) -> dict[str, pd.DataFrame]:
    """
    Fetch daily OHLCV for a named index via Upstox V3.

    Parameters
    ----------
    index_name : str
        Currently supported: 'NIFTY50', 'NIFTY500'
        SENSEX is deferred — instrument key not verified (see _INDEX_KEYS comments).

    Returns
    -------
    dict[str, pd.DataFrame]
        Keyed by index_name. Empty dict if fetch fails.
    """
    to_date = date.today()
    from_date = to_date - timedelta(days=lookback_calendar_days)

    name = index_name.upper().strip()
    try:
        instrument_key = _resolve_index_key(name)
    except UpstoxInstrumentNotFoundError as exc:
        logger.error(
            "source=UPSTOX_V3 symbol=%s status=FAILED reason=INDEX_NOT_FOUND detail=%s",
            name, exc,
        )
        return {}

    try:
        df = _fetch_symbol_ohlcv(name, instrument_key, from_date, to_date)
    except UpstoxAuthError:
        raise
    except Exception as exc:
        logger.error(
            "source=UPSTOX_V3 symbol=%s instrument=%s status=FAILED reason=%s",
            name, instrument_key, exc,
        )
        return {}

    if df is None:
        return {}

    return {name: df}


# ---------------------------------------------------------------------------
# Stale-data circuit breaker
# ---------------------------------------------------------------------------

def assert_no_stale_data(
    conn,
    symbols: list[str],
    table: str = "daily_prices",
) -> bool:
    """
    Verify that `table` contains data up to the most recent expected trading date
    for all listed symbols.

    A symbol is considered stale if its MAX(date) < the most recent trading date
    (last weekday, skipping today if before market close or today is weekend).

    Returns True if all symbols are fresh.
    Logs a STALE_DATA warning for each stale symbol.
    Returns False if any symbol is stale.

    NOTE: Does not account for market holidays. A symbol stale by exactly 1 day
    on a holiday is a false alarm. A symbol stale by 2+ days is always a real failure.
    """
    expected = _last_expected_trading_date()
    stale: list[str] = []

    with conn.cursor() as cur:
        for sym in symbols:
            cur.execute(
                f"SELECT MAX(date) FROM {table} WHERE symbol = %s",
                (sym,),
            )
            row = cur.fetchone()
            latest = row[0] if row else None
            if latest is None or latest < expected:
                logger.warning(
                    "STALE_DATA symbol=%s table=%s latest=%s expected>=%s",
                    sym, table, latest, expected,
                )
                stale.append(sym)
            else:
                logger.info(
                    "FRESHNESS_OK symbol=%s table=%s latest=%s",
                    sym, table, latest,
                )

    if stale:
        logger.error(
            "CIRCUIT_BREAKER TRIGGERED: %d symbol(s) have stale data: %s. "
            "Downstream MRI/regime/signal generation should NOT run on stale prices.",
            len(stale), stale,
        )
        return False

    return True


def _last_expected_trading_date() -> date:
    """
    Return the most recent date we'd expect to have data for.
    Heuristic: last completed weekday (Mon-Fri) before now.
    Does not know about Indian market holidays.
    """
    today = date.today()
    # If today is Monday, the last trading day was Friday
    offset = max(1, today.weekday() - 4) if today.weekday() >= 5 else 1
    return today - timedelta(days=offset)
