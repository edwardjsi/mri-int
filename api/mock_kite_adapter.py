from enum import Enum
from typing import Dict, Any


class GTTBrokerExecutionState(str, Enum):
    ACTIVE = "ACTIVE"
    GTT_TRIGGERED = "GTT_TRIGGERED"
    ORDER_PENDING = "ORDER_PENDING"
    ORDER_EXECUTED = "ORDER_EXECUTED"
    POSITION_EXIT_CONFIRMED = "POSITION_EXIT_CONFIRMED"
    ORDER_FAILED = "ORDER_FAILED"
    OUT_OF_SYNC = "OUT_OF_SYNC"
    MISSING = "MISSING"


class MockKiteServerAdapter:
    """
    Mock Kite Server Adapter to simulate the explicit broker execution pipeline
    for Phase 1 testing and GTT reconciliation.
    """

    def __init__(self):
        # Maps tracking_id to current state for simulation purposes
        self._gtt_orders: Dict[str, Dict[str, Any]] = {}

    def create_gtt_order(self, tracking_id: str, trigger_price: float, symbol: str) -> bool:
        """Simulate creating a GTT order in the broker."""
        self._gtt_orders[tracking_id] = {
            "symbol": symbol,
            "trigger_price": trigger_price,
            "state": GTTBrokerExecutionState.ACTIVE
        }
        return True

    def get_order_state(self, tracking_id: str) -> GTTBrokerExecutionState:
        """Retrieve the current state of a simulated order."""
        if tracking_id not in self._gtt_orders:
            return GTTBrokerExecutionState.MISSING
        return self._gtt_orders[tracking_id]["state"]

    def simulate_state_transition(self, tracking_id: str, new_state: GTTBrokerExecutionState) -> bool:
        """Helper to advance the mock order state for testing."""
        if tracking_id not in self._gtt_orders:
            return False
        self._gtt_orders[tracking_id]["state"] = new_state
        return True
