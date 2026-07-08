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
    compute_ema_100,
    compute_overhead_supply_score,
    compute_rolling_high_52w,
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
        """Inject 15 distinct highs above close — should score 100 (capped at max_count=10)."""
        df = _make_uptrend_series(n_days=300)
        # Force close = 100, then make last 126 days have 15 highs at 105, 110, 115, ..., 175
        df["close"] = 100.0
        inject_highs = np.linspace(105, 175, 15)
        # Place them at distinct rows in the last 126 days
        for i, h in enumerate(inject_highs):
            df.iloc[-(126 - i * 8), df.columns.get_loc("high")] = h
        score = compute_overhead_supply_score(df["high"], df["close"])
        assert score.iloc[-1] == 100.0, (
            f"15 distinct overheads should cap at 100; got {score.iloc[-1]}"
        )

    def test_partial_overhead_score(self):
        """3 distinct highs above close with max_count=10 → 30.

        To get a clean count, we force ALL highs in the lookback window to
        be below close, then inject 3 distinct overheads at known positions.
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
        assert score.iloc[-1] == pytest.approx(30.0, rel=1e-6)

    def test_duplicate_highs_counted_once(self):
        """Two days with the same high value should count as 1 distinct overhead."""
        df = _make_uptrend_series(n_days=300)
        df["close"] = 100.0
        df.iloc[-150:, df.columns.get_loc("high")] = 90.0
        df.iloc[200, df.columns.get_loc("high")] = 110.0
        df.iloc[210, df.columns.get_loc("high")] = 110.0  # duplicate
        df.iloc[220, df.columns.get_loc("high")] = 120.0
        score = compute_overhead_supply_score(df["high"], df["close"])
        # 2 distinct overheads (110, 120) → 20
        assert score.iloc[-1] == pytest.approx(20.0, rel=1e-6)

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
