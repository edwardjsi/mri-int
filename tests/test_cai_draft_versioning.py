import pytest
from unittest.mock import MagicMock
from api.cai_alert_orchestrator import upsert_draft, CAIConfigDraft
from fastapi import HTTPException

def test_draft_versioning_increments_max():
    # Setup mock DB
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    
    # Define sequence of fetchone() returns:
    # 1st: _get_admin_client -> {"id": "admin-123"}
    # 2nd: MAX(version) -> {"max": 1}
    # 3rd: INSERT RETURNING * -> {"id": "new-draft-id", "version": 2}
    mock_cur.fetchone.side_effect = [
        {"id": "admin-123"},
        {"max": 1},
        {"id": "new-draft-id", "version": 2, "status": "DRAFT"}
    ]
    
    req = CAIConfigDraft(
        pullback_lower_bound=720.0,
        pullback_upper_bound=730.0,
        breakout_confirmation_price=800.0,
        next_add_price=820.0,
        structural_break_price=670.0
    )
    
    res = upsert_draft("HSCL", req, mock_conn)
    
    # Assert successful save
    assert res["status"] == "success"
    assert res["draft"]["version"] == 2
    
    # Verify SQL execution
    executed_queries = [call[0][0].strip() for call in mock_cur.execute.call_args_list]
    
    # Should delete existing DRAFT/SYNC_FAILED
    assert any("DELETE FROM cai_alert_config_versions" in q and "IN ('DRAFT', 'SYNC_FAILED')" in q for q in executed_queries)
    
    # Should query MAX(version)
    assert any("SELECT MAX(version)" in q for q in executed_queries)
    
    # Should insert with explicit version
    insert_call = next(call for call in mock_cur.execute.call_args_list if "INSERT INTO cai_alert_config_versions" in call[0][0])
    query = insert_call[0][0]
    args = insert_call[0][1]
    
    assert "version" in query
    # The 3rd argument in our VALUES (%s, %s, %s, ...) corresponds to version
    # args = (client_id, symbol, next_version, ...)
    assert args[2] == 2  # next_version = max_version (1) + 1 = 2

def test_draft_versioning_no_existing():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    
    mock_cur.fetchone.side_effect = [
        {"id": "admin-123"},
        {"max": None}, # No existing configs
        {"id": "new-draft-id", "version": 1, "status": "DRAFT"}
    ]
    
    req = CAIConfigDraft(pullback_lower_bound=720.0, pullback_upper_bound=730.0, breakout_confirmation_price=800.0, next_add_price=820.0, structural_break_price=670.0)
    res = upsert_draft("RELIANCE", req, mock_conn)
    
    assert res["draft"]["version"] == 1
    
    insert_call = next(call for call in mock_cur.execute.call_args_list if "INSERT INTO cai_alert_config_versions" in call[0][0])
    args = insert_call[0][1]
    assert args[2] == 1 # (None or 0) + 1 = 1

def test_draft_versioning_v3_to_v4():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    
    mock_cur.fetchone.side_effect = [
        {"id": "admin-123"},
        {"max": 3}, # Max is v3
        {"id": "new-draft-id", "version": 4, "status": "DRAFT"}
    ]
    
    req = CAIConfigDraft(pullback_lower_bound=720.0, pullback_upper_bound=730.0, breakout_confirmation_price=800.0, next_add_price=820.0, structural_break_price=670.0)
    res = upsert_draft("TCS", req, mock_conn)
    
    assert res["draft"]["version"] == 4
    
    insert_call = next(call for call in mock_cur.execute.call_args_list if "INSERT INTO cai_alert_config_versions" in call[0][0])
    args = insert_call[0][1]
    assert args[2] == 4

