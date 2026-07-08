"""CAS V1.1c — Decision Layer.

Per Decision 101 expert feedback (2026-07-08):

    Hysteresis applies to ACTION only, NOT to Confidence/Stars.
    Compare decision tiers (NO_ACTION < WATCH < FIRST_TRANCHE < ADD_SECOND_TRANCHE),
    NOT just CAS deltas.
    NO_ACTION has THREE triggers: no eligible, top-N empty, best CAS < deployment threshold.
    Recommendation Lifecycle: NEW → ACTIVE → MATURED → ARCHIVED.

Design philosophy:
    "A recommendation is a scientific hypothesis.
     Calibration is the process of proving or disproving that hypothesis using observed outcomes."

This module is PURE LOGIC — no DB, no I/O. Tested in test_cas_decision_layer.py.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Optional

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

STABILITY_UPGRADED = "UPGRADED"
STABILITY_DOWNGRADED = "DOWNGRADED"
STABILITY_UNCHANGED = "UNCHANGED"
STABILITY_NEW = "NEW"

# Tier ordering (per expert feedback)
TIER_ORDER = ["NO_ACTION", "WATCH", "FIRST_TRANCHE", "ADD_SECOND_TRANCHE"]

# Map DB action enum → tier name
ACTION_TIER_MAP = {
    "NO_ACTION": "NO_ACTION",
    "WATCH": "WATCH",
    "BUY": "FIRST_TRANCHE",
    "ADD": "ADD_SECOND_TRANCHE",
}

# Map tier name → DB action enum
TIER_ACTION_MAP = {tier: action for action, tier in ACTION_TIER_MAP.items()}

# Tier CAS thresholds (lower bound of each tier)
TIER_CAS_THRESHOLDS = {
    "WATCH": 60.0,
    "FIRST_TRANCHE": 80.0,
    "ADD_SECOND_TRANCHE": 85.0,
}

# Lifecycle states
LIFECYCLE_NEW = "NEW"
LIFECYCLE_ACTIVE = "ACTIVE"
LIFECYCLE_MATURED = "MATURED"
LIFECYCLE_ARCHIVED = "ARCHIVED"

# NO_ACTION reasons (machine-readable codes)
NO_ACTION_REASON_NO_ELIGIBLE = "NO_ELIGIBLE_STOCKS"
NO_ACTION_REASON_TOP_N_EMPTY = "TOP_N_EMPTY"
NO_ACTION_REASON_BELOW_DEPLOYMENT = "BELOW_DEPLOYMENT_THRESHOLD"

# All milestones that must be filled for MATURED
ALL_MILESTONES = ("w1", "w2", "w4", "m3", "m6")
ARCHIVE_AGE_DAYS = 180


# ----------------------------------------------------------------------------
# Tier <-> action helpers
# ----------------------------------------------------------------------------

def cas_to_tier(cas: float | None) -> str:
    """Map a CAS score to its decision tier.

    Tier boundaries (default, override via config['decision_layer']['tier_thresholds']):
        NO_ACTION:        CAS < 60
        WATCH:            60 <= CAS < 80
        FIRST_TRANCHE:    80 <= CAS < 85
        ADD_SECOND_TRANCHE: CAS >= 85
    """
    if cas is None or cas < TIER_CAS_THRESHOLDS["WATCH"]:
        return "NO_ACTION"
    if cas < TIER_CAS_THRESHOLDS["FIRST_TRANCHE"]:
        return "WATCH"
    if cas < TIER_CAS_THRESHOLDS["ADD_SECOND_TRANCHE"]:
        return "FIRST_TRANCHE"
    return "ADD_SECOND_TRANCHE"


def tier_to_action(tier: str) -> str:
    """Map tier name back to DB action enum (BUY/ADD/WATCH/NO_ACTION)."""
    if tier not in TIER_ACTION_MAP:
        raise ValueError(f"Unknown tier: {tier!r}. Must be one of {TIER_ORDER}")
    return TIER_ACTION_MAP[tier]


# ----------------------------------------------------------------------------
# stabilize_action — tier-based hysteresis (API-only, never persisted)
# ----------------------------------------------------------------------------

def stabilize_action(
    prev_action: Optional[str],
    current_action: str,
    prev_cas: Optional[float],
    current_cas: float,
    hysteresis_cas: float = 3.0,
) -> dict[str, str]:
    """Apply tier-based hysteresis to the current action.

    Rules (per expert feedback):
      - BOTH upgrades and downgrades are DAMPENED by `hysteresis_cas`.
        An upgrade (e.g., WATCH→FIRST_TRANCHE) is only applied if
        `current_cas >= new_tier_threshold + hysteresis`.
        A downgrade is only applied if
        `current_cas < new_tier_threshold - hysteresis`.
        This prevents oscillation around tier boundaries (e.g., "84→85
        shouldn't necessarily upgrade").
      - CONFIDENCE/STARS are NEVER touched here. They are computed
        from today's data and returned separately by the API layer.

    Returns:
        Dict with 'action' and 'stability' keys. Stability is one of:
            UPGRADED, DOWNGRADED, UNCHANGED, NEW.
    """
    # Resolve prev to tier index (default to NO_ACTION if missing)
    if prev_action is None or prev_action not in TIER_ORDER and prev_action not in ACTION_TIER_MAP:
        prev_tier_idx = 0  # NO_ACTION
    else:
        prev_tier_name = ACTION_TIER_MAP.get(prev_action, prev_action)
        prev_tier_idx = TIER_ORDER.index(prev_tier_name)

    curr_tier_name = ACTION_TIER_MAP.get(current_action, "NO_ACTION")
    curr_tier_idx = TIER_ORDER.index(curr_tier_name)

    # No prev data → NEW
    if prev_cas is None or prev_action is None:
        return {"action": current_action, "stability": STABILITY_NEW}

    # Same tier → UNCHANGED
    if curr_tier_idx == prev_tier_idx:
        return {"action": current_action, "stability": STABILITY_UNCHANGED}

    # Upgrade (higher tier): dampen unless current_cas is well above the
    # target tier's threshold (boundary + hysteresis). The expert wants
    # "84 → 85 shouldn't necessarily upgrade" — so upgrades are also gated.
    if curr_tier_idx > prev_tier_idx:
        target_threshold = TIER_CAS_THRESHOLDS[TIER_ORDER[curr_tier_idx]]
        if current_cas >= target_threshold + hysteresis_cas:
            return {"action": current_action, "stability": STABILITY_UPGRADED}
        prev_action_resolved = TIER_ACTION_MAP[TIER_ORDER[prev_tier_idx]]
        return {"action": prev_action_resolved, "stability": STABILITY_UNCHANGED}

    # Downgrade (lower tier): dampen unless current_cas is well below the
    # new tier's threshold (boundary - hysteresis).
    new_tier_name = TIER_ORDER[curr_tier_idx]
    new_tier_threshold = TIER_CAS_THRESHOLDS.get(new_tier_name, 0.0)

    # If we're trying to downgrade to NO_ACTION, use the WATCH threshold
    # (NO_ACTION has no explicit threshold; it's "anything below WATCH")
    if new_tier_name == "NO_ACTION":
        new_tier_threshold = TIER_CAS_THRESHOLDS["WATCH"]

    if current_cas < new_tier_threshold - hysteresis_cas:
        # Comfortably below — allow downgrade
        return {"action": current_action, "stability": STABILITY_DOWNGRADED}

    # Within hysteresis band — stay at prev tier
    prev_action_resolved = TIER_ACTION_MAP[TIER_ORDER[prev_tier_idx]]
    return {"action": prev_action_resolved, "stability": STABILITY_UNCHANGED}


# ----------------------------------------------------------------------------
# NO_ACTION decision
# ----------------------------------------------------------------------------

def should_return_no_action(
    n_eligible: int,
    n_top_n: int,
    best_eligible_cas: Optional[float],
    min_deployable_cas: float,
) -> dict[str, Any]:
    """Decide whether to return NO_ACTION for today's recommendations.

    Three triggers (per expert feedback):
      1. No eligible stocks at all.
      2. Top-N list is empty (even if eligible exist).
      3. Best eligible CAS is below the deployment threshold.

    Returns:
        Dict with:
          - 'is_no_action' (bool)
          - 'reason' (machine-readable code) or None
          - 'reason_text' (human-readable) or None
    """
    if n_eligible == 0:
        return {
            "is_no_action": True,
            "reason": NO_ACTION_REASON_NO_ELIGIBLE,
            "reason_text": "No stocks passed eligibility today.",
        }

    if n_top_n == 0:
        return {
            "is_no_action": True,
            "reason": NO_ACTION_REASON_TOP_N_EMPTY,
            "reason_text": "Eligible stocks exist but Top-N is empty.",
        }

    if best_eligible_cas is None:
        raise ValueError(
            "n_eligible > 0 but best_eligible_cas is None. "
            "Either pass the best CAS or set n_eligible=0."
        )

    if best_eligible_cas < min_deployable_cas:
        return {
            "is_no_action": True,
            "reason": NO_ACTION_REASON_BELOW_DEPLOYMENT,
            "reason_text": (
                f"No opportunity met the deployment threshold. "
                f"Best eligible CAS {best_eligible_cas:.1f} < "
                f"min deployable {min_deployable_cas:.1f}."
            ),
        }

    return {"is_no_action": False, "reason": None, "reason_text": None}


# ----------------------------------------------------------------------------
# Recommendation Lifecycle
# ----------------------------------------------------------------------------

def compute_recommendation_lifecycle(
    recommendation: dict[str, Any],
    outcome: dict[str, Any],
    today: date,
    archive_age_days: int = ARCHIVE_AGE_DAYS,
) -> str:
    """Determine the current lifecycle state of a recommendation.

    Lifecycle:
      NEW      — created today, no movement yet
      ACTIVE   — past creation, milestones still being filled
      MATURED  — all 5 milestones filled (w1, w2, w4, m3, m6)
      ARCHIVED — MATURED + age > archive_age_days (default 180)

    Args:
        recommendation: dict with at least 'created_at' and 'milestones_reached'.
        outcome: dict with at least 'updated_at'.
        today: current date.
        archive_age_days: age threshold for archiving matured recs.

    Returns:
        Lifecycle state string.
    """
    created_at = recommendation["created_at"]
    if isinstance(created_at, str):
        created_at = date.fromisoformat(created_at)

    milestones = set(recommendation.get("milestones_reached") or [])
    all_filled = all(m in milestones for m in ALL_MILESTONES)

    age_days = (today - created_at).days

    # NEW: created today
    if age_days == 0:
        return LIFECYCLE_NEW

    # MATURED: all milestones filled
    if all_filled:
        if age_days > archive_age_days:
            return LIFECYCLE_ARCHIVED
        return LIFECYCLE_MATURED

    # ACTIVE: still being tracked
    return LIFECYCLE_ACTIVE


# ----------------------------------------------------------------------------
# Regression tolerance helper
# ----------------------------------------------------------------------------

def assert_cas_within_tolerance(
    actual: float,
    expected: float,
    tolerance: float = 2.0,
    message: str = "",
) -> None:
    """Assert actual CAS is within ±tolerance of expected.

    Used by regression tests to allow small drift when only tuning
    weights/thresholds (per Decision 101 expert feedback V1.1d F).
    If actual differs by more than tolerance, that's a SIGNAL — the
    tuning change has bigger consequences than expected and warrants
    a calibration journal entry.

    Args:
        actual: computed CAS from current run.
        expected: baseline CAS from prior regression snapshot.
        tolerance: max allowed absolute difference (default 2.0 points).
        message: optional context for failure message.

    Raises:
        AssertionError if |actual - expected| > tolerance.
    """
    delta = abs(actual - expected)
    assert delta <= tolerance, (
        f"CAS drift {delta:.3f} exceeds tolerance ±{tolerance}. "
        f"actual={actual}, expected={expected}. "
        f"{'Context: ' + message if message else ''}"
        f"Action: review Calibration.md — was this tuning change expected?"
    )
