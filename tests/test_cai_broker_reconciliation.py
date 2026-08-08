from api.cai_broker_reconciliation import CAIAlertReconciliation, ReconciliationStatus
from api.zerodha_adapter import KiteAlertAdapter

def test_alert_reconciliation_healthy():
    adapter = KiteAlertAdapter()
    worker = CAIAlertReconciliation(adapter)
    
    # Create an alert in the adapter
    uuid = adapter.create_alert("IPCA", "LTP >=", 1800.0, "Breakout_IPCA")
    
    config = {"levels": {"alert_condition": "LTP >=", "alert_price": 1800.0}}
    cai_pos = {"symbol": "IPCA", "alert_uuid": uuid}
    status = worker.reconcile_alerts(cai_pos, config)
    
    assert status == ReconciliationStatus.HEALTHY


def test_alert_reconciliation_missing():
    adapter = KiteAlertAdapter()
    worker = CAIAlertReconciliation(adapter)
    
    config = {"levels": {"alert_condition": "LTP >=", "alert_price": 1800.0}}
    cai_pos = {"symbol": "IPCA", "alert_uuid": "nonexistent_uuid"}
    status = worker.reconcile_alerts(cai_pos, config)
    
    assert status == ReconciliationStatus.ALERT_MISSING


def test_alert_reconciliation_mismatch():
    adapter = KiteAlertAdapter()
    worker = CAIAlertReconciliation(adapter)
    
    # Create an alert with the wrong price
    uuid = adapter.create_alert("IPCA", "LTP >=", 1850.0, "Breakout_IPCA")
    
    config = {"levels": {"alert_condition": "LTP >=", "alert_price": 1800.0}}
    cai_pos = {"symbol": "IPCA", "alert_uuid": uuid}
    status = worker.reconcile_alerts(cai_pos, config)
    
    assert status == ReconciliationStatus.ALERT_MISMATCH
