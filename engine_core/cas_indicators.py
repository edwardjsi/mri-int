"""
engine_core.cas_indicators — Pure indicator computations for CAS V1.0 (Decision 100, rev 3).

This module provides the four new columns on `daily_prices` required by the
Capital Allocation Score. Each function is PURE — takes pandas Series, returns
pandas Series. No DB, no I/O.

    ema_100               — Simple EMA over 100 trading days
    rolling_high_52w      — Rolling max of `high` over 252 trading days
    weekly_trend_score    — 5-component composite (HH + HL + above weekly EMA-13
                             + above weekly EMA-20 + within 5% of 52w high)
    overhead_supply_score — Distinct high values in last 126 days that exceed
                             the current close, normalized 0–100 by max_count=10

These functions are called from `engine_core/indicator_engine.py` inside the
`compute_indicators()` pipeline and are wired into the DB write path via the
`INDICATOR_COLUMNS` tuple.

Rev 3 (2026-07-07):
    - All numeric thresholds (max_count, lookback, window sizes) are PARAMETERS
      with sensible defaults — they can be overridden at call time, but live in
      code (not YAML) because they're the canonical math definition, not
      business tunables. Business tunables (calibration.rs_strong, etc.) live in
      `config/capital_allocation.yaml` → `calibration.*`.
    - All functions return pd.Series indexed identically to the input so the
      caller can assign back to s_df directly.

Run:
    venv/bin/pytest engine_core/test_cas_indicators.py -v
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Default parameters — canonical math definition. Override only at the call
# site if you need to deviate (e.g., for sensitivity analysis).
EMA_100_SPAN = 100
ROLLING_HIGH_52W_WINDOW = 252  # ~1 year of trading days
ROLLING_HIGH_52W_MIN_PERIODS = 50  # Emit values early for thin histories
WEEKLY_EMA13_SPAN = 13
WEEKLY_EMA20_SPAN = 20
WEEKLY_RESAMPLE_FREQ = "W-FRI"  # Friday close (Indian market)
OVERHEAD_LOOKBACK = 126  # ~6 months of trading days
OVERHEAD_MAX_COUNT = 10  # Score saturates at this many distinct highs

# Weekly trend score component weights (sum = 100)
WTS_HIGHER_HIGHS = 25
WTS_HIGHER_LOWS = 25
WTS_ABOVE_WEEKLY_EMA13 = 20
WTS_ABOVE_WEEKLY_EMA20 = 15
WTS_WITHIN_52W_HIGH = 15
WTS_TOTAL = (WTS_HIGHER_HIGHS + WTS_HIGHER_LOWS + WTS_ABOVE_WEEKLY_EMA13
             + WTS_ABOVE_WEEKLY_EMA20 + WTS_WITHIN_52W_HIGH)
assert WTS_TOTAL == 100, f"Weekly trend score weights must sum to 100; got {WTS_TOTAL}"

NEAR_52W_HIGH_PCT = 5  # within 5% of 52w high


# ── ema_100 ─────────────────────────────────────────────────────────────────


def compute_ema_100(close: pd.Series, span: int = EMA_100_SPAN) -> pd.Series:
    """Compute EMA over `span` days on the close price.

    Convention: rows before `span - 1` are NaN (warm-up incomplete). Caller
    decides whether to fall back to ema_50 (matching the existing pattern
    in `engine_core/indicator_engine.py` for ema_200).

    Args:
        close: pd.Series of close prices indexed by date.
        span:  EMA span (default 100).

    Returns:
        pd.Series of EMA values, same index as input.
    """
    ema = close.ewm(span=span, adjust=False).mean()
    # Mark the first `span - 1` rows as NaN (incomplete warm-up).
    # pandas ewm seeds at row 0 with adjust=False, but we want the engine to
    # treat early values as "not reliable" so downstream consumers can fall
    # back (e.g., use ema_50 when ema_100 is NaN).
    ema.iloc[: span - 1] = np.nan
    return ema


# ── rolling_high_52w ────────────────────────────────────────────────────────


def compute_rolling_high_52w(
    high: pd.Series,
    window: int = ROLLING_HIGH_52W_WINDOW,
    min_periods: int = ROLLING_HIGH_52W_MIN_PERIODS,
) -> pd.Series:
    """Rolling max of `high` over `window` trading days.

    Uses `high` (not `close`) because the 52-week high is the highest intraday
    price, which is the most relevant resistance level.

    Args:
        high:        pd.Series of high prices.
        window:      Window size in trading days (default 252 ≈ 1 year).
        min_periods: Emit NaN until this many rows are available (default 50).

    Returns:
        pd.Series of rolling high values.
    """
    return high.rolling(window=window, min_periods=min_periods).max()


# ── weekly components + weekly_trend_score ──────────────────────────────────


def compute_weekly_components(
    df: pd.DataFrame,
    date_col: str = "date",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
) -> pd.DataFrame:
    """Compute the intermediate weekly series needed for `weekly_trend_score`.

    Returns a DataFrame indexed by week-end (W-FRI), with columns:
        weekly_high       — max of daily high in the week
        weekly_low        — min of daily low in the week
        weekly_ema13      — EMA-13 on weekly close
        weekly_ema20      — EMA-20 on weekly close
        hh_confirmed      — True if this week's high > previous week's high
        hl_confirmed      — True if this week's low > previous week's low

    Intermediate columns; not persisted. The CAS engine consumes these via
    `compute_weekly_trend_score(df, rolling_high_52w)` which forward-fills
    to daily.

    Args:
        df:        DataFrame with date, high, low, close columns.
        date_col:  Name of the date column.
        high_col:  Name of the high column.
        low_col:   Name of the low column.
        close_col: Name of the close column.

    Returns:
        pd.DataFrame indexed by week-end (DatetimeIndex, freq='W-FRI').
    """
    if date_col not in df.columns:
        # If df already has a DatetimeIndex, use that
        if isinstance(df.index, pd.DatetimeIndex):
            work = df.copy()
        else:
            raise ValueError(
                f"DataFrame must have a '{date_col}' column or a DatetimeIndex"
            )
    else:
        work = df.set_index(pd.to_datetime(df[date_col])).copy()

    weekly = pd.DataFrame()
    weekly["weekly_high"] = work[high_col].resample(WEEKLY_RESAMPLE_FREQ).max()
    weekly["weekly_low"] = work[low_col].resample(WEEKLY_RESAMPLE_FREQ).min()
    weekly_close = work[close_col].resample(WEEKLY_RESAMPLE_FREQ).last()
    weekly["weekly_ema13"] = weekly_close.ewm(span=WEEKLY_EMA13_SPAN, adjust=False).mean()
    weekly["weekly_ema20"] = weekly_close.ewm(span=WEEKLY_EMA20_SPAN, adjust=False).mean()

    weekly["hh_confirmed"] = (weekly["weekly_high"] > weekly["weekly_high"].shift(1)).fillna(False)
    weekly["hl_confirmed"] = (weekly["weekly_low"] > weekly["weekly_low"].shift(1)).fillna(False)

    return weekly


def compute_weekly_trend_score(
    df: pd.DataFrame,
    rolling_high_52w: pd.Series,
    near_52w_pct: float = NEAR_52W_HIGH_PCT,
) -> pd.Series:
    """5-component weekly trend score (0–100), daily-indexed.

    Components:
        Higher Highs confirmed      (+25) — weekly high > prev weekly high
        Higher Lows confirmed       (+25) — weekly low > prev weekly low
        Above weekly EMA-13         (+20) — daily close > weekly EMA-13 (fwd-filled)
        Above weekly EMA-20         (+15) — daily close > weekly EMA-20 (fwd-filled)
        Within 5% of 52w high       (+15) — daily close >= 0.95 × rolling_high_52w

    Args:
        df:               DataFrame with date, high, low, close columns.
        rolling_high_52w: pd.Series of 52w rolling highs, same index as df.
        near_52w_pct:     Threshold for "near 52w high" (default 5%).

    Returns:
        pd.Series of weekly trend scores, indexed identically to df.
    """
    if "date" in df.columns:
        daily_idx = pd.to_datetime(df["date"])
        close = pd.Series(df["close"].values, index=daily_idx)
    else:
        daily_idx = df.index
        close = df["close"] if "close" in df.columns else df.iloc[:, 0]

    # Also align rolling_high_52w to daily_idx
    rh52_aligned = pd.Series(rolling_high_52w.values, index=daily_idx)

    weekly = compute_weekly_components(df)

    # Forward-fill weekly series to daily index (each daily row gets the most
    # recent week's values).
    weekly_daily = weekly.reindex(daily_idx, method="ffill")

    hh = weekly_daily["hh_confirmed"].fillna(False).astype(bool).astype(int) * WTS_HIGHER_HIGHS
    hl = weekly_daily["hl_confirmed"].fillna(False).astype(bool).astype(int) * WTS_HIGHER_LOWS

    above_ema13 = (close > weekly_daily["weekly_ema13"]).fillna(False).astype(bool).astype(int) * WTS_ABOVE_WEEKLY_EMA13
    above_ema20 = (close > weekly_daily["weekly_ema20"]).fillna(False).astype(bool).astype(int) * WTS_ABOVE_WEEKLY_EMA20

    near_52w_threshold = (1 - near_52w_pct / 100) * rh52_aligned
    within_52w = (close >= near_52w_threshold).fillna(False).astype(bool).astype(int) * WTS_WITHIN_52W_HIGH

    score = hh + hl + above_ema13 + above_ema20 + within_52w

    # Cast to float (sum of ints becomes int in older pandas; spec says NUMERIC)
    return score.astype(float).reset_index(drop=True)


# ── overhead_supply_score ───────────────────────────────────────────────────


def compute_overhead_supply_score(
    high: pd.Series,
    close: pd.Series,
    lookback: int = OVERHEAD_LOOKBACK,
    max_count: int = OVERHEAD_MAX_COUNT,
    bucket_pct: float | None = 0.5,
) -> pd.Series:
    """Per-row distinct `high` values above current close in last `lookback` rows.

    Score = min(distinct_count / max_count × 100, 100).
        0 distinct highs above close → 0 (clear air)
        1 distinct high above close → 10
        ...
        max_count distinct highs → 100 (saturated)

    Per design doc §3.4. The score is stored as "badness" — higher = more
    resistance. The CAS engine (`compute_market_score`) inverts internally so
    higher is better in the final score.

    Bucket rounding (Decision 101, expert Q1): by default, highs are rounded
    to nearest `bucket_pct`% before deduplication. This avoids the float
    granularity artifact where 110.01 / 110.03 / 110.04 (all within 0.04%)
    count as 3 distinct resistances instead of 1. Pass `bucket_pct=None` to
    disable bucketing.

    Convention: rows before `lookback` rows are available return 0
    (not enough data).

    Args:
        high:       pd.Series of high prices.
        close:      pd.Series of close prices.
        lookback:   Window size in trading days (default 126 ≈ 6 months).
        max_count:  Score saturates at this many distinct highs (default 10).
        bucket_pct: Round highs to nearest `bucket_pct`% before dedup.
                    Default 0.5. Pass None to disable (legacy behavior).

    Returns:
        pd.Series of overhead supply scores, same index as `high`.
    """
    n = len(high)
    scores = np.zeros(n, dtype=float)

    high_arr = high.values
    close_arr = close.values

    for i in range(lookback, n):
        window_highs = high_arr[i - lookback: i]
        current_close = close_arr[i]
        above = window_highs[window_highs > current_close]
        if len(above) == 0:
            scores[i] = 0.0
            continue
        if bucket_pct is not None and bucket_pct > 0:
            # Round to nearest bucket_pct% bucket. Example with bucket_pct=0.5:
            # 110.01 / 110.03 / 110.04 → all round to 110.0 → 1 distinct.
            # Anchor step size on the mean of `above` so the bucket is
            # proportional to the price level (a 0.5% bucket at 110 ≈ 0.55
            # is the same precision as a 0.5% bucket at 5000 ≈ 25.0).
            anchor = float(np.mean(above))
            step = anchor * (bucket_pct / 100.0)
            if step > 0:
                above = np.round(above / step) * step
        distinct = np.unique(above)
        scores[i] = min(len(distinct) / max_count * 100.0, 100.0)

    return pd.Series(scores, index=high.index)
