import pytest
from api.zerodha_adapter import KiteAlertAdapter

def test_hard_block_ato_alerts():
    adapter = KiteAlertAdapter()
    
    # Valid simple alert
    uuid = adapter.create_alert("IPCA", "LTP >", 1600.0, "Test Simple")
    assert uuid is not None
    
    # Explicit ATO alert must be hard-blocked
    with pytest.raises(ValueError, match="HARD BLOCK: type=ato is strictly forbidden"):
        adapter.create_alert("RATEGAIN", "LTP >", 800.0, "Test ATO", alert_type="ato")
