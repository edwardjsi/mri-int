import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_core.portfolio_os_position_repository import (  # noqa: E402
    PortfolioPositionNotFoundError,
    PortfolioPositionRepository,
)


class FakeCursor:
    def __init__(self, fetchone_values=None):
        self.fetchone_values = fetchone_values or []
        self.call_count = 0
        self.executed = []

    def execute(self, sql, params=()):
        self.executed.append((sql, params))

    def fetchone(self):
        if self.call_count < len(self.fetchone_values):
            val = self.fetchone_values[self.call_count]
            self.call_count += 1
            return val
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self, fetchone_values=None):
        self.fetchone_values = fetchone_values
        self.cursors = []
        self.closed = False

    def cursor(self, cursor_factory=None):
        cursor = FakeCursor(self.fetchone_values)
        self.cursors.append(cursor)
        return cursor

    def close(self):
        self.closed = True


class TestPortfolioPositionRepository:
    def test_fetches_valid_position(self):
        repo = PortfolioPositionRepository()
        
        conn = FakeConnection([
            # First fetchone: cai_position
            {'symbol': 'TCS', 'quantity': 100, 'average_price': 1500.0, 'allocation': 10.0, 'tranche': 2, 'status': 'ACTIVE'},
            # Second fetchone: daily_prices
            {'close': 1600.0}
        ])
        
        pos = repo.get_position_by_id("pos_123", conn=conn)
        
        assert pos.symbol == "TCS"
        assert pos.quantity == 100
        assert pos.entry_price == 1500.0
        assert pos.current_price == 1600.0
        assert pos.current_allocation == 0.10
        assert pos.number_of_tranches == 2
        assert pos.current_state == "ACTIVE"

    def test_raises_error_when_position_not_found(self):
        repo = PortfolioPositionRepository()
        
        conn = FakeConnection([None])
        
        with pytest.raises(PortfolioPositionNotFoundError, match="No position found with id pos_123"):
            repo.get_position_by_id("pos_123", conn=conn)

    def test_defaults_current_price_to_entry_when_no_price_history(self):
        repo = PortfolioPositionRepository()
        
        conn = FakeConnection([
            {'symbol': 'NEW_STOCK', 'quantity': 50, 'average_price': 500.0, 'allocation': 5.0, 'tranche': 1, 'status': 'ACTIVE'},
            None  # No price history
        ])
        
        pos = repo.get_position_by_id("pos_456", conn=conn)
        
        assert pos.symbol == "NEW_STOCK"
        assert pos.current_price == 500.0

    def test_owns_connection_when_opened_internally(self, monkeypatch):
        repo = PortfolioPositionRepository()
        fake_conn = FakeConnection([
            {'symbol': 'INFY', 'quantity': 50, 'average_price': 1000.0, 'allocation': 2.5, 'tranche': 1, 'status': 'ACTIVE'},
            {'close': 1100.0}
        ])

        import engine_core.portfolio_os_position_repository as mod
        monkeypatch.setattr(mod, 'get_connection', lambda: fake_conn)

        pos = repo.get_position_by_id("pos_789")
        
        assert pos.symbol == "INFY"
        assert fake_conn.closed is True
