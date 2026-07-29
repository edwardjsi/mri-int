import os
import sys
from datetime import date, datetime, timezone

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_core.portfolio_os_snapshot_repository import (  # noqa: E402
    StockSnapshotNotFoundError,
    StockSnapshotRepository,
)


class FakeCursor:
    def __init__(self, fetchone_value=None):
        self.fetchone_value = fetchone_value
        self.executed = []

    def execute(self, sql, params=()):
        self.executed.append((sql, params))

    def fetchone(self):
        return self.fetchone_value

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self, rows):
        self.rows = list(rows)
        self.cursors = []
        self.closed = False

    def cursor(self):
        row = self.rows.pop(0) if self.rows else None
        cursor = FakeCursor(row)
        self.cursors.append(cursor)
        return cursor

    def close(self):
        self.closed = True


class TestStockSnapshotRepository:
    def test_fetch_source_rows_collects_all_latest_rows(self):
        repo = StockSnapshotRepository()
        conn = FakeConnection([
            {'symbol': 'TCS', 'date': date(2026, 7, 28), 'close': 100.0},
            {'symbol': 'TCS', 'date': date(2026, 7, 28), 'total_score': 88, 'condition_ema_50_200': True},
            {'symbol': 'TCS', 'updated_at': datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc), 'score': 77, 'category': 'HIGH_QUALITY'},
            {'date': date(2026, 7, 28), 'classification': 'BULLISH'},
        ])

        rows = repo.fetch_source_rows('TCS', conn)
        assert rows['indicator_row']['symbol'] == 'TCS'
        assert rows['score_row']['total_score'] == 88
        assert rows['quality_row']['qif_score'] == 77
        assert rows['quality_row']['date'] == datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
        assert rows['regime_row']['classification'] == 'BULLISH'
        assert len(conn.cursors) == 4
        assert conn.cursors[0].executed[0][1] == ('TCS',)

    def test_build_latest_for_symbol_returns_snapshot(self):
        repo = StockSnapshotRepository()
        conn = FakeConnection([
            {
                'symbol': 'TCS',
                'date': date(2026, 7, 28),
                'close': 100.0,
                'volume': 5000.0,
                'ema_10': 95.0,
                'ema_20': 94.0,
                'ema_50': 90.0,
                'ema_100': 85.0,
                'ema_200': 80.0,
                'ema_100_slope_5d': 1.5,
                'ema_200_slope_20': 2.5,
                'rs_90d': 12.0,
                'avg_volume_20d': 4500.0,
                'rolling_high_52w': 110.0,
                'weekly_trend_score': 90.0,
                'overhead_supply_score': 5.0,
                'breakout_state': 'BROKEN_OUT',
                'breakout_age': 2,
                'condition_breakout_10d': True,
                'condition_price_quality': 0.75,
            },
            {'symbol': 'TCS', 'date': date(2026, 7, 28), 'total_score': 84, 'condition_ema_50_200': True},
            {'symbol': 'TCS', 'updated_at': datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc), 'score': 72},
            {'date': date(2026, 7, 28), 'classification': 'BULLISH'},
        ])

        snapshot = repo.build_latest_for_symbol(
            'tcs',
            conn=conn,
            generated_at=datetime(2026, 7, 29, 7, 0, tzinfo=timezone.utc),
        )
        assert snapshot.symbol == 'TCS'
        assert snapshot.mri_score == 55.33
        assert snapshot.quality_score == 72.0
        assert snapshot.market_regime == 'BULLISH'
        assert snapshot.trend_score == 80.0
        assert snapshot.indicators.breakout_age == 2
        assert conn.closed is False

    def test_missing_indicator_row_raises_lookup_error(self):
        repo = StockSnapshotRepository()
        conn = FakeConnection([None])
        with pytest.raises(StockSnapshotNotFoundError, match='No indicator row found for INFY'):
            repo.fetch_source_rows('INFY', conn)

    def test_build_latest_for_symbol_owns_connection_when_it_opens_it(self, monkeypatch):
        repo = StockSnapshotRepository()
        fake_conn = FakeConnection([
            {'symbol': 'INFY', 'date': date(2026, 7, 28), 'close': 100.0},
            None,
            None,
            {'date': date(2026, 7, 28), 'classification': 'NEUTRAL'},
        ])

        import engine_core.portfolio_os_snapshot_repository as mod
        monkeypatch.setattr(mod, 'get_connection', lambda: fake_conn)

        snapshot = repo.build_latest_for_symbol('INFY')
        assert snapshot.symbol == 'INFY'
        assert fake_conn.closed is True
