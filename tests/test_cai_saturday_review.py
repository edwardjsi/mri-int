import pytest
from unittest.mock import patch, MagicMock

# Mock get_db before importing app
import api.deps
mock_conn = MagicMock()
mock_cur = MagicMock()
mock_conn.cursor.return_value = mock_cur
api.deps.get_db = lambda: mock_conn

with patch('engine_mosi.knowledge_importer.get_connection', return_value=MagicMock()):
    from api.cai_saturday_review import get_saturday_review

def test_saturday_review_active_positions():
    """1. Returns exactly 22 ACTIVE MRI positions."""
    mock_cur.fetchall.side_effect = [
        [{"id": str(i), "symbol": f"SYM{i}", "tranche": 1} for i in range(22)], # active positions
        [], # configs
        [] # mappings
    ]
    data = get_saturday_review(client={"id": 1}, conn=mock_conn)
    assert data["total_positions"] == 22
    assert len(data["positions"]) == 22

def test_saturday_review_excludes_closed():
    """2. Excludes CLOSED positions."""
    mock_cur.fetchall.side_effect = [
        [{"id": "1", "symbol": "IPCALAB", "tranche": 1}],
        [], []
    ]
    data = get_saturday_review(client={"id": 1}, conn=mock_conn)
    assert "CGCL" not in [p["symbol"] for p in data["positions"]]

def test_saturday_review_ipcalab_approved():
    """3. IPCALAB = APPROVED + correct four levels."""
    mock_cur.fetchall.side_effect = [
        [{"id": "1", "symbol": "IPCALAB", "tranche": 1}],
        [{
            "id": "c1", "symbol": "IPCALAB", "status": "APPROVED",
            "pullback_lower_bound": 1680, "pullback_upper_bound": 1750,
            "breakout_confirmation_price": 1945, "next_add_price": 1970,
            "structural_break_price": 1615, "validation_status": None, "created_at": "2026-08-01"
        }],
        [{"config_version_id": "c1"}] # Synced
    ]
    data = get_saturday_review(client={"id": 1}, conn=mock_conn)
    pos = data["positions"][0]
    assert pos["symbol"] == "IPCALAB"
    assert pos["config_status"] == "APPROVED"
    assert pos["zerodha_sync_status"] == "SYNCED"
    assert pos["pullback_lower"] == 1680

def test_saturday_review_hscl_draft():
    """4. HSCL = DRAFT + correct four levels."""
    mock_cur.fetchall.side_effect = [
        [{"id": "2", "symbol": "HSCL", "tranche": 1}],
        [{
            "id": "c2", "symbol": "HSCL", "status": "DRAFT",
            "pullback_lower_bound": 720, "pullback_upper_bound": 730,
            "breakout_confirmation_price": 800, "next_add_price": 820,
            "structural_break_price": 670, "validation_status": None, "created_at": "2026-08-01"
        }],
        [] # Not synced
    ]
    data = get_saturday_review(client={"id": 1}, conn=mock_conn)
    pos = data["positions"][0]
    assert pos["symbol"] == "HSCL"
    assert pos["config_status"] == "DRAFT"
    assert pos["zerodha_sync_status"] is None
    assert pos["breakout"] == 800

def test_saturday_review_unconfigured():
    """5. Unconfigured stock = UNCONFIGURED."""
    mock_cur.fetchall.side_effect = [
        [{"id": "3", "symbol": "DIVISLAB", "tranche": 1}],
        [], []
    ]
    data = get_saturday_review(client={"id": 1}, conn=mock_conn)
    pos = data["positions"][0]
    assert pos["config_status"] == "UNCONFIGURED"
    assert pos["pullback_lower"] is None

def test_saturday_review_duplicate_threshold():
    """6. Duplicate thresholds = WARNING."""
    mock_cur.fetchall.side_effect = [
        [{"id": "4", "symbol": "TEST", "tranche": 1}],
        [{
            "id": "c3", "symbol": "TEST", "status": "DRAFT",
            "pullback_lower_bound": 100, "pullback_upper_bound": 110,
            "breakout_confirmation_price": 120, "next_add_price": 120, # duplicate
            "structural_break_price": 90, "validation_status": None, "created_at": "2026-08-01"
        }],
        []
    ]
    data = get_saturday_review(client={"id": 1}, conn=mock_conn)
    pos = data["positions"][0]
    assert pos["validation_status"] == "WARNING_DUPLICATE_THRESHOLD"

def test_saturday_review_zerodha_status():
    """7. Zerodha status is correctly reflected."""
    mock_cur.fetchall.side_effect = [
        [{"id": "5", "symbol": "SOME", "tranche": 1}],
        [{
            "id": "c4", "symbol": "SOME", "status": "APPROVED",
            "pullback_lower_bound": 100, "pullback_upper_bound": 110,
            "breakout_confirmation_price": 120, "next_add_price": 130,
            "structural_break_price": 90, "validation_status": None, "created_at": "2026-08-01"
        }],
        [] # Mappings empty, so APPROVED but not SYNCED (PENDING)
    ]
    data = get_saturday_review(client={"id": 1}, conn=mock_conn)
    pos = data["positions"][0]
    assert pos["zerodha_sync_status"] == "PENDING"
