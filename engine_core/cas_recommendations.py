"""CAS Recommendation Recording & Outcome Tracking (V1.1b, Decision 101).

Two events per expert architectural review:

  Event A — Recommendation capture (immediate on API CAS computation):
    record_cas_recommendation() writes one row to cas_recommendations
    with full provenance (factor_snapshot JSONB + engine_signature).

  Event B — Daily EOD outcome update (separate cron, after market close):
    update_cas_outcomes() fills milestone prices at 7d / 14d / 28d /
    63d / 126d elapsed trading days. NOT calendar weeks — catches
    Friday→Monday gap events that weekly sampling misses.

Path tracking per Decision 101: every recommendation gets full
week 1 / week 2 / week 4 / month 3 / month 6 progression recorded,
plus max_favorable / max_adverse excursion since recommendation.

Recommendation ID format: CAS-YYYY-MM-DD-SYMBOL (deterministic,
human-readable, sortable — per Decision 101).
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, NamedTuple, Optional

from engine_core.capital_allocation import compute_engine_signature
from engine_core.db import get_connection

logger = logging.getLogger(__name__)


# Public constants — exported for tests + callers
MILESTONE_DAYS: dict[str, int] = {
    "w1": 7,
    "w2": 14,
    "w4": 28,
    "m3": 63,
    "m6": 126,
}

REQUIRED_FACTOR_KEYS: tuple[str, ...] = (
    "weekly", "breakout", "volume", "rs",
    "overhead_supply", "regime", "sector",
    "weekly_trend_score", "breakout_age", "overhead_supply_score",
    "rs_90d", "avg_volume_20d", "close",
)


# ===========================================================================
# Decision 103 V2 Pyramiding Discipline — gate result + action result types
# ===========================================================================

class GateResult(NamedTuple):
    """Result of `evaluate_add_gates()` (Decision 103).

    Attributes:
        gates_passed:   how many of the 6 checks passed (G1–G5 + confidence)
        gates_total:    total checks evaluated (always 6 for the V2 model)
        blocked_gates:  machine-readable codes for the failed checks,
                        empty list when all pass
        gate_score_pct: 0–100, gates_passed / gates_total × 100, rounded to 1 dp
    """

    gates_passed: int
    gates_total: int
    blocked_gates: list[str]
    gate_score_pct: float


class ActionResult(NamedTuple):
    """Result of `compute_action()` (Decision 103).

    Replaces the legacy `str` return type. `final_state` is the V2
    4-state model label, or None when gate_inputs was not provided
    (legacy compatibility — see `compute_action` docstring).

    Attributes:
        action:        'BUY' | 'ADD' | 'WATCH'
        final_state:   'OBSERVE' | 'APPROACHING_ADD' | 'READY_FOR_ADD' |
                       'ADD_SECOND_TRANCHE' | None
        blocked_gates: from GateResult, [] when all pass
    """

    action: str
    final_state: Optional[str]
    blocked_gates: list[str]


# Gate failure codes (machine-readable, used in factor_snapshot.blocked_gates
# and surfaced in the UI/API for debugging).
GATE_BLOCK_CODES: tuple[str, ...] = (
    "G1_DECISION_SCORE_BELOW_MIN",
    "G2_MRI_TECHNICAL_BELOW_MIN",
    "G3_WEEKLY_CLOSE_BELOW_RESISTANCE",
    "G4_VOLUME_NOT_CONFIRMED",
    "G5_BREAKOUT_AGE_TOO_OLD",
    "CONFIDENCE_STARS_BELOW_MIN",
)


# ===========================================================================
# Pure helpers
# ===========================================================================

def make_recommendation_id(rec_date: Any, symbol: str) -> str:
    """Build recommendation_id in CAS-YYYY-MM-DD-SYMBOL format.

    Accepts date, datetime, or ISO date string. Symbol is normalized
    to uppercase. Deterministic — same inputs always produce same ID.
    """
    if isinstance(rec_date, str):
        rec_date = date.fromisoformat(rec_date)
    elif isinstance(rec_date, datetime):
        rec_date = rec_date.date()
    elif not isinstance(rec_date, date):
        raise TypeError(f"rec_date must be date, datetime, or ISO string, got {type(rec_date)}")
    return f"CAS-{rec_date.isoformat()}-{symbol.upper()}"


def evaluate_add_gates(
    gate_inputs: dict[str, Any] | None,
    config: dict[str, Any],
) -> GateResult:
    """Evaluate the 5 ADD_SECOND_TRANCHE gates + confidence stars.

    Decision 103 P3: pure helper, all thresholds read from YAML.

    Args:
        gate_inputs: dict with these optional keys:
            - decision_score             (float)  — G1 (≥ decision_score_min)
            - mri_technical_score        (float)  — G2 (≥ mri_technical_min)
            - weekly_close_above_resistance (bool) — G3 (must be True)
            - volume_confirmed_breakout  (bool)   — G4 (must be True)
            - breakout_age               (int)    — G5 (≤ breakout_age_max)
            - confidence_stars           (int)    — confidence (≥ confidence_stars_min)

            Missing keys count as 'not passed' (defensive: never auto-pass).

            Pass `None` to fall back to legacy behavior (assume all 6 pass).
            This keeps the V1.1d behavior for callers that haven't migrated
            to the V2 gate model yet.

        config: full CAS config dict (must be loaded via load_config).
                Reads `add_gate.decision_score_min`, `add_gate.mri_technical_min`,
                `add_gate.breakout_age_max`, `add_gate.confidence_stars_min`.

    Returns:
        GateResult(gates_passed, gates_total, blocked_gates, gate_score_pct).
    """
    if gate_inputs is None:
        # Legacy compatibility path: assume all 6 checks pass so the
        # V1.1d CAS+stars behavior is preserved exactly.
        return GateResult(6, 6, [], 100.0)

    add_gate = config.get("add_gate", {})
    g1_min = add_gate.get("decision_score_min", 85)
    g2_min = add_gate.get("mri_technical_min", 80)
    g5_max = add_gate.get("breakout_age_max", 15)
    conf_min = add_gate.get("confidence_stars_min", 4)

    blocked: list[str] = []

    # G1: decision_score ≥ threshold
    ds = gate_inputs.get("decision_score")
    if ds is None or not isinstance(ds, (int, float)) or ds < g1_min:
        blocked.append(GATE_BLOCK_CODES[0])

    # G2: mri_technical_score ≥ threshold
    mts = gate_inputs.get("mri_technical_score")
    if mts is None or not isinstance(mts, (int, float)) or mts < g2_min:
        blocked.append(GATE_BLOCK_CODES[1])

    # G3: weekly close strictly above resistance
    wcar = gate_inputs.get("weekly_close_above_resistance")
    if wcar is not True:
        blocked.append(GATE_BLOCK_CODES[2])

    # G4: breakout-day volume ≥ 1.3× 20d average
    vcb = gate_inputs.get("volume_confirmed_breakout")
    if vcb is not True:
        blocked.append(GATE_BLOCK_CODES[3])

    # G5: breakout_age ≤ 15 trading days
    ba = gate_inputs.get("breakout_age")
    if ba is None or not isinstance(ba, int) or ba > g5_max:
        blocked.append(GATE_BLOCK_CODES[4])

    # Confidence stars ≥ threshold
    stars = gate_inputs.get("confidence_stars")
    if stars is None or not isinstance(stars, int) or stars < conf_min:
        blocked.append(GATE_BLOCK_CODES[5])

    gates_total = 6
    gates_passed = gates_total - len(blocked)
    gate_score_pct = round(100.0 * gates_passed / gates_total, 1)

    return GateResult(gates_passed, gates_total, blocked, gate_score_pct)


def compute_action(
    cas_score: float,
    confidence_stars: int,
    has_existing_position: bool,
    config: dict[str, Any],
    gate_inputs: dict[str, Any] | None = None,
) -> ActionResult:
    """Map (cas_score, confidence_stars, position state, gates) → ActionResult.

    Decision 103 V2: extends the legacy 3-action model (BUY/ADD/WATCH) with
    a 4-state decision state (OBSERVE / APPROACHING_ADD / READY_FOR_ADD /
    ADD_SECOND_TRANCHE) plus a list of blocked gates.

    Layer 3 vocabulary (action):
      BUY   = first tranche / fresh position
      ADD   = adding to existing position
      WATCH = eligible but no action yet (or gates failed)

    Priority:
      1. If has_existing_position AND cas ≥ add_cas_min AND stars ≥ min_stars
         AND all 6 gates pass → ADD
      2. If has_existing_position AND cas ≥ add_cas_min AND stars ≥ min_stars
         BUT some gates fail → WATCH (degraded — final_state = READY_FOR_ADD)
      3. If cas ≥ buy_cas_min AND stars ≥ min_stars → BUY
      4. Else → WATCH

    The 4-state decision state (`final_state`):
      ADD_SECOND_TRANCHE — action == 'ADD' (all gates passed)
      READY_FOR_ADD     — cas ≥ add_cas_min but some gate failed
      APPROACHING_ADD   — 80 ≤ cas < add_cas_min
      OBSERVE           — cas < 80

    Backward compatibility:
      - When `gate_inputs is None`, the function falls back to legacy V1.1d
        behavior: action = BUY/ADD/WATCH based purely on CAS+stars, with
        `final_state = None` and `blocked_gates = []`. This keeps the
        existing 259 CAS tests green.
      - Return type changed from `str` to `ActionResult` (NamedTuple). Callers
        that need just the action should access `.action`. The two internal
        callers in this module have been updated; external callers should
        migrate to `compute_action(...).action`.

    Note: stars check applies to BOTH BUY and ADD. Even high CAS with
    low stars → WATCH (we don't act on uncertain signals).
    """
    a = config.get("action", {})
    buy_min = a.get("buy_cas_min", 80)
    add_min = a.get("add_cas_min", buy_min)  # default: ADD requires same CAS
    min_stars = a.get("min_confidence_stars_for_buy", 4)

    # Legacy action path (CAS+stars only)
    if cas_score >= max(buy_min, add_min) and confidence_stars >= min_stars:
        base_action = "ADD" if has_existing_position else "BUY"
    else:
        base_action = "WATCH"

    # V2 gate evaluation
    gate_result = evaluate_add_gates(gate_inputs, config)
    blocked_gates: list[str] = list(gate_result.blocked_gates)

    # Degrade ADD → WATCH if any gate failed (Decision 103 invariant: we
    # never recommend adding to a position when the gate evidence is incomplete).
    if base_action == "ADD" and blocked_gates:
        action = "WATCH"
    else:
        action = base_action

    # V2 4-state final_state (only computed when gate_inputs was provided)
    # Delegate to compute_layered_state for DRY — single source of truth.
    # (Previous inline derivation duplicated logic and missed the
    # READY_FOR_ADD branch for the BUY-without-position case.)
    final_state: Optional[str] = None
    if gate_inputs is not None:
        from engine_core.cas_decision_layer import compute_layered_state
        final_state = compute_layered_state(
            cas_score, blocked_gates, has_existing_position, config
        )

    return ActionResult(action, final_state, blocked_gates)


def compute_milestones_to_fill(
    elapsed_days: int,
    already_filled: list[str],
) -> list[str]:
    """Return milestone names (in order) that should be filled.

    Idempotent: excludes milestones already in already_filled.
    Does NOT raise on duplicates — caller should ensure
    already_filled is canonical (e.g., {"w1", "w2", ...}).
    """
    filled = set(already_filled)
    return [name for name, days in MILESTONE_DAYS.items()
            if elapsed_days >= days and name not in filled]


def compute_factor_snapshot(
    row: dict[str, Any],
    sub_scores: dict[str, float],
    regime: str,
    action: str,
    *,
    gate_result: "GateResult | None" = None,
    final_state: str | None = None,
    resistance_source: str | None = None,
    add_gate_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the factor_snapshot dict for JSONB storage.

    Per Decision 101 expert rec: store ACTUAL INPUTS, not just CAS=91.
    This lets us reconstruct historical state for drift analysis.
    Adding/removing sub-scores does NOT require DDL changes.

    Note on regime: stored as the STATE string ('BULLISH'/'BEARISH') under
    the key 'regime' so it can be filtered cleanly in dashboards. The
    regime sub-score is implied by the state (BULLISH=100, BEAR_TRANSITION
    = 50, BEARISH=0) and recoverable via _regime_score().

    Decision 103 V2 ADD gate inputs (all optional, backward-compatible):
      gate_result       — if provided, adds 'gates' (passed/total/blocked)
                          and 'gate_score_pct'
      final_state       — if provided, adds 'final_state' (V2 4-state label)
      resistance_source — if provided, adds 'resistance_source' (C9 enum)
      add_gate_config   — if provided, adds 'config_snapshot' (Decision 103 C5:
                          version + thresholds, so historical rows can be
                          reproduced even after threshold changes)
    """
    snap: dict[str, Any] = {
        # Sub-scores (the inputs to compute_market_score_breakdown)
        "weekly": sub_scores.get("weekly"),
        "breakout": sub_scores.get("breakout"),
        "volume": sub_scores.get("volume"),
        "rs": sub_scores.get("rs"),
        "overhead_supply": sub_scores.get("overhead_supply"),
        "regime": regime,                       # STATE string, not sub-score
        "regime_score": sub_scores.get("regime"),  # numeric sub-score
        "sector": sub_scores.get("sector"),
        # Raw indicator values (for drift / regression analysis)
        "weekly_trend_score": row.get("weekly_trend_score"),
        "breakout_age": row.get("breakout_age"),
        "overhead_supply_score": row.get("overhead_supply_score"),
        "rs_90d": row.get("rs_90d"),
        "avg_volume_20d": row.get("avg_volume_20d"),
        "close": row.get("close"),
        # Decision context
        "action": action,
    }

    # ── Decision 103 V2 ADD gate inputs ──────────────────────────────────
    if gate_result is not None:
        snap["gates"] = {
            "passed": gate_result.gates_passed,
            "total": gate_result.gates_total,
            "blocked": list(gate_result.blocked_gates),
        }
        snap["gate_score_pct"] = gate_result.gate_score_pct
    if final_state is not None:
        snap["final_state"] = final_state
    if resistance_source is not None:
        snap["resistance_source"] = resistance_source
    if add_gate_config is not None:
        # C5: persist the gate config that was active when this snapshot
        # was generated. Lets us reproduce historical gate decisions even
        # after the live YAML thresholds change.
        snap["config_snapshot"] = {
            "version": add_gate_config.get("version", "2.0.0"),
            "decision_score_min": add_gate_config.get("decision_score_min"),
            "mri_technical_min": add_gate_config.get("mri_technical_min"),
            "breakout_age_max": add_gate_config.get("breakout_age_max"),
            "breakout_volume_ratio": add_gate_config.get("breakout_volume_ratio"),
            "confidence_stars_min": add_gate_config.get("confidence_stars_min"),
        }

    return snap


def build_factor_snapshot(*args, **kwargs) -> dict[str, Any]:
    """Public alias for compute_factor_snapshot (for callers that prefer
    'build' verb). Identical behavior."""
    return compute_factor_snapshot(*args, **kwargs)


def compute_outcome_returns(
    price_at_rec: float | Decimal | None,
    milestone_prices: dict[str, float | Decimal | None],
) -> dict[str, float | None]:
    """Compute return_pct for each milestone relative to price_at_recommendation.

    Returns dict keyed by milestone name ('w1', 'w2', etc.).
    Returns None for missing prices OR zero/None base price
    (defensive: avoid Inf in stored data).
    """
    if price_at_rec is None or float(price_at_rec) == 0:
        return {k: None for k in MILESTONE_DAYS}

    base = float(price_at_rec)
    result: dict[str, float | None] = {}
    for name in MILESTONE_DAYS:
        px = milestone_prices.get(name)
        if px is None:
            result[name] = None
        else:
            result[name] = (float(px) / base - 1.0) * 100.0
    return result


def compute_outcome_status(
    milestones_reached: list[str],
    elapsed_days: int,
) -> str:
    """Map (milestones_reached, elapsed_days) → status string.

    Status values:
      'open'        = tracking (no terminal milestone reached)
      'closed-w4'   = w4 is the deepest reached (28d horizon terminal)
      'closed-m6'   = m6 is the deepest reached (126d horizon terminal)

    The semantic is: status reflects the DEEPEST milestone reached.
    If w4 is reached but m3/m6 not yet → "closed-w4" (terminal at
    28d horizon). If m3 is reached → "open" again because we're
    still tracking for m6. If m6 is reached → "closed-m6".
    """
    filled = set(milestones_reached)
    if "m6" in filled:
        return "closed-m6"
    if "w4" in filled and "m3" not in filled:
        return "closed-w4"
    return "open"


# ===========================================================================
# DB-touching functions
# ===========================================================================

def record_cas_recommendation(
    row: dict[str, Any],
    market_score: float,
    cas_score: float,
    confidence_stars: int,
    action: str,
    regime: str,
    sub_scores: dict[str, float],
    config: dict[str, Any],
    has_existing_position: bool = False,
    gate_inputs: dict[str, Any] | None = None,
) -> str:
    """Event A — Record a CAS recommendation (idempotent UPSERT).

    One row per (symbol, recommendation_date). If the API recomputes CAS
    for the same symbol on the same day, the latest computation wins.

    Args:
        row: full DB row (symbol, date, close, indicators...)
        market_score: pre-CAS market score (0-100)
        cas_score: CAS (0-100)
        confidence_stars: 0-5
        action: 'BUY' / 'ADD' / 'WATCH'
        regime: 'BULLISH' / 'BEARISH' / etc.
        sub_scores: dict of factor scores (weekly, breakout, volume, rs, overhead_supply, regime, sector)
        config: full CAS config dict (must be loaded via load_config)
        has_existing_position: whether user already holds this symbol
        gate_inputs: Decision 103 V2 ADD_SECOND_TRANCHE gate inputs (None
                     = legacy behavior; assume all gates pass). When provided,
                     the snapshot records gate_result + final_state +
                     config_snapshot for historical reproducibility.

    Returns:
        The recommendation_id string.
    """
    rec_date = row.get("date") or row.get("recommendation_date")
    if isinstance(rec_date, datetime):
        rec_date = rec_date.date()
    elif isinstance(rec_date, str):
        rec_date = date.fromisoformat(rec_date)

    symbol = row["symbol"]
    rid = make_recommendation_id(rec_date, symbol)
    sig = compute_engine_signature(config)

    # ── Decision 103 V2 gate evaluation + final_state derivation ───────────
    gate_result = evaluate_add_gates(gate_inputs, config)
    final_state: str | None = None
    if gate_inputs is not None:
        # Lazy import to avoid any circular import risk (cas_decision_layer
        # does not currently import cas_recommendations, but keeping this
        # local keeps the dependency direction explicit).
        from engine_core.cas_decision_layer import compute_layered_state
        final_state = compute_layered_state(
            cas_score, gate_result.blocked_gates, has_existing_position, config
        )
    resistance_source = row.get("resistance_source")
    add_gate_config = config.get("add_gate") if isinstance(config, dict) else None

    snap = compute_factor_snapshot(
        row, sub_scores, regime, action,
        gate_result=gate_result,
        final_state=final_state,
        resistance_source=resistance_source,
        add_gate_config=add_gate_config,
    )
    price = float(row.get("close") or 0)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO cas_recommendations (
                    recommendation_id, recommendation_date, symbol, regime,
                    market_score, cas, confidence_stars, action,
                    price_at_recommendation, factor_snapshot,
                    cas_version, config_hash, commit_sha, engine_signature
                ) VALUES (
                    %(rid)s, %(rec_date)s, %(symbol)s, %(regime)s,
                    %(market_score)s, %(cas)s, %(stars)s, %(action)s,
                    %(price)s, %(snap)s::jsonb,
                    %(cas_version)s, %(config_hash)s, %(commit_sha)s, %(signature)s
                )
                ON CONFLICT (symbol, recommendation_date) DO UPDATE SET
                    regime = EXCLUDED.regime,
                    market_score = EXCLUDED.market_score,
                    cas = EXCLUDED.cas,
                    confidence_stars = EXCLUDED.confidence_stars,
                    action = EXCLUDED.action,
                    price_at_recommendation = EXCLUDED.price_at_recommendation,
                    factor_snapshot = EXCLUDED.factor_snapshot,
                    cas_version = EXCLUDED.cas_version,
                    config_hash = EXCLUDED.config_hash,
                    commit_sha = EXCLUDED.commit_sha,
                    engine_signature = EXCLUDED.engine_signature,
                    created_at = NOW()
                """,
                {
                    "rid": rid,
                    "rec_date": rec_date,
                    "symbol": symbol,
                    "regime": regime,
                    "market_score": float(market_score),
                    "cas": float(cas_score),
                    "stars": int(confidence_stars),
                    "action": action,
                    "price": price,
                    "snap": json_dumps_safe(snap),
                    "cas_version": sig["cas_version"],
                    "config_hash": sig["config_hash"],
                    "commit_sha": sig["commit_sha"],
                    "signature": sig["signature"],
                },
            )
            # Insert empty outcome row if it doesn't exist.
            # Idempotent — subsequent calls don't reset filled milestones.
            cur.execute(
                """
                INSERT INTO cas_recommendation_outcomes (recommendation_id)
                VALUES (%(rid)s)
                ON CONFLICT (recommendation_id) DO NOTHING
                """,
                {"rid": rid},
            )
            conn.commit()

    logger.info("Recorded CAS recommendation %s (action=%s, cas=%.1f, stars=%d)",
                rid, action, cas_score, confidence_stars)
    return rid


def json_dumps_safe(obj: Any) -> str:
    """JSON-serialize with Decimal/date/datetime handling for JSONB."""
    import json as _json
    from decimal import Decimal as _Dec

    def default(o):
        if isinstance(o, _Dec):
            return float(o)
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")

    return _json.dumps(obj, default=default)


# ===========================================================================
# Outcome updates — Event B (called by daily EOD cron)
# ===========================================================================

def update_cas_outcomes(today: date) -> dict[str, int]:
    """Event B — Update outcomes for all open recommendations as of `today`.

    For each open recommendation:
      1. Compute elapsed trading days since recommendation_date
      2. Look up current close price
      3. Look up close prices at 7/14/28/63/126 trading days ago
         (for milestone prices)
      4. Fill unfilled milestones
      5. Compute max_favorable / max_adverse excursion since recommendation
      6. Update status, milestones_reached, updated_at

    Args:
        today: the date to update for (typically max(daily_prices.date))

    Returns:
        Stats dict: {'recommendations_processed': int,
                     'milestones_filled': int,
                     'closed_w4': int,
                     'closed_m6': int}
    """
    stats = {
        "recommendations_processed": 0,
        "milestones_filled": 0,
        "closed_w4": 0,
        "closed_m6": 0,
    }

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Fetch all open recommendations
            cur.execute(
                """
                SELECT r.recommendation_id, r.symbol, r.recommendation_date,
                       r.price_at_recommendation, o.milestones_reached, o.status
                FROM cas_recommendations r
                JOIN cas_recommendation_outcomes o USING (recommendation_id)
                WHERE r.recommendation_date <= %s
                  AND o.status NOT IN ('closed-m6')
                ORDER BY r.recommendation_date
                """,
                (today,),
            )
            recs = cur.fetchall()

            for rec in recs:
                rid = rec["recommendation_id"]
                symbol = rec["symbol"]
                rec_date = rec["recommendation_date"]
                price_at_rec = float(rec["price_at_recommendation"])
                already = list(rec["milestones_reached"] or [])

                # Compute elapsed trading days from a count of daily_prices rows
                cur.execute(
                    """
                    SELECT COUNT(*) AS n FROM daily_prices
                    WHERE symbol = %s AND date > %s AND date <= %s
                    """,
                    (symbol, rec_date, today),
                )
                elapsed_days = cur.fetchone()["n"]

                # Find milestone dates (trading-day offsets from rec_date)
                milestones = compute_milestones_to_fill(elapsed_days, already)
                if not milestones and elapsed_days < MILESTONE_DAYS["w1"]:
                    # No work to do, skip
                    continue

                # Build milestone → price map (only fill NEW ones)
                milestone_prices: dict[str, float | None] = {
                    name: None for name in MILESTONE_DAYS
                }
                for name in milestones:
                    target_day = MILESTONE_DAYS[name]
                    cur.execute(
                        """
                        SELECT close FROM daily_prices
                        WHERE symbol = %s AND date > %s
                        ORDER BY date ASC
                        OFFSET %s LIMIT 1
                        """,
                        (symbol, rec_date, target_day - 1),
                    )
                    row = cur.fetchone()
                    if row:
                        milestone_prices[name] = float(row["close"])

                # Current price (latest available close on or before today)
                cur.execute(
                    """
                    SELECT close FROM daily_prices
                    WHERE symbol = %s AND date <= %s
                    ORDER BY date DESC LIMIT 1
                    """,
                    (symbol, today),
                )
                cur_row = cur.fetchone()
                current_price = float(cur_row["close"]) if cur_row else None

                # Compute max favorable / adverse excursion since rec_date
                cur.execute(
                    """
                    SELECT MAX(high) AS max_high, MIN(low) AS min_low
                    FROM daily_prices
                    WHERE symbol = %s AND date >= %s AND date <= %s
                    """,
                    (symbol, rec_date, today),
                )
                ext_row = cur.fetchone()
                mfe = (float(ext_row["max_high"]) / price_at_rec - 1.0) * 100.0 \
                    if ext_row and ext_row["max_high"] else None
                mae = (float(ext_row["min_low"]) / price_at_rec - 1.0) * 100.0 \
                    if ext_row and ext_row["min_low"] else None

                # Compute returns
                returns = compute_outcome_returns(price_at_rec, milestone_prices)

                # Merge milestones_reached
                new_filled = sorted(set(already) | set(milestones),
                                    key=lambda n: MILESTONE_DAYS[n])
                status = compute_outcome_status(new_filled, elapsed_days)

                # UPDATE the outcome row
                cur.execute(
                    """
                    UPDATE cas_recommendation_outcomes SET
                        current_price = %(current_price)s,
                        current_price_date = %(current_price_date)s,
                        price_w1 = COALESCE(%(price_w1)s, price_w1),
                        price_w2 = COALESCE(%(price_w2)s, price_w2),
                        price_w4 = COALESCE(%(price_w4)s, price_w4),
                        price_m3 = COALESCE(%(price_m3)s, price_m3),
                        price_m6 = COALESCE(%(price_m6)s, price_m6),
                        return_pct_w1 = COALESCE(%(return_w1)s, return_pct_w1),
                        return_pct_w2 = COALESCE(%(return_w2)s, return_pct_w2),
                        return_pct_w4 = COALESCE(%(return_w4)s, return_pct_w4),
                        return_pct_m3 = COALESCE(%(return_m3)s, return_pct_m3),
                        return_pct_m6 = COALESCE(%(return_m6)s, return_pct_m6),
                        max_favorable_excursion_pct = %(mfe)s,
                        max_adverse_excursion_pct = %(mae)s,
                        milestones_reached = %(filled)s::text[],
                        status = %(status)s,
                        updated_at = NOW()
                    WHERE recommendation_id = %(rid)s
                    """,
                    {
                        "current_price": current_price,
                        "current_price_date": today if current_price else None,
                        "price_w1": milestone_prices.get("w1"),
                        "price_w2": milestone_prices.get("w2"),
                        "price_w4": milestone_prices.get("w4"),
                        "price_m3": milestone_prices.get("m3"),
                        "price_m6": milestone_prices.get("m6"),
                        "return_w1": returns.get("w1"),
                        "return_w2": returns.get("w2"),
                        "return_w4": returns.get("w4"),
                        "return_m3": returns.get("m3"),
                        "return_m6": returns.get("m6"),
                        "mfe": mfe,
                        "mae": mae,
                        "filled": new_filled,
                        "status": status,
                        "rid": rid,
                    },
                )

                stats["recommendations_processed"] += 1
                stats["milestones_filled"] += len(milestones)
                if status == "closed-w4":
                    stats["closed_w4"] += 1
                elif status == "closed-m6":
                    stats["closed_m6"] += 1

            conn.commit()

    logger.info("update_cas_outcomes(%s): processed=%d, milestones=%d, closed_w4=%d, closed_m6=%d",
                today, stats["recommendations_processed"], stats["milestones_filled"],
                stats["closed_w4"], stats["closed_m6"])
    return stats


# ===========================================================================
# Daily scanner — record recommendations for every eligible stock
# ===========================================================================
# Per Decision 101 expert pushback: outcomes must be captured for EVERY
# eligible stock, not just BUY/ADD recommendations. Otherwise calibration
# analysis misses the WATCH cases (which is half the data).
#
# This function iterates all symbols with recent data, computes CAS, and
# records the recommendation (BUY/ADD/WATCH) for every eligible stock.
# It's designed to be called once per trading day, BEFORE the outcome
# updater. Calling it more often is harmless (idempotent UPSERT per day).


def _latest_row_per_symbol(as_of: date) -> list[dict[str, Any]]:
    """Return one row per symbol — the latest as of `as_of`.

    Sorted by symbol for stable test ordering. The first 10 symbols
    alphabetically are often non-eligible (e.g., 500xxx codes that
    don't have CAS-quality history). For testing, prefer using
    golden case symbols or passing `limit`.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (symbol) symbol, date, close, open, high, low,
                       volume, ema_10, ema_20, ema_50, ema_100, ema_200,
                       ema_100_slope_5d, ema_200_slope_20, rsi_14,
                       rolling_high_6m, rolling_high_52w, weekly_trend_score,
                       overhead_supply_score, breakout_state, breakout_age,
                       avg_volume_20d, rs_90d, rs_21d, rs_63d
                FROM daily_prices
                WHERE date <= %s
                ORDER BY symbol, date DESC
                """,
                (as_of,),
            )
            return [dict(r) for r in cur.fetchall()]


def _enrich_row_with_extras(row: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Add regime, qif_score, proxies_used, data_completeness to a raw row.

    Regime: read from a separate 'regime' table or pass-through.
    qif_score: from qif-related table or row.get('qif_score', 0).
        If missing, default to the eligibility minimum (70) and flag in
        proxies_used['qif']. This lets the scanner record outcomes for
        stocks whose QIF isn't yet joined. V1.1c will wire proper joins.
    proxies_used: dict of which sub-scores used fallback proxies.
    data_completeness_pct: percent of required fields present.
    """
    enriched = dict(row)
    enriched.setdefault("regime", "BULLISH")
    proxies: dict[str, Any] = {}

    # qif_score handling: if missing, use proxy value. The structure gate
    # uses market_subgates.quality.min_quality (75) which is STRICTER than
    # the eligibility min (70). Using 75 lets us pass both gates while
    # flagging the proxy so calibration analysis can exclude proxied data.
    if enriched.get("qif_score") is None:
        proxy_q = (
            config.get("market_subgates", {}).get("quality", {}).get("min_quality", 75)
        )
        enriched["qif_score"] = proxy_q
        proxies["qif"] = f"proxy={proxy_q} (QIF not yet joined; V1.1c will fix)"

    enriched.setdefault("winner_profit_pct", None)
    enriched.setdefault("concentration_weight_pct", None)
    enriched["proxies_used"] = proxies

    # data_completeness_pct — count of present required fields × 100 / total
    required = ("close", "ema_10", "ema_20", "ema_50", "ema_100",
                "ema_100_slope_5d", "breakout_state", "breakout_age",
                "weekly_trend_score", "overhead_supply_score", "rolling_high_52w",
                "rs_90d", "avg_volume_20d", "regime", "qif_score")
    present = sum(1 for f in required if enriched.get(f) is not None)
    enriched["data_completeness_pct"] = round(present / len(required) * 100, 1)
    enriched["data_age_days"] = 0  # scanner only fetches latest
    return enriched


def scan_and_record_eligible_recommendations(
    as_of: date,
    config: dict[str, Any],
    limit: int | None = None,
) -> dict[str, int]:
    """Scan every symbol, compute CAS, record recommendation if eligible.

    Records ONE recommendation per symbol per day (idempotent UPSERT).
    Captures BUY/ADD/WATCH — never skips eligible stocks just because
    the action is WATCH. (Decision 101 expert pushback.)

    Args:
        as_of: date to compute recommendations for.
        config: full CAS config dict (loaded via load_config).
        limit: optional cap on number of symbols to scan (for testing).

    Returns:
        Stats: {'symbols_scanned': int, 'recommendations_recorded': int,
                'buy_count': int, 'add_count': int, 'watch_count': int,
                'ineligible_count': int}
    """
    from engine_core.capital_allocation import (
        normalize_row, check_eligibility, compute_market_structure,
        compute_market_score_breakdown, compute_portfolio_allocation_score,
        compute_confidence_stars, _regime_score, _weekly_score,
        _breakout_score, _rs_score, _volume_score, _sector_score,
    )

    stats = {
        "symbols_scanned": 0,
        "recommendations_recorded": 0,
        "buy_count": 0,
        "add_count": 0,
        "watch_count": 0,
        "ineligible_count": 0,
    }

    rows = _latest_row_per_symbol(as_of)
    if limit:
        rows = rows[:limit]

    for raw_row in rows:
        stats["symbols_scanned"] += 1
        row = normalize_row(_enrich_row_with_extras(raw_row, config))
        regime = row.get("regime", "BULLISH")

        # Eligibility gate
        elig_ok, elig_failed = check_eligibility(row, regime, config)
        if not elig_ok:
            stats["ineligible_count"] += 1
            continue

        # Market structure sub-gates
        struct_ok, struct_failed = compute_market_structure(row, config)
        if not struct_ok:
            stats["ineligible_count"] += 1
            continue

        # Compute sub-scores
        sub_scores = {
            "regime": _regime_score(regime, config),
            "weekly": _weekly_score(row, config),
            "breakout": _breakout_score(row, config),
            "overhead_supply": float(row.get("overhead_supply_score") or 50),
            "rs": _rs_score(row, config),
            "volume": _volume_score(row, config),
            "sector": _sector_score(row, config),
        }
        market_score, _breakdown = compute_market_score_breakdown(sub_scores, config)
        cas = compute_portfolio_allocation_score(
            market_score,
            winner_profit_pct=row.get("winner_profit_pct"),
            concentration_weight_pct=row.get("concentration_weight_pct"),
            config=config,
        )
        stars = compute_confidence_stars(
            row, sub_scores, row.get("proxies_used", {}), config
        )

        # Action verb (BUY/ADD/WATCH — V1.1c will add NO_ACTION path).
        # Decision 103 P3c: compute_action now returns ActionResult. The
        # scanner passes `gate_inputs=None` to keep V1.1d legacy behavior
        # (final_state will be None). Future P5 frontend work will pass
        # real gate inputs from the new daily_prices columns.
        action = compute_action(
            cas, stars, has_existing_position=False,
            config=config, gate_inputs=None,
        ).action

        record_cas_recommendation(
            row=row,
            market_score=market_score,
            cas_score=cas,
            confidence_stars=stars,
            action=action,
            regime=regime,
            sub_scores=sub_scores,
            config=config,
            has_existing_position=False,
        )

        stats["recommendations_recorded"] += 1
        if action == "BUY":
            stats["buy_count"] += 1
        elif action == "ADD":
            stats["add_count"] += 1
        else:
            stats["watch_count"] += 1

    logger.info(
        "scan_and_record_eligible_recommendations(%s): scanned=%d, recorded=%d "
        "(buy=%d, add=%d, watch=%d), ineligible=%d",
        as_of, stats["symbols_scanned"], stats["recommendations_recorded"],
        stats["buy_count"], stats["add_count"], stats["watch_count"],
        stats["ineligible_count"],
    )
    return stats
