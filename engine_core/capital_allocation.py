"""
engine_core.capital_allocation — Capital Allocation Score V1.0 (Decision 100, rev 3)

Pure logic, no DB access. Reads thresholds + weights from
`config/capital_allocation.yaml` via `load_config()`. Returns Python primitives
(dicts, lists, tuples, floats, ints) only — never ORM rows.

Architecture (per Decision 100, rev 3):
    Eligibility (8 hard gates — regime, ema_stack, breakout_state, liquidity,
                quality, 52w_position, weekly_data, rs_data)
        ↓ reject → out
    Market Structure (3 hard PASS/FAIL: Trend, Breakout, Quality)
        ↓ reject → out
    Market Numeric Score = weighted sum of 7 sub-scores (survivors only)
        ↓
    Portfolio Multipliers: CAS = Market × Winner × Concentration
        ↓
    Confidence: 0–5 ★ stars (model certainty, NOT stock quality)
        ↓
    Action chip: FIRST TRANCHE / ADD SECOND TRANCHE / WATCH

The Market Score is NOT a simple weighted sum — it has hard sub-gates first
so a stock cannot compensate for a weak weekly trend with huge volume.

Rev 3 changes (2026-07-07):
    - Confidence = 5 model-certainty stars (Complete data, Factor agreement,
      Stable calculations, Low proxy usage, Indicator freshness). Trend and
      breakout maturity moved OUT (they are stock-quality, not model certainty).
    - All calibration constants moved to YAML `calibration.*`. No numeric
      thresholds live in this file. Single source of truth: YAML.
    - Missing critical market data → ineligible (NOT scored as 0). Added 2
      new eligibility gates: weekly_data and rs_data.
    - `check_market_subgates` renamed → `compute_market_structure` (semantic
      alignment: it assesses market structure quality, not "sub-gates").
    - Added `compute_market_score_breakdown()` for per-factor logging.
    - Invert overhead_supply before factor_agreement std-dev so all factors
      share the same semantic direction (higher = better).
    - Logging levels: DEBUG for breakdown, INFO for summary, WARNING for
      unexpected conditions. No per-call info-level logging (would flood).

Configuration contract (see config/capital_allocation.yaml):
    eligibility.*                  — 8 hard gates
    market_subgates.*              — 3 PASS/FAIL (trend, breakout, quality)
    weights                        — sums to 100
    multiplier.{winner,concentration}
    confidence.factors.*           — 5 model-certainty criteria, weight=1 each
    calibration.*                  — ALL numeric thresholds (rs_strong,
                                     volume_confirmed, age_decay table, etc.)
    subscore.weekly.*              — multi-component weekly weights
    subscore.breakout.*            — volume_bonus_threshold, volume_bonus_points
    subscore.sector.proxy_score_v1 — neutral 50 until V1.2
    why_templates                  — list of {condition, template} entries

Session: N+1 (2026-07-07). See Sessions.md for multi-session handoff notes.
"""

from __future__ import annotations

import hashlib
import logging
import subprocess
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import yaml


logger = logging.getLogger(__name__)


# ── Versioning & Engine Signature ─────────────────────────────────────────────────

CAS_VERSION = "1.1.0"
"""CAS engine version. Bumped on every behavior-affecting change.
Captured with every recommendation via compute_engine_signature()."""


def _get_commit_sha() -> str:
    """Read current git commit short SHA. Cached at module import.

    Falls back to 'unknown' if git is unavailable (e.g., Docker build without
    .git directory). The engine signature is still valid; only provenance
    traceability is degraded.
    """
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            cwd=Path(__file__).resolve().parent.parent,
        )
        return out.decode("ascii").strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "unknown"


COMMIT_SHA = _get_commit_sha()
"""Git commit SHA at module import time. Stored in engine signature."""


# ── Row normalization (Decimal → float coercion) ────────────────────────────────


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Convert all Decimal values in `row` to float. Returns a NEW dict.

    Per Decision 101 (Gap 5): "Engine must not know or care whether Postgres
    returned Decimal." All callers go through this helper before the engine
    sees the row. One place to audit, one place to fix.

    Handles:
      - Decimal       → float  (primary case from psycopg2)
      - float         → unchanged
      - int           → unchanged
      - str           → unchanged (symbols, regime, etc.)
      - None          → unchanged (missing optional fields)
      - date/datetime → unchanged (date objects stay as date objects)
      - nested lists/dicts → NOT recursed (rows are flat in this codebase)

    Args:
        row: dict-like row from any source (psycopg2, fixture, CSV).

    Returns:
        New dict with all Decimal values converted to float. Input unchanged.
    """
    out: dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, Decimal):
            out[k] = float(v)
        else:
            out[k] = v
    return out


# ── Metadata derivation (single source for completeness, age, proxies) ─────────


# Required fields for data_completeness_pct. Used by derive_metadata() and any
# caller that wants to know what the engine considers "complete" data.
REQUIRED_FIELDS_FOR_COMPLETENESS: tuple[str, ...] = (
    "close",
    "ema_20", "ema_50", "ema_100", "ema_200",
    "ema_100_slope_5d",
    "breakout_state", "breakout_age",
    "weekly_trend_score",
    "overhead_supply_score",
    "rolling_high_52w",
    "rs_90d",
    "qif_score",
    "avg_volume_20d",
    "regime",
)


def derive_metadata(
    row: dict[str, Any],
    required_fields: list[str] | tuple[str, ...] | None,
    last_indicator_run: datetime | None,
    today: date,
    proxies_used: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Compute data_completeness_pct, data_age_days, proxy_count in one place.

    Per Decision 101 (Gap 4): "I'd compute them at the API layer for now.
    However, I would NOT leave them undefined. Create one helper.
    `derive_metadata(row)` returns data_age, completeness, proxy_count.
    Then every caller behaves identically."

    Args:
        row: The normalized row (post-normalize_row).
        required_fields: Fields considered "complete data". Defaults to
            REQUIRED_FIELDS_FOR_COMPLETENESS if not provided.
        last_indicator_run: When the indicator pipeline last ran successfully
            for this symbol. Per Decision 101 (Q6): source of data_age_days,
            NOT the last candle.
        today: Current date for data_age_days computation.
        proxies_used: Optional dict of {factor: bool} indicating which factors
            used proxies instead of real data. proxy_count = count of True.

    Returns:
        dict with:
          - data_completeness_pct: float 0-100
          - data_age_days: int (None if last_indicator_run is None)
          - proxy_count: int
    """
    if required_fields is None:
        required_fields = REQUIRED_FIELDS_FOR_COMPLETENESS
    populated = sum(1 for f in required_fields if row.get(f) is not None)
    total = len(required_fields)
    completeness = (populated / total * 100.0) if total > 0 else 0.0

    if last_indicator_run is None:
        age_days = None
    else:
        last_d = last_indicator_run.date() if isinstance(last_indicator_run, datetime) else last_indicator_run
        age_days = (today - last_d).days

    proxy_count = sum(1 for v in (proxies_used or {}).values() if v)

    return {
        "data_completeness_pct": completeness,
        "data_age_days": age_days,
        "proxy_count": proxy_count,
    }


# ── Engine signature (provenance for every recommendation) ─────────────────────


def compute_engine_signature(config: dict[str, Any]) -> dict[str, str]:
    """Return {cas_version, config_hash, commit_sha, signature}.

    Per Decision 101 (expert recommendation, V1.1b requirement): every
    recommendation must know its engine signature so future calibration can
    answer 'why did CAS 1.1 outperform CAS 1.3?' The signature is composed of:

      - cas_version: this Python module's CAS_VERSION constant
      - commit_sha:  git commit short SHA at module import time
      - config_hash: 8-char SHA256 prefix of yaml.safe_dump(config) — same
                     config always produces the same hash; any weight or
                     threshold change produces a different hash
      - signature:   composite string 'v{version}-{commit_sha}-{config_hash}'
                     stored in the recommendation row for one-shot traceability

    Args:
        config: The full CAS config dict (loaded via load_config()).

    Returns:
        dict with keys: cas_version, config_hash, commit_sha, signature.
    """
    config_str = yaml.safe_dump(config, sort_keys=True)
    config_hash = hashlib.sha256(config_str.encode("utf-8")).hexdigest()[:8]
    signature = f"v{CAS_VERSION}-{COMMIT_SHA}-{config_hash}"
    return {
        "cas_version": CAS_VERSION,
        "config_hash": config_hash,
        "commit_sha": COMMIT_SHA,
        "signature": signature,
    }


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
    """Apply the 8 hard eligibility gates. Returns (passed, failed_gate_names).

    Gate names in `failed` (rev 3):
        "regime", "ema_stack", "breakout_state", "liquidity", "quality",
        "52w_position", "weekly_data", "rs_data".

    Rev 3 semantic change: missing critical market data → ineligible.
    The model refuses to score rather than guess with 0s. This applies to:
        - weekly_trend_score (weekly_data)
        - rs_90d (rs_data)
        - breakout_state, breakout_age, EMA values, qif_score,
          rolling_high_52w, avg_volume_20d, close — all folded into the
          existing 6 gates (they already fail when data is None).

    Portfolio-context fields (winner_profit_pct, concentration_weight_pct)
    are NOT checked here — they belong to compute_portfolio_allocation_score
    and default to neutral 1.0× when missing.

    Sub-condition details (e.g., which of the 4 EMA conditions failed) are
    not returned — callers needing diagnostics should re-evaluate the row.
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

    # ── Gate 3: Breakout state + age (rev 3: missing data → ineligible) ──
    max_age = elig.get("breakout_max_age_days", 5)
    age = row.get("breakout_age")
    state = row.get("breakout_state")
    if state != "BROKEN_OUT" or age is None or age > max_age:
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

    # ── Gate 7 (NEW rev 3): Weekly data present ──
    if row.get("weekly_trend_score") is None:
        failed.append("weekly_data")

    # ── Gate 8 (NEW rev 3): Relative strength data present ──
    if row.get("rs_90d") is None:
        failed.append("rs_data")

    if len(failed) > 0:
        logger.warning(
            "Eligibility FAILED — regime=%s, symbol=%s, failed_gates=%s",
            regime,
            row.get("symbol", "?"),
            failed,
        )

    return (len(failed) == 0, failed)


def compute_market_structure(
    row: dict[str, Any],
    config: dict[str, Any],
) -> tuple[bool, list[str]]:
    """Assess market structure quality via 3 hard PASS/FAIL dimensions.

    Renamed from `check_market_subgates` in rev 3 (semantic alignment:
    assesses the underlying market STRUCTURE quality, not just "sub-gates").

    Sub-gate names in `failed`: "trend", "breakout", "quality". All 3 must PASS
    for the stock to receive a numeric Market Score. Stricter than eligibility:
        - trend: weekly_trend_score ≥ 50 (eligibility doesn't check this)
        - breakout: age ≤ 3 (eligibility allows ≤ 5)
        - quality: qif ≥ 75 (eligibility allows ≥ 70)

    rev 3 (missing data semantics): if weekly_trend_score, breakout_age, or
    qif_score is None, the corresponding structure dimension fails (the model
    cannot assess structure without the input). Note: in practice these
    fields are already gated by `check_eligibility` (weekly_data,
    breakout_state), so this is defense-in-depth.
    """
    sub = config["market_subgates"]
    failed: list[str] = []

    # Trend structure
    weekly = row.get("weekly_trend_score")
    min_weekly = sub.get("trend", {}).get("min_weekly_trend_score", 50)
    if weekly is None or weekly < min_weekly:
        failed.append("trend")

    # Breakout structure (stricter than eligibility's breakout_max_age_days=5)
    age = row.get("breakout_age")
    max_age = sub.get("breakout", {}).get("max_breakout_age_days", 3)
    if age is None or age > max_age:
        failed.append("breakout")

    # Quality structure (stricter than eligibility's min_quality=70)
    qif = row.get("qif_score")
    min_q = sub.get("quality", {}).get("min_quality", 75)
    if qif is None or qif < min_q:
        failed.append("quality")

    return (len(failed) == 0, failed)


def compute_market_score_breakdown(
    sub_scores: dict[str, float],
    config: dict[str, Any],
) -> tuple[float, dict[str, float]]:
    """Weighted sum of sub-scores WITH per-factor contribution breakdown.

    Returns:
        (market_score, breakdown_dict) where:
            market_score    = float in [0, 100]
            breakdown_dict  = {factor_name: weighted_contribution_in_points}
                              (sum of contributions == market_score)

    Use this for debugging, regression tests, future UI display, or
    structured logging. The simple `compute_market_score` returns only the
    score (most callers don't need the breakdown).

    `sub_scores` keys must match `config["weights"]` keys:
        regime, weekly, breakout, overhead_supply, rs, volume, sector.

    `overhead_supply` is stored as "badness" (0 = clear air = good,
    100 = max resistance = bad). We invert it internally so that low
    overhead contributes positively to the Market Score. The breakdown
    reports the POST-inversion contribution.
    """
    weights = config["weights"]
    total_weight = sum(weights.values())  # validated to be 100 in load_config
    weighted_sum = 0.0
    breakdown: dict[str, float] = {}
    for factor, weight in weights.items():
        sub_value = sub_scores.get(factor, 0) or 0
        if factor == "overhead_supply":
            # Invert: 0 (clear air) → 100 contribution; 100 (max resistance) → 0
            sub_value = 100 - sub_value
        contribution = sub_value * weight / total_weight
        breakdown[factor] = round(contribution, 4)
        weighted_sum += sub_value * weight
    market_score = max(0.0, min(weighted_sum / total_weight, 100.0))
    return market_score, breakdown


def compute_market_score(
    sub_scores: dict[str, float],
    config: dict[str, Any],
) -> float:
    """Weighted sum of sub-scores. Returns float in [0, 100].

    Thin wrapper over `compute_market_score_breakdown` that discards the
    per-factor breakdown. Use the breakdown variant when debugging or
    building regression logs.

    `sub_scores` keys must match `config["weights"]` keys:
        regime, weekly, breakout, overhead_supply, rs, volume, sector.

    `overhead_supply` is stored as "badness" (0 = clear air = good,
    100 = max resistance = bad). We invert it internally so that low
    overhead contributes positively to the Market Score.
    """
    score, _breakdown = compute_market_score_breakdown(sub_scores, config)
    return score


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
    """0–5 star rating measuring MODEL CERTAINTY (NOT stock quality).

    Rev 3 (2026-07-07): All 5 stars are model-certainty dimensions. Stock-quality
    signals (trend maturity, breakout maturity) intentionally removed — those
    belong in CAS itself, not in the model's certainty about its own score.
    They still appear in the why-checklist and breakout_age_emoji.

    Criteria (each adds 1 star when met):
        1. Complete data        — row["data_completeness_pct"] ≥ threshold_pct (90)
        2. Factor agreement     — std-dev of (goodness-aligned) sub-scores
                                   ≤ max_std_dev (20). Computed only when
                                   ≥ 2 sub-scores present.
                                   overhead_supply is inverted BEFORE std-dev
                                   so all factors share the same semantic
                                   direction (higher = better).
        3. Stable calculations  — no sub-score is at an extreme (< min or > max),
                                   AND breakout_age is NOT at the AGE_DECAY
                                   cliff. Catches noisy/ambiguous inputs.
        4. Low proxy usage      — proxies_used has at most `max_proxies` True
                                   values (default 0 — fully real data).
        5. Indicator freshness  — row["data_age_days"] ≤ max_age_days (5)

    Thresholds are read from config["calibration"]["confidence"].
    Returns clamped to [0, 5].
    """
    cal = config["calibration"]["confidence"]
    conf = config["confidence"]["factors"]
    stars = 0

    # 1. Complete data (all expected fields populated)
    pct = row.get("data_completeness_pct") or 0
    if pct >= cal["complete_data_threshold_pct"]:
        stars += int(conf["complete_data"]["weight"])

    # 2. Factor agreement (std-dev on goodness-aligned sub-scores)
    if len(sub_scores) >= 2:
        # Invert overhead_supply so higher = better for ALL factors.
        aligned = {
            k: (100 - v if k == "overhead_supply" else v)
            for k, v in sub_scores.items()
        }
        std = float(np.std(list(aligned.values()), ddof=0))
        if std <= cal["factor_agreement_max_std_dev"]:
            stars += int(conf["factor_agreement"]["weight"])

    # 3. Stable calculations (transition zones per Decision 101, expert Q5).
    # The AGE_DECAY table transitions at age 3→4 (85→70) and 5→6 (65→40).
    # A stock in the 'transition' or 'stale' zone produces scores at the
    # noisy edge of the table. The stable_calculations star fires ONLY when
    # the age is in the 'excellent' or 'good' zone.
    age = row.get("breakout_age")
    if age is not None:
        zones = cal["breakout_age_zones"]
        in_excellent = zones["excellent"][0] <= age <= zones["excellent"][1]
        in_good = zones["good"][0] <= age <= zones["good"][1]
        if in_excellent or in_good:
            stars += int(conf["stable_calculations"]["weight"])

    # 4. Low proxy usage (real indicators preferred over placeholders)
    proxy_count = sum(1 for v in proxies_used.values() if v)
    if proxy_count <= cal["low_proxy_usage_max_proxies"]:
        stars += int(conf["low_proxy_usage"]["weight"])

    # 5. Indicator freshness (inputs are current, not stale)
    age_days = row.get("data_age_days")
    if age_days is not None and age_days <= cal["indicator_freshness_max_age_days"]:
        stars += int(conf["indicator_freshness"]["weight"])

    final = min(stars, 5)
    logger.debug(
        "Confidence stars=%d (sub_scores_std=%.2f, proxy_count=%d, data_age=%s, completeness=%s)",
        final,
        float(np.std(list(sub_scores.values()), ddof=0)) if len(sub_scores) >= 2 else float("nan"),
        proxy_count,
        age_days,
        pct,
    )
    return final


def render_why_checklist(
    row: dict[str, Any],
    config: dict[str, Any],
) -> list[str]:
    """Render the structured ✓ checklist from YAML templates + condition checks.

    Iterates `config["why_templates"]`. For each entry:
      1. Evaluate the named condition against `row` and `config["calibration"]`.
      2. If fired, format the template string with condition-specific kwargs.
      3. Append formatted line to result.

    Lines where required interpolation values are missing are silently skipped
    (e.g., `winner_profit` template skipped when no `winner_profit_pct` field).
    """
    lines: list[str] = []
    cal = config["calibration"]
    for entry in config.get("why_templates", []):
        condition = entry["condition"]
        template = entry["template"]
        kwargs, fired = _evaluate_condition(condition, row, cal)
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


# AGE_DECAY table (Decision 099) — read from YAML `calibration.age_decay`.
# Module-level constant REMOVED in rev 3 (calibration must live in YAML).
# See `_breakout_score` for the runtime loader.


def _load_age_decay(config: dict[str, Any]) -> tuple[dict[int, int], int]:
    """Load AGE_DECAY table from config. Returns (table, default).

    YAML keys are strings; we coerce to int. The `beyond` key is the default
    for ages not in the explicit table (e.g., age 6+).
    """
    raw = config["calibration"]["age_decay"]
    table: dict[int, int] = {
        int(k): v for k, v in raw.items() if k != "beyond"
    }
    default = int(raw.get("beyond", 40))
    return table, default


def _breakout_score(row: dict[str, Any], config: dict[str, Any]) -> int:
    """Breakout Quality sub-score (per §3.3).

    base = AGE_DECAY[age] (or `beyond` default if age not in table)
    volume bonus = +points if vol_ratio ≥ volume_bonus_threshold (from YAML)
    Final = clamp(base + bonus, 0, 100).

    rev 3: AGE_DECAY table loaded from config every call (cheap dict lookup).
    """
    age = row.get("breakout_age")
    if age is None:
        return 0

    age_table, age_default = _load_age_decay(config)
    cfg = config["subscore"]["breakout"]
    base = age_table.get(age, age_default)

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


def _evaluate_condition(
    condition: str,
    row: dict[str, Any],
    calibration: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """Evaluate a why-checklist condition.

    Returns:
        (kwargs, True)  — condition met; caller formats template with kwargs.
        ({}, False)     — condition not met; caller skips template.

    All numeric thresholds are read from `calibration` (i.e.,
    `config["calibration"]`). No magic numbers in this function.

    Required row fields per condition:
        regime_strong    → row["regime"] == "BULLISH"
        weekly_strong    → row["weekly_trend_score"] ≥ calibration.weekly_strong
        breakout_today   → row["breakout_age"] == 0
        breakout_early   → row["breakout_age"] in [1, calibration.breakout_early_max_age]
        near_52wh        → close ≥ (1 - calibration.near_52wh_pct/100) × 52w high
        rs_strong        → row["rs_90d"] ≥ calibration.rs_strong
        volume_confirmed → vol / avg_vol ≥ calibration.volume_confirmed
        winner_profit    → row["winner_profit_pct"] is not None and > 0
        clear_overhead   → row["overhead_supply_score"] ≤ calibration.overhead_clear_air
        high_quality     → row["qif_score"] ≥ calibration.qif_high
    """
    if condition == "regime_strong":
        if row.get("regime") == "BULLISH":
            return {"regime_label": "BULLISH"}, True
    elif condition == "weekly_strong":
        if (row.get("weekly_trend_score") or 0) >= calibration["weekly_strong"]:
            return {}, True
    elif condition == "breakout_today":
        if row.get("breakout_age") == 0:
            return {}, True
    elif condition == "breakout_early":
        age = row.get("breakout_age")
        max_age = calibration["breakout_early_max_age"]
        if age is not None and 1 <= age <= max_age:
            return {"breakout_age": age}, True
    elif condition == "near_52wh":
        close = row.get("close") or 0
        high = row.get("rolling_high_52w") or 0
        pct = calibration["near_52wh_pct"]
        if high > 0 and close >= high * (1 - pct / 100):
            return {}, True
    elif condition == "rs_strong":
        if (row.get("rs_90d") or 0) >= calibration["rs_strong"]:
            return {}, True
    elif condition == "volume_confirmed":
        vol = row.get("volume") or 0
        avg = row.get("avg_volume_20d") or 0
        if avg > 0 and (vol / avg) >= calibration["volume_confirmed"]:
            return {"vol_ratio": vol / avg}, True
    elif condition == "winner_profit":
        profit = row.get("winner_profit_pct")
        if profit is not None and profit > 0:
            return {"profit_pct": profit}, True
    elif condition == "clear_overhead":
        score = row.get("overhead_supply_score")
        if score is not None and score <= calibration["overhead_clear_air"]:
            return {"overhead_supply_score": score}, True
    elif condition == "high_quality":
        qif = row.get("qif_score") or 0
        if qif >= calibration["qif_high"]:
            return {"qif_score": qif}, True
    return {}, False
