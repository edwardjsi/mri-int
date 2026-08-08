import logging
from typing import Dict, Any

class ReconciliationStatus:
    HEALTHY = "HEALTHY"
    ALERT_MISMATCH = "ALERT_MISMATCH"
    ALERT_MISSING = "ALERT_MISSING"


class CAIAlertReconciliation:
    """
    Core worker responsible for synchronizing CAI alert state with the broker's simple price alerts.
    Detects mismatches and ensures Kite matches the CAI config.
    """

    def __init__(self, alert_adapter):
        self.alert_adapter = alert_adapter

    def reconcile_alerts(self, cai_position: Dict[str, Any], config: Dict[str, Any]) -> str:
        """
        Reconciles a CAI position with its expected Kite Price Alert.
        Returns the ReconciliationStatus.
        """
        symbol = cai_position.get("symbol")
        alert_uuid = cai_position.get("alert_uuid")
        
        expected_condition = config.get("levels", {}).get("alert_condition")
        expected_price = config.get("levels", {}).get("alert_price")
        
        if expected_price is None or expected_condition is None:
            return ReconciliationStatus.HEALTHY
            
        all_alerts = self.alert_adapter.get_all_alerts()
        # Find alert by UUID
        active_alert = next((a for a in all_alerts if a.get("uuid") == alert_uuid and a["status"] == "ACTIVE"), None)
        
        if not active_alert:
            logging.warning(f"Reconciliation: ALERT MISSING for {symbol} (UUID: {alert_uuid}).")
            # CAI triggers REVIEW_REQUIRED for the user to resolve or sync
            return ReconciliationStatus.ALERT_MISSING
            
        actual_price = active_alert.get("price")
        actual_condition = active_alert.get("condition")
        
        if actual_price != expected_price or actual_condition != expected_condition:
            logging.warning(f"Reconciliation: ALERT MISMATCH for {symbol}. Expected: {expected_condition} {expected_price}, Broker: {actual_condition} {actual_price}")
            return ReconciliationStatus.ALERT_MISMATCH
            
        return ReconciliationStatus.HEALTHY

    def process_human_decision_to_broker(self, decision: str, config: Dict[str, Any], symbol: str):
        """
        Processes an explicit human decision.
        In V1 Alert Orchestration, CAI NEVER executes trades.
        """
        if decision in ["ADD", "EXIT"]:
            logging.info(f"Intent recorded for {symbol}: Human decided to {decision}. EXECUTION IS OUT OF SCOPE FOR CAI V1.")
            return None
        return None
