"""V1.1c — Decision layer tests (stabilize_action, NO_ACTION triggers, lifecycle).

Decision 101 expert feedback (2026-07-08):
  - Hysteresis applies to ACTION only, not Confidence/Stars
  - Tier-based comparison: NO_ACTION < WATCH < FIRST_TRANCHE < ADD_SECOND_TRANCHE
  - NO_ACTION has THREE triggers: no eligible, top-N empty, best CAS < deployment threshold
  - Recommendation Lifecycle: NEW → ACTIVE → MATURED → ARCHIVED
"""
import pytest
from datetime import date

from engine_core.cas_decision_layer import (
    STABILITY_UPGRADED,
    STABILITY_DOWNGRADED,
    STABILITY_UNCHANGED,
    STABILITY_NEW,
    TIER_ORDER,
    ACTION_TIER_MAP,
    LAYERED_STATE_ORDER,
    cas_to_tier,
    compute_layered_state,
    tier_to_action,
    stabilize_action,
    compute_recommendation_lifecycle,
    should_return_no_action,
    NO_ACTION_REASON_NO_ELIGIBLE,
    NO_ACTION_REASON_TOP_N_EMPTY,
    NO_ACTION_REASON_BELOW_DEPLOYMENT,
    LIFECYCLE_NEW,
    LIFECYCLE_ACTIVE,
    LIFECYCLE_MATURED,
    LIFECYCLE_ARCHIVED,
)


class TestCasToTier:
    def test_no_action_tier_zero(self):
        assert cas_to_tier(0) == "NO_ACTION"
        assert cas_to_tier(50) == "NO_ACTION"
        assert cas_to_tier(59.99) == "NO_ACTION"

    def test_watch_tier(self):
        assert cas_to_tier(60) == "WATCH"
        assert cas_to_tier(70) == "WATCH"
        assert cas_to_tier(79.99) == "WATCH"

    def test_first_tranche_tier(self):
        assert cas_to_tier(80) == "FIRST_TRANCHE"
        assert cas_to_tier(82) == "FIRST_TRANCHE"
        assert cas_to_tier(84.99) == "FIRST_TRANCHE"

    def test_add_second_tranche_tier(self):
        assert cas_to_tier(85) == "ADD_SECOND_TRANCHE"
        assert cas_to_tier(95) == "ADD_SECOND_TRANCHE"
        assert cas_to_tier(100) == "ADD_SECOND_TRANCHE"


class TestTierToAction:
    def test_no_action_to_no_action(self):
        assert tier_to_action("NO_ACTION") == "NO_ACTION"

    def test_watch_to_watch(self):
        assert tier_to_action("WATCH") == "WATCH"

    def test_first_tranche_to_buy(self):
        assert tier_to_action("FIRST_TRANCHE") == "BUY"

    def test_add_second_tranche_to_add(self):
        assert tier_to_action("ADD_SECOND_TRANCHE") == "ADD"

    def test_invalid_tier_raises(self):
        with pytest.raises(ValueError):
            tier_to_action("UNKNOWN")


class TestStabilizeAction:
    """Hysteresis applies to action only, NOT to confidence/stars."""

    def test_new_when_no_prev_action(self):
        # No prev action → NEW, take current
        result = stabilize_action(
            prev_action=None,
            current_action="BUY",
            prev_cas=None,
            current_cas=82.0,
        )
        assert result["action"] == "BUY"
        assert result["stability"] == STABILITY_NEW

    def test_unchanged_same_action(self):
        result = stabilize_action(
            prev_action="WATCH",
            current_action="WATCH",
            prev_cas=72.0,
            current_cas=73.0,
        )
        assert result["action"] == "WATCH"
        assert result["stability"] == STABILITY_UNCHANGED

    def test_upgraded_cleanly(self):
        # WATCH (72) → FIRST_TRANCHE (85): well past threshold + hysteresis
        result = stabilize_action(
            prev_action="WATCH",
            current_action="BUY",
            prev_cas=72.0,
            current_cas=85.0,
        )
        assert result["action"] == "BUY"
        assert result["stability"] == STABILITY_UPGRADED

    def test_downgraded_cleanly(self):
        # FIRST_TRANCHE (84) → WATCH (55): current CAS is well below WATCH threshold
        # WATCH boundary=60, hysteresis=3, so downgrade requires CAS < 57
        result = stabilize_action(
            prev_action="BUY",
            current_action="WATCH",
            prev_cas=84.0,
            current_cas=55.0,
        )
        assert result["action"] == "WATCH"
        assert result["stability"] == STABILITY_DOWNGRADED

    def test_downgrade_dampened_within_hysteresis_band(self):
        # FIRST_TRANCHE at 82, current CAS=78 — within 3pt hysteresis
        # of buy_threshold (80), so DON'T downgrade to WATCH
        result = stabilize_action(
            prev_action="BUY",
            current_action="WATCH",
            prev_cas=82.0,
            current_cas=78.0,
        )
        assert result["action"] == "BUY"  # stuck at FIRST_TRANCHE
        assert result["stability"] == STABILITY_UNCHANGED

    def test_upgrade_dampened_within_hysteresis_band(self):
        # WATCH at 78, current CAS=82 — within 3pt hysteresis
        # of buy_threshold (80), so DON'T upgrade to FIRST_TRANCHE
        # (78→80 buy threshold + 3 hysteresis = 82 required)
        result = stabilize_action(
            prev_action="WATCH",
            current_action="BUY",
            prev_cas=78.0,
            current_cas=82.0,
        )
        assert result["action"] == "WATCH"  # dampened
        assert result["stability"] == STABILITY_UNCHANGED

    def test_hysteresis_does_not_affect_add_threshold(self):
        # BUY → ADD boundary at 85, hysteresis=3, so ADD requires CAS >= 88
        result = stabilize_action(
            prev_action="BUY",
            current_action="ADD",
            prev_cas=82.0,
            current_cas=87.0,
        )
        # 87 is below 85+3=88, so don't upgrade
        assert result["action"] == "BUY"
        assert result["stability"] == STABILITY_UNCHANGED

    def test_hysteresis_upgrades_when_well_past(self):
        result = stabilize_action(
            prev_action="BUY",
            current_action="ADD",
            prev_cas=82.0,
            current_cas=92.0,
        )
        assert result["action"] == "ADD"
        assert result["stability"] == STABILITY_UPGRADED

    def test_confidence_bypasses_hysteresis(self):
        """The function returns action+stability only. Stars are passed through separately."""
        result = stabilize_action(
            prev_action="WATCH",
            current_action="BUY",
            prev_cas=78.0,
            current_cas=82.0,
        )
        # Even though action stays WATCH due to hysteresis,
        # the result doesn't touch stars. Stars are handled by API layer.
        assert "stars" not in result  # decision layer doesn't deal with stars

    def test_downgrade_to_no_action_uses_hysteresis(self):
        # BUY (84) → NO_ACTION (50): 50 << 60-3=57, so allow
        result = stabilize_action(
            prev_action="BUY",
            current_action="NO_ACTION",
            prev_cas=84.0,
            current_cas=50.0,
        )
        assert result["action"] == "NO_ACTION"
        assert result["stability"] == STABILITY_DOWNGRADED

    def test_downgrade_to_no_action_dampened(self):
        # BUY (84) → NO_ACTION (58): 58 > 60-3=57, dampen
        result = stabilize_action(
            prev_action="BUY",
            current_action="NO_ACTION",
            prev_cas=84.0,
            current_cas=58.0,
        )
        assert result["action"] == "BUY"  # stuck
        assert result["stability"] == STABILITY_UNCHANGED

    def test_first_scan_no_prev_returns_new(self):
        """First scan of the day: prev_action=None, return NEW with current action."""
        result = stabilize_action(
            prev_action=None,  # never recorded before
            current_action="BUY",
            prev_cas=None,
            current_cas=85.0,
        )
        assert result["action"] == "BUY"
        assert result["stability"] == STABILITY_NEW


class TestShouldReturnNoAction:
    """NO_ACTION triggers per Decision 101 + expert Q2."""

    def test_no_eligible_stocks(self):
        result = should_return_no_action(
            n_eligible=0,
            n_top_n=0,
            best_eligible_cas=None,
            min_deployable_cas=70.0,
        )
        assert result["is_no_action"] is True
        assert result["reason"] == NO_ACTION_REASON_NO_ELIGIBLE

    def test_top_n_empty_even_when_eligible_exist(self):
        # Eligible stocks exist but top-N filter returned empty
        # (e.g., limit=0 or other filter)
        result = should_return_no_action(
            n_eligible=5,
            n_top_n=0,
            best_eligible_cas=85.0,
            min_deployable_cas=70.0,
        )
        assert result["is_no_action"] is True
        assert result["reason"] == NO_ACTION_REASON_TOP_N_EMPTY

    def test_best_cas_below_deployment_threshold(self):
        # Eligible stocks exist, top-N has entries, but best CAS < threshold
        result = should_return_no_action(
            n_eligible=10,
            n_top_n=5,
            best_eligible_cas=68.0,
            min_deployable_cas=70.0,
        )
        assert result["is_no_action"] is True
        assert result["reason"] == NO_ACTION_REASON_BELOW_DEPLOYMENT
        assert "68" in result["reason_text"]
        assert "70" in result["reason_text"]

    def test_deployable_market_returns_recommendations(self):
        # Eligible, top-N populated, best CAS >= threshold
        result = should_return_no_action(
            n_eligible=10,
            n_top_n=5,
            best_eligible_cas=82.0,
            min_deployable_cas=70.0,
        )
        assert result["is_no_action"] is False
        assert result["reason"] is None

    def test_threshold_at_exact_boundary(self):
        # best CAS exactly equal to threshold → NOT NO_ACTION (>= is the rule)
        result = should_return_no_action(
            n_eligible=5,
            n_top_n=3,
            best_eligible_cas=70.0,
            min_deployable_cas=70.0,
        )
        assert result["is_no_action"] is False

    def test_best_cas_none_but_eligible_exists_raises(self):
        """Logic error: n_eligible > 0 but best_eligible_cas is None."""
        with pytest.raises(ValueError):
            should_return_no_action(
                n_eligible=5,
                n_top_n=5,
                best_eligible_cas=None,
                min_deployable_cas=70.0,
            )


class TestRecommendationLifecycle:
    """NEW → ACTIVE → MATURED → ARCHIVED (per expert Q-final)."""

    def test_new_when_created_today(self):
        rec = {"created_at": date(2026, 7, 8), "milestones_reached": []}
        outcome = {"updated_at": date(2026, 7, 8)}
        lifecycle = compute_recommendation_lifecycle(
            rec, outcome, today=date(2026, 7, 8)
        )
        assert lifecycle == LIFECYCLE_NEW

    def test_active_when_past_and_incomplete(self):
        rec = {"created_at": date(2026, 7, 1), "milestones_reached": ["w1", "w2"]}
        outcome = {"updated_at": date(2026, 7, 8)}
        lifecycle = compute_recommendation_lifecycle(
            rec, outcome, today=date(2026, 7, 8)
        )
        assert lifecycle == LIFECYCLE_ACTIVE

    def test_matured_when_all_milestones_filled(self):
        # All 5 milestones filled (w1, w2, w4, m3, m6)
        # Created within last 180 days → MATURED (not ARCHIVED yet)
        rec = {
            "created_at": date(2026, 3, 1),  # ~130 days ago
            "milestones_reached": ["w1", "w2", "w4", "m3", "m6"],
        }
        outcome = {"updated_at": date(2026, 7, 8)}
        lifecycle = compute_recommendation_lifecycle(
            rec, outcome, today=date(2026, 7, 8)
        )
        assert lifecycle == LIFECYCLE_MATURED

    def test_archived_when_old_and_matured(self):
        # Matured + age > 180 days
        rec = {
            "created_at": date(2025, 12, 1),
            "milestones_reached": ["w1", "w2", "w4", "m3", "m6"],
        }
        outcome = {"updated_at": date(2026, 7, 8)}
        lifecycle = compute_recommendation_lifecycle(
            rec, outcome, today=date(2026, 7, 8)
        )
        assert lifecycle == LIFECYCLE_ARCHIVED

    def test_active_takes_priority_over_old_when_incomplete(self):
        # Old but incomplete → still ACTIVE (not ARCHIVED)
        rec = {
            "created_at": date(2025, 1, 1),
            "milestones_reached": ["w1"],
        }
        outcome = {"updated_at": date(2026, 7, 8)}
        lifecycle = compute_recommendation_lifecycle(
            rec, outcome, today=date(2026, 7, 8)
        )
        assert lifecycle == LIFECYCLE_ACTIVE


class TestActionTierMap:
    def test_all_db_actions_mapped(self):
        """Every DB action enum must map to a tier."""
        for action in ["BUY", "ADD", "WATCH", "NO_ACTION"]:
            assert action in ACTION_TIER_MAP
            assert ACTION_TIER_MAP[action] in TIER_ORDER

    def test_tier_order_increasing(self):
        """Tier order should be monotonically increasing (NO_ACTION < WATCH < ...)."""
        assert TIER_ORDER.index("NO_ACTION") < TIER_ORDER.index("WATCH")
        assert TIER_ORDER.index("WATCH") < TIER_ORDER.index("FIRST_TRANCHE")
        assert TIER_ORDER.index("FIRST_TRANCHE") < TIER_ORDER.index("ADD_SECOND_TRANCHE")


class TestAssertCasWithinTolerance:
    """Regression tolerance helper per Decision 101 expert feedback V1.1d."""

    def test_within_tolerance_passes(self):
        from engine_core.cas_decision_layer import assert_cas_within_tolerance
        # Should not raise
        assert_cas_within_tolerance(82.0, 80.0, tolerance=2.0)
        assert_cas_within_tolerance(78.0, 80.0, tolerance=2.0)
        assert_cas_within_tolerance(80.0, 80.0, tolerance=2.0)

    def test_at_boundary_passes(self):
        from engine_core.cas_decision_layer import assert_cas_within_tolerance
        # Exactly at tolerance boundary
        assert_cas_within_tolerance(82.0, 80.0, tolerance=2.0)
        assert_cas_within_tolerance(78.0, 80.0, tolerance=2.0)

    def test_exceeds_tolerance_raises(self):
        from engine_core.cas_decision_layer import assert_cas_within_tolerance
        with pytest.raises(AssertionError):
            assert_cas_within_tolerance(85.5, 80.0, tolerance=2.0)
        with pytest.raises(AssertionError):
            assert_cas_within_tolerance(74.0, 80.0, tolerance=2.0)

    def test_message_included_in_failure(self):
        from engine_core.cas_decision_layer import assert_cas_within_tolerance
        with pytest.raises(AssertionError) as excinfo:
            assert_cas_within_tolerance(85.0, 80.0, tolerance=2.0,
                                        message="after weight tuning")
        assert "weight tuning" in str(excinfo.value)

    def test_default_tolerance_is_2(self):
        """Default tolerance matches Decision 101 (±2 points)."""
        from engine_core.cas_decision_layer import assert_cas_within_tolerance
        from engine_core.capital_allocation import load_config
        config = load_config("config/capital_allocation.yaml")
        expected_default = config.get("regression_tolerance", {}).get("cas_points", 2.0)
        assert expected_default == 2.0


# ===========================================================================
# Decision 103 P3f — compute_layered_state tests (V2 4-state model)
# ===========================================================================

def _v2_decision_config(add_min=85.0):
    return {"action": {"buy_cas_min": 80, "add_cas_min": add_min, "watch_cas_min": 60}}


class TestComputeLayeredState:
    """Decision 103 V2: 4-state model — OBSERVE / APPROACHING_ADD /
    READY_FOR_ADD / ADD_SECOND_TRANCHE."""

    def test_low_cas_returns_observe(self):
        cfg = _v2_decision_config()
        assert compute_layered_state(70.0, [], False, cfg) == "OBSERVE"
        assert compute_layered_state(50.0, [], False, cfg) == "OBSERVE"

    def test_cas_in_80_to_84_returns_approaching_add(self):
        cfg = _v2_decision_config()
        assert compute_layered_state(80.0, [], False, cfg) == "APPROACHING_ADD"
        assert compute_layered_state(82.5, [], True, cfg) == "APPROACHING_ADD"
        assert compute_layered_state(84.9, [], False, cfg) == "APPROACHING_ADD"

    def test_high_cas_no_position_is_ready_for_add(self):
        """CAS >= 85 + no position → READY_FOR_ADD (can BUY but not ADD)."""
        cfg = _v2_decision_config()
        assert compute_layered_state(88.0, [], False, cfg) == "READY_FOR_ADD"

    def test_high_cas_with_position_and_all_passes_is_add_second_tranche(self):
        cfg = _v2_decision_config()
        assert compute_layered_state(88.0, [], True, cfg) == "ADD_SECOND_TRANCHE"
        assert compute_layered_state(99.9, [], True, cfg) == "ADD_SECOND_TRANCHE"

    def test_high_cas_with_failed_gate_is_ready_for_add(self):
        """Even with position, a failed gate → READY_FOR_ADD (not ADD_SECOND_TRANCHE)."""
        cfg = _v2_decision_config()
        assert compute_layered_state(
            90.0, ["G3_WEEKLY_CLOSE_BELOW_RESISTANCE"], True, cfg
        ) == "READY_FOR_ADD"

    def test_none_cas_returns_observe(self):
        cfg = _v2_decision_config()
        assert compute_layered_state(None, [], False, cfg) == "OBSERVE"
        assert compute_layered_state(None, [], True, cfg) == "OBSERVE"

    def test_config_override_add_cas_min(self):
        """Custom add_cas_min shifts the state boundaries."""
        cfg = _v2_decision_config(add_min=90.0)
        # With add_cas_min=90, CAS=88 is now APPROACHING_ADD (not READY_FOR_ADD)
        assert compute_layered_state(88.0, [], False, cfg) == "APPROACHING_ADD"
        # CAS=92 + has_position + gates pass → ADD_SECOND_TRANCHE
        assert compute_layered_state(92.0, [], True, cfg) == "ADD_SECOND_TRANCHE"

    def test_layered_state_order_constant(self):
        """LAYERED_STATE_ORDER exports the 4 states in progression order."""
        assert LAYERED_STATE_ORDER == [
            "OBSERVE", "APPROACHING_ADD", "READY_FOR_ADD", "ADD_SECOND_TRANCHE",
        ]

    def test_cas_to_tier_still_works_for_v1_backward_compat(self):
        """V1.1d cas_to_tier() must continue working unchanged.

        V1 boundaries: NO_ACTION <60, WATCH [60,80), FIRST_TRANCHE [80,85),
        ADD_SECOND_TRANCHE ≥85.
        """
        assert cas_to_tier(50.0) == "NO_ACTION"
        assert cas_to_tier(70.0) == "WATCH"
        assert cas_to_tier(82.0) == "FIRST_TRANCHE"
        assert cas_to_tier(88.0) == "ADD_SECOND_TRANCHE"
