"""
Tests for engine_core.capital_allocation — Decision 100 V1.0 (rev 3).

Per Decision 100 / §7 of docs/CAPITAL_ALLOCATION_SCORE_PLAN_2026-07-06.md:
  Session N+1 ships the pure logic module + this 24-scenario test suite.
  No DB, no API — pure synthetic row dicts. Same pattern as
  test_guidance_email_sections.py.

Rev 3 (2026-07-07) test additions:
  - Confidence tests restructured from 5 stock-quality stars → 5 model-certainty
    stars (complete_data, factor_agreement, stable_calculations, low_proxy_usage,
    indicator_freshness).
  - New tests for missing-data eligibility gates (weekly_data, rs_data).
  - New test for compute_market_score_breakdown.
  - Renamed `check_market_subgates` → `compute_market_structure`.

Scenarios per Sessions.md (July 6, 2026 late evening handoff):
  - 5 sub-score:    regime / weekly / breakout / overhead_supply / rs+volume+sector
  - 3 multiplier:   winner / concentration / combined
  - 9 eligibility + structure: pass / multi-fail / regime / ema-stack /
                                trend / breakout / quality / all-required /
                                weekly_data / rs_data
  - 5 confidence:   per-star / full / zero / partial / max-clamp
  - 3 why-checklist: matching lines / missing fields / value interpolation
  + 1 sanity:       load_config + weights sum to 100
  + 1 breakdown:    compute_market_score_breakdown returns score + per-factor dict
"""

import os
import sys
from datetime import date

import pytest

# Make the repo root importable so `engine_core.capital_allocation` resolves
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine_core.capital_allocation import (  # noqa: E402
    load_config,
    check_eligibility,
    compute_market_structure,
    compute_market_score,
    compute_market_score_breakdown,
    compute_portfolio_allocation_score,
    compute_confidence_stars,
    render_why_checklist,
    _regime_score,
    _weekly_score,
    _breakout_score,
    _rs_score,
    _volume_score,
    _sector_score,
)


CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "config", "capital_allocation.yaml")
)


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def config():
    """Load the frozen V1.0 (rev 3) config — single source of truth."""
    return load_config(CONFIG_PATH)


@pytest.fixture
def passing_row():
    """A row that should pass ALL 8 eligibility gates AND all 3 structure
    dimensions AND score in the top band. Used as the baseline for most tests."""
    return {
        # EMA stack (4 conditions, rev 2 relaxed)
        "close": 100.0,
        "ema_20": 95.0,             # close > ema20 ✓
        "ema_50": 90.0,             # ema20 > ema50 ✓
        "ema_200": 80.0,            # ema50 > ema200 ✓
        "ema_100_slope_5d": 0.5,    # ema100 rising ✓
        # Liquidity (≥ ₹10 Cr ADTV)
        "volume": 2_000_000,
        "avg_volume_20d": 1_000_000,  # vol_ratio = 2.0, ADTV proxy at threshold
        # 52-week position (within 10%)
        "rolling_high_52w": 105.0,  # close / 52wh = 100/105 = 95.2% ✓
        # Weekly Structure (multi-component)
        "weekly_ema13": 90.0,       # close > weekly_ema13 ✓
        "weekly_ema20": 88.0,       # close > weekly_ema20 ✓
        "hh_confirmed": True,
        "hl_confirmed": True,
        # Breakout
        "breakout_state": "BROKEN_OUT",
        "breakout_age": 2,
        # RS / overhead / quality
        "rs_90d": 0.05,             # +5% vs Nifty
        "overhead_supply_score": 18,  # low = clear air (good)
        "qif_score": 80,
        "weekly_trend_score": 80,  # ≥ 50 (Trend structure) — pure stock-quality signal
        # Confidence support
        "data_completeness_pct": 95,
        "data_age_days": 2,         # 2 days old → fresh (indicator_freshness star)
        # Why-checklist support
        "winner_profit_pct": 8.0,
    }


# ── Sanity (not counted in the 24) ────────────────────────────────────────


def test_load_config_parses_and_weights_sum_to_100(config):
    """Sanity: YAML parses cleanly and weighted factors sum to 100."""
    assert config["version"] == "1.0.0-rev3"
    weights = config["weights"]
    assert sum(weights.values()) == pytest.approx(100, abs=0.01), (
        f"Weights must sum to 100, got {sum(weights.values())}: {weights}"
    )
    assert set(weights.keys()) == {
        "regime", "weekly", "breakout", "overhead_supply", "rs", "volume", "sector"
    }
    # Rev 3: calibration section must exist with all required keys
    cal = config["calibration"]
    required_cal = (
        "rs_strong", "volume_confirmed", "overhead_clear_air", "qif_high",
        "weekly_strong", "near_52wh_pct", "breakout_early_max_age", "age_decay",
        "confidence",
    )
    for key in required_cal:
        assert key in cal, f"Missing calibration key: {key}"
    # Confidence calibration sub-keys (rev 3, refined in V1.1a)
    conf_cal = cal["confidence"]
    for key in ("complete_data_threshold_pct", "factor_agreement_max_std_dev",
                "breakout_age_zones", "low_proxy_usage_max_proxies",
                "indicator_freshness_max_age_days"):
        assert key in conf_cal, f"Missing calibration.confidence key: {key}"
    # breakout_age_zones must contain all 4 zones (Decision 101, Q5)
    zones = conf_cal["breakout_age_zones"]
    for zone in ("excellent", "good", "transition", "stale"):
        assert zone in zones, f"Missing age zone: {zone}"
        lo, hi = zones[zone]
        assert isinstance(lo, int) and isinstance(hi, int)


# ── 1. Sub-score: Regime (5 sub-score tests) ──────────────────────────────


@pytest.mark.parametrize("regime,expected", [
    ("BULLISH", 100),
    ("SIDEWAYS", 60),
    ("BEARISH", 20),
])
def test_regime_subscore(config, regime, expected):
    assert _regime_score(regime, config) == expected


# ── 2. Sub-score: Weekly (multi-component) ────────────────────────────────


@pytest.mark.parametrize("components,expected", [
    # All 5 components True → max 100 (25+25+20+15+15)
    ({"hh": True, "hl": True, "above_e13": True, "above_e20": True, "near_52wh": True}, 100),
    # None → 0
    ({"hh": False, "hl": False, "above_e13": False, "above_e20": False, "near_52wh": False}, 0),
    # Just HH + HL → 50
    ({"hh": True, "hl": True, "above_e13": False, "above_e20": False, "near_52wh": False}, 50),
    # Just above weekly EMAs → 35 (20 + 15)
    ({"hh": False, "hl": False, "above_e13": True, "above_e20": True, "near_52wh": False}, 35),
    # HH + HL + 52WH → 65 (no weekly EMA component)
    ({"hh": True, "hl": True, "above_e13": False, "above_e20": False, "near_52wh": True}, 65),
    # Just 52WH → 15
    ({"hh": False, "hl": False, "above_e13": False, "above_e20": False, "near_52wh": True}, 15),
])
def test_weekly_subscore_multi_component(config, components, expected):
    """Weekly Structure = HH + HL + above weekly EMA-13 + above weekly EMA-20
    + within 5% of 52w high, weighted 25/25/20/15/15 = 100 max."""
    row = {
        "close": 100.0,
        "weekly_ema13": 99.0 if components["above_e13"] else 101.0,
        "weekly_ema20": 99.0 if components["above_e20"] else 101.0,
        "rolling_high_52w": 100.0 if components["near_52wh"] else 110.0,  # 95% of 110 = 104.5
        "hh_confirmed": components["hh"],
        "hl_confirmed": components["hl"],
    }
    assert _weekly_score(row, config) == expected


# ── 3. Sub-score: Breakout (age decay + volume bonus) ─────────────────────


@pytest.mark.parametrize("age,vol_ratio,expected", [
    (0, 1.0, 100),    # day 0 = 100
    (0, 2.5, 100),    # +10 bonus but clamped to 100
    (1, 1.0, 95),     # day 1 = 95
    (2, 1.0, 90),     # day 2 = 90
    (3, 1.0, 85),     # day 3 = 85
    (4, 1.0, 70),     # day 4 = 70
    (5, 1.0, 65),     # day 5 = 65
    (6, 1.0, 40),     # stale = 40
    (5, 2.5, 75),     # age 5 + volume bonus = 75
    (6, 2.5, 50),     # stale + volume bonus = 50
    (0, 1.5, 100),    # below 2x bonus threshold
])
def test_breakout_subscore_age_decay_and_volume_bonus(config, age, vol_ratio, expected):
    """Breakout base = AGE_DECAY[age] (100/95/90/85/70/65/40 for ages 0-6+).
    Volume bonus = +10 when vol_ratio ≥ 2.0. Final clamped to [0, 100]."""
    row = {
        "breakout_age": age,
        "volume": int(vol_ratio * 1_000_000),
        "avg_volume_20d": 1_000_000,
    }
    assert _breakout_score(row, config) == expected


# ── 4. Sub-score: Overhead Supply (already-computed field, bounds check) ──


@pytest.mark.parametrize("raw_score", [0, 18, 50, 99, 100])
def test_overhead_supply_subscore_preserves_value(config, raw_score):
    """Overhead Supply is computed in indicator_engine.py and stored on
    daily_prices. The engine just READS the value — verify it's passed
    through unchanged when used in weighted aggregation."""
    # Compute a full market score with only overhead_supply varying
    sub_scores = {
        "regime": 100, "weekly": 100, "breakout": 100, "rs": 100,
        "volume": 100, "sector": 100,
        "overhead_supply": raw_score,  # raw "badness" score
    }
    market_score = compute_market_score(sub_scores, config)

    # All other factors at 100 (each contributes its full weight).
    # Overhead weight = 14, so overhead contributes (100 - raw_score) / 100 * 14
    # Total = (100 + 21 + 17 + 11 + 8 + 6) + (100 - raw_score) * 0.14
    #       = 63 + 14 - raw_score * 0.14
    #       = 77 - raw_score * 0.14
    expected = 100 - raw_score * 0.14
    assert market_score == pytest.approx(expected, abs=0.01), (
        f"overhead_supply={raw_score} → market={market_score:.2f}, expected ~{expected:.2f}"
    )


# ── 5. Sub-score: RS / Volume / Sector (combined) ─────────────────────────


@pytest.mark.parametrize("rs_90d,expected_rs", [
    (0.10, 100), (0.05, 50), (0.0, 0), (-0.05, 0), (0.20, 100),  # clamped
])
def test_rs_subscore(config, rs_90d, expected_rs):
    """RS score = clamp(rs_90d / 0.10 × 100, 0, 100)."""
    assert _rs_score({"rs_90d": rs_90d}, config) == pytest.approx(expected_rs, abs=0.01)


@pytest.mark.parametrize("vol_ratio,expected_vol", [
    (3.0, 100), (2.0, 50), (1.0, 0), (0.5, 0), (5.0, 100),  # clamped
])
def test_volume_subscore(config, vol_ratio, expected_vol):
    """Volume score = 100 × clamp((vol_ratio - 1.0) / 2.0, 0, 1)."""
    row = {
        "volume": int(vol_ratio * 1_000_000),
        "avg_volume_20d": 1_000_000,
    }
    assert _volume_score(row, config) == pytest.approx(expected_vol, abs=0.01)


def test_sector_subscore_v1_proxy(config):
    """V1.0 sector = 50 (neutral proxy). V1.2 will use real sector_rs_60d."""
    assert _sector_score({}, config) == 50


# ── 6. Portfolio Multiplier: Winner (capped at +10%, floor -15%) ──────────


@pytest.mark.parametrize("profit_pct,expected_mult", [
    (0, 1.00),
    (5, 1.05),
    (10, 1.10),
    (30, 1.10),    # clamped at +10%
    (-5, 0.95),
    (-10, 0.90),
    (-15, 0.85),   # clamped at -15%
    (-30, 0.85),   # clamped at -15%
])
def test_winner_multiplier_caps(config, profit_pct, expected_mult):
    """Winner multiplier = 1 + (profit_pct / scale_pct) × max_boost,
    clamped to [min_multiplier, 1 + max_boost] = [0.85, 1.10]."""
    mult = compute_portfolio_allocation_score(
        market_score=80.0,
        winner_profit_pct=profit_pct,
        concentration_weight_pct=0.0,  # isolate winner effect
        config=config,
    )
    # market × winner × concentration = 80 × winner × 1.0
    assert mult == pytest.approx(80.0 * expected_mult, abs=0.01)


# ── 7. Portfolio Multiplier: Concentration (curve, clamped at 15%+) ───────


@pytest.mark.parametrize("weight_pct,expected_conc", [
    (0, 1.00),
    (7.5, 0.95),   # half-penalty at 7.5%
    (15, 0.90),    # full penalty at threshold
    (25, 0.90),    # clamped
    (50, 0.90),    # clamped
])
def test_concentration_multiplier_curve(config, weight_pct, expected_conc):
    """Concentration = 1 - clamp(weight_pct / max_weight_pct, 0, 1) × max_penalty.
    At 0% → 1.00, at 15%+ → 0.90 (max -10%)."""
    mult = compute_portfolio_allocation_score(
        market_score=80.0,
        winner_profit_pct=0.0,        # no winner effect
        concentration_weight_pct=weight_pct,
        config=config,
    )
    assert mult == pytest.approx(80.0 * expected_conc, abs=0.01)


# ── 8. Portfolio Multiplier: Combined (winner × concentration) ────────────


def test_combined_multipliers_clamp_cas(config):
    """Verify winner and concentration stack multiplicatively.
    market=80, winner=+10% (1.10), concentration=15% (0.90) → 80 × 0.99 = 79.2."""
    cas = compute_portfolio_allocation_score(
        market_score=80.0,
        winner_profit_pct=10.0,
        concentration_weight_pct=15.0,
        config=config,
    )
    assert cas == pytest.approx(79.2, abs=0.01)


# ── 9. Eligibility: Combined PASS ─────────────────────────────────────────


def test_eligibility_all_gates_pass(config, passing_row):
    """A row that satisfies all 6 eligibility gates returns (True, [])."""
    passed, failed = check_eligibility(passing_row, regime="BULLISH", config=config)
    assert passed is True
    assert failed == []


# ── 10. Eligibility: Multi-fail returns all failed gate names ─────────────


def test_eligibility_fail_returns_all_failed_gates(config):
    """A row failing multiple gates returns (False, [...list of gate names])."""
    bad_row = {
        "close": 50.0, "ema_20": 100.0,         # close < ema20 (fail 1)
        "ema_50": 90.0, "ema_200": 80.0,
        "ema_100_slope_5d": -0.5,               # ema100 falling (fail 2)
        "volume": 100_000, "avg_volume_20d": 100_000,  # tiny liquidity (fail 3)
        "rolling_high_52w": 200.0,              # way off 52w high (fail 4)
        "breakout_state": "CONSOLIDATING",      # not broken out (fail 5)
        "breakout_age": 99,
        "qif_score": 30,                        # low quality (fail 6)
    }
    passed, failed = check_eligibility(bad_row, regime="BEARISH", config=config)  # regime fails too
    assert passed is False
    # All 7 things should fail: regime, ema, liquidity, 52w, breakout, quality, (em100 slope)
    # We expect at least these named failures:
    assert "regime" in failed
    assert "ema_stack" in failed
    assert "liquidity" in failed
    assert "52w_position" in failed
    assert "breakout_state" in failed
    assert "quality" in failed


# ── 11. Eligibility: Regime gate (4 cases) ────────────────────────────────


@pytest.mark.parametrize("regime,aggressive,expected_pass", [
    ("BULLISH", False, True),
    ("SIDEWAYS", False, True),
    ("BEARISH", False, False),
    ("BEARISH", True, True),    # aggressive_mode bypasses BEARISH
])
def test_eligibility_regime_gate(config, passing_row, regime, aggressive, expected_pass):
    cfg = dict(config)
    cfg["eligibility"] = dict(config["eligibility"])
    cfg["eligibility"]["aggressive_mode"] = aggressive
    passed, failed = check_eligibility(passing_row, regime=regime, config=cfg)
    assert passed is expected_pass
    if not expected_pass:
        assert "regime" in failed


# ── 12. Eligibility: EMA Stack (5 conditions, partial-fail detection) ─────


@pytest.mark.parametrize("field_to_break,expected_fail_label", [
    ("close_gt_ema20", "close_gt_ema20"),
    ("ema20_gt_ema50", "ema20_gt_ema50"),
    ("ema50_gt_ema200", "ema50_gt_ema200"),
    ("ema100_rising", "ema100_rising"),
])
def test_eligibility_ema_stack(config, passing_row, field_to_break, expected_fail_label):
    """Each of the 4 EMA conditions can independently fail eligibility."""
    row = dict(passing_row)
    if field_to_break == "close_gt_ema20":
        row["close"] = row["ema_20"] - 1.0  # close below ema20
    elif field_to_break == "ema20_gt_ema50":
        row["ema_20"] = row["ema_50"] - 1.0  # ema20 below ema50
    elif field_to_break == "ema50_gt_ema200":
        row["ema_50"] = row["ema_200"] - 1.0  # ema50 below ema200
    elif field_to_break == "ema100_rising":
        row["ema_100_slope_5d"] = -0.5  # falling
    passed, failed = check_eligibility(row, regime="BULLISH", config=config)
    assert passed is False
    assert "ema_stack" in failed


# ── 13. Sub-Gate: Trend (weekly_trend_score ≥ 50) ─────────────────────────


@pytest.mark.parametrize("weekly_trend_score,expected_pass", [
    (50.0, True),
    (49.99, False),
    (100.0, True),
    (0.0, False),
])
def test_subgate_trend(config, passing_row, weekly_trend_score, expected_pass):
    """Trend structure dimension: weekly_trend_score must be ≥ 50."""
    row = dict(passing_row)
    row["weekly_trend_score"] = weekly_trend_score
    passed, failed = compute_market_structure(row, config=config)
    assert passed is expected_pass
    if not expected_pass:
        assert "trend" in failed


# ── 14. Sub-Gate: Breakout (age ≤ 3, stricter than eligibility's ≤ 5) ─────


@pytest.mark.parametrize("breakout_age,expected_pass", [
    (3, True),
    (4, False),
    (5, False),  # sub-gate stricter: eligibility allows 5, sub-gate doesn't
    (0, True),
])
def test_subgate_breakout(config, passing_row, breakout_age, expected_pass):
    """Breakout structure dimension: age ≤ 3. Stricter than eligibility's age ≤ 5."""
    row = dict(passing_row)
    row["breakout_age"] = breakout_age
    passed, failed = compute_market_structure(row, config=config)
    assert passed is expected_pass
    if not expected_pass:
        assert "breakout" in failed


# ── 15. Sub-Gate: Quality (QIF ≥ 75, stricter than eligibility's ≥ 70) ────


@pytest.mark.parametrize("qif_score,expected_pass", [
    (75, True),
    (74.99, False),
    (100, True),
    (70, False),  # sub-gate stricter: eligibility allows 70, sub-gate doesn't
])
def test_subgate_quality(config, passing_row, qif_score, expected_pass):
    """Quality structure dimension: QIF ≥ 75. Stricter than eligibility's QIF ≥ 70."""
    row = dict(passing_row)
    row["qif_score"] = qif_score
    passed, failed = compute_market_structure(row, config=config)
    assert passed is expected_pass
    if not expected_pass:
        assert "quality" in failed


# ── 16. Sub-Gates: All 3 must pass (combined) ─────────────────────────────


def test_subgates_all_pass_required(config, passing_row):
    """All 3 structure dimensions must PASS. Failing any one rejects the stock."""
    # First verify baseline passes
    passed, failed = compute_market_structure(passing_row, config=config)
    assert passed is True
    assert failed == []

    # Now fail ONE structure dimension and verify it's named in `failed`
    bad = dict(passing_row)
    bad["weekly_trend_score"] = 30  # trend dimension fails
    passed, failed = compute_market_structure(bad, config=config)
    assert passed is False
    assert failed == ["trend"]


# ── 17. Confidence: Each of the 5 stars independently ─────────────────────


@pytest.mark.parametrize("star_name,row_delta,sub_scores,proxies,expected_stars", [
    # complete_data: data_completeness_pct >= 90 → +1
    # sub_scores {0,100}: factor_agreement (std=70) fails; base breakout_age=4 → stable fails
    ("complete_data_met", {"data_completeness_pct": 95}, {"a": 0, "b": 100}, {"any": True}, 1),
    ("complete_data_below", {"data_completeness_pct": 89}, {"a": 0, "b": 100}, {"any": True}, 0),
    # factor_agreement: std-dev of (goodness-aligned) sub-scores <= 20 → +1
    ("factor_agreement_tight", {}, {"a": 60, "b": 70, "c": 65}, {"any": True}, 1),
    ("factor_agreement_wide", {}, {"a": 0, "b": 100}, {"any": True}, 0),
    # factor_agreement with overhead_supply inverted: raw=50 → aligned=50, {50,50} std-dev=0
    ("factor_agreement_overhead_inverted", {}, {"a": 50, "overhead_supply": 50}, {"any": True}, 1),
    # stable_calculations (V1.1a, Decision 101 Q5): breakout_age in
    # 'excellent' (0-2) or 'good' (3) zone → +1; 'transition' (4-5) or
    # 'stale' (6+) → 0. The single cliff at age=4 was replaced with zones.
    ("stable_excellent_zone_age_2", {"breakout_age": 2}, {"a": 0, "b": 100}, {"any": True}, 1),
    ("stable_good_zone_age_3", {"breakout_age": 3}, {"a": 0, "b": 100}, {"any": True}, 1),
    ("stable_transition_zone_age_4", {"breakout_age": 4}, {"a": 0, "b": 100}, {"any": True}, 0),
    ("stable_transition_zone_age_5", {"breakout_age": 5}, {"a": 0, "b": 100}, {"any": True}, 0),
    ("stable_stale_zone_age_6", {"breakout_age": 6}, {"a": 0, "b": 100}, {"any": True}, 0),
    # low_proxy_usage: 0 proxies → +1; >=1 proxy → 0
    ("low_proxy_zero", {}, {"a": 0, "b": 100}, {"any": False}, 1),
    ("low_proxy_one", {}, {"a": 0, "b": 100}, {"sector": True}, 0),
    # indicator_freshness: data_age_days <= 5 → +1
    ("fresh_data", {"data_age_days": 5}, {"a": 0, "b": 100}, {"any": True}, 1),
    ("stale_data", {"data_age_days": 10}, {"a": 0, "b": 100}, {"any": True}, 0),
])
def test_confidence_each_star_criterion(config, star_name, row_delta, sub_scores, proxies, expected_stars):
    """Each of the 5 MODEL-CERTAINTY criteria contributes exactly 1 star when met.

    Base row uses breakout_age=4 (AT cliff → stable fails by default),
    data_completeness=50 (below 90), data_age=100 (stale). Each test isolates
    one criterion by carefully choosing row_delta / sub_scores / proxies that
    don't accidentally trigger other criteria.
    """
    base_row = {
        "data_completeness_pct": 50,
        "breakout_age": 4,   # at AGE_DECAY cliff → stable fails by default
        "data_age_days": 100,
    }
    row = {**base_row, **row_delta}
    stars = compute_confidence_stars(row, sub_scores, proxies, config)
    assert stars == expected_stars, f"{star_name}: expected {expected_stars} stars, got {stars}"


# ── 18. Confidence: All 5 stars (max) ─────────────────────────────────────


def test_confidence_full_5_stars(config, passing_row):
    """When all 5 model-certainty criteria are met, confidence = 5 stars.

    Note: trend_maturity + breakout_maturity (stock-quality stars from rev 2)
    are GONE in rev 3. Stock quality now lives in CAS itself, not in confidence.
    """
    row = dict(passing_row)
    row["data_completeness_pct"] = 95        # ★ complete_data
    row["data_age_days"] = 2                  # ★ indicator_freshness
    row["breakout_age"] = 2                   # not at cliff (4) → ★ stable_calculations
    sub_scores = {"a": 70, "b": 75, "c": 72}  # std-dev ~2.1 → ★ factor_agreement
    proxies = {"sector": False, "rr": False}  # ★ low_proxy_usage
    assert compute_confidence_stars(row, sub_scores, proxies, config) == 5


# ── 19. Confidence: Zero stars ────────────────────────────────────────────


def test_confidence_zero_stars(config, passing_row):
    """When NO model-certainty criteria are met, confidence = 0 stars."""
    row = dict(passing_row)
    row["data_completeness_pct"] = 50        # below 90
    row["data_age_days"] = 30                 # stale
    row["breakout_age"] = 4                   # at the AGE_DECAY cliff
    sub_scores = {"a": 10, "b": 90, "c": 50}  # wide std-dev
    proxies = {"sector": True, "rr": True}    # proxies used
    assert compute_confidence_stars(row, sub_scores, proxies, config) == 0


# ── 20. Confidence: Partial 3 stars ───────────────────────────────────────


def test_confidence_partial_3_stars(config, passing_row):
    """When 3 of 5 model-certainty criteria are met, confidence = 3 stars."""
    row = dict(passing_row)
    row["data_completeness_pct"] = 95        # ★ complete_data
    row["data_age_days"] = 2                  # ★ indicator_freshness
    row["breakout_age"] = 4                   # AT cliff → stable fails
    sub_scores = {"a": 0, "b": 100}           # std-dev wide → agreement fails
    proxies = {"sector": False, "rr": False}  # ★ low_proxy_usage
    assert compute_confidence_stars(row, sub_scores, proxies, config) == 3


# ── 21. Confidence: Clamped at 5 (defensive) ──────────────────────────────


def test_confidence_max_clamped_at_5(config, passing_row):
    """Even if all model-certainty criteria are met, confidence is clamped at 5 (not 6+)."""
    row = dict(passing_row)
    row["data_completeness_pct"] = 100
    row["data_age_days"] = 0
    row["breakout_age"] = 2
    sub_scores = {"a": 80, "b": 80}
    proxies = {"any": False}
    stars = compute_confidence_stars(row, sub_scores, proxies, config)
    assert stars == 5
    assert 0 <= stars <= 5


# ── 22. Why-Checklist: Renders matching ✓ lines ───────────────────────────


def test_why_checklist_renders_matching_lines(config, passing_row):
    """For a row with multiple positive signals, multiple ✓ lines render."""
    lines = render_why_checklist(passing_row, config=config)
    assert isinstance(lines, list)
    assert len(lines) > 0
    # All lines start with ✓
    assert all(line.startswith("✓") for line in lines)
    # Specific expected lines (template-derived):
    assert any("Existing winner" in line for line in lines), (
        f"Expected 'Existing winner' in checklist, got: {lines}"
    )
    assert any("Near 52-week high" in line for line in lines)
    assert any("Clear overhead supply" in line for line in lines)


# ── 23. Why-Checklist: Skips lines where required field is missing ────────


def test_why_checklist_skips_missing_fields(config, passing_row):
    """When winner_profit_pct is missing, the 'Existing winner' line is skipped."""
    row = dict(passing_row)
    del row["winner_profit_pct"]
    lines = render_why_checklist(row, config=config)
    assert not any("Existing winner" in line for line in lines), (
        f"'Existing winner' should be skipped when profit field missing, got: {lines}"
    )


# ── 24. Why-Checklist: Interpolates values into templates ─────────────────


def test_why_checklist_interpolates_values(config, passing_row):
    """Vol ratio, breakout age, and other values are interpolated into templates."""
    row = dict(passing_row)
    row["breakout_age"] = 3               # not 0, so use early_continuation template
    row["volume"] = 2_500_000             # vol_ratio = 2.5
    row["avg_volume_20d"] = 1_000_000
    row["qif_score"] = 82
    lines = render_why_checklist(row, config=config)
    # breakout_age interpolated
    assert any("Day 3" in line for line in lines), (
        f"Expected 'Day 3' in some line, got: {lines}"
    )
    # vol_ratio interpolated (2.5x)
    assert any("2.5x average" in line for line in lines), (
        f"Expected '2.5x average' in some line, got: {lines}"
    )
    # qif interpolated
    assert any("82/100" in line for line in lines), (
        f"Expected '82/100' in some line, got: {lines}"
    )


# ── 25. Eligibility (rev 3): Missing weekly_trend_score → weekly_data gate ─


def test_eligibility_missing_weekly_data_returns_weekly_data(config, passing_row):
    """Missing weekly_trend_score → eligibility FAIL with 'weekly_data' gate.

    Rev 3 semantic: the model REFUSES to score rather than guessing with 0.
    weekly_trend_score is critical for both the trend sub-gate AND the
    weekly sub-score — missing it means no meaningful trend assessment.
    """
    row = dict(passing_row)
    row["weekly_trend_score"] = None
    passed, failed = check_eligibility(row, regime="BULLISH", config=config)
    assert passed is False
    assert "weekly_data" in failed


def test_eligibility_missing_rs_data_returns_rs_data(config, passing_row):
    """Missing rs_90d → eligibility FAIL with 'rs_data' gate.

    Rev 3 semantic: same as weekly_data. RS is critical for the rs sub-score
    and the 'Strong RS' why-checklist line. Missing it = ineligible.
    """
    row = dict(passing_row)
    row["rs_90d"] = None
    passed, failed = check_eligibility(row, regime="BULLISH", config=config)
    assert passed is False
    assert "rs_data" in failed


def test_eligibility_missing_both_data_gates(config, passing_row):
    """Missing both weekly_trend_score and rs_90d → both gates fail."""
    row = dict(passing_row)
    row["weekly_trend_score"] = None
    row["rs_90d"] = None
    passed, failed = check_eligibility(row, regime="BULLISH", config=config)
    assert passed is False
    assert "weekly_data" in failed
    assert "rs_data" in failed


# ── 26. compute_market_score_breakdown (rev 3) ──────────────────────────────────


def test_compute_market_score_breakdown_returns_score_and_contributions(config):
    """Breakdown returns (score, {factor: contribution}) where contributions sum to score."""
    sub_scores = {
        "regime": 100, "weekly": 80, "breakout": 90, "overhead_supply": 20,
        "rs": 50, "volume": 100, "sector": 50,
    }
    score, breakdown = compute_market_score_breakdown(sub_scores, config)

    # Score is a float in [0, 100]
    assert isinstance(score, float)
    assert 0 <= score <= 100

    # Breakdown has all 7 factor keys
    assert set(breakdown.keys()) == {
        "regime", "weekly", "breakout", "overhead_supply", "rs", "volume", "sector"
    }

    # Sum of contributions == score (within rounding)
    assert sum(breakdown.values()) == pytest.approx(score, abs=0.01), (
        f"Breakdown sum {sum(breakdown.values()):.4f} != score {score:.4f}"
    )

    # overhead_supply contribution uses the INVERTED value (100 - raw=20 = 80)
    # weight 14 / total 100 → contribution = 80 * 14 / 100 = 11.2
    assert breakdown["overhead_supply"] == pytest.approx(11.2, abs=0.01)


def test_compute_market_score_breakdown_matches_simple(config):
    """compute_market_score_breakdown score matches compute_market_score."""
    sub_scores = {
        "regime": 80, "weekly": 60, "breakout": 70, "overhead_supply": 40,
        "rs": 50, "volume": 50, "sector": 50,
    }
    simple = compute_market_score(sub_scores, config)
    detailed, _ = compute_market_score_breakdown(sub_scores, config)
    assert simple == pytest.approx(detailed, abs=0.0001)


# ── 27. Golden Cases Regression Suite (tests/golden_cases.yaml) ─────────────────


GOLDEN_CASES_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "tests", "golden_cases.yaml")
)


def _load_golden_cases():
    """Load regression scenarios from tests/golden_cases.yaml."""
    import yaml  # imported lazily to keep this test isolated
    with open(GOLDEN_CASES_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _run_golden_case(scenario, config):
    """Run a single golden case scenario through the full CAS pipeline.

    Returns: dict with keys: eligible_passed, structure_passed, eligible_failed,
             structure_failed, market_score, cas, confidence, why_lines.
    """
    row = scenario["row"]
    regime = scenario["regime"]
    proxies = scenario.get("proxies_used", {})

    elig_passed, elig_failed = check_eligibility(row, regime=regime, config=config)
    struct_passed, struct_failed = compute_market_structure(row, config=config)

    # If eligible + structure passed, compute full score
    if elig_passed and struct_passed:
        sub_scores = {
            "regime":         _regime_score(regime, config),
            "weekly":         _weekly_score(row, config),
            "breakout":       _breakout_score(row, config),
            "overhead_supply":row.get("overhead_supply_score") or 0,
            "rs":             _rs_score(row, config),
            "volume":         _volume_score(row, config),
            "sector":         _sector_score(row, config),
        }
        ms = compute_market_score(sub_scores, config)
        cas = compute_portfolio_allocation_score(
            ms,
            winner_profit_pct=scenario.get("winner_profit_pct"),
            concentration_weight_pct=scenario.get("concentration_weight_pct"),
            config=config,
        )
        conf = compute_confidence_stars(row, sub_scores, proxies, config)
        why = render_why_checklist(row, config=config)
    else:
        ms = 0.0
        cas = 0.0
        conf = 0
        why = []

    return {
        "eligible_passed":    elig_passed,
        "structure_passed":   struct_passed,
        "eligible_failed":    elig_failed,
        "structure_failed":   struct_failed,
        "market_score":       ms,
        "cas":                cas,
        "confidence":         conf,
        "why_lines":          why,
    }


@pytest.mark.parametrize("scenario", _load_golden_cases(), ids=lambda s: s["name"])
def test_golden_cases(config, scenario):
    """Regression suite: every scenario in tests/golden_cases.yaml must match its expected outcomes.

    When you tune weights or thresholds, run this. If a scenario starts failing,
    either the tuning was too aggressive (revert) or business intent changed
    (update YAML + Decisions.md).
    """
    exp = scenario["expected"]
    result = _run_golden_case(scenario, config)

    # Eligibility / structure
    assert result["eligible_passed"] is exp["eligible"], (
        f"{scenario['name']}: eligibility expected {exp['eligible']}, got {result['eligible_passed']} "
        f"(failed={result['eligible_failed']})"
    )
    assert result["structure_passed"] is exp["structure_passed"], (
        f"{scenario['name']}: structure expected {exp['structure_passed']}, got {result['structure_passed']} "
        f"(failed={result['structure_failed']})"
    )

    # Required gate / structure failures
    for gate in exp.get("eligible_failed_contains", []):
        assert gate in result["eligible_failed"], (
            f"{scenario['name']}: expected '{gate}' in eligible_failed, got {result['eligible_failed']}"
        )
    for dim in exp.get("structure_failed_contains", []):
        assert dim in result["structure_failed"], (
            f"{scenario['name']}: expected '{dim}' in structure_failed, got {result['structure_failed']}"
        )

    # Market score / CAS / confidence bounds
    if "market_score_gte" in exp:
        assert result["market_score"] >= exp["market_score_gte"], (
            f"{scenario['name']}: market_score {result['market_score']:.2f} < expected {exp['market_score_gte']}"
        )
    if "market_score_lte" in exp:
        assert result["market_score"] <= exp["market_score_lte"], (
            f"{scenario['name']}: market_score {result['market_score']:.2f} > expected {exp['market_score_lte']}"
        )
    if "cas_gte" in exp:
        assert result["cas"] >= exp["cas_gte"], (
            f"{scenario['name']}: CAS {result['cas']:.2f} < expected {exp['cas_gte']}"
        )
    if "cas_lte" in exp:
        assert result["cas"] <= exp["cas_lte"], (
            f"{scenario['name']}: CAS {result['cas']:.2f} > expected {exp['cas_lte']}"
        )
    if "confidence_gte" in exp:
        assert result["confidence"] >= exp["confidence_gte"], (
            f"{scenario['name']}: confidence {result['confidence']} < expected {exp['confidence_gte']}"
        )
    if "confidence_lte" in exp:
        assert result["confidence"] <= exp["confidence_lte"], (
            f"{scenario['name']}: confidence {result['confidence']} > expected {exp['confidence_lte']}"
        )

    # Why-checklist contents
    why_text = "\n".join(result["why_lines"])
    for substring in exp.get("why_contains", []):
        assert substring in why_text, (
            f"{scenario['name']}: expected '{substring}' in why-checklist, got:\n{why_text}"
        )
    for substring in exp.get("why_not_contains", []):
        assert substring not in why_text, (
            f"{scenario['name']}: did NOT expect '{substring}' in why-checklist, got:\n{why_text}"
        )
