import pytest
from datetime import datetime, timezone, timedelta
from engine_core.cai_v2_engine import CaiV2Engine
from engine_core.cai_v2_models import DecisionState, RuleCategory

@pytest.fixture
def engine():
    return CaiV2Engine()

def test_scenario_a_add_vs_structure(engine):
    # Scenario A: High Growth (ADD) + High Overhead Supply (STRUCTURE) -> Resolves to STRUCTURE.
    context = {
        "high_growth_fundamentals": True,
        "high_overhead_supply": True
    }
    result = engine.evaluate_position("pos_1", "TESTA", context, [])
    
    assert result.decision_state == DecisionState.STRUCTURE
    assert "R_STRUC_OVERHEAD" in result.triggered_rules
    assert RuleCategory.TECHNICAL in result.rule_categories

def test_scenario_b_quit_vs_add(engine):
    # Scenario B: Price below 200 EMA (QUIT) + Strong Fundamentals (ADD) -> Resolves to QUIT.
    context = {
        "price_below_200_ema": True,
        "high_growth_fundamentals": True
    }
    result = engine.evaluate_position("pos_2", "TESTB", context, [])
    
    assert result.decision_state == DecisionState.QUIT
    assert "R_QUIT_EMA200" in result.triggered_rules

def test_scenario_c_hold_vs_alert(engine):
    # Scenario C: Marginal Breakout (HOLD) + Expired Stability (ALERT) -> Resolves to ALERT.
    # Marginal Breakout isn't explicitly modeled in dummy, but absence of ADD triggers HOLD.
    context = {
        "expired_stability": True
    }
    result = engine.evaluate_position("pos_3", "TESTC", context, [])
    
    assert result.decision_state == DecisionState.ALERT
    assert "R_ALERT_STABILITY" in result.triggered_rules

def test_default_to_hold(engine):
    # Empty context -> HOLD
    result = engine.evaluate_position("pos_4", "TESTD", {}, [])
    assert result.decision_state == DecisionState.HOLD

def test_illegal_transition_fail_closed(engine):
    # Cannot jump from QUIT directly to ADD. Should fail closed and stay QUIT.
    ledger_history = [
        {"to_state": "QUIT", "timestamp": datetime.now(timezone.utc) - timedelta(days=2)}
    ]
    context = {
        "high_growth_fundamentals": True # would normally trigger ADD
    }
    result = engine.evaluate_position("pos_5", "TESTE", context, ledger_history)
    
    # Normally this would be ADD, but validation fails closed to QUIT
    assert result.decision_state == DecisionState.QUIT
    assert "Transition violation" in result.why_not_add

def test_stability_computation(engine):
    now = datetime.now(timezone.utc)
    ledger_history = [
        {"from_state": "HOLD", "to_state": "ADD", "timestamp": now - timedelta(days=28)},
        {"from_state": "ADD", "to_state": "HOLD", "timestamp": now - timedelta(days=15)},
        {"from_state": "HOLD", "to_state": "ALERT", "timestamp": now - timedelta(days=2)},
    ]
    
    context = {}
    result = engine.evaluate_position("pos_6", "TESTF", context, ledger_history)
    
    # 3 flips. days_since_last_flip = 2.
    # recency_penalty = 1.0 / (2 + 1) = 0.333
    # stability = 1.0 - (3 * 0.1) - (0.333 * 0.5) = 1.0 - 0.3 - 0.1665 = 0.5335
    assert 0.50 <= result.decision_stability <= 0.60
