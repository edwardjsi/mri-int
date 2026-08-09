import pytest
import os
from unittest.mock import patch, MagicMock
from api.zerodha_adapter import KiteAlertAdapter

@pytest.fixture
def adapter(monkeypatch):
    monkeypatch.setenv("KITE_API_KEY", "test_key")
    adapter = KiteAlertAdapter()
    adapter.access_token = "test_token"
    return adapter

@patch("api.zerodha_adapter.requests.post")
def test_create_alert_success(mock_post, adapter):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"status": "success", "data": {"uuid": "real-uuid-123"}}
    
    uuid = adapter.create_alert("INFY", ">=", 1500.0, "INFY - 🟢 Pullback")
    assert uuid == "real-uuid-123"
    
    mock_post.assert_called_once()
    kwargs = mock_post.call_args.kwargs
    assert kwargs["headers"]["Authorization"] == "token test_key:test_token"
    assert kwargs["data"]["operator"] == ">="
    assert kwargs["data"]["lhs_tradingsymbol"] == "INFY"
    assert kwargs["data"]["rhs_constant"] == "1500.0"

@patch("api.zerodha_adapter.requests.post")
def test_create_alert_api_error(mock_post, adapter):
    mock_post.return_value.status_code = 400
    mock_post.return_value.json.return_value = {"status": "error", "message": "Invalid token"}
    
    with pytest.raises(RuntimeError) as exc:
        adapter.create_alert("INFY", ">=", 1500.0, "INFY - 🟢 Pullback")
    assert "Zerodha API Error: Invalid token" in str(exc.value)

@patch("api.zerodha_adapter.requests.get")
def test_retrieve_alert(mock_get, adapter):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"status": "success", "data": {"uuid": "abc", "name": "Test"}}
    
    data = adapter.retrieve_alert("abc")
    assert data["name"] == "Test"
    assert mock_get.call_args[0][0].endswith("/abc")

@patch("api.zerodha_adapter.requests.get")
def test_get_all_alerts(mock_get, adapter):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"status": "success", "data": [{"uuid": "abc"}]}
    
    alerts = adapter.get_all_alerts()
    assert len(alerts) == 1
    assert alerts[0]["uuid"] == "abc"

@patch("api.zerodha_adapter.requests.delete")
def test_delete_alert(mock_delete, adapter):
    mock_delete.return_value.status_code = 200
    mock_delete.return_value.json.return_value = {"status": "success"}
    
    success = adapter.delete_alert("abc")
    assert success is True
    assert "uuid=abc" in mock_delete.call_args[0][0]

def test_missing_api_key(monkeypatch):
    if "KITE_API_KEY" in os.environ:
        monkeypatch.delenv("KITE_API_KEY")
    with pytest.raises(ValueError) as exc:
        KiteAlertAdapter()
    assert "KITE_API_KEY is not configured" in str(exc.value)

