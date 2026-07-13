"""
engine_core.cas_indicators — Pure indicator computations for CAS V1.0 (Decision 100, rev 3)
and V2 ADD_SECOND_TRANCHE gates (Decision 103).

This module provides the four new columns on `daily_prices` required by the
Capital Allocation Score. Each function is PURE — takes pandas Series, returns
pandas Series. No DB, no I/O.

    ema_100               — Simple EMA over 100 trading days
    rolling_high_52w      — Rolling max of `high` over 252 trading days
    weekly_trend_score    — 5-component composite (HH + HL + above weekly EMA-13
                             + above weekly EMA-20 + within 5% of 52w high)
    overhead_supply_score — Distinct high values in last 126 days that exceed
                             the current close, normalized 0–100 by max_count=20
                             (Decision 102: raised from 10 for better discriminatory power)

Decision 103 (V2 Pyramiding Discipline Gates, 2026-07-13) — ADD_SECOND_TRANCHE
gate inputs G3 (weekly breakout) + G4 (volume-confirmed breakout):

    ResistanceSource            — str enum: PRIOR_52W_HIGH | ALL_TIME_HIGH (C9)
    compute_prior_52w_high      — max of weekly highs in the prior 52 weeks,
                                  excluding current week (G3 primary)
    compute_all_time_high_before_current_week — cumulative weekly high before
                                  current week (G3 fallback for thin history)
    compute_weekly_close_above_resistance     — bool per row: most recent
                                  Friday close > selected resistance level
    compute_breakout_day_volume_ratio         — DataFrame of 6 columns frozen
                                  at the breakout day (G4 versioned metadata)

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

Rev 4 (2026-07-13, Decision 103 P2):
    - Added ResistanceSource enum + 4 gate-input functions for ADD_SECOND_TRANCHE.
    - All gate-input functions are pure; the `ResistanceSource` enum value for a
      symbol is determined by history_weeks at the symbol level (constant per
      symbol, stored on every row for query convenience).
    - Threshold values (52 weeks, 1.3 ratio) are parameters with sensible
      defaults — production code reads them from `config/capital_allocation.yaml`
      → `add_gate.*` and passes them at call time. The defaults here match the
      YAML as of Decision 103 so unit tests stay deterministic.

Run:
    venv/bin/pytest engine_core/test_cas_indicators.py -v
"""

import logging
from enum import Enum

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ── Decision 103 enum: resistance source ────────────────────────────────────


class ResistanceSource(str, Enum):
    """Enum of valid resistance-source values for the G3 weekly breakout gate.

    C9: stored as TEXT in the DB (`daily_prices.resistance_source`), but the
    application code MUST use this enum. Migration 010 adds a CHECK constraint
    at the DB level as defense in depth.

    Inherits from `str` so values serialize naturally to JSON and Postgres TEXT.

    Members:
        PRIOR_52W_HIGH  — symbol has ≥ `min_history_weeks` of weekly history;
                           resistance = max of the prior 52 weekly highs.
        ALL_TIME_HIGH   — symbol has < `min_history_weeks` of weekly history;
                           resistance = all-time high (cumulative weekly high
                           before current week).
    """

    PRIOR_52W_HIGH = "PRIOR_52W_HIGH"
    ALL_TIME_HIGH = "ALL_TIME_HIGH"

# Default parameters — canonical math definition. Override only at the call
# site if you need to deviate (e.g., for sensitivity analysis).
EMA_100_SPAN = 100
ROLLING_HIGH_52W_WINDOW = 252  # ~1 year of trading days
ROLLING_HIGH_52W_MIN_PERIODS = 50  # Emit values early for thin histories
WEEKLY_EMA13_SPAN = 13
WEEKLY_EMA20_SPAN = 20
WEEKLY_RESAMPLE_FREQ = "W-FRI"  # Friday close (Indian market)
OVERHEAD_LOOKBACK = 126  # ~6 months of trading days
OVERHEAD_MAX_COUNT = 20  # Score saturates at this many distinct highs (Decision 102 override: was 10, expert override pre-V1.1 merge)

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


# ── Decision 103 V2 ADD gate inputs ─────────────────────────────────────────
#
# G3 (weekly breakout above resistance) + G4 (volume-confirmed breakout).
# All four functions below are PURE: take pandas Series, return pandas
# Series/DataFrame. No DB calls. The weekly resample pipeline
# (WEEKLY_RESAMPLE_FREQ = "W-FRI") is reused from the CAS V1.0 machinery
# above so that "what is a week" is defined in exactly one place.
#
# Threshold defaults (52 weeks, 1.3 ratio) match `config/capital_allocation.yaml`
# `add_gate.*` as of Decision 103. Production callers should read the YAML and
# pass the values explicitly; defaults exist so unit tests stay deterministic
# without YAML plumbing.


# ── prior_52w_high (G3 primary) ─────────────────────────────────────────────


def compute_prior_52w_high(
    high: pd.Series,
    window_weeks: int = 52,
) -> pd.Series:
    """For each daily row, max of weekly `high` in the prior `window_weeks` weeks,
    excluding the current week. Forward-filled to the daily index.

    Args:
        high:         pd.Series of daily high prices, MUST have a DatetimeIndex.
        window_weeks: Lookback in weeks (default 52). The function uses
                      `shift(1).rolling(window_weeks).max()` so that exactly
                      `window_weeks` prior weeks are considered.

    Returns:
        pd.Series of resistance levels, same daily index as `high`. Rows in
        the current week carry the most recent completed week's prior-N max;
        rows before the first completed week carry NaN.

    Notes:
        Convention: a row's "current week" is the W-FRI bucket containing that
        row's date. The row's value is the max of the prior `window_weeks`
        weekly highs — the current week's high is excluded (`shift(1)`).
    """
    if not isinstance(high.index, pd.DatetimeIndex):
        raise ValueError("`high` must have a DatetimeIndex")

    weekly_high = high.resample(WEEKLY_RESAMPLE_FREQ).max()
    prior_max = (
        weekly_high.shift(1).rolling(window=window_weeks, min_periods=1).max()
    )
    return prior_max.reindex(high.index, method="ffill")


# ── all_time_high_before_current_week (G3 fallback) ─────────────────────────


def compute_all_time_high_before_current_week(high: pd.Series) -> pd.Series:
    """For each daily row, max of weekly `high` since the start of the series,
    strictly before the current week. Forward-filled to the daily index.

    Used as the G3 fallback when the symbol has fewer than 52 weeks of weekly
    history (per Decision 103 C1). The caller is responsible for selecting
    between `prior_52w_high` and this function based on `history_weeks`.

    Args:
        high: pd.Series of daily high prices, MUST have a DatetimeIndex.

    Returns:
        pd.Series of all-time-high-before-current-week values, same daily index.
    """
    if not isinstance(high.index, pd.DatetimeIndex):
        raise ValueError("`high` must have a DatetimeIndex")

    weekly_high = high.resample(WEEKLY_RESAMPLE_FREQ).max()
    prior_max = weekly_high.shift(1).expanding().max()
    return prior_max.reindex(high.index, method="ffill")


# ── weekly_close_above_resistance (G3 boolean) ──────────────────────────────


def compute_weekly_close_above_resistance(
    close: pd.Series,
    resistance_level: pd.Series,
) -> pd.Series:
    """For each daily row, True if the most recent weekly close (W-FRI) is
    strictly greater than `resistance_level` for that row.

    Both inputs must be daily-indexed and aligned. The resistance level for
    each daily row is typically `prior_52w_high` or `all_time_high_before_current_week`
    computed by the sibling functions above; the caller selects which one based
    on the symbol's `history_weeks`.

    Args:
        close:            pd.Series of daily close prices, DatetimeIndex.
        resistance_level: pd.Series of resistance levels, same index as `close`.

    Returns:
        pd.Series of bool, same index as `close`. NaN → False.

    Notes:
        The comparison is strict (`>`), matching Decision 103 G3: a weekly
        close that merely ties the resistance does NOT count as a breakout.
        This avoids the ambiguous "kissed the high" case from triggering an ADD.
    """
    if not isinstance(close.index, pd.DatetimeIndex):
        raise ValueError("`close` must have a DatetimeIndex")

    weekly_close = close.resample(WEEKLY_RESAMPLE_FREQ).last()
    weekly_close_daily = weekly_close.reindex(close.index, method="ffill")

    # Align resistance_level to the daily index just in case.
    res_aligned = resistance_level.reindex(close.index)

    return (weekly_close_daily > res_aligned).fillna(False).astype(bool)


# ── breakout_day_volume_ratio (G4 versioned metadata) ──────────────────────


def compute_breakout_day_volume_metrics(
    volume: pd.Series,
    breakout_date: pd.Timestamp | None,
    avg20_volume: pd.Series | None = None,
    threshold: float = 1.3,
    avg_window: int = 20,
) -> pd.DataFrame:
    """Compute the six G4 volume-confirmation columns, frozen at the breakout day.

    C2 (Decision 103): volume metadata is versioned. We persist the ratio, the
    threshold USED at the time, the raw breakout-day volume, the raw 20-day
    average, and the breakout date itself — not just the boolean. This lets us
    reproduce historical gate decisions when the threshold changes later.

    Returns a DataFrame of the same length and index as `volume`, with all six
    columns NaN/NaT/False EXCEPT on the breakout-date row. The caller writes
    these columns to `daily_prices` (or wherever) with `df[cols] = result`.

    Args:
        volume:        pd.Series of daily volume, MUST have DatetimeIndex.
        breakout_date: The breakout day's date. Pass None to populate every
                       row (treats the entire series as one breakout event —
                       useful for unit tests).
        avg20_volume:  Pre-computed 20-day rolling mean of `volume`. If None,
                       it is computed here with `rolling(avg_window).mean()`.
        threshold:     The ratio threshold (default 1.3 = 1.3× avg). Persisted
                       to `volume_threshold_used` for auditability.
        avg_window:    Window for the fallback 20-day avg (default 20).

    Returns:
        pd.DataFrame with columns (in this order):
            breakout_day_volume       — float, NaN except on breakout day
            breakout_day_avg20_volume — float, NaN except on breakout day
            breakout_day_volume_ratio — float, NaN except on breakout day
            volume_threshold_used     — float, NaN except on breakout day
            breakout_date_for_volume  — date,  NaT except on breakout day
            volume_confirmed_breakout — bool,  False except on breakout day
    """
    if not isinstance(volume.index, pd.DatetimeIndex):
        raise ValueError("`volume` must have a DatetimeIndex")

    n = len(volume)
    idx = volume.index

    out = pd.DataFrame(
        {
            "breakout_day_volume":       np.full(n, np.nan, dtype=float),
            "breakout_day_avg20_volume": np.full(n, np.nan, dtype=float),
            "breakout_day_volume_ratio": np.full(n, np.nan, dtype=float),
            "volume_threshold_used":     np.full(n, np.nan, dtype=float),
            "breakout_date_for_volume":  pd.array([pd.NaT] * n, dtype="datetime64[ns]"),
            "volume_confirmed_breakout": np.full(n, False, dtype=bool),
        },
        index=idx,
    )

    # Which rows to fill. None = entire series (test mode).
    if breakout_date is not None:
        mask = volume.index == breakout_date
        if not mask.any():
            logger.warning(
                "compute_breakout_day_volume_metrics: breakout_date=%s not found in index",
                breakout_date,
            )
            return out
    else:
        mask = pd.Series(True, index=idx)

    # Compute / fetch avg20_volume.
    if avg20_volume is None:
        avg = volume.rolling(window=avg_window, min_periods=avg_window).mean()
    else:
        avg = avg20_volume

    bd_vol = volume[mask].to_numpy(dtype=float)
    bd_avg = avg[mask].to_numpy(dtype=float)

    # Safe ratio: NaN where avg is 0 or NaN (avoid div-by-zero).
    ratios = np.where(bd_avg > 0, bd_vol / bd_avg, np.nan)

    out.loc[mask, "breakout_day_volume"]       = bd_vol
    out.loc[mask, "breakout_day_avg20_volume"] = bd_avg
    out.loc[mask, "breakout_day_volume_ratio"] = ratios
    out.loc[mask, "volume_threshold_used"]     = float(threshold)
    out.loc[mask, "breakout_date_for_volume"]  = breakout_date if breakout_date is not None else idx[mask]
    out.loc[mask, "volume_confirmed_breakout"] = (ratios >= threshold)

    return out
