import os
import pytest
from unittest.mock import patch, MagicMock
import uuid
import hashlib
from fastapi import HTTPException

from api.kite_auth import kite_login, kite_callback, kite_status

# Dummy client for auth dependency
class DummyClient(dict):
    pass

dummy_client = DummyClient({"id": str(uuid.uuid4()), "email": "test_cai@example.com"})

def dummy_db():
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    from datetime import datetime
    cur.fetchone.return_value = {"kite_user_id": "XY1234", "updated_at": datetime.utcnow()}
    return conn

@pytest.fixture
def mock_env():
    os.environ["KITE_API_KEY"] = "test_api_key"
    os.environ["KITE_API_SECRET"] = "test_api_secret"
    yield
    if "KITE_API_KEY" in os.environ:
        del os.environ["KITE_API_KEY"]
    if "KITE_API_SECRET" in os.environ:
        del os.environ["KITE_API_SECRET"]

def test_login_redirect(mock_env):
    response = kite_login()
    assert response.status_code == 307
    assert response.headers["location"] == "https://kite.trade/connect/login?v=3&api_key=test_api_key"

def test_callback_missing_token(mock_env):
    with pytest.raises(HTTPException) as excinfo:
        kite_callback(request_token=None, status="success", error_type=None, conn=dummy_db())
    assert "Missing request_token" in str(excinfo.value)

def test_callback_zerodha_failure(mock_env):
    with pytest.raises(HTTPException) as excinfo:
        kite_callback(request_token="abc", status="error", error_type="TokenException", conn=dummy_db())
    assert "TokenException" in str(excinfo.value)

from datetime import datetime

@patch("httpx.post")
def test_callback_success(mock_post, mock_env):
    mock_post.return_value = MagicMock(
        json=lambda: {
            "status": "success",
            "data": {
                "access_token": "secret_access_token_123",
                "user_id": "XY1234"
            }
        }
    )
    
    db = dummy_db()
    cur = db.cursor()
    # First fetchone is information_schema check, second is the admin client fetch
    cur.fetchone.side_effect = [{"exists": 1}, {"id": dummy_client["id"]}]

    request_token = "req_tok_abc"
    response = kite_callback(request_token=request_token, status="success", error_type=None, conn=db)
    
    assert response["message"] == "Authentication successful"
    assert response["kite_user_id"] == "XY1234"
    
    mock_post.assert_called_once()
    payload = mock_post.call_args[1]["data"]
    assert payload["api_key"] == "test_api_key"
    assert payload["request_token"] == request_token
    assert payload["checksum"] == hashlib.sha256(b"test_api_keyreq_tok_abctest_api_secret").hexdigest()

@patch("httpx.post")
def test_callback_token_exchange_failure(mock_post, mock_env):
    mock_post.return_value = MagicMock(
        json=lambda: {
            "status": "error",
            "message": "Invalid Checksum"
        }
    )
    with pytest.raises(HTTPException) as excinfo:
        kite_callback(request_token="abc", status="success", error_type=None, conn=dummy_db())
    assert "Invalid Checksum" in str(excinfo.value)

def test_kite_status():
    db = dummy_db()
    cur = db.cursor()
    cur.fetchone.return_value = {"kite_user_id": "XY1234", "updated_at": datetime.utcnow()}
    
    resp = kite_status(client=dummy_client, conn=db)
    assert resp["status"] == "Connected"
    assert resp["kite_user_id"] == "XY1234"

def test_missing_credentials():
    if "KITE_API_KEY" in os.environ:
        del os.environ["KITE_API_KEY"]
    if "KITE_API_SECRET" in os.environ:
        del os.environ["KITE_API_SECRET"]
    
    with pytest.raises(HTTPException) as excinfo:
        kite_callback(request_token="123", status="success", error_type=None, conn=dummy_db())
    assert excinfo.value.status_code == 500
    assert "Server misconfiguration" in excinfo.value.detail

def test_ato_hard_block():
    from api.zerodha_adapter import KiteAlertAdapter
    adapter = KiteAlertAdapter()
    with pytest.raises(ValueError, match="HARD BLOCK"):
        adapter.create_alert("RELIANCE", "LTP >=", 2000, "ATO Alert", alert_type="ato")
