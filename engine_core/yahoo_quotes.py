from __future__ import annotations

import os
import time
from dataclasses import dataclass

import yfinance as yf


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
    source_ticker: str
    fetched_at_unix: int


_CACHE_TTL_SECONDS = int(os.getenv("YAHOO_QUOTE_CACHE_TTL_SECONDS", "90"))
_cache: dict[str, Quote] = {}


def _now_unix() -> int:
    return int(time.time())


def _get_cached(symbol: str) -> Quote | None:
    q = _cache.get(symbol)
    if not q:
        return None
    if (_now_unix() - q.fetched_at_unix) > _CACHE_TTL_SECONDS:
        return None
    return q


def _set_cached(symbol: str, quote: Quote) -> None:
    _cache[symbol] = quote


def _extract_last_close(df, ticker: str) -> float | None:
    """Best-effort extraction of the latest close from yfinance download() output."""
    if df is None or getattr(df, "empty", True):
        return None

    try:
        # Single ticker: columns are Close/Open/...
        if "Close" in df.columns:
            v = df["Close"].dropna()
            return float(v.iloc[-1]) if len(v) else None
    except Exception:
        pass

    # Multi-ticker: columns may be a MultiIndex (Field, Ticker) or (Ticker, Field)
    cols = getattr(df, "columns", None)
    if cols is None:
        return None

    try:
        if getattr(cols, "nlevels", 1) >= 2:
            # Try (Field, Ticker)
            if ("Close", ticker) in cols:
                v = df[("Close", ticker)].dropna()
                return float(v.iloc[-1]) if len(v) else None
            # Try (Ticker, Field)
            if (ticker, "Close") in cols:
                v = df[(ticker, "Close")].dropna()
                return float(v.iloc[-1]) if len(v) else None
    except Exception:
        return None

    return None


def fetch_quotes(symbols: list[str]) -> tuple[dict[str, Quote], str | None]:
    """Fetch near-real-time quotes via Yahoo Finance (best effort).

    Returns:
      (quotes_by_symbol, error_message)
    """
    if not symbols:
        return {}, None

    normalized = [str(s).upper().strip() for s in symbols if str(s).strip()]
    unique = sorted(set(normalized))

    quotes: dict[str, Quote] = {}

    # Serve from cache where possible
    remaining: list[str] = []
    for sym in unique:
        cached = _get_cached(sym)
        if cached:
            quotes[sym] = cached
        else:
            remaining.append(sym)

    if not remaining:
        return quotes, None

    fetched_at = _now_unix()

    try:
        ns_tickers = [f"{s}.NS" for s in remaining]
        df_ns = yf.download(
            ns_tickers,
            period="1d",
            interval="1m",
            progress=False,
            auto_adjust=True,
            group_by="column",
            threads=True,
        )

        ns_prices: dict[str, float] = {}
        for sym in remaining:
            ticker = f"{sym}.NS"
            p = _extract_last_close(df_ns, ticker)
            if p is not None:
                ns_prices[sym] = p

        missing = [s for s in remaining if s not in ns_prices]
        bo_prices: dict[str, float] = {}
        if missing:
            bo_tickers = [f"{s}.BO" for s in missing]
            df_bo = yf.download(
                bo_tickers,
                period="1d",
                interval="1m",
                progress=False,
                auto_adjust=True,
                group_by="column",
                threads=True,
            )
            for sym in missing:
                ticker = f"{sym}.BO"
                p = _extract_last_close(df_bo, ticker)
                if p is not None:
                    bo_prices[sym] = p

        for sym, p in {**ns_prices, **bo_prices}.items():
            source_ticker = f"{sym}.NS" if sym in ns_prices else f"{sym}.BO"
            q = Quote(symbol=sym, price=float(p), source_ticker=source_ticker, fetched_at_unix=fetched_at)
            _set_cached(sym, q)
            quotes[sym] = q

        return quotes, None
    except Exception as e:
        # If Yahoo blocks/rate-limits, we fall back to EOD DB prices.
        return quotes, f"Yahoo quote fetch failed: {str(e)}"

