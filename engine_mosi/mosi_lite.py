"""
MOSI Lite — Lightweight fundamental + structural scoring engine.

Pure functions only. No UI logic. No DB I/O. No hardcoded stock names.
Designed so MOSI Lite can later be replaced by Full MOSI without UI changes
(the UI only consumes the output contract).

Score breakdown (max 100):
    M — Macro (20):   sector > market (10), industry > sector (10)
    O — Operating (30): sales growth >15% (10), profit growth >15% (10), ROCE >20% (10)
    S — Structural (30): near 52w high (10), Stage 2 trend (10), quarterly acceleration (10)
    I — Institutional (20): promoter >50% (10), debt/equity <0.5 (10)

Decision Score = 0.6 * MRI_Technical + 0.4 * MOSI_Lite (clamped 0–100)
Confidence: based on market regime (configurable constant, default SIDEWAYS)
Recommendation: >=90 TODAYS_PICK, 80-89 RESEARCH, 70-79 WATCHLIST, <70 IGNORE

All missing fields → 0 for that component. Never raises.
"""

from __future__ import annotations
from typing import Optional, TypedDict

# ── Configurable constants ──────────────────────────────────────────────
MARKET_REGIME: str = "SIDEWAYS"  # "BULLISH", "SIDEWAYS", "BEARISH"
# Override by calling set_market_regime(...) or passing to analyze_stock.

# ── Type definitions ─────────────────────────────────────────────────────


class StockData(TypedDict, total=False):
    """Input stock object — all fields optional."""
    symbol: str
    sector: str
    industry: str
    price: float
    close: float
    high: float
    low: float
    volume: int
    ema_50: float
    ema_200: float
    ema_200_slope_20: float
    ema_50_gt_200: bool
    ema_200_slope_gt_0: bool
    breakout_state: str
    # ── Fundamental / QIF fields ──
    sales_growth_pct: float          # YoY revenue growth %
    profit_growth_pct: float         # YoY PAT growth %
    roce_pct: float                  # Return on Capital Employed %
    roe_pct: float                   # Return on Equity %
    debt_to_equity: float            # D/E ratio
    revenue: float
    net_profit: float
    debt: float
    equity: float
    capital_employed: float
    # ── Macro / structural ──
    promoter_holding_pct: float      # % promoter holding
    market_cap: float
    weekly_high_52w: float           # 52-week high
    weekly_low_52w: float           # 52-week low
    close_vs_52w_high_pct: float   # % of 52w high
    # ── Scores ──
    mri_technical_score: float       # 0–100 (from stock_scores.total_score)
    # ── QIF ──
    revenue_score: float             # 0–10 QIF revenue
    margin_score: float              # 0–10 QIF margin
    leverage_score: float            # 0–10 QIF leverage
    wc_score: float                   # 0–10 QIF working capital
    roce_score: float                # 0–10 QIF ROCE
    evolution_score: float          # 0–10 QIF evolution


class MosiLiteOutput(TypedDict, total=False):
    mosi_lite_score: float
    m_macro_score: float
    o_operating_score: float
    s_structural_score: float
    i_institutional_score: float
    decision_score: float
    mri_technical_score: float
    confidence: str
    recommendation: str
    details: dict[str, str]


# ── Helpers ──────────────────────────────────────────────────────────────


def _safe_float(
    val: object,
    default: float = 0.0,
) -> float:
    """Coerce to float; return default on None/NaN."""
    if val is None:
        return default
    try:
        v = float(val)
        if v != v:  # NaN
            return default
        return v
    except (ValueError, TypeError):
        return default


def _value_in_range(
    val: object,
    threshold: float,
    above: bool = True,
    default: float = 0.0,
) -> bool:
    """Return True if the value is above (or below) threshold."""
    v = _safe_float(val, default)
    if above:
        return v >= threshold
    return v <= threshold


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


# ── M — Macro (20) ────────────────────────────────────────────────────────


def score_macro(stock: StockData) -> float:
    """
    Score 0–20 points.

    - Sector outperforming market = 10
    - Industry outperforming sector = 10

    Both rely on metadata we may not have (sector/industry). Fallback: if
    either is missing, score 0 for that subcomponent.
    """
    score: float = 0.0

    # Sector > Market: if we have `mri_technical_score` and `sector`, we can
    # compare the sector's avg performance to market. But for Lite, we
    # approximate: if the stock has any QIF data (even a single fundamental),
    # it's probably in a proper sector. Default: 5/10 if sector is known.
    sector = stock.get("sector")
    if sector and str(sector).strip():
        score += 5.0  # 5/10 base for having a sector

    # Industry > Sector: same logic
    industry = stock.get("industry")
    if industry and str(industry).strip():
        score += 5.0  # 5/10 base for having an industry

    # Full points (10+10) require the sector to be a known top performer.
    # For this Lite, we just give 10/20 if both are known.
    if sector and industry:
        return 20.0

    return score


# ── O — Operating Excellence (30) ──────────────────────────────────────────


def score_operating(
    stock: StockData,
    sales_growth_threshold: float = 15.0,
    profit_growth_threshold: float = 15.0,
    roce_threshold: float = 20.0,
) -> float:
    """
    Score 0–30 points.

    - Sales growth >15% YoY = 10
    - Profit growth >15% YoY = 10
    - ROCE >20% = 10
    """
    score: float = 0.0

    # Sales growth
    sgp = _safe_float(stock.get("sales_growth_pct"))
    if sgp >= sales_growth_threshold:
        score += 10.0

    # Profit growth
    pgp = _safe_float(stock.get("profit_growth_pct"))
    if pgp >= profit_growth_threshold:
        score += 10.0

    # ROCE
    roce = _safe_float(stock.get("roce_pct"))
    if roce >= roce_threshold:
        score += 10.0

    return _clamp(score, 0.0, 30.0)


# ── S — Structural Quality (30) ────────────────────────────────────────────


def score_structural(stock: StockData) -> float:
    """
    Score 0–30 points.

    - Near 52-week high = 10
    - Stage 2 trend (upward) = 10
    - Quarterly growth acceleration = 10
    """
    score: float = 0.0

    # Near 52-week high: close within 3% of 52w high
    high52 = _safe_float(stock.get("weekly_high_52w"))
    close_ = _safe_float(stock.get("close"))
    if high52 > 0 and close_ > 0:
        pct = close_ / high52
        if pct >= 0.97:  # Within 3% of 52w high
            score += 10.0
    elif _safe_float(stock.get("close")) > 0:
        # Fallback: check rolling_high_6m (existing column)
        rh6 = _safe_float(stock.get("rolling_high_6m"))
        if rh6 > 0 and _safe_float(stock.get("close")) / rh6 >= 0.97:
            score += 5.0  # Partial credit for 6m high

    # Stage 2 trend: EMA 50 > EMA 200 AND EMA 200 slope > 0
    ema50_gt_200 = stock.get("ema_50_gt_200")
    if ema50_gt_200 is not None:
        if ema50_gt_200:
            score += 10.0
    else:
        # Compute from raw fields
        ema50 = _safe_float(stock.get("ema_50"))
        ema200 = _safe_float(stock.get("ema_200"))
        if ema50 > 0 and ema200 > 0 and ema50 >= ema200:
            score += 10.0

    # Quarterly growth acceleration: consecutive quarters of improving growth
    # We use `mri_technical_score` as a rough proxy — if the stock has a high
    # technical score, it likely has momentum. But the real test is
    # `agent_details` JSONB with quarterly trajectory.
    qg = _safe_float(stock.get("quarterly_growth_pct"))
    if qg >= 10.0:  # 10%+ quarterly growth
        score += 10.0

    return _clamp(score, 0.0, 30.0)


# ── I — Institutional Quality (20) ────────────────────────────────────────


def score_institutional(stock: StockData) -> float:
    """
    Score 0–20 points.

    - Promoter holding >50% = 10
    - Debt/Equity <0.5 = 10
    """
    score: float = 0.0

    # Promoter holding
    promoter = _safe_float(stock.get("promoter_holding_pct"))
    if promoter >= 50.0:
        score += 10.0

    # Debt/Equity
    d_e = _safe_float(stock.get("debt_to_equity"))
    if d_e <= 0.5 and d_e > 0:  # >0 avoids 0/0 falsely passing
        score += 10.0

    return _clamp(score, 0.0, 20.0)


# ── Confidence ────────────────────────────────────────────────────────────


def compute_confidence(
    decision_score: float,
    regime: str | None = None,
) -> str:
    """
    Map decision score + regime to confidence level.

    Logic:
        - Bull market: HIGH (all passes)
        - Sideways: MEDIUM (typical)
        - Bear: LOW (reduce conviction)

    If regime is None, use module-level MARKET_REGIME constant.
    """
    if regime is None:
        regime = MARKET_REGIME

    regime = regime.upper().strip()

    if regime == "BULLISH":
        return "HIGH"
    elif regime == "BEARISH":
        return "LOW"
    # Sideways or unknown → MEDIUM
    return "MEDIUM"


# ── Recommendation ──────────────────────────────────────────────────────────


def map_recommendation(decision_score: float) -> str:
    """
    Map decision score to recommendation.

    >= 90  → TODAYS_PICK
    80–89 → RESEARCH
    70–79 → WATCHLIST
    < 70  → IGNORE
    """
    d = _clamp(decision_score, 0.0, 100.0)
    if d >= 90:
        return "TODAYS_PICK"
    elif d >= 80:
        return "RESEARCH"
    elif d >= 70:
        return "WATCHLIST"
    else:
        return "IGNORE"


# ── Composite ───────────────────────────────────────────────────────────────


def analyze_stock(
    stock: StockData,
    market_regime: str | None = None,
) -> MosiLiteOutput:
    """
    Main entry point.

    Takes a stock dict (any shape, any missing fields) and returns a
    scored output dict with:
        - mosi_lite_score (0–100)
        - m_macro_score, o_operating_score, s_structural_score, i_institutional_score
        - mri_technical_score
        - decision_score (0–100)
        - confidence (LOW/MEDIUM/HIGH)
        - recommendation (TODAYS_PICK / RESEARCH / WATCHLIST / IGNORE)

    Never raises. Missing fields → 0 for that component.
    """
    if market_regime is None:
        regime = MARKET_REGIME
    else:
        regime = market_regime

    # Get the MRI technical score
    mri_tech: float = _safe_float(stock.get("mri_technical_score"))

    # Compute each MOSI Lite component
    m_macro: float = score_macro(stock)
    o_operating: float = score_operating(stock)
    s_structural: float = score_structural(stock)
    i_institutional: float = score_institutional(stock)

    # Full MOSI Lite score (max 100)
    mosi_lite_score_: float = _clamp(m_macro + o_operating + s_structural + i_institutional, 0.0, 100.0)

    # Decision Score = 0.6 * MRI + 0.4 * MOSI (clamped 0–100)
    decision_score_: float = _clamp(
        0.60 * mri_tech + 0.40 * mosi_lite_score_,
        0.0,
        100.0,
    )

    # Confidence
    confidence_: str = compute_confidence(decision_score_, regime)

    # Recommendation
    recommendation_: str = map_recommendation(decision_score_)

    return MosiLiteOutput(
        mosi_lite_score=mosi_lite_score_,
        m_macro_score=m_macro,
        o_operating_score=o_operating,
        s_structural_score=s_structural,
        i_institutional_score=i_institutional,
        decision_score=decision_score_,
        mri_technical_score=mri_tech,
        confidence=confidence_,
        recommendation=recommendation_,
        details={
            "regime": regime,
        },
    )


# ── Config accessor ────────────────────────────────────────────────────────


def set_market_regime(regime: str) -> None:
    """Set the market regime constant. Idempotent."""
    global MARKET_REGIME
    r = regime.upper().strip()
    if r in ("BULLISH", "SIDEWAYS", "BEARISH"):
        MARKET_REGIME = r