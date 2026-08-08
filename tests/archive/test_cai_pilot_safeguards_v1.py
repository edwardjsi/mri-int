import pytest
from api.zerodha_adapter import ProductionGTTAdapter
from api.cai_state_machine import BrokerLifecycleEngine, BrokerExecutionState
from api.cai_broker_reconciliation import CAIBrokerReconciliation, ReconciliationStatus

def test_kill_switch_blocks_mutation():
    adapter = ProductionGTTAdapter()
    
    # Assert default state is OFF (fail-closed)
    assert adapter.LIVE_MUTATION_ENABLED is False
    
    # Attempt creation on an allowed symbol
    result = adapter.create_gtt("IPCA", 1600.0, 7)
    assert result == "BLOCKED"
    
    # Attempt modify/delete
    assert adapter.modify_gtt("gtt_id", "IPCA", 1650.0, 8) is False
    assert adapter.delete_gtt("gtt_id", "IPCA") is False

def test_allowlist_blocks_unauthorized_symbols():
    adapter = ProductionGTTAdapter()
    
    # Turn ON the kill switch specifically for this test
    adapter.LIVE_MUTATION_ENABLED = True
    
    # Attempt creation on a FORBIDDEN symbol (e.g. WELCORP)
    result = adapter.create_gtt("WELCORP", 500.0, 1)
    assert result == "BLOCKED"
    
    # Attempt creation on an ALLOWED symbol
    result_allowed = adapter.create_gtt("IPCA", 1600.0, 7)
    assert "real_prod_gtt_id" in result_allowed
    
    # Revert for safety
    adapter.LIVE_MUTATION_ENABLED = False

def test_broker_lifecycle_strict_separation():
    state = BrokerExecutionState.GTT_ACTIVE
    
    # Trigger occurs
    state = BrokerLifecycleEngine.evaluate_transition(state, "TRIGGER")
    assert state == BrokerExecutionState.GTT_TRIGGERED
    
    # GTT Triggered must NOT infer POSITION_EXIT_CONFIRMED
    with pytest.raises(ValueError):
        BrokerLifecycleEngine.evaluate_transition(state, "CONFIRM_EXIT")
        
    # The true path requires ORDER_PENDING -> ORDER_EXECUTED -> CONFIRM_EXIT
    state = BrokerLifecycleEngine.evaluate_transition(state, "PLACE_ORDER")
    assert state == BrokerExecutionState.ORDER_PENDING
    
    state = BrokerLifecycleEngine.evaluate_transition(state, "EXECUTE")
    assert state == BrokerExecutionState.ORDER_EXECUTED
    
    state = BrokerLifecycleEngine.evaluate_transition(state, "CONFIRM_EXIT")
    assert state == BrokerExecutionState.POSITION_EXIT_CONFIRMED

def test_reconciliation_flags_failed_gtts():
    # We mock the gtt adapter list returning a CANCELLED status
    class MockAdapterReturnsCancelled:
        def get_all_gtts(self):
            return [{"symbol": "IPCA", "status": "CANCELLED", "trigger_price": 1600.0}]
            
    worker = CAIBrokerReconciliation(MockAdapterReturnsCancelled())
    config = {"levels": {"structural_break_price": 1600.0}}
    
    status = worker.reconcile_gtt({"symbol": "IPCA"}, config)
    assert status == ReconciliationStatus.GTT_FAILED

def test_reconciliation_proposes_mutation():
    class MockAdapterReturnsMissing:
        def get_all_gtts(self):
            return []
            
    worker = CAIBrokerReconciliation(MockAdapterReturnsMissing())
    config = {"levels": {"structural_break_price": 1600.0}}
    
    status = worker.reconcile_gtt({"symbol": "IPCA"}, config)
    assert status == ReconciliationStatus.GTT_MUTATION_PROPOSED
    
    # Verify the dual confirmation step
    intent = worker.process_human_decision_to_broker("CONFIRM_MUTATION", config, "IPCA")
    assert intent == "PROCEED_MUTATION"
