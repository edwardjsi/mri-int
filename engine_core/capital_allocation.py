"""
engine_core.capital_allocation — Capital Allocation Score V1.0 (Decision 100, rev 2)

Pure logic, no DB access. Reads thresholds + weights from
`config/capital_allocation.yaml` via `load_config()`. Returns Python primitives
(dicts, lists, tuples, floats, ints) only — never ORM rows.

Architecture (per Decision 100):
    Eligibility (6 hard gates)
        ↓ reject → out
    Market Sub-Gates (3 hard PASS/FAIL: Trend, Breakout, Quality)
        ↓ reject → out
    Market Numeric Score = weighted sum of 7 sub-scores (survivors only)
        ↓
    Portfolio Multipliers: CAS = Market × Winner × Concentration
        ↓
    Confidence: 0–5 ★ stars (display-only)
        ↓
    Action chip: FIRST TRANCHE / ADD SECOND TRANCHE / WATCH

The Market Score is NOT a simple weighted sum — it has hard sub-gates first
so a stock cannot compensate for a weak weekly trend with huge volume.

Configuration contract (see config/capital_allocation.yaml):
    eligibility.*                  — 6 hard gates (regime, EMA, breakout, liq, qif, 52w)
    market_subgates.*              — 3 PASS/FAIL (trend, breakout, quality)
    weights                        — sums to 100; keys: regime, weekly, breakout,
                                     overhead_supply, rs, volume, sector
    multiplier.{winner,concentration}
    confidence.factors.*           — 5 binary criteria, each weight=1
    subscore.weekly.*              — multi-component weekly structure
    subscore.breakout.*            — volume_bonus_threshold, volume_bonus_points
    subscore.sector.proxy_score_v1 — neutral 50 until V1.2
    why_templates                  — list of {condition, template} entries

Session: N+1 (2026-07-07). See Sessions.md for multi-session handoff notes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import yaml


# ── Public API ──────────────────────────────────────────────────────────────


def load_config(config_path: str | Path) -> dict[str, Any]:
    """Load CAS config from YAML. Validates weights sum to 100.

    Raises:
        FileNotFoundError: path does not exist
        ValueError: weights do not sum to 100
        yaml.YAMLError: malformed YAML
    """
    with open(config_path, "r", encoding="utf-8") as f:
        cfg: dict[str, Any] = yaml.safe_load(f)

    weights = cfg.get("weights", {})
    total = sum(weights.values())
    if not (99.99 <= total <= 100.01):
        raise ValueError(
            f"Config weights must sum to 100, got {total}: {weights}"
        )
    return cfg


def check_eligibility(
    row: dict[str, Any],
    regime: str,
    config: dict[str, Any],
) -> tuple[bool, list[str]]:
    """Apply the 6 hard eligibility gates. Returns (passed, failed_gate_names).

    Gate names in `failed`: "regime", "ema_stack", "breakout_state",
    "liquidity", "quality", "52w_position". Sub-condition details (e.g. which
    of the 4 EMA conditions failed) are not returned — callers needing
    diagnostics should re-evaluate the row directly.
    """
    elig = config["eligibility"]
    failed: list[str] = []

    # ── Gate 1: Regime ──
    allowed = set(elig.get("allowed_regimes", []))
    aggressive = elig.get("aggressive_mode", False)
    if regime not in allowed and not (aggressive and regime == "BEARISH"):
        failed.append("regime")

    # ── Gate 2: EMA stack (rev 2: 4 conditions, relaxed from strict 20>50>100>200) ──
    ema_conds = elig.get("ema_conditions", {})
    close = row.get("close")
    ema_20 = row.get("ema_20")
    ema_50 = row.get("ema_50")
    ema_200 = row.get("ema_200")
    ema_100_slope = row.get("ema_100_slope_5d")

    ema_pass = True
    if ema_conds.get("close_gt_ema20") and not (close and ema_20 and close > ema_20):
        ema_pass = False
    if ema_conds.get("ema20_gt_ema50") and not (ema_20 and ema_50 and ema_20 > ema_50):
        ema_pass = False
    if ema_conds.get("ema50_gt_ema200") and not (ema_50 and ema_200 and ema_50 > ema_200):
        ema_pass = False
    if ema_conds.get("ema100_rising") and not (
        ema_100_slope is not None and ema_100_slope > 0
    ):
        ema_pass = False
    if not ema_pass:
        failed.append("ema_stack")

    # ── Gate 3: Breakout state + age ──
    max_age = elig.get("breakout_max_age_days", 5)
    age = row.get("breakout_age")
    if (
        row.get("breakout_state") != "BROKEN_OUT"
        or age is None
        or age > max_age
    ):
        failed.append("breakout_state")

    # ── Gate 4: Liquidity (ADTV ≥ min_liquidity_crores × 1e7 INR) ──
    # ADTV convention per engine_core/signal_generator.py: avg_volume_20d × close
    avg_vol = row.get("avg_volume_20d")
    min_cr = elig.get("min_liquidity_crores", 10)
    if not (
        avg_vol
        and close
        and (avg_vol * close) >= min_cr * 10_000_000
    ):
        failed.append("liquidity")

    # ── Gate 5: Quality (QIF ≥ min_quality, rev 2 raised 65 → 70) ──
    qif = row.get("qif_score")
    if qif is None or qif < elig.get("min_quality", 70):
        failed.append("quality")

    # ── Gate 6: 52-week position (within max_distance_from_52wh_pct of high) ──
    high_52w = row.get("rolling_high_52w")
    max_dist_pct = elig.get("max_distance_from_52wh_pct", 10)
    if not (
        close
        and high_52w
        and high_52w > 0
        and close >= high_52w * (1 - max_dist_pct / 100)
    ):
        failed.append("52w_position")

    return (len(failed) == 0, failed)


def check_market_subgates(
    row: dict[str, Any],
    config: dict[str, Any],
) -> tuple[bool, list[str]]:
    """Apply the 3 hard PASS/FAIL sub-gates (post-eligibility).

    Sub-gate names in `failed`: "trend", "breakout", "quality". All 3 must PASS
    for the stock to receive a numeric Market Score. Stricter than eligibility:
        - trend: weekly_trend_score ≥ 50 (eligibility doesn't check this)
        - breakout: age ≤ 3 (eligibility allows ≤ 5)
        - quality: qif ≥ 75 (eligibility allows ≥ 70)
    """
    sub = config["market_subgates"]
    failed: list[str] = []

    # Trend sub-gate
    weekly = row.get("weekly_trend_score")
    min_weekly = sub.get("trend", {}).get("min_weekly_trend_score", 50)
    if weekly is None or weekly < min_weekly:
        failed.append("trend")

    # Breakout sub-gate (stricter than eligibility's breakout_max_age_days=5)
    age = row.get("breakout_age")
    max_age = sub.get("breakout", {}).get("max_breakout_age_days", 3)
    if age is None or age > max_age:
        failed.append("breakout")

    # Quality sub-gate (stricter than eligibility's min_quality=70)
    qif = row.get("qif_score")
    min_q = sub.get("quality", {}).get("min_quality", 75)
    if qif is None or qif < min_q:
        failed.append("quality")

    return (len(failed) == 0, failed)


def compute_market_score(
    sub_scores: dict[str, float],
    config: dict[str, Any],
) -> float:
    """Weighted sum of 7 sub-scores. Returns float in [0, 100].

    `sub_scores` keys (must match config["weights"] keys):
        regime, weekly, breakout, overhead_supply, rs, volume, sector.

    `overhead_supply` is stored as "badness" (0 = clear air = good,
    100 = max resistance = bad). We invert it internally so that low
    overhead contributes positively to the Market Score.
    """
    weights = config["weights"]
    total_weight = sum(weights.values())  # validated to be 100 in load_config
    weighted_sum = 0.0
    for factor, weight in weights.items():
        sub_value = sub_scores.get(factor, 0) or 0
        if factor == "overhead_supply":
            # Invert: 0 (clear air) → 100 contribution; 100 (max resistance) → 0
            sub_value = 100 - sub_value
        weighted_sum += sub_value * weight
    return max(0.0, min(weighted_sum / total_weight, 100.0))


def compute_portfolio_allocation_score(
    market_score: float,
    winner_profit_pct: float | None,
    concentration_weight_pct: float | None,
    config: dict[str, Any],
) -> float:
    """CAS = market_score × winner_multiplier × concentration_multiplier.

    Winner (rev 2, softened cap):
        multiplier = 1 + (profit / scale_pct) × max_boost,
        clamped to [min_multiplier, 1 + max_boost].
        +10% profit → 1.10× (cap). +30% profit → 1.10× (still capped).
        −15% loss → 0.85× (floor). −30% loss → 0.85× (still floored).

    Concentration:
        multiplier = 1 − clamp(weight_pct / max_weight_pct, 0, 1) × max_penalty.
        0% weight → 1.00×. 15%+ weight → 0.90× (max −10% penalty).

    `None` for either multiplier arg = treat as 1.00× (no info available).
    """
    mult_cfg = config["multiplier"]

    # ── Winner multiplier ──
    if winner_profit_pct is None:
        winner_mult = 1.0
    else:
        w = mult_cfg["winner"]
        raw = 1.0 + (winner_profit_pct / w["scale_pct"]) * w["max_boost"]
        winner_mult = max(w["min_multiplier"], min(raw, 1.0 + w["max_boost"]))

    # ── Concentration multiplier ──
    if concentration_weight_pct is None:
        conc_mult = 1.0
    else:
        c = mult_cfg["concentration"]
        weight_frac = min(concentration_weight_pct / c["max_weight_pct"], 1.0)
        conc_mult = 1.0 - weight_frac * c["max_penalty"]

    return market_score * winner_mult * conc_mult


def compute_confidence_stars(
    row: dict[str, Any],
    sub_scores: dict[str, float],
    proxies_used: dict[str, bool],
    config: dict[str, Any],
) -> int:
    """0–5 star rating from 5 binary criteria. Clamped to [0, 5].

    Criteria (each adds 1 star when met):
        1. no_proxy_used   — no proxy values are True in `proxies_used`
        2. data_completeness — row["data_completeness_pct"] ≥ threshold_pct (90)
        3. factor_agreement  — std-dev of sub_scores ≤ max_std_dev (20),
                              computed only when ≥ 2 sub-scores present
        4. trend_maturity    — weekly_trend_score ≥ min_weekly_trend (75)
        5. breakout_maturity — breakout_age in [age_min, age_max] = [1, 3]
    """
    conf = config["confidence"]["factors"]
    stars = 0

    # 1. No proxies used
    if not any(proxies_used.values()):
        stars += int(conf["no_proxy_used"]["weight"])

    # 2. Data completeness
    pct = row.get("data_completeness_pct") or 0
    if pct >= conf["data_completeness"]["threshold_pct"]:
        stars += int(conf["data_completeness"]["weight"])

    # 3. Factor agreement (only meaningful with ≥ 2 sub-scores)
    if len(sub_scores) >= 2:
        std = float(np.std(list(sub_scores.values()), ddof=0))
        if std <= conf["factor_agreement"]["max_std_dev"]:
            stars += int(conf["factor_agreement"]["weight"])

    # 4. Trend maturity
    weekly = row.get("weekly_trend_score") or 0
    if weekly >= conf["trend_maturity"]["min_weekly_trend"]:
        stars += int(conf["trend_maturity"]["weight"])

    # 5. Breakout maturity (age in [1, 3])
    age = row.get("breakout_age")
    if (
        age is not None
        and conf["breakout_maturity"]["age_min"]
        <= age
        <= conf["breakout_maturity"]["age_max"]
    ):
        stars += int(conf["breakout_maturity"]["weight"])

    return min(stars, 5)


def render_why_checklist(
    row: dict[str, Any],
    config: dict[str, Any],
) -> list[str]:
    """Render the structured ✓ checklist from YAML templates + condition checks.

    Iterates `config["why_templates"]`. For each entry:
      1. Evaluate the named condition against `row`.
      2. If fired, format the template string with condition-specific kwargs.
      3. Append formatted line to result.

    Lines where required interpolation values are missing are silently skipped
    (e.g., `winner_profit` template skipped when no `winner_profit_pct` field).
    """
    lines: list[str] = []
    for entry in config.get("why_templates", []):
        condition = entry["condition"]
        template = entry["template"]
        kwargs, fired = _evaluate_condition(condition, row)
        if not fired:
            continue
        try:
            lines.append(template.format(**kwargs))
        except (KeyError, IndexError, ValueError):
            # Missing interpolation value → skip line rather than crash
            continue
    return lines


# ── Sub-score helpers (private; imported by tests) ──────────────────────────


def _regime_score(regime: str, config: dict[str, Any]) -> int:
    """Regime sub-score: BULLISH=100, SIDEWAYS=60, BEARISH=20 (per §3.1)."""
    table = config["subscore"]["regime"]
    return int(table.get(regime.lower(), 0))


def _weekly_score(row: dict[str, Any], config: dict[str, Any]) -> int:
    """Multi-component Weekly Structure score, max 100 (per §3.2).

    Components (weights from config["subscore"]["weekly"], summing to 100):
        - hh_weight:                 HH confirmed                (+25)
        - hl_weight:                 HL confirmed                (+25)
        - above_weekly_ema13_weight: close > weekly EMA-13       (+20)
        - above_weekly_ema20_weight: close > weekly EMA-20       (+15)
        - within_52wh_weight:        close ≥ 0.95 × 52w high     (+15)
    """
    cfg = config["subscore"]["weekly"]
    score = 0

    if row.get("hh_confirmed"):
        score += cfg["hh_weight"]
    if row.get("hl_confirmed"):
        score += cfg["hl_weight"]

    close = row.get("close")
    if close and row.get("weekly_ema13") is not None and close > row["weekly_ema13"]:
        score += cfg["above_weekly_ema13_weight"]
    if close and row.get("weekly_ema20") is not None and close > row["weekly_ema20"]:
        score += cfg["above_weekly_ema20_weight"]
    if (
        close
        and row.get("rolling_high_52w")
        and row["rolling_high_52w"] > 0
        and close >= row["rolling_high_52w"] * 0.95
    ):
        score += cfg["within_52wh_weight"]

    return min(score, 100)


# AGE_DECAY table (Decision 099) for breakout sub-score
AGE_DECAY: dict[int, int] = {0: 100, 1: 95, 2: 90, 3: 85, 4: 70, 5: 65}
AGE_DECAY_DEFAULT: int = 40  # age > 5 → stale


def _breakout_score(row: dict[str, Any], config: dict[str, Any]) -> int:
    """Breakout Quality sub-score (per §3.3).

    base = AGE_DECAY[age] (or 40 if age > 5)
    volume bonus = +points if vol_ratio ≥ threshold
    Final = clamp(base + bonus, 0, 100).
    """
    age = row.get("breakout_age")
    if age is None:
        return 0

    cfg = config["subscore"]["breakout"]
    base = AGE_DECAY.get(age, AGE_DECAY_DEFAULT)

    avg_vol = row.get("avg_volume_20d") or 0
    vol = row.get("volume") or 0
    if avg_vol > 0 and (vol / avg_vol) >= cfg["volume_bonus_threshold"]:
        base += cfg["volume_bonus_points"]

    return max(0, min(base, 100))


def _rs_score(row: dict[str, Any], config: dict[str, Any]) -> float:
    """Relative Strength sub-score (per §3.6).

    score = clamp(rs_90d / 0.10 × 100, 0, 100). +10% vs Nifty → 100.
    """
    rs = row.get("rs_90d") or 0.0
    return max(0.0, min(rs / 0.10 * 100, 100.0))


def _volume_score(row: dict[str, Any], config: dict[str, Any]) -> float:
    """Volume Confirmation sub-score (per §3.7).

    score = 100 × clamp((vol_ratio − 1.0) / 2.0, 0, 1).
    3× average → 100. 1× (at average) → 0. 5× average → still 100 (capped).
    """
    vol = row.get("volume") or 0
    avg = row.get("avg_volume_20d") or 0
    if avg == 0:
        return 0.0
    ratio = vol / avg
    return 100.0 * max(0.0, min((ratio - 1.0) / 2.0, 1.0))


def _sector_score(row: dict[str, Any], config: dict[str, Any]) -> int:
    """Sector Strength sub-score. V1.0 = neutral proxy (50).
    V1.2 (deferred) will use real `sector_rs_60d` from stock_sectors.
    """
    return int(config["subscore"]["sector"]["proxy_score_v1"])


# ── Why-checklist condition registry ────────────────────────────────────────


# Thresholds used by `_evaluate_condition` (kept here for visibility;
# the YAML `why_templates` list is the source of truth for which conditions
# are evaluated, but the threshold logic lives next to the code).
_OVERHEAD_CLEAR_AIR_THRESHOLD = 30  # overhead_supply_score ≤ this → "clear air"
_RS_STRONG_THRESHOLD = 0.05        # rs_90d ≥ this → "strong RS" (+5% vs Nifty 90d)
_QIF_HIGH_THRESHOLD = 70           # qif_score ≥ this → "high quality"


def _evaluate_condition(
    condition: str,
    row: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """Evaluate a why-checklist condition.

    Returns:
        (kwargs, True)  — condition met; caller formats template with kwargs.
        ({}, False)     — condition not met; caller skips template.

    Required row fields per condition:
        regime_strong    → row["regime"] == "BULLISH"
        weekly_strong    → row["weekly_trend_score"] ≥ 75
        breakout_today   → row["breakout_age"] == 0
        breakout_early   → row["breakout_age"] in [1, 5]
        near_52wh        → row["close"] ≥ 0.95 × row["rolling_high_52w"]
        rs_strong        → row["rs_90d"] ≥ 0.05
        volume_confirmed → row["volume"] / row["avg_volume_20d"] ≥ 2.0
        winner_profit    → row["winner_profit_pct"] is not None and > 0
        clear_overhead   → row["overhead_supply_score"] ≤ 30
        high_quality     → row["qif_score"] ≥ 70
    """
    if condition == "regime_strong":
        if row.get("regime") == "BULLISH":
            return {"regime_label": "BULLISH"}, True
    elif condition == "weekly_strong":
        if (row.get("weekly_trend_score") or 0) >= 75:
            return {}, True
    elif condition == "breakout_today":
        if row.get("breakout_age") == 0:
            return {}, True
    elif condition == "breakout_early":
        age = row.get("breakout_age")
        if age is not None and 1 <= age <= 5:
            return {"breakout_age": age}, True
    elif condition == "near_52wh":
        close = row.get("close") or 0
        high = row.get("rolling_high_52w") or 0
        if high > 0 and close >= high * 0.95:
            return {}, True
    elif condition == "rs_strong":
        if (row.get("rs_90d") or 0) >= _RS_STRONG_THRESHOLD:
            return {}, True
    elif condition == "volume_confirmed":
        vol = row.get("volume") or 0
        avg = row.get("avg_volume_20d") or 0
        if avg > 0 and (vol / avg) >= 2.0:
            return {"vol_ratio": vol / avg}, True
    elif condition == "winner_profit":
        profit = row.get("winner_profit_pct")
        if profit is not None and profit > 0:
            return {"profit_pct": profit}, True
    elif condition == "clear_overhead":
        score = row.get("overhead_supply_score")
        if score is not None and score <= _OVERHEAD_CLEAR_AIR_THRESHOLD:
            return {"overhead_supply_score": score}, True
    elif condition == "high_quality":
        qif = row.get("qif_score") or 0
        if qif >= _QIF_HIGH_THRESHOLD:
            return {"qif_score": qif}, True
    return {}, False
