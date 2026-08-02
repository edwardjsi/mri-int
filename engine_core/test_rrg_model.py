import pytest
import datetime
from decimal import Decimal
from engine_core.rrg_model import RrgModel

class MockCursor:
    def __init__(self, fetchone_data=None):
        self.fetchone_data = fetchone_data
        
    def execute(self, query, params=None):
        pass
        
    def fetchone(self):
        return self.fetchone_data
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class MockConnection:
    def __init__(self, fetchone_data=None):
        self.cursor_mock = MockCursor(fetchone_data)
        
    def cursor(self):
        return self.cursor_mock
        
    def close(self):
        pass

def test_rrg_model_success(monkeypatch):
    # Mock the database connection
    mock_row = {
        "date": datetime.date(2026, 7, 31),
        "rrg_quadrant": "LEADING",
        "rrg_heading": Decimal("47.2"),
        "jdk_rs_ratio": Decimal("108.3"),
        "jdk_rs_momentum": Decimal("104.1"),
        "rrg_benchmark": "NIFTY50"
    }
    monkeypatch.setattr("engine_core.rrg_model.get_connection", lambda: MockConnection(mock_row))
    
    model = RrgModel()
    result = model.evaluate("TCS", datetime.date(2026, 8, 2))
    
    assert result.status == "SUCCESS"
    assert result.model_id == "RRG"
    assert result.model_version == "1.0"
    assert result.payload["quadrant"] == "LEADING"
    assert result.payload["heading"] == 47.2
    assert result.payload["rs_ratio"] == 108.3
    assert result.payload["rs_momentum"] == 104.1
    assert result.payload["benchmark"] == "NIFTY50"
    assert result.payload["methodology"] == "MRI_RRG_V1.0"

def test_rrg_model_missing_data(monkeypatch):
    # Mock empty result from DB
    monkeypatch.setattr("engine_core.rrg_model.get_connection", lambda: MockConnection(None))
    
    model = RrgModel()
    result = model.evaluate("NEWSTOCK", datetime.date(2026, 8, 2))
    
    assert result.status == "FAILED"
    assert result.payload is None
    assert "primitives not found" in result.error_message
