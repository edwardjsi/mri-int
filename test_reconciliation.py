import os
import json
from unittest.mock import patch, MagicMock
import pytest

from api.cai_alert_orchestrator import preview_sync, approve_and_sync, KiteAlertAdapter

def test_reconciliation():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value = mock_cur
    
    # Setup mock data for IPCALAB
    client_id = "test-client-id"
    pos_id = "test-ipcalab-id"
    draft_config_id = "draft-config-123"
    
    # 1. _get_admin_client -> client_id
    # 2. _get_position_id -> pos_id
    # 3. SELECT * DRAFT -> draft config
    # 4. validate_config -> pass
    # 5. SELECT * MAPPINGS -> 4 obsolete mappings
    # 6. UPDATE DRAFT -> SYNC_IN_PROGRESS
    
    def mock_execute(query, params=None):
        pass
        
    class TrackedCursor(MagicMock):
        last_query = ""
        def execute(self, query, params=None):
            self.last_query = query
        def fetchone(self):
            if "cai_position" in self.last_query:
                return {"id": pos_id}
            elif "admin client" in self.last_query or "SELECT id FROM clients" in self.last_query:
                return {"id": client_id}
            elif "status = 'DRAFT'" in self.last_query:
                return {
                    "id": draft_config_id,
                    "client_id": client_id,
                    "symbol": "IPCALAB",
                    "structural_break_price": 1600.0,
                    "pullback_lower_bound": 1690.0,
                    "pullback_upper_bound": 1760.0,
                    "breakout_confirmation_price": 1950.0,
                    "next_add_price": 1980.0
                }
            return None
            
        def fetchall(self):
            if "cai_alert_mappings" in self.last_query and "active = TRUE" in self.last_query:
                return [
                    {"id": 1, "kite_uuid": "kite-old-uuid-1", "alert_role": "STRUCTURE_BREAK"},
                    {"id": 2, "kite_uuid": "kite-old-uuid-2", "alert_role": "HEALTHY_PULLBACK"},
                    {"id": 3, "kite_uuid": "kite-old-uuid-3", "alert_role": "BREAKOUT_CONFIRMATION"},
                    {"id": 4, "kite_uuid": "kite-old-uuid-4", "alert_role": "NEXT_ADD"}
                ]
            return []

    tracked_cur = TrackedCursor()
    mock_conn.cursor.return_value = tracked_cur
    
    # Track adapter calls
    created_alerts = []
    deleted_alerts = []
    
    class FakeAdapter:
        def create_alert(self, name, symbol, condition, price):
            new_uuid = f"new-kite-uuid-{len(created_alerts)+1}"
            created_alerts.append({"name": name, "price": price, "uuid": new_uuid})
            return {"data": {"alert_uuid": new_uuid}}
            
        def delete_alert(self, alert_uuid):
            deleted_alerts.append(alert_uuid)

    print("=== RUNNING RECONCILIATION TEST ===")
    
    with patch("api.cai_alert_orchestrator.KiteAlertAdapter", return_value=FakeAdapter()):
        res = approve_and_sync(symbol="IPCALAB", conn=mock_conn)
        print(f"Result: {res['status']} - {res['message']}")
        print(f"Alerts Deleted: {len(deleted_alerts)}")
        for u in deleted_alerts:
            print(f"  - Deleted {u}")
        print(f"Alerts Created: {len(created_alerts)}")
        for c in created_alerts:
            print(f"  - Created {c['name']} at {c['price']} ({c['uuid']})")

if __name__ == '__main__':
    test_reconciliation()
