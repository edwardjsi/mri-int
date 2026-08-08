import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from api.main import app
from api.cai_alert_orchestrator import get_db

client = TestClient(app)

def test_divislab_unconfigured_state():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    
    # Mock _get_admin_client
    mock_cur.fetchone.side_effect = [{"id": "admin-id"}]
    
    # Mock config versions (returns empty for DIVISLAB)
    mock_cur.fetchall.return_value = []
    
    app.dependency_overrides[get_db] = lambda: mock_conn
    
    response = client.get("/api/cai/alerts/DIVISLAB")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "DIVISLAB"
    assert data["approved"] is None
    assert data["draft"] is None
    assert data["sync_count"] == 0

def test_hscl_draft_state():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    
    # Mock _get_admin_client
    mock_cur.fetchone.side_effect = [{"id": "admin-id"}]
    
    # Mock config versions (returns DRAFT for HSCL)
    mock_cur.fetchall.return_value = [{
        "id": "draft-id",
        "symbol": "HSCL",
        "status": "DRAFT",
        "pullback_lower_bound": 720.0,
        "pullback_upper_bound": 730.0,
        "breakout_confirmation_price": 800.0,
        "next_add_price": 820.0,
        "structural_break_price": 670.0
    }]
    
    app.dependency_overrides[get_db] = lambda: mock_conn
    
    response = client.get("/api/cai/alerts/HSCL")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "HSCL"
    assert data["approved"] is None
    assert data["draft"]["status"] == "DRAFT"
    assert data["draft"]["pullback_lower_bound"] == 720.0
    assert data["draft"]["breakout_confirmation_price"] == 800.0

app.dependency_overrides = {}
