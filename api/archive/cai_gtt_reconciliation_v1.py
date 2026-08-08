import logging
from typing import Dict, Any, List, Optional
from api.cai_state_machine import AlertLifecycleEngine, AlertState
from api.zerodha_adapter import MockGTTAdapter


class ReconciliationStatus:
    HEALTHY = "HEALTHY"
    GTT_MISMATCH = "GTT_MISMATCH"
    GTT_MISSING = "GTT_MISSING"
    GTT_MUTATION_PROPOSED = "GTT_MUTATION_PROPOSED"
    GTT_FAILED = "GTT_FAILED"


class CAIBrokerReconciliation:
    """
    Core worker responsible for synchronizing CAI state with the broker.
    Detects mismatches and enforces human-in-the-loop for mutations.
    """

    def __init__(self, gtt_adapter):
        self.gtt_adapter = gtt_adapter

    def reconcile_gtt(self, cai_position: Dict[str, Any], config: Dict[str, Any]) -> str:
        """
        Reconciles a CAI position with its expected GTT protection level on the broker.
        Returns the ReconciliationStatus.
        """
        symbol = cai_position.get("symbol")
        expected_price = config.get("levels", {}).get("structural_break_price")
        
        if expected_price is None:
            return ReconciliationStatus.HEALTHY
            
        all_gtts = self.gtt_adapter.get_all_gtts()
        # A GTT is conceptually matching if symbol matches.
        gtt_for_symbol = next((g for g in all_gtts if g["symbol"] == symbol), None)
        
        if not gtt_for_symbol:
            logging.warning(f"Reconciliation: GTT MISSING for {symbol}.")
            # Propose mutation; await user confirmation
            return ReconciliationStatus.GTT_MUTATION_PROPOSED
            
        status = gtt_for_symbol.get("status")
        
        if status in ["DISABLED", "CANCELLED", "REJECTED", "EXPIRED"]:
            logging.error(f"Reconciliation: GTT {status} for {symbol}. REVIEW_REQUIRED.")
            return ReconciliationStatus.GTT_FAILED
            
        if status != "ACTIVE":
            # Might be TRIGGERED, meaning it's in flight. 
            return ReconciliationStatus.HEALTHY
            
        actual_price = gtt_for_symbol.get("trigger_price")
        
        if actual_price != expected_price:
            logging.warning(f"Reconciliation: GTT MISMATCH for {symbol}. CAI: {expected_price}, Broker: {actual_price}")
            # Propose mutation; await user confirmation
            return ReconciliationStatus.GTT_MUTATION_PROPOSED
            
        return ReconciliationStatus.HEALTHY

    def process_human_decision_to_broker(self, decision: str, config: Dict[str, Any], symbol: str):
        """
        Processes an explicit human decision.
        Safety Invariant: `ADD` NEVER executes a buy order in V1.
        """
        if decision == "ADD":
            logging.info(f"Intent recorded for {symbol}: Human decided to ADD. BUY execution is MANUAL in V1.")
            return None
            
        elif decision == "EXIT":
            logging.info(f"Intent recorded for {symbol}: Human decided to EXIT.")
            return None
            
        elif decision == "CONFIRM_MUTATION":
            # Explicit user confirmation received to mutate GTT.
            # At this point, the adapter's LIVE_MUTATION_ENABLED flag will ALSO be checked.
            logging.info(f"User explicitly confirmed GTT mutation for {symbol}.")
            return "PROCEED_MUTATION"
            
        return None
