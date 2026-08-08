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
    
    # Mock _get_admin_client and _get_position_id
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
