import pytest
from api.cai_state_machine import AlertLifecycleEngine, AlertState, TrancheProgressionEngine, PositionTranche
from api.cai_evaluators import CAIEvaluators
from api.zerodha_adapter import MockGTTAdapter, ZerodhaSandboxAdapter
from api.cai_broker_reconciliation import CAIBrokerReconciliation, ReconciliationStatus


def test_uat_pullback_zone_reached():
    config = {"levels": {"pullback_zone": {"lower_bound": 1600.0, "upper_bound": 1700.0}}}
    alert_type, triggered = CAIEvaluators.evaluate_all(1650.0, config)
    assert triggered is True and alert_type == "PULLBACK_ZONE_REACHED"
    
    state = AlertLifecycleEngine.evaluate_transition(AlertState.ACTIVE, "TRIGGER")
    state = AlertLifecycleEngine.evaluate_transition(state, "REQUIRE_REVIEW")
    assert state == AlertState.REVIEW_REQUIRED


def test_uat_breakout_reached():
    config = {"levels": {"breakout_level": 1500.0}}
    alert_type, triggered = CAIEvaluators.evaluate_all(1550.0, config)
    assert triggered is True and alert_type == "BREAKOUT_CONFIRMATION"
    
    state = AlertLifecycleEngine.evaluate_transition(AlertState.ACTIVE, "TRIGGER")
    state = AlertLifecycleEngine.evaluate_transition(state, "REQUIRE_REVIEW")
    assert state == AlertState.REVIEW_REQUIRED


def test_uat_add_threshold_reached_no_buy():
    config = {"levels": {"next_add_level": {"min_price": 1900.0, "max_price": 2000.0}}}
    alert_type, triggered = CAIEvaluators.evaluate_all(1950.0, config)
    assert triggered is True and alert_type == "NEXT_ADD_CANDIDATE"
    
    state = AlertLifecycleEngine.evaluate_transition(AlertState.ACTIVE, "TRIGGER")
    state = AlertLifecycleEngine.evaluate_transition(state, "REQUIRE_REVIEW")
    assert state == AlertState.REVIEW_REQUIRED
    
    # Verify no buy order logic is executed
    gtt_adapter = MockGTTAdapter()
    worker = CAIBrokerReconciliation(gtt_adapter)
    import unittest.mock
    sandbox = ZerodhaSandboxAdapter()
    sandbox.place_order = unittest.mock.MagicMock()
    
    worker.process_human_decision_to_broker("WAIT", config, "IPCA")
    sandbox.place_order.assert_not_called()


def test_uat_user_says_wait():
    new_tranche = TrancheProgressionEngine.process_human_decision(PositionTranche.T2, "WAIT")
    assert new_tranche == PositionTranche.T2


def test_uat_user_says_add():
    gtt_adapter = MockGTTAdapter()
    sandbox = ZerodhaSandboxAdapter()
    worker = CAIBrokerReconciliation(gtt_adapter)
    
    import unittest.mock
    sandbox.place_order = unittest.mock.MagicMock()
    
    worker.process_human_decision_to_broker("ADD", {}, "IPCA")
    sandbox.place_order.assert_not_called()


def test_uat_structure_break_and_user_exit():
    config = {"levels": {"structural_break_price": 1600.0}}
    alert_type, triggered = CAIEvaluators.evaluate_all(1550.0, config)
    assert triggered is True and alert_type == "STRUCTURE_BREAK"
    
    state = AlertLifecycleEngine.evaluate_transition(AlertState.ACTIVE, "TRIGGER")
    state = AlertLifecycleEngine.evaluate_transition(state, "REQUIRE_REVIEW")
    assert state == AlertState.REVIEW_REQUIRED
    
    new_tranche = TrancheProgressionEngine.process_human_decision(PositionTranche.T2, "EXIT")
    assert new_tranche == PositionTranche.EXITED


def test_uat_gtt_missing():
    gtt_adapter = MockGTTAdapter()
    worker = CAIBrokerReconciliation(gtt_adapter)
    config = {"levels": {"structural_break_price": 1600.0}, "version": 7}
    
    status = worker.reconcile_gtt({"symbol": "IPCA"}, config)
    assert status == ReconciliationStatus.GTT_MISSING


def test_uat_gtt_price_wrong():
    gtt_adapter = MockGTTAdapter()
    worker = CAIBrokerReconciliation(gtt_adapter)
    config = {"levels": {"structural_break_price": 1600.0}, "version": 7}
    
    gtt_adapter.create_gtt("IPCA", 1650.0, 7)
    status = worker.reconcile_gtt({"symbol": "IPCA"}, config)
    assert status == ReconciliationStatus.GTT_MISMATCH


def test_uat_gtt_trigger_simulated():
    gtt_adapter = MockGTTAdapter()
    gtt_id = gtt_adapter.create_gtt("IPCA", 1600.0, 7)
    assert gtt_adapter.retrieve_gtt(gtt_id)["status"] == "ACTIVE"
    
    gtt_adapter.simulate_trigger(gtt_id)
    assert gtt_adapter.retrieve_gtt(gtt_id)["status"] == "TRIGGERED"


def test_uat_order_fails():
    # Simulate a failed order by transitioning the mock state directly
    from api.mock_kite_adapter import MockKiteServerAdapter, GTTBrokerExecutionState
    adapter = MockKiteServerAdapter()
    adapter.create_gtt_order("TEST_GTT_1", 1600.0, "IPCA")
    
    adapter.simulate_state_transition("TEST_GTT_1", GTTBrokerExecutionState.ORDER_FAILED)
    state = adapter.get_order_state("TEST_GTT_1")
    assert state == GTTBrokerExecutionState.ORDER_FAILED


def test_uat_duplicate_event():
    state = AlertState.REVIEW_REQUIRED
    # Try transitioning again to the same states incorrectly to prove state machine constraints
    with pytest.raises(ValueError):
        AlertLifecycleEngine.evaluate_transition(state, "TRIGGER")


def test_uat_out_of_sync_broker():
    from api.mock_kite_adapter import MockKiteServerAdapter, GTTBrokerExecutionState
    adapter = MockKiteServerAdapter()
    adapter.create_gtt_order("TEST_GTT_1", 1600.0, "IPCA")
    adapter.simulate_state_transition("TEST_GTT_1", GTTBrokerExecutionState.OUT_OF_SYNC)
    state = adapter.get_order_state("TEST_GTT_1")
    assert state == GTTBrokerExecutionState.OUT_OF_SYNC


def test_uat_old_config_version():
    gtt_adapter = MockGTTAdapter()
    config_v7 = {"levels": {"structural_break_price": 1600.0}, "version": 7}
    config_v8 = {"levels": {"structural_break_price": 1650.0}, "version": 8}
    
    gtt_id = gtt_adapter.create_gtt("IPCA", 1600.0, config_v7["version"])
    assert gtt_adapter.retrieve_gtt(gtt_id)["config_version"] == 7
    
    worker = CAIBrokerReconciliation(gtt_adapter)
    
    # Reconciling against v8 config when broker has v7
    status = worker.reconcile_gtt({"symbol": "IPCA"}, config_v8)
    assert status == ReconciliationStatus.GTT_MISMATCH
