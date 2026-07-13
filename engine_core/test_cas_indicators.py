"""
engine_core.test_cas_indicators — unit tests for the pure CAS indicator
computations (Decision 100, rev 3, Session N+2).

Tests are written FIRST (TDD red-green) for the four new columns on
`daily_prices`:

    * ema_100              — simple EMA, span=100
    * rolling_high_52w     — rolling max of `high` over 252 trading days
    * weekly_trend_score   — 5-component composite (HH + HL + above EMA-13
                              + above EMA-20 + within 5% of 52w high)
    * overhead_supply_score — distinct high values in last 126 days that are
                              above current close, normalized 0–100 by
                              max_count=10

These functions are PURE: they take pandas Series and return pandas Series.
No DB, no I/O. They live in `engine_core/cas_indicators.py`.

Run:
    venv/bin/pytest engine_core/test_cas_indicators.py -v
"""

import numpy as np
import pandas as pd
import pytest

from engine_core.cas_indicators import (
    ResistanceSource,
    compute_all_time_high_before_current_week,
    compute_breakout_day_volume_metrics,
    compute_ema_100,
    compute_overhead_supply_score,
    compute_prior_52w_high,
    compute_rolling_high_52w,
    compute_weekly_close_above_resistance,
    compute_weekly_trend_score,
    compute_weekly_components,
)


# ── Test fixtures ───────────────────────────────────────────────────────────


def _make_uptrend_series(n_days: int = 300, start: float = 100.0,
                          daily_drift: float = 0.003,
                          daily_vol: float = 0.015,
                          seed: int = 42) -> pd.DataFrame:
    """Synthesize a clean uptrending price series of `n_days` rows.

    The deterministic seed guarantees reproducible tests.
    """
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n_days, freq="B")
    returns = rng.normal(loc=daily_drift, scale=daily_vol, size=n_days)
    close = start * np.exp(np.cumsum(returns))
    # open, high, low derived from close to look natural
    open_ = close * (1 + rng.normal(0, 0.005, n_days))
    high = np.maximum(close, open_) * (1 + np.abs(rng.normal(0, 0.005, n_days)))
    low = np.minimum(close, open_) * (1 - np.abs(rng.normal(0, 0.005, n_days)))
    volume = rng.integers(100_000, 1_000_000, n_days).astype(float)
    return pd.DataFrame(
        {"date": dates, "open": open_, "high": high,
         "low": low, "close": close, "volume": volume}
    )


def _make_flat_series(n_days: int = 300, start: float = 100.0) -> pd.DataFrame:
    """Synthesize a flat price series — useful for HH/HL = False, weekly EMAs at price."""
    dates = pd.date_range("2024-01-01", periods=n_days, freq="B")
    close = np.full(n_days, start)
    return pd.DataFrame(
        {"date": dates, "open": close, "high": close,
         "low": close, "close": close, "volume": np.full(n_days, 1e5)}
    )


# ── ema_100 tests ───────────────────────────────────────────────────────────


class TestEma100:
    def test_ema100_matches_pandas_ewm(self):
        """EMA-100 must equal pandas ewm(span=100, adjust=False).mean() — that's the spec.

        Note: the engine masks the first `span-1` rows as NaN (warm-up incomplete),
        so we compare only from row 99 onward.
        """
        df = _make_uptrend_series(n_days=250)
        result = compute_ema_100(df["close"])
        expected = df["close"].ewm(span=100, adjust=False).mean()
        # After warm-up masking, the values should match exactly from row 99 onward
        pd.testing.assert_series_equal(result.iloc[99:], expected.iloc[99:], check_names=False)

    def test_ema100_warmup_first_99_rows_are_nan(self):
        """EMA needs at least `span` rows to seed; the first 99 rows must be NaN
        because ewm(span=100) starts from row index 99 (the 100th element)."""
        df = _make_uptrend_series(n_days=250)
        result = compute_ema_100(df["close"])
        # Pandas ewm with adjust=False seeds at first non-null value (index 0).
        # The contract for THIS engine: rows before index 99 (the 100th data point)
        # are flagged as "warm-up incomplete" because the EMA isn't reliable yet.
        warmup_mask = result.isna()
        assert warmup_mask.sum() == 99, (
            f"Expected 99 NaN warm-up rows; got {warmup_mask.sum()}"
        )

    def test_ema100_positive_on_uptrend(self):
        df = _make_uptrend_series(n_days=200, daily_drift=0.005, daily_vol=0.005)
        result = compute_ema_100(df["close"])
        assert result.iloc[-1] > result.iloc[100], "EMA-100 must rise on a clean uptrend"

    def test_ema100_index_preserved(self):
        df = _make_uptrend_series(n_days=150)
        result = compute_ema_100(df["close"])
        assert result.index.equals(df["close"].index)


# ── rolling_high_52w tests ──────────────────────────────────────────────────


class TestRollingHigh52w:
    def test_rolling_high_52w_uses_high_column_not_close(self):
        """The 52w high must be the max of `high`, not `close` — intraday peaks matter."""
        df = _make_uptrend_series(n_days=300)
        # Inject a spike: day 150 has high = 999 but close = 102 (a long upper wick).
        df.loc[150, "high"] = 999.0
        result = compute_rolling_high_52w(df["high"])
        # The 52w high for days [150, 300) must include this spike.
        assert result.iloc[200] == 999.0, (
            f"Expected spike to be in rolling high; got {result.iloc[200]}"
        )

    def test_rolling_high_52w_window_252(self):
        df = _make_uptrend_series(n_days=300)
        result = compute_rolling_high_52w(df["high"])
        # First 49 rows are warmup (min_periods=50)
        assert result.iloc[:49].isna().all()
        # From row 50 onward, each value is the max of the prior 252 rows.
        for i in range(50, len(df)):
            expected = df["high"].iloc[max(0, i - 251):i + 1].max()
            assert result.iloc[i] == pytest.approx(expected, rel=1e-9), (
                f"Rolling high mismatch at row {i}: {result.iloc[i]} vs {expected}"
            )

    def test_rolling_high_52w_increasing_uptrend(self):
        df = _make_uptrend_series(n_days=300, daily_drift=0.005, daily_vol=0.005)
        result = compute_rolling_high_52w(df["high"])
        assert result.iloc[-1] > result.iloc[200]

    def test_rolling_high_52w_min_periods_50(self):
        """Symbols with < 252 days of history still get a value after row 49."""
        df = _make_uptrend_series(n_days=100)
        result = compute_rolling_high_52w(df["high"])
        # Row 49 (the 50th) is the first valid value
        assert not pd.isna(result.iloc[49])
        # Rows 0..48 are NaN
        assert result.iloc[:49].isna().all()


# ── weekly_trend_score tests ─────────────────────────────────────────────────


class TestWeeklyTrendScore:
    """The weekly trend score is a 5-component composite summed to max 100.
    Test each component independently before testing the sum."""

    def test_higher_highs_true_on_clean_uptrend(self):
        df = _make_uptrend_series(n_days=300, daily_drift=0.005, daily_vol=0.001)
        weekly = compute_weekly_components(df)
        # HH confirmed for the most recent week (last week > prior week)
        # weekly is resampled weekly, so we test the LAST element of `hh_confirmed`.
        assert weekly["hh_confirmed"].iloc[-1] == True

    def test_higher_highs_false_on_flat_series(self):
        df = _make_flat_series(n_days=300)
        weekly = compute_weekly_components(df)
        # No HH on a flat series
        assert weekly["hh_confirmed"].iloc[-1] == False

    def test_higher_lows_true_on_clean_uptrend(self):
        df = _make_uptrend_series(n_days=300, daily_drift=0.005, daily_vol=0.001)
        weekly = compute_weekly_components(df)
        assert weekly["hl_confirmed"].iloc[-1] == True

    def test_higher_lows_false_on_flat_series(self):
        df = _make_flat_series(n_days=300)
        weekly = compute_weekly_components(df)
        assert weekly["hl_confirmed"].iloc[-1] == False

    def test_weekly_trend_score_uptrend_above_50(self):
        """A clean uptrend with weekly EMAs and near 52w high should score well above 50."""
        df = _make_uptrend_series(n_days=300, daily_drift=0.005, daily_vol=0.005)
        rh52 = compute_rolling_high_52w(df["high"])
        score = compute_weekly_trend_score(df, rh52)
        # The last few rows should be in the 80+ range (all 5 components met)
        assert score.iloc[-1] >= 80, (
            f"Clean uptrend should score 80+; got {score.iloc[-1]}"
        )

    def test_weekly_trend_score_flat_series_below_50(self):
        """A flat series: HH=False, HL=False, EMA-13=above (==), EMA-20=above (==),
        within 5% of 52w high=True. Score = 0+0+20+15+15 = 50. Should be ≤ 50."""
        df = _make_flat_series(n_days=300)
        rh52 = compute_rolling_high_52w(df["high"])
        score = compute_weekly_trend_score(df, rh52)
        # On flat: HH=False, HL=False, above EMAs (close == EMA), within 5% of high = True
        # 0 + 0 + 20 + 15 + 15 = 50
        assert score.iloc[-1] <= 50, (
            f"Flat series should score ≤ 50; got {score.iloc[-1]}"
        )

    def test_weekly_trend_score_max_100(self):
        """A score must never exceed 100 — it's a sum of 5 components capped at 100."""
        df = _make_uptrend_series(n_days=300, daily_drift=0.01, daily_vol=0.001)
        rh52 = compute_rolling_high_52w(df["high"])
        score = compute_weekly_trend_score(df, rh52)
        assert score.max() <= 100

    def test_weekly_trend_score_within_52w_high_component(self):
        """Within 5% of 52w high must add 15. Verify on a series near its high."""
        df = _make_uptrend_series(n_days=300, daily_drift=0.005, daily_vol=0.005)
        rh52 = compute_rolling_high_52w(df["high"])
        score = compute_weekly_trend_score(df, rh52)
        # Last row should have within_52wh component met (close >= 0.95 * 52w high)
        # because it's near the recent high
        assert score.iloc[-1] >= 75  # at least 4 components met

    def test_weekly_components_returns_dataframe_with_5_columns(self):
        df = _make_uptrend_series(n_days=200)
        weekly = compute_weekly_components(df)
        expected_cols = {"weekly_high", "weekly_low", "weekly_ema13",
                         "weekly_ema20", "hh_confirmed", "hl_confirmed"}
        assert set(weekly.columns) >= expected_cols

    def test_weekly_trend_score_index_aligned_with_daily(self):
        """compute_weekly_trend_score must return a Series indexed by daily dates."""
        df = _make_uptrend_series(n_days=300)
        rh52 = compute_rolling_high_52w(df["high"])
        score = compute_weekly_trend_score(df, rh52)
        assert score.index.equals(df["date"]) or score.index.equals(df.index)


# ── overhead_supply_score tests ─────────────────────────────────────────────


class TestOverheadSupplyScore:
    def test_no_overhead_when_close_above_all_recent_highs(self):
        """If close > every high in the last 126 days, score = 0 (clear air)."""
        df = _make_uptrend_series(n_days=300, daily_drift=0.01, daily_vol=0.001)
        # The last close is higher than all prior highs (steep uptrend)
        score = compute_overhead_supply_score(df["high"], df["close"])
        assert score.iloc[-1] == 0.0, (
            f"Clear-air stock should score 0; got {score.iloc[-1]}"
        )

    def test_max_overhead_when_lots_of_distinct_highs_above(self):
        """Inject 25 distinct highs above close — should score 100 (capped at max_count=20).

        Decision 102 (2026-07-08): raised max_count_for_100 from 10 to 20 for
        better discriminatory power. Saturation dropped from 83% → 35.5%.
        """
        df = _make_uptrend_series(n_days=300)
        # Force close = 100, then make last 126 days have 25 highs at 105, 110, ..., 225
        df["close"] = 100.0
        inject_highs = np.linspace(105, 225, 25)
        # Place them at distinct rows in the last 126 days
        for i, h in enumerate(inject_highs):
            df.iloc[-(126 - i * 5), df.columns.get_loc("high")] = h
        score = compute_overhead_supply_score(df["high"], df["close"])
        assert score.iloc[-1] == 100.0, (
            f"25 distinct overheads should cap at 100; got {score.iloc[-1]}"
        )

    def test_partial_overhead_score(self):
        """3 distinct highs above close with max_count=20 → 15.

        Decision 102 (2026-07-08): max_count_for_100 raised from 10 to 20.
        """
        df = _make_uptrend_series(n_days=300)
        df["close"] = 100.0
        # Force the lookback window PLUS a buffer to high=90 so only injected
        # overheads remain above close. Window for row 299 is [173, 299); force
        # a wider range [150, 299) to be safe.
        df.iloc[-150:, df.columns.get_loc("high")] = 90.0
        # Inject 3 distinct overheads (rows 200, 210, 220 are inside [150, 299))
        df.iloc[200, df.columns.get_loc("high")] = 110.0
        df.iloc[210, df.columns.get_loc("high")] = 120.0
        df.iloc[220, df.columns.get_loc("high")] = 130.0
        score = compute_overhead_supply_score(df["high"], df["close"])
        assert score.iloc[-1] == pytest.approx(15.0, rel=1e-6)

    def test_duplicate_highs_counted_once(self):
        """Two days with the same high value should count as 1 distinct overhead."""
        df = _make_uptrend_series(n_days=300)
        df["close"] = 100.0
        df.iloc[-150:, df.columns.get_loc("high")] = 90.0
        df.iloc[200, df.columns.get_loc("high")] = 110.0
        df.iloc[210, df.columns.get_loc("high")] = 110.0  # duplicate
        df.iloc[220, df.columns.get_loc("high")] = 120.0
        score = compute_overhead_supply_score(df["high"], df["close"])
        # 2 distinct overheads (110, 120) → 10 (was 20 with max_count=10)
        assert score.iloc[-1] == pytest.approx(10.0, rel=1e-6)

    def test_warmup_first_125_rows_are_zero(self):
        """Before lookback=126 rows are available, return 0 (not enough data)."""
        df = _make_uptrend_series(n_days=200)
        score = compute_overhead_supply_score(df["high"], df["close"])
        assert score.iloc[:125].sum() == 0

    def test_score_in_range_0_to_100(self):
        df = _make_uptrend_series(n_days=300, daily_drift=0.002, daily_vol=0.02)
        score = compute_overhead_supply_score(df["high"], df["close"])
        valid = score.dropna()
        assert (valid >= 0).all() and (valid <= 100).all()


# ── Integration: all four together on fixture data ─────────────────────────


class TestIntegration:
    def test_all_four_columns_on_realistic_series(self):
        """Smoke test: compute all 4 indicators on 1 year of synthetic data.

        Uses a tight uptrend (low daily vol, steady drift) so the close stays
        near the recent highs — yields a high weekly trend score and low
        overhead supply score (clear air).
        """
        df = _make_uptrend_series(n_days=300, daily_drift=0.004, daily_vol=0.005)
        df["ema_100"] = compute_ema_100(df["close"])
        df["rolling_high_52w"] = compute_rolling_high_52w(df["high"])
        df["weekly_trend_score"] = compute_weekly_trend_score(df, df["rolling_high_52w"])
        df["overhead_supply_score"] = compute_overhead_supply_score(df["high"], df["close"])

        # Last row should have all 4 values populated
        last = df.iloc[-1]
        assert not pd.isna(last["ema_100"])
        assert not pd.isna(last["rolling_high_52w"])
        assert not pd.isna(last["weekly_trend_score"])
        assert not pd.isna(last["overhead_supply_score"])
        # Weekly trend score should be high for a clean tight uptrend
        assert last["weekly_trend_score"] >= 60, (
            f"Tight uptrend should score 60+; got {last['weekly_trend_score']}"
        )
        # Overhead should be moderate or low (tight uptrend keeps close near highs)
        assert last["overhead_supply_score"] <= 80


# ── Decision 103 V2 ADD gate inputs ─────────────────────────────────────────
#
# Tests for the four new pure indicator functions + ResistanceSource enum
# introduced by Decision 103. The functions are pure (pd.Series → pd.Series /
# pd.DataFrame) so the tests synthesize daily Series directly with known
# weekly structure and assert on the output.
#
# Helpers `_make_daily_with_weekly_highs` and `_make_daily_with_weekly_closes`
# build a daily Series where every business day in week N shares the same
# high (or close), so the weekly resample is fully deterministic.


def _make_daily_with_weekly_highs(
    n_weeks: int, weekly_highs: list[float]
) -> pd.Series:
    """Build a daily-indexed Series of `high` where each week's max equals
    `weekly_highs[w]` exactly (5 business days per week, all set to that value).
    """
    assert len(weekly_highs) == n_weeks
    n_days = n_weeks * 5
    dates = pd.date_range("2024-01-01", periods=n_days, freq="B")
    highs: list[float] = []
    for w in range(n_weeks):
        highs.extend([float(weekly_highs[w])] * 5)
    return pd.Series(highs, index=dates, name="high")


def _make_daily_with_weekly_closes(
    n_weeks: int, weekly_closes: list[float]
) -> pd.Series:
    """Build a daily-indexed Series of `close` where every business day in
    week N uses `weekly_closes[w]`. Resample('W-FRI').last() returns exactly
    `weekly_closes[w]` for week N.
    """
    assert len(weekly_closes) == n_weeks
    n_days = n_weeks * 5
    dates = pd.date_range("2024-01-01", periods=n_days, freq="B")
    closes: list[float] = []
    for w in range(n_weeks):
        closes.extend([float(weekly_closes[w])] * 5)
    return pd.Series(closes, index=dates, name="close")


# ── ResistanceSource enum tests ─────────────────────────────────────────────


class TestResistanceSource:
    def test_enum_values_match_db_check_constraint(self):
        """Migration 010 has a CHECK constraint allowing exactly these two values.
        If we ever rename a member here, the migration must move with it.
        """
        assert ResistanceSource.PRIOR_52W_HIGH.value == "PRIOR_52W_HIGH"
        assert ResistanceSource.ALL_TIME_HIGH.value == "ALL_TIME_HIGH"
        # No other members should exist.
        assert {m.value for m in ResistanceSource} == {
            "PRIOR_52W_HIGH",
            "ALL_TIME_HIGH",
        }

    def test_enum_is_str_subclass_for_json_serialization(self):
        """Inherits from `str` so it serializes to plain strings in JSON / DB."""
        assert isinstance(ResistanceSource.PRIOR_52W_HIGH, str)
        assert ResistanceSource.PRIOR_52W_HIGH == "PRIOR_52W_HIGH"


# ── prior_52w_high tests ────────────────────────────────────────────────────


class TestPrior52wHigh:
    def test_exactly_52_weeks_boundary(self):
        """With exactly 52 weeks of data, the most recent daily row's value
        must be the max of weekly highs from weeks 0..50 (i.e., the prior 51
        weeks — the 52nd is excluded as the current week).
        """
        # Week 51 is the "current week" for the last daily row.
        # Prior 52 weeks = weeks 0..50 (51 weeks since we exclude current).
        # Wait — the spec says rolling(window=52).max() after shift(1), so:
        #   shift(1) drops current week, then rolling(52).max() takes up to 52
        #   prior weeks. With 52 total weeks, that means weeks 0..50 → 51 weeks.
        prior_highs = [100.0 + i for i in range(51)]  # weeks 0..50
        current_week_high = 999.0  # should be EXCLUDED
        weekly_highs = prior_highs + [current_week_high]  # 52 weeks total
        high = _make_daily_with_weekly_highs(n_weeks=52, weekly_highs=weekly_highs)

        result = compute_prior_52w_high(high, window_weeks=52)
        last_val = result.iloc[-1]

        # Prior weeks 0..50 max = 100 + 50 = 150. Current week (999) excluded.
        assert last_val == pytest.approx(150.0, rel=1e-9)

    def test_excludes_current_week_via_shift(self):
        """If the current week's high is HIGHER than any prior week, the result
        must still reflect only the prior weeks (shift(1) verification).
        """
        # 10 weeks total. Weekly highs: 100, 110, 120, ..., 180, 999 (current).
        weekly_highs = [100.0 + i * 10 for i in range(10)]
        weekly_highs[-1] = 999.0  # current week
        high = _make_daily_with_weekly_highs(n_weeks=10, weekly_highs=weekly_highs)

        result = compute_prior_52w_high(high, window_weeks=10)
        # Last row's value = max of weeks 0..8 (prior 9 weeks) = 100 + 80 = 180.
        assert result.iloc[-1] == pytest.approx(180.0, rel=1e-9)

    def test_warmup_returns_nan_before_first_completed_week(self):
        """Daily rows in the very first week should be NaN (no prior weeks).

        Also: daily rows in week 2 (before Friday) are still NaN because the
        forward-fill from the prior weekly bucket only kicks in at the week's
        Friday close (the W-FRI resample boundary).
        """
        weekly_highs = [100.0] * 5
        high = _make_daily_with_weekly_highs(n_weeks=5, weekly_highs=weekly_highs)
        result = compute_prior_52w_high(high, window_weeks=52)

        # First week + first 4 days of week 2 (rows 0..8): no prior completed
        # week yet → NaN.
        assert result.iloc[:9].isna().all()
        # From Friday of week 2 onward (rows 9..): prior_max = week-1 high = 100.
        assert not result.iloc[9:].isna().any()
        assert result.iloc[9] == pytest.approx(100.0, rel=1e-9)

    def test_window_weeks_parameter_limits_lookback(self):
        """Setting window_weeks=2 limits the lookback to 2 prior weeks."""
        # 5 weeks total. Prior highs: 100, 200, 300, 400 (weeks 0..3).
        # Current week (4) = 999 (excluded).
        weekly_highs = [100.0, 200.0, 300.0, 400.0, 999.0]
        high = _make_daily_with_weekly_highs(n_weeks=5, weekly_highs=weekly_highs)

        # window_weeks=2 → look at prior 2 weeks only (weeks 2,3) → max=400.
        result = compute_prior_52w_high(high, window_weeks=2)
        assert result.iloc[-1] == pytest.approx(400.0, rel=1e-9)


# ── all_time_high_before_current_week tests ────────────────────────────────


class TestAllTimeHighBeforeCurrentWeek:
    def test_cumulative_max_excludes_current_week(self):
        """The value at the last row must equal the max of ALL prior weeks."""
        weekly_highs = [50.0, 80.0, 70.0, 120.0, 60.0, 999.0]  # 6 weeks
        high = _make_daily_with_weekly_highs(n_weeks=6, weekly_highs=weekly_highs)
        result = compute_all_time_high_before_current_week(high)
        # Prior 5 weeks max = 120 (week 3). Current week (999) excluded.
        assert result.iloc[-1] == pytest.approx(120.0, rel=1e-9)

    def test_thin_history_no_nan_after_warmup(self):
        """A symbol with only 20 weeks of history must still produce a valid
        value (not NaN) — this is what makes it the G3 fallback.
        """
        weekly_highs = [100.0 + i for i in range(20)]
        weekly_highs[-1] = 999.0  # current week, should be excluded
        high = _make_daily_with_weekly_highs(n_weeks=20, weekly_highs=weekly_highs)
        result = compute_all_time_high_before_current_week(high)
        # First week rows: NaN (no prior week yet).
        assert result.iloc[:5].isna().all()
        # From week 2 onward: max of prior weeks (excludes current).
        assert result.iloc[-1] == pytest.approx(118.0, rel=1e-9)


# ── weekly_close_above_resistance tests ─────────────────────────────────────


class TestWeeklyCloseAboveResistance:
    def test_returns_true_when_weekly_close_above_resistance(self):
        """Most recent weekly close > resistance_level → True."""
        # 3 weeks: weekly closes = [100, 110, 120]; resistance = 115.
        close = _make_daily_with_weekly_closes(
            n_weeks=3, weekly_closes=[100.0, 110.0, 120.0]
        )
        resistance = pd.Series(115.0, index=close.index)
        result = compute_weekly_close_above_resistance(close, resistance)
        # Last row: most recent Friday close = 120 > 115 → True.
        assert result.iloc[-1] == True  # noqa: E712 — comparing to pd bool

    def test_returns_false_when_weekly_close_below_resistance(self):
        """Most recent weekly close < resistance_level → False."""
        close = _make_daily_with_weekly_closes(
            n_weeks=3, weekly_closes=[100.0, 110.0, 120.0]
        )
        resistance = pd.Series(125.0, index=close.index)
        result = compute_weekly_close_above_resistance(close, resistance)
        # 120 < 125 → False.
        assert result.iloc[-1] == False  # noqa: E712

    def test_strict_inequality_at_boundary(self):
        """A weekly close EQUAL to resistance must be False (strict > spec).

        Decision 103 G3 wording: 'weekly close > resistance'. Equal does NOT
        count — avoids the 'kissed the high' false-positive case.
        """
        close = _make_daily_with_weekly_closes(
            n_weeks=3, weekly_closes=[100.0, 110.0, 120.0]
        )
        resistance = pd.Series(120.0, index=close.index)
        result = compute_weekly_close_above_resistance(close, resistance)
        # 120 > 120 is False.
        assert result.iloc[-1] == False  # noqa: E712


# ── breakout_day_volume_metrics tests ──────────────────────────────────────


class TestBreakoutDayVolumeMetrics:
    def test_populates_only_breakout_date_row(self):
        """All 6 columns must be NaN/NaT/False everywhere EXCEPT on breakout_date."""
        dates = pd.date_range("2024-01-01", periods=20, freq="B")
        volume = pd.Series([100_000.0] * 20, index=dates)
        avg20 = pd.Series([100_000.0] * 20, index=dates)

        result = compute_breakout_day_volume_metrics(
            volume, breakout_date=dates[10], avg20_volume=avg20, threshold=1.3
        )

        # Other rows: NaN / NaT / False.
        other_mask = result.index != dates[10]
        assert result.loc[other_mask, "breakout_day_volume"].isna().all()
        assert result.loc[other_mask, "breakout_day_avg20_volume"].isna().all()
        assert result.loc[other_mask, "breakout_day_volume_ratio"].isna().all()
        assert result.loc[other_mask, "volume_threshold_used"].isna().all()
        assert result.loc[other_mask, "breakout_date_for_volume"].isna().all()
        assert result.loc[other_mask, "volume_confirmed_breakout"].eq(False).all()

        # Breakout-day row: all populated.
        row = result.loc[dates[10]]
        assert row["breakout_day_volume"] == pytest.approx(100_000.0, rel=1e-9)
        assert row["breakout_day_avg20_volume"] == pytest.approx(100_000.0, rel=1e-9)
        assert row["breakout_day_volume_ratio"] == pytest.approx(1.0, rel=1e-9)
        assert row["volume_threshold_used"] == pytest.approx(1.3, rel=1e-9)
        assert row["breakout_date_for_volume"] == dates[10]
        assert row["volume_confirmed_breakout"] == False  # 1.0 < 1.3

    def test_volume_ratio_above_threshold_confirms(self):
        """ratio=1.5 >= 1.3 threshold → volume_confirmed_breakout=True."""
        dates = pd.date_range("2024-01-01", periods=20, freq="B")
        volume = pd.Series([100_000.0] * 20, index=dates)
        avg20 = pd.Series([100_000.0] * 20, index=dates)
        # Spike the breakout day to 150k → ratio 1.5.
        volume.iloc[10] = 150_000.0

        result = compute_breakout_day_volume_metrics(
            volume, breakout_date=dates[10], avg20_volume=avg20, threshold=1.3
        )
        row = result.loc[dates[10]]
        assert row["breakout_day_volume_ratio"] == pytest.approx(1.5, rel=1e-9)
        assert row["volume_confirmed_breakout"] == True  # noqa: E712

    def test_volume_ratio_at_threshold_confirms(self):
        """Boundary: ratio EXACTLY at threshold (1.3) → True (>= is inclusive)."""
        dates = pd.date_range("2024-01-01", periods=20, freq="B")
        volume = pd.Series([100_000.0] * 20, index=dates)
        avg20 = pd.Series([100_000.0] * 20, index=dates)
        volume.iloc[10] = 130_000.0  # ratio = 1.3 exactly

        result = compute_breakout_day_volume_metrics(
            volume, breakout_date=dates[10], avg20_volume=avg20, threshold=1.3
        )
        row = result.loc[dates[10]]
        assert row["volume_confirmed_breakout"] == True  # noqa: E712

    def test_volume_ratio_just_below_threshold_rejects(self):
        """Boundary: ratio 1.29 < 1.3 → volume_confirmed_breakout=False."""
        dates = pd.date_range("2024-01-01", periods=20, freq="B")
        volume = pd.Series([100_000.0] * 20, index=dates)
        avg20 = pd.Series([100_000.0] * 20, index=dates)
        volume.iloc[10] = 129_000.0  # ratio = 1.29

        result = compute_breakout_day_volume_metrics(
            volume, breakout_date=dates[10], avg20_volume=avg20, threshold=1.3
        )
        row = result.loc[dates[10]]
        assert row["volume_confirmed_breakout"] == False  # noqa: E712

    def test_avg_zero_returns_nan_ratio_no_division_error(self):
        """If avg20_volume is 0 on breakout day, ratio must be NaN (no crash)."""
        dates = pd.date_range("2024-01-01", periods=20, freq="B")
        volume = pd.Series([100_000.0] * 20, index=dates)
        avg20 = pd.Series([0.0] * 20, index=dates)  # zero avg → div-by-zero guard

        result = compute_breakout_day_volume_metrics(
            volume, breakout_date=dates[10], avg20_volume=avg20, threshold=1.3
        )
        row = result.loc[dates[10]]
        assert pd.isna(row["breakout_day_volume_ratio"])
        # volume_confirmed_breakout remains False (NaN >= 1.3 is False).
        assert row["volume_confirmed_breakout"] == False  # noqa: E712

    def test_breakout_date_none_populates_all_rows(self):
        """Test mode: breakout_date=None treats the whole series as breakout."""
        dates = pd.date_range("2024-01-01", periods=5, freq="B")
        volume = pd.Series([100_000.0] * 5, index=dates)
        avg20 = pd.Series([100_000.0] * 5, index=dates)

        result = compute_breakout_day_volume_metrics(
            volume, breakout_date=None, avg20_volume=avg20, threshold=1.3
        )
        # Every row populated.
        assert result["breakout_day_volume"].notna().all()
        assert result["volume_confirmed_breakout"].eq(False).all()  # ratio = 1.0 < 1.3

    def test_breakout_date_not_in_index_returns_empty(self):
        """If breakout_date is not in the index, return all-NaN (no crash)."""
        dates = pd.date_range("2024-01-01", periods=10, freq="B")
        volume = pd.Series([100_000.0] * 10, index=dates)
        result = compute_breakout_day_volume_metrics(
            volume, breakout_date=pd.Timestamp("2030-01-01")  # far future
        )
        assert result["breakout_day_volume"].isna().all()
        assert result["volume_confirmed_breakout"].eq(False).all()
