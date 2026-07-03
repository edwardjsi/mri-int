"""
Tests for MOSI Lite scoring engine.

Covers:
    1. ROCE scoring (operating)
    2. Sales growth scoring (operating)
    3. Debt scoring (institutional)
    4. Missing data / graceful empty-stock
    5. Decision Score formula (0.6 · MRI + 0.4 · MOSI, clamped 0–100)
    6. Confidence mapping by regime (Bull→HIGH, Sideways→MEDIUM, Bear→LOW)
    7. Recommendation mapping (≥90 / 80–89 / 70–79 / <70)
"""

import pytest
from engine_mosi.mosi_lite import (
    analyze_stock,
    score_macro,
    score_operating,
    score_structural,
    score_institutional,
    compute_confidence,
    map_recommendation,
    set_market_regime,
    MARKET_REGIME as DEFAULT_REGIME,
)

# ── Shared mock ────────────────────────────────────────────────────────────

PERFECT_STOCK = {
    "symbol": "TEST",
    "sector": "Technology",
    "industry": "Software",
    "price": 2500.0,
    "close": 2550.0,
    "high": 2600.0,
    "low": 2400.0,
    "volume": 1_000_000,
    "ema_50": 2400.0,
    "ema_200": 2200.0,
    "ema_200_slope_20": 2.0,
    "ema_50_gt_200": True,
    "ema_200_slope_gt_0": True,
    "breakout_state": "BROKEN_OUT",
    # ── Fundamentals ──
    "sales_growth_pct": 25.0,
    "profit_growth_pct": 22.0,
    "roce_pct": 24.0,
    "roe_pct": 18.0,
    "debt_to_equity": 0.3,
    "revenue": 500_000_000,
    "net_profit": 120_000_000,
    "debt": 30_000_000,
    "equity": 100_000_000,
    "capital_employed": 400_000_000,
    # ── Macro / structural ──
    "promoter_holding_pct": 70.0,
    "market_cap": 50_000_000_000,
    "weekly_high_52w": 2600.0,
    "weekly_low_52w": 1800.0,
    "close_vs_52w_high_pct": 0.98,
    "rolling_high_6m": 2580.0,
    "quarterly_growth_pct": 15.0,
    # ── Scores ──
    "mri_technical_score": 95.0,
    # ── QIF ──
    "revenue_score": 8.0,
    "margin_score": 8.0,
    "leverage_score": 7.0,
    "wc_score": 6.0,
    "roce_score": 9.0,
    "evolution_score": 7.0,
}

EMPTY_STOCK: dict = {}


# ── Tests ────────────────────────────────────────────────────────────────────


def test_roce_scoring_missing() -> None:
    """ROCE >20% not met → score_operating returns 0 for that subcomponent."""
    stock = {"roce_pct": 10.0}
    op = score_operating(stock)
    assert op < 10.0, "ROCE < 20% should not give the ROCE points"


def test_roce_scoring_above_threshold() -> None:
    """ROCE ≥ 20% → full 10 points for the ROCE subcomponent."""
    # Only ROCE set; sales and profit are missing → 0
    stock = {"roce_pct": 22.0, "sales_growth_pct": None, "profit_growth_pct": None}
    op = score_operating(stock)
    assert op == 10.0, "ROCE > 20% should give 10 for operating; others missing are 0"


def test_sales_growth_scoring() -> None:
    """Sales growth >15% → 10 points; below → 0."""
    stock_above = {"sales_growth_pct": 20.0, "profit_growth_pct": 0, "roce_pct": 0}
    stock_below = {"sales_growth_pct": 10.0, "profit_growth_pct": 0, "roce_pct": 0}
    assert score_operating(stock_above) >= 10.0
    assert score_operating(stock_below) < 10.0, "10% not >15% → should be 0"


def test_debt_scoring() -> None:
    """D/E <0.5 → 10 for institutional; >0.5 → 0."""
    stock_low = {"debt_to_equity": 0.3, "promoter_holding_pct": 0}
    stock_high = {"debt_to_equity": 1.5, "promoter_holding_pct": 0}
    assert score_institutional(stock_low) >= 10.0
    assert score_institutional(stock_high) < 10.0


def test_missing_data_graceful() -> None:
    """Empty stock → all scores 0, NO crash, recommendation = IGNORE."""
    result = analyze_stock(EMPTY_STOCK)
    assert result["mosi_lite_score"] == 0.0, "Empty → score 0"
    assert result["m_macro_score"] == 0.0
    assert result["o_operating_score"] == 0.0
    assert result["s_structural_score"] == 0.0
    assert result["i_institutional_score"] == 0.0
    assert result["decision_score"] == 0.0
    assert result["recommendation"] == "IGNORE", "Empty → IGNORE"


def test_decision_score_formula() -> None:
    """
    Decision = 0.6 * MRI + 0.4 * MOSI.
    Perfect stock: 95*0.6 + 100*0.4 = 57 + 40 = 97, clamped → 97.
    """
    result = analyze_stock(PERFECT_STOCK)
    expected = 0.60 * 95.0 + 0.40 * 100.0
    assert result["decision_score"] == pytest.approx(expected, abs=0.01)
    # Also check clamping: if MRI=0 and MOSI=0, decision=0
    assert analyze_stock(EMPTY_STOCK)["decision_score"] == 0.0


def test_confidence_mapping() -> None:
    """Bull→HIGH, Side→MEDIUM, Bear→LOW."""
    assert compute_confidence(90.0, "BULLISH") == "HIGH"
    assert compute_confidence(50.0, "SIDEWAYS") == "MEDIUM"
    assert compute_confidence(30.0, "BEARISH") == "LOW"


def test_recommendation_mapping() -> None:
    """
    ≥90 → TODAYS_PICK
    80–89 → RESEARCH
    70–79 → WATCHLIST
    <70 → IGNORE
    """
    assert map_recommendation(95.0) == "TODAYS_PICK"
    assert map_recommendation(85.0) == "RESEARCH"
    assert map_recommendation(75.0) == "WATCHLIST"
    assert map_recommendation(60.0) == "IGNORE"
    # Edge: exactly 90
    assert map_recommendation(90.0) == "TODAYS_PICK"
    assert map_recommendation(80.0) == "RESEARCH"
    assert map_recommendation(70.0) == "WATCHLIST"


def test_full_perfect_stock_score_100() -> None:
    """
    A stock with ALL fields perfect should score:
        M (20) → 20 (sector + industry present)
        O (30) → 30 (all three >threshold)
        S (30) → 30 (near 52w, stage 2, acceleration)
        I (20) → 20 (promoter >50%, D/E <0.5)
        Total = 100
    """
    result = analyze_stock(PERFECT_STOCK)
    assert result["mosi_lite_score"] == 100.0, "Perfect → 100"
    assert result["m_macro_score"] == 20.0
    assert result["o_operating_score"] == 30.0
    assert result["s_structural_score"] == 30.0
    assert result["i_institutional_score"] == 20.0
    # Decision: 95*0.6 + 100*0.4 = 97
    assert result["decision_score"] == 97.0
    assert result["recommendation"] == "TODAYS_PICK"


# ── Regression guard: needs a helper alias for the typo in the source ──

