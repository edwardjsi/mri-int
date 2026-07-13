"""
Tests for V1.1a helpers — Decision 101.

These tests cover the new helpers added to engine_core.capital_allocation
in V1.1a (Session — Engine correctness):

  - normalize_row(row)             — Decimal → float coercion (Gap 5 fix)
  - derive_metadata(row, ...)      — single source for data_completeness,
                                     data_age_days, proxy_count (Gap 4 helper)
  - compute_engine_signature()     — CAS_VERSION + CONFIG_HASH + COMMIT_SHA
                                     (expert recommendation, V1.1b requirement)

Plus modifications to existing functions:

  - compute_overhead_supply_score  — 0.5% bucket rounding (Q1 answered)
  - compute_confidence_stars       — age transition zones (Q5 answered, replaces
                                     single cliff at breakout_age=4)

Pure logic, no DB. Same pattern as test_capital_allocation.py.
"""

import os
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

# Make the repo root importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine_core.capital_allocation import (  # noqa: E402
    load_config,
    compute_confidence_stars,
    normalize_row,
    derive_metadata,
    compute_engine_signature,
)
from engine_core.cas_indicators import (  # noqa: E402
    compute_overhead_supply_score,
)


CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "config", "capital_allocation.yaml")
)


@pytest.fixture
def config():
    return load_config(CONFIG_PATH)


# ─────────────────────────────────────────────────────────────────────────────
# normalize_row() — Decimal → float coercion (Gap 5)
# ─────────────────────────────────────────────────────────────────────────────


class TestNormalizeRow:
    """normalize_row() is the ONLY place Decimal → float conversion happens.

    Per Decision 101 (Gap 5): "Engine must not know or care whether Postgres
    returned Decimal." All callers go through this helper before engine sees
    the row.
    """

    def test_decimal_becomes_float(self):
        from decimal import Decimal
        row = {"close": Decimal("1022.25"), "volume": Decimal("350000")}
        out = normalize_row(row)
        assert isinstance(out["close"], float)
        assert isinstance(out["volume"], float)
        assert out["close"] == 1022.25
        assert out["volume"] == 350000.0

    def test_float_passes_through(self):
        row = {"close": 1022.25, "volume": 350000.0}
        out = normalize_row(row)
        assert out["close"] == 1022.25
        assert out["volume"] == 350000.0

    def test_int_passes_through(self):
        row = {"breakout_age": 3, "qif_score": 82}
        out = normalize_row(row)
        assert out["breakout_age"] == 3
        assert out["qif_score"] == 82

    def test_str_passes_through(self):
        row = {"symbol": "WELCORP", "regime": "BULLISH"}
        out = normalize_row(row)
        assert out["symbol"] == "WELCORP"
        assert out["regime"] == "BULLISH"

    def test_none_passes_through(self):
        row = {"winner_profit_pct": None, "concentration_weight_pct": None}
        out = normalize_row(row)
        assert out["winner_profit_pct"] is None
        assert out["concentration_weight_pct"] is None

    def test_mixed_types(self):
        row = {
            "close": Decimal("100.5"),
            "volume": 350000,  # int
            "regime": "BULLISH",  # str
            "winner_profit_pct": None,  # None
        }
        out = normalize_row(row)
        assert isinstance(out["close"], float)
        assert isinstance(out["volume"], int)
        assert isinstance(out["regime"], str)
        assert out["winner_profit_pct"] is None

    def test_does_not_mutate_input(self):
        """normalize_row returns a NEW dict (caller can safely keep original)."""
        from decimal import Decimal
        original = {"close": Decimal("100.0")}
        out = normalize_row(original)
        assert isinstance(original["close"], Decimal), "input should not be mutated"
        assert isinstance(out["close"], float), "output should be float"

    def test_handles_realistic_db_row(self):
        """Sanity check on a row that could come from psycopg2."""
        from decimal import Decimal
        row = {
            "symbol": "INDUSINDBK",
            "date": date(2026, 7, 7),
            "close": Decimal("1022.25"),
            "ema_20": Decimal("941.80"),
            "ema_50": Decimal("919.00"),
            "ema_100": Decimal("899.88"),
            "ema_200": Decimal("887.42"),
            "weekly_trend_score": Decimal("100"),
            "overhead_supply_score": Decimal("0"),
            "breakout_age": 1,
            "breakout_state": "BROKEN_OUT",
            "regime": "BULLISH",
        }
        out = normalize_row(row)
        for k in ["close", "ema_20", "ema_50", "ema_100", "ema_200",
                  "weekly_trend_score", "overhead_supply_score"]:
            assert isinstance(out[k], float), f"{k} should be float"
        assert out["breakout_age"] == 1
        assert out["regime"] == "BULLISH"


# ─────────────────────────────────────────────────────────────────────────────
# derive_metadata() — single source for metadata fields (Gap 4 helper)
# ─────────────────────────────────────────────────────────────────────────────


class TestDeriveMetadata:
    """derive_metadata() is the ONE helper for data_completeness_pct,
    data_age_days, proxy_count (per Decision 101, Gap 4).
    """

    def test_full_completeness_when_all_required_fields_populated(self):
        row = {f"field_{i}": i for i in range(10)}
        required = [f"field_{i}" for i in range(10)]
        meta = derive_metadata(
            row, required_fields=required,
            last_indicator_run=datetime(2026, 7, 7, tzinfo=timezone.utc),
            today=date(2026, 7, 7),
        )
        assert meta["data_completeness_pct"] == 100.0
        assert meta["data_age_days"] == 0
        assert meta["proxy_count"] == 0

    def test_partial_completeness(self):
        row = {"a": 1, "b": 2}  # 2 of 4 required
        required = ["a", "b", "c", "d"]
        meta = derive_metadata(
            row, required_fields=required,
            last_indicator_run=datetime(2026, 7, 7, tzinfo=timezone.utc),
            today=date(2026, 7, 7),
        )
        assert meta["data_completeness_pct"] == 50.0

    def test_zero_completeness_when_all_missing(self):
        row = {}
        required = ["a", "b", "c"]
        meta = derive_metadata(
            row, required_fields=required,
            last_indicator_run=datetime(2026, 7, 7, tzinfo=timezone.utc),
            today=date(2026, 7, 7),
        )
        assert meta["data_completeness_pct"] == 0.0

    def test_none_treated_as_missing(self):
        row = {"a": 1, "b": None, "c": 3}
        required = ["a", "b", "c"]
        meta = derive_metadata(
            row, required_fields=required,
            last_indicator_run=datetime(2026, 7, 7, tzinfo=timezone.utc),
            today=date(2026, 7, 7),
        )
        assert meta["data_completeness_pct"] == pytest.approx(66.666, abs=0.01)

    def test_data_age_days_from_execution_timestamp(self):
        """Per Decision 101 (Q6): data_age_days = today - last_successful_indicator_run."""
        last_run = datetime(2026, 7, 2, 16, 0, tzinfo=timezone.utc)  # 5 days ago
        meta = derive_metadata(
            row={}, required_fields=[],
            last_indicator_run=last_run,
            today=date(2026, 7, 7),
        )
        assert meta["data_age_days"] == 5

    def test_data_age_days_zero_when_run_today(self):
        meta = derive_metadata(
            row={}, required_fields=[],
            last_indicator_run=datetime(2026, 7, 7, 10, 0, tzinfo=timezone.utc),
            today=date(2026, 7, 7),
        )
        assert meta["data_age_days"] == 0

    def test_proxy_count_from_proxies_dict(self):
        proxies = {"sector": True, "rs": False, "regime": True}
        meta = derive_metadata(
            row={}, required_fields=[],
            last_indicator_run=datetime(2026, 7, 7, tzinfo=timezone.utc),
            today=date(2026, 7, 7),
            proxies_used=proxies,
        )
        assert meta["proxy_count"] == 2

    def test_proxy_count_defaults_to_zero_when_no_proxies(self):
        meta = derive_metadata(
            row={}, required_fields=[],
            last_indicator_run=datetime(2026, 7, 7, tzinfo=timezone.utc),
            today=date(2026, 7, 7),
        )
        assert meta["proxy_count"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# compute_engine_signature() — CAS_VERSION + CONFIG_HASH + COMMIT_SHA
# ─────────────────────────────────────────────────────────────────────────────


class TestComputeEngineSignature:
    """Per Decision 101 (expert recommendation): every recommendation must
    know its engine signature so future calibration can answer 'why did
    CAS 1.1 outperform CAS 1.3?'.
    """

    def test_returns_required_keys(self, config):
        sig = compute_engine_signature(config)
        assert "cas_version" in sig
        assert "config_hash" in sig
        assert "commit_sha" in sig
        assert "signature" in sig

    def test_config_hash_is_8_hex_chars(self, config):
        sig = compute_engine_signature(config)
        assert len(sig["config_hash"]) == 8
        assert all(c in "0123456789abcdef" for c in sig["config_hash"])

    def test_config_hash_deterministic_for_same_config(self, config):
        sig1 = compute_engine_signature(config)
        sig2 = compute_engine_signature(config)
        assert sig1["config_hash"] == sig2["config_hash"]

    def test_config_hash_changes_when_config_changes(self, config):
        sig1 = compute_engine_signature(config)
        modified = dict(config)
        modified["weights"] = dict(config["weights"])
        modified["weights"]["regime"] = 24  # change one weight
        sig2 = compute_engine_signature(modified)
        assert sig1["config_hash"] != sig2["config_hash"]

    def test_commit_sha_format(self, config):
        sig = compute_engine_signature(config)
        # git short SHA is 7+ hex chars
        assert len(sig["commit_sha"]) >= 7
        assert all(c in "0123456789abcdef" for c in sig["commit_sha"])

    def test_signature_format(self, config):
        """Signature = 'v{cas_version}-{commit_sha}-{config_hash}'."""
        sig = compute_engine_signature(config)
        assert sig["signature"] == f"v{sig['cas_version']}-{sig['commit_sha']}-{sig['config_hash']}"


# ─────────────────────────────────────────────────────────────────────────────
# compute_overhead_supply_score() — 0.5% bucket rounding (Decision 101, Q1)
# ─────────────────────────────────────────────────────────────────────────────


class TestOverheadBucketing:
    """Per Decision 101 (expert Q1 answer): round distinct highs to nearest
    0.5% to avoid float granularity (110.01 / 110.03 / 110.04 → one
    resistance, not three).
    """

    def test_three_close_highs_count_as_one_with_bucketing(self):
        """110.01, 110.03, 110.04 are within 0.5% → 1 distinct."""
        import pandas as pd
        # 5 rows so the last row (i=4) has 4 prior rows visible (lookback=4).
        high = pd.Series([110.01, 110.03, 110.04, 110.02, 100.0])
        close = pd.Series([99.0, 99.0, 99.0, 99.0, 99.0])
        scores = compute_overhead_supply_score(
            high, close, lookback=4, max_count=10, bucket_pct=0.5,
        )
        # Row 4 sees [110.01, 110.03, 110.04, 110.02] above close=99.
        # All 4 round to 110.0 (nearest 0.5%) → 1 distinct → score = 10.0
        assert scores.iloc[4] == 10.0

    def test_widely_spaced_highs_count_separately(self):
        """120.0 and 130.0 are >0.5% apart → 2 distinct."""
        import pandas as pd
        high = pd.Series([120.0, 130.0, 100.0, 99.0])
        close = pd.Series([99.0, 99.0, 99.0, 99.0])
        scores = compute_overhead_supply_score(
            high, close, lookback=3, max_count=10, bucket_pct=0.5,
        )
        # Row 3 sees [120, 130, 100] above close=99
        # 120 rounds to 120, 130 rounds to 130, 100 rounds to 100 → 3 distinct → score = 30.0
        assert scores.iloc[3] == 30.0

    def test_no_bucketing_when_disabled(self):
        """Default behavior (bucket_pct=None) keeps existing distinct logic."""
        import pandas as pd
        high = pd.Series([110.01, 110.03, 110.04, 110.02, 100.0])
        close = pd.Series([99.0, 99.0, 99.0, 99.0, 99.0])
        scores = compute_overhead_supply_score(
            high, close, lookback=4, max_count=10, bucket_pct=None,
        )
        # All 4 are distinct (no bucketing) → score = 40.0
        assert scores.iloc[4] == 40.0


# ─────────────────────────────────────────────────────────────────────────────
# compute_confidence_stars() — age transition zones (Decision 101, Q5)
# ─────────────────────────────────────────────────────────────────────────────


class TestConfidenceAgeZones:
    """Per Decision 101 (expert Q5 answer): replace single cliff at age=4
    with transition zone. 0-2 → excellent, 3 → good, 4-5 → transition,
    6+ → stale. Stable_calculations star fires ONLY in excellent/good zones.
    """

    @pytest.mark.parametrize("age", [0, 1, 2])
    def test_excellent_zone_fires_star(self, config, age):
        row = {
            "breakout_age": age,
            "data_completeness_pct": 100.0,
            "data_age_days": 0,
        }
        sub_scores = {"regime": 100, "weekly": 90}
        stars = compute_confidence_stars(row, sub_scores, {}, config)
        # Should get at least complete_data + stable_calculations + factor_agreement + low_proxy + freshness
        assert stars == 5, f"age {age} (excellent) should get full stars"

    def test_good_zone_fires_star(self, config):
        """breakout_age=3 is the 'good' zone — still fires stable_calculations."""
        row = {
            "breakout_age": 3,
            "data_completeness_pct": 100.0,
            "data_age_days": 0,
        }
        sub_scores = {"regime": 100, "weekly": 90}
        stars = compute_confidence_stars(row, sub_scores, {}, config)
        assert stars == 5

    @pytest.mark.parametrize("age", [4, 5])
    def test_transition_zone_does_not_fire_star(self, config, age):
        """breakout_age 4-5 is the 'transition' zone — NO stable_calculations star."""
        row = {
            "breakout_age": age,
            "data_completeness_pct": 100.0,
            "data_age_days": 0,
        }
        sub_scores = {"regime": 100, "weekly": 90}
        stars = compute_confidence_stars(row, sub_scores, {}, config)
        # Should get 4 (missing stable_calculations)
        assert stars == 4, f"age {age} (transition) should get 4 stars"

    @pytest.mark.parametrize("age", [6, 10, 100])
    def test_stale_zone_does_not_fire_star(self, config, age):
        """breakout_age 6+ is 'stale' — NO stable_calculations star."""
        row = {
            "breakout_age": age,
            "data_completeness_pct": 100.0,
            "data_age_days": 0,
        }
        sub_scores = {"regime": 100, "weekly": 90}
        stars = compute_confidence_stars(row, sub_scores, {}, config)
        assert stars == 4, f"age {age} (stale) should get 4 stars"
