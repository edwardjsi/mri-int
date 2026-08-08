import logging
from typing import Dict, Any
from api.zerodha_adapter import KiteAlertAdapter
from api.cai_state_machine import AlertState, AlertLifecycleEngine

logging.basicConfig(level=logging.INFO, format="%(message)s")


class LiveAlertTester:
    """
    Executes a safe, end-to-end test of the CAI Alert Orchestration loop.
    This creates a real 'simple' Kite alert at an un-triggerable price to prove 
    the API plumbing without any execution risk.
    """
    
    def __init__(self):
        self.adapter = KiteAlertAdapter()
        # Initialize state to CREATED
        self.state = AlertState.CREATED
        
    def run_e2e_test(self, safe_symbol: str = "RELIANCE", safe_price: float = 100000.0):
        logging.info("--- CAI V1 End-to-End Alert Plumbing Test ---")
        logging.info(f"Using deeply out-of-the-money test: {safe_symbol} LTP >= {safe_price}\n")
        
        # 1. CAI config dictates an alert creation
        logging.info("[1] CAI configuration initiates alert creation...")
        self.state = AlertLifecycleEngine.evaluate_transition(self.state, "ACTIVATE")
        logging.info(f"CAI State -> {self.state}")
        
        alert_uuid = self.adapter.create_alert(
            symbol=safe_symbol,
            condition="LTP >=",
            price=safe_price,
            alert_name=f"CAI_TEST_{safe_symbol}",
            alert_type="simple"
        )
        
        # 2. Verify alert exists in Kite
        logging.info("\n[2] Verifying Kite alert via API retrieval...")
        retrieved = self.adapter.retrieve_alert(alert_uuid)
        if retrieved:
            logging.info(f"SUCCESS: Alert {alert_uuid} is ACTIVE on Kite.")
            logging.info(f"Details: {retrieved['condition']} {retrieved['price']} (Type: {retrieved['type']})")
        else:
            logging.error("FAILED: Alert not found.")
            return
            
        # 3. Simulate the alert triggering (Broker sends notification -> CAI records trigger)
        logging.info("\n[3] Simulating the broker trigger notification...")
        logging.info("In reality, you will receive a push notification on your Kite app.")
        self.state = AlertLifecycleEngine.evaluate_transition(self.state, "TRIGGER")
        logging.info(f"CAI State -> {self.state}")
        
        # 4. CAI surfaces the alert for Human Review
        logging.info("\n[4] CAI escalates to REVIEW_REQUIRED...")
        self.state = AlertLifecycleEngine.evaluate_transition(self.state, "REQUIRE_REVIEW")
        logging.info(f"CAI State -> {self.state}")
        
        # 5. Clean up
        logging.info("\n[5] Cleaning up test alert...")
        if self.adapter.delete_alert(alert_uuid):
            logging.info(f"SUCCESS: Alert {alert_uuid} deleted from Kite.")
            self.state = AlertLifecycleEngine.evaluate_transition(self.state, "HUMAN_REVIEW")
            self.state = AlertLifecycleEngine.evaluate_transition(self.state, "RESOLVE")
            logging.info(f"Final CAI State -> {self.state}")
        else:
            logging.error("FAILED: Could not delete alert.")
            
        logging.info("\nEnd-to-End Plumbing Test Complete. Pipeline is pristine.")


if __name__ == "__main__":
    tester = LiveAlertTester()
    # Execute with a safe, extreme price to ensure it doesn't spontaneously trigger in a live market
    tester.run_e2e_test(safe_symbol="RELIANCE", safe_price=100000.0)
