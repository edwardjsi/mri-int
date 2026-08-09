import pytest
from api.cai_validation import validate_alert_configuration, is_valid_tranche_progression

def test_valid_alert_configuration():
    payload = {
        "levels": {
            "structural_break_price": 100.0,
            "pullback_zone": {
                "lower_bound": 90.0,
                "upper_bound": 95.0
            },
            "next_add_level": {
                "min_price": 105.0,
                "max_price": 110.0,
                "target_tranche": "T2"
            }
        }
    }
    is_valid, errors = validate_alert_configuration(payload, "T1")
    assert is_valid is True
    assert len(errors) == 0

def test_negative_structural_break_price():
    payload = {
        "levels": {
            "structural_break_price": -10.0,
            "pullback_zone": {"lower_bound": 90.0, "upper_bound": 95.0},
            "next_add_level": {"min_price": 105.0, "max_price": 110.0, "target_tranche": "T2"}
        }
    }
    is_valid, errors = validate_alert_configuration(payload, "T1")
    assert is_valid is False
    assert "Structural break price must be greater than 0." in errors

def test_invalid_pullback_bounds():
    payload = {
        "levels": {
            "structural_break_price": 100.0,
            "pullback_zone": {"lower_bound": 95.0, "upper_bound": 90.0},
            "next_add_level": {"min_price": 105.0, "max_price": 110.0, "target_tranche": "T2"}
        }
    }
    is_valid, errors = validate_alert_configuration(payload, "T1")
    assert is_valid is False
    assert "Pullback lower_bound must be strictly less than upper_bound." in errors

def test_negative_pullback_bounds():
    payload = {
        "levels": {
            "structural_break_price": 100.0,
            "pullback_zone": {"lower_bound": -10.0, "upper_bound": 90.0},
            "next_add_level": {"min_price": 105.0, "max_price": 110.0, "target_tranche": "T2"}
        }
    }
    is_valid, errors = validate_alert_configuration(payload, "T1")
    assert is_valid is False
    assert "Pullback bounds must be greater than 0." in errors

def test_invalid_next_add_bounds():
    payload = {
        "levels": {
            "structural_break_price": 100.0,
            "pullback_zone": {"lower_bound": 90.0, "upper_bound": 95.0},
            "next_add_level": {"min_price": 110.0, "max_price": 105.0, "target_tranche": "T2"}
        }
    }
    is_valid, errors = validate_alert_configuration(payload, "T1")
    assert is_valid is False
    assert "Next ADD min_price must be strictly less than max_price." in errors

def test_invalid_tranche_progression():
    payload = {
        "levels": {
            "structural_break_price": 100.0,
            "pullback_zone": {"lower_bound": 90.0, "upper_bound": 95.0},
            "next_add_level": {"min_price": 105.0, "max_price": 110.0, "target_tranche": "T1"}
        }
    }
    # Current is T2, trying to go to T1
    is_valid, errors = validate_alert_configuration(payload, "T2")
    assert is_valid is False
    assert "Target tranche T1 must be downstream of current tranche T2." in errors

def test_tranche_progression_helper():
    assert is_valid_tranche_progression("T0", "T1") is True
    assert is_valid_tranche_progression("T1", "T5") is True
    assert is_valid_tranche_progression("T5", "FULL") is True
    assert is_valid_tranche_progression("FULL", "EXITED") is True
    assert is_valid_tranche_progression("T2", "T1") is False
    assert is_valid_tranche_progression("T5", "T1") is False

def test_approve_sync_blocked_on_duplicate_threshold():
    from fastapi.testclient import TestClient
    from unittest.mock import MagicMock, patch
    from api.main import app
    from api.cai_alert_orchestrator import get_db

    client = TestClient(app)
    
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    
    # Mock _get_admin_client, _get_position_id, and draft config
    mock_cur.fetchone.side_effect = [
        {"id": "admin-id"},  # _get_admin_client
        {"id": "pos-id"},    # _get_position_id
        {                    # The DRAFT config
            "id": "draft-id",
            "symbol": "IPCALAB",
            "status": "DRAFT",
            "pullback_lower_bound": 1682.50,
            "pullback_upper_bound": 1801.29,
            "breakout_confirmation_price": 1944.90,
            "next_add_price": 1944.90,
            "structural_break_price": 1623.10
        }
    ]
    
    app.dependency_overrides[get_db] = lambda: mock_conn
    
    with patch("api.cai_alert_orchestrator.KiteAlertAdapter") as mock_kite:
        response = client.post("/api/cai/alerts/IPCALAB/approve-sync")
        
        # Must return HTTP 400
        assert response.status_code == 400
        assert "Breakout equals Next ADD" in response.json()["detail"]
        
        # Kite adapter must NOT be invoked
        mock_kite.assert_not_called()
        
    app.dependency_overrides = {}

def test_approve_sync_position_resolution_success():
    from fastapi.testclient import TestClient
    from unittest.mock import MagicMock, patch
    from api.main import app
    from api.cai_alert_orchestrator import get_db

    client = TestClient(app)
    
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    
    # Mock _get_admin_client, _get_position_id, draft config
    mock_cur.fetchone.side_effect = [
        {"id": "admin-id"},  # _get_admin_client
        {"id": "pos-id"},    # _get_position_id
        {                    # The DRAFT config
            "id": "draft-id",
            "symbol": "IPCALAB",
            "status": "DRAFT",
            "pullback_lower_bound": 1680.00,
            "pullback_upper_bound": 1750.00,
            "breakout_confirmation_price": 1945.00,
            "next_add_price": 1970.00,
            "structural_break_price": 1615.00
        }
    ]
    
    mock_cur.fetchall.return_value = [] # obsolete mappings
    
    app.dependency_overrides[get_db] = lambda: mock_conn
    
    with patch("api.cai_alert_orchestrator.KiteAlertAdapter") as mock_kite_class:
        mock_kite = MagicMock()
        mock_kite.create_alert.return_value = {"data": {"alert_uuid": "mock_uuid"}}
        mock_kite_class.return_value = mock_kite
        
        response = client.post("/api/cai/alerts/IPCALAB/approve-sync")
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        
        # Kite adapter must be invoked 4 times for the 4 alerts
        assert mock_kite.create_alert.call_count == 4
        
    app.dependency_overrides = {}


def test_approve_sync_fake_symbol_fails_cleanly():
    from fastapi.testclient import TestClient
    from unittest.mock import MagicMock, patch
    from api.main import app
    from api.cai_alert_orchestrator import get_db

    client = TestClient(app)
    
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    
    # Mock _get_admin_client, and _get_position_id returns None
    mock_cur.fetchone.side_effect = [
        {"id": "admin-id"},  # _get_admin_client
        None                 # _get_position_id (not found)
    ]
    
    app.dependency_overrides[get_db] = lambda: mock_conn
    
    with patch("api.cai_alert_orchestrator.KiteAlertAdapter") as mock_kite:
        response = client.post("/api/cai/alerts/FAKE_SYMBOL/approve-sync")
        
        # Must return HTTP 400
        assert response.status_code == 400
        assert "No active MRI position found for FAKE_SYMBOL" in response.json()["detail"]
        
        # Kite adapter must NOT be invoked
        mock_kite.assert_not_called()
        
    app.dependency_overrides = {}


def test_approve_sync_inactive_position_fails_cleanly():
    from fastapi.testclient import TestClient
    from unittest.mock import MagicMock, patch
    from api.main import app
    from api.cai_alert_orchestrator import get_db

    client = TestClient(app)
    
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    
    # Mock _get_admin_client, and _get_position_id returns None (since query filters by status='ACTIVE')
    mock_cur.fetchone.side_effect = [
        {"id": "admin-id"},  # _get_admin_client
        None                 # _get_position_id (not active)
    ]
    
    app.dependency_overrides[get_db] = lambda: mock_conn
    
    with patch("api.cai_alert_orchestrator.KiteAlertAdapter") as mock_kite:
        response = client.post("/api/cai/alerts/CLOSED_POS/approve-sync")
        
        # Must return HTTP 400
        assert response.status_code == 400
        assert "No active MRI position found for CLOSED_POS" in response.json()["detail"]
        
        # Kite adapter must NOT be invoked
        mock_kite.assert_not_called()
        
    app.dependency_overrides = {}

def test_approve_sync_adapter_call_signature():
    from fastapi.testclient import TestClient
    from unittest.mock import MagicMock, patch
    from api.main import app
    from api.cai_alert_orchestrator import get_db

    client = TestClient(app)
    
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    
    mock_cur.fetchone.side_effect = [
        {"id": "admin-id"},
        {"id": "pos-id"},
        {
            "id": "draft-id",
            "symbol": "HSCL",
            "status": "DRAFT",
            "pullback_lower_bound": 720.0,
            "pullback_upper_bound": 730.0,
            "breakout_confirmation_price": 800.0,
            "next_add_price": 820.0,
            "structural_break_price": 670.0
        }
    ]
    mock_cur.fetchall.return_value = []
    
    app.dependency_overrides[get_db] = lambda: mock_conn
    
    with patch("api.cai_alert_orchestrator.KiteAlertAdapter") as MockKite:
        adapter_instance = MockKite.return_value
        
        def strict_create_alert(alert_name, symbol, condition, price, alert_type="simple"):
            return {"data": {"alert_uuid": f"mock-{alert_name}"}}
            
        adapter_instance.create_alert.side_effect = strict_create_alert
        
        response = client.post("/api/cai/alerts/HSCL/approve-sync")
        
        assert response.status_code == 200
        assert adapter_instance.create_alert.call_count == 4
        
        update_calls = [call for call in mock_cur.execute.call_args_list if "UPDATE cai_alert_config_versions SET status =" in call[0][0]]
        assert len(update_calls) == 2
        assert "SYNC_IN_PROGRESS" in update_calls[0][0][0]
        assert "APPROVED" in update_calls[1][0][0]

def test_approve_sync_adapter_failure():
    from fastapi.testclient import TestClient
    from unittest.mock import MagicMock, patch
    from api.main import app
    from api.cai_alert_orchestrator import get_db

    client = TestClient(app)
    
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    
    mock_cur.fetchone.side_effect = [
        {"id": "admin-id"},
        {"id": "pos-id"},
        {
            "id": "draft-id",
            "symbol": "HSCL",
            "status": "DRAFT",
            "pullback_lower_bound": 720.0,
            "pullback_upper_bound": 730.0,
            "breakout_confirmation_price": 800.0,
            "next_add_price": 820.0,
            "structural_break_price": 670.0
        }
    ]
    
    app.dependency_overrides[get_db] = lambda: mock_conn
    
    with patch("api.cai_alert_orchestrator.KiteAlertAdapter") as MockKite:
        adapter_instance = MockKite.return_value
        adapter_instance.create_alert.side_effect = Exception("Kite API Error")
        
        response = client.post("/api/cai/alerts/HSCL/approve-sync")
        
        assert response.status_code == 500
        assert "Kite API Error" in response.json()["detail"]
        
        update_calls = [call for call in mock_cur.execute.call_args_list if "UPDATE cai_alert_config_versions SET status = 'APPROVED'" in call[0][0]]
        assert len(update_calls) == 0
