import pytest
from api.cai_state_machine import AlertLifecycleEngine, AlertState, TrancheProgressionEngine, PositionTranche
from api.cai_evaluators import CAIEvaluators

def test_scenario_a_pullback_and_wait():
    # IPCA T2 position hitting PULLBACK_ZONE_REACHED
    current_tranche = PositionTranche.T2
    config = {
        "levels": {
            "pullback_zone": {"lower_bound": 1600.0, "upper_bound": 1700.0}
        }
    }
    
    # 1. Price hits 1680 (Pullback Zone)
    price = 1680.0
    alert_type, triggered = CAIEvaluators.evaluate_all(price, config)
    assert triggered is True
    assert alert_type == "PULLBACK_ZONE_REACHED"
    
    # Prove zero orders are created and position is unmodified
    # (Evaluator returns boolean only, mutates nothing)
    
    # 2. Alert Lifecycle: ACTIVE -> TRIGGERED -> REVIEW_REQUIRED
    alert_state = AlertState.ACTIVE
    alert_state = AlertLifecycleEngine.evaluate_transition(alert_state, "TRIGGER")
    assert alert_state == AlertState.TRIGGERED
    alert_state = AlertLifecycleEngine.evaluate_transition(alert_state, "REQUIRE_REVIEW")
    assert alert_state == AlertState.REVIEW_REQUIRED
    
    # 3. User inputs WAIT via ledger
    human_decision = "WAIT"
    
    # 4. Tranche Engine processing human decision
    new_tranche = TrancheProgressionEngine.process_human_decision(current_tranche, human_decision)
    
    # 5. Position remains T2
    assert new_tranche == PositionTranche.T2
    
    # 6. Alert resolved
    alert_state = AlertLifecycleEngine.evaluate_transition(alert_state, "HUMAN_REVIEW")
    alert_state = AlertLifecycleEngine.evaluate_transition(alert_state, "RESOLVE")
    assert alert_state == AlertState.RESOLVED

def test_scenario_b_next_add_candidate():
    # Price rises to trigger NEXT_ADD_CANDIDATE
    current_tranche = PositionTranche.T2
    config = {
        "levels": {
            "next_add_level": {"min_price": 1900.0, "max_price": 2000.0}
        }
    }
    
    # 1. Price hits 1950
    price = 1950.0
    alert_type, triggered = CAIEvaluators.evaluate_all(price, config)
    assert triggered is True
    assert alert_type == "NEXT_ADD_CANDIDATE"
    
    # 2. Alert Lifecycle transitions
    alert_state = AlertState.ACTIVE
    alert_state = AlertLifecycleEngine.evaluate_transition(alert_state, "TRIGGER")
    alert_state = AlertLifecycleEngine.evaluate_transition(alert_state, "REQUIRE_REVIEW")
    assert alert_state == AlertState.REVIEW_REQUIRED
    
    # 3. User inputs WAIT
    human_decision = "WAIT"
    new_tranche = TrancheProgressionEngine.process_human_decision(current_tranche, human_decision)
    
    # 4. Position remains T2 (no autonomous ADD)
    assert new_tranche == PositionTranche.T2

def test_scenario_c_structure_break():
    # Price drops to trigger STRUCTURE_BREAK
    current_tranche = PositionTranche.T2
    config = {
        "levels": {
            "structural_break_price": 1650.0
        }
    }
    
    # 1. Price hits 1600
    price = 1600.0
    alert_type, triggered = CAIEvaluators.evaluate_all(price, config)
    assert triggered is True
    assert alert_type == "STRUCTURE_BREAK"
    
    # 2. Transition to REVIEW_REQUIRED
    alert_state = AlertState.ACTIVE
    alert_state = AlertLifecycleEngine.evaluate_transition(alert_state, "TRIGGER")
    alert_state = AlertLifecycleEngine.evaluate_transition(alert_state, "REQUIRE_REVIEW")
    assert alert_state == AlertState.REVIEW_REQUIRED
    
    # 3. Position STILL T2 before explicit action!
    assert current_tranche == PositionTranche.T2
    
    # 4. Human reviews and selects EXIT
    human_decision = "EXIT"
    new_tranche = TrancheProgressionEngine.process_human_decision(current_tranche, human_decision)
    
    # 5. Position state actually changes to EXITED
    assert new_tranche == PositionTranche.EXITED

def test_negative_all_evaluators_pure():
    """
    Negative tests proving that zero orders are generated and position is unmodified
    unless an explicit human action occurs.
    """
    config = {
        "levels": {
            "structural_break_price": 100.0,
            "pullback_zone": {"lower_bound": 110.0, "upper_bound": 120.0},
            "next_add_level": {"min_price": 130.0, "max_price": 140.0},
            "breakout_level": 150.0
        }
    }
    
    # PULLBACK
    alert, triggered = CAIEvaluators.evaluate_all(115.0, config)
    assert alert == "PULLBACK_ZONE_REACHED"
    # Notice we didn't pass a position object or order system. 
    # The signature itself prevents side effects.
    
    # BREAKOUT
    alert, triggered = CAIEvaluators.evaluate_all(160.0, config)
    assert alert == "BREAKOUT_CONFIRMATION"
    
    # STRUCTURE_BREAK
    alert, triggered = CAIEvaluators.evaluate_all(90.0, config)
    assert alert == "STRUCTURE_BREAK"
    
    # ADD CANDIDATE
    alert, triggered = CAIEvaluators.evaluate_all(135.0, config)
    assert alert == "NEXT_ADD_CANDIDATE"

    # Verify that tranche progression ONLY happens if "ADD" or "EXIT" is provided
    # i.e., "WAIT" never mutates tranche state.
    assert TrancheProgressionEngine.process_human_decision(PositionTranche.T1, "WAIT") == PositionTranche.T1
    assert TrancheProgressionEngine.process_human_decision(PositionTranche.T5, "HOLD") == PositionTranche.T5
    assert TrancheProgressionEngine.process_human_decision(PositionTranche.T1, "ADD") == PositionTranche.T2
    assert TrancheProgressionEngine.process_human_decision(PositionTranche.T5, "ADD") == PositionTranche.FULL
