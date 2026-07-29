import os
import sys
from datetime import date, datetime, timezone

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_core.portfolio_os_snapshot import StockSnapshot, IndicatorSnapshot
from engine_core.portfolio_os_position import PortfolioPosition
from engine_core.portfolio_os_context import DecisionContext
from engine_core.portfolio_os_cai_engine import CaiRecommendation
from engine_core.portfolio_os_ledger_repository import DecisionLedgerRepository  # noqa: E402


class FakeCursor:
    def __init__(self):
        self.executed_queries = []

    def execute(self, query, params=None):
        self.executed_queries.append((query, params))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class FakeConnection:
    def __init__(self):
        self.cursor_obj = FakeCursor()
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        pass


class TestDecisionLedgerRepository:
    def setup_method(self):
        self.repo = DecisionLedgerRepository()
        self.indicator = IndicatorSnapshot(
            close=100.0, volume=1000000, ema_10=90.0, ema_20=85.0, ema_50=80.0,
            ema_100=75.0, ema_200=70.0, ema_100_slope_5d=1.0, ema_200_slope_20=2.0,
            rs_90d=10.0, avg_volume_20d=900000, rolling_high_52w=110.0,
            weekly_trend_score=90.0, overhead_supply_score=0.0,
            breakout_state="BROKEN_OUT", breakout_age=1,
            condition_breakout_10d=True, condition_price_quality=0.8
        )
        self.snapshot = StockSnapshot(
            symbol="TCS", as_of_date=date(2026, 7, 28), generated_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
            market_regime="BULLISH", mri_score=85.0, mri_grade="HIGH_CONVICTION_BUY",
            trend_score=90.0, quality_score=80.0, breakout_score=85.0, risk_score=20.0,
            indicators=self.indicator, supporting_flags=()
        )
        self.position = PortfolioPosition(
            symbol="TCS", entry_price=90.0, current_price=100.0, quantity=50, weeks_held=2,
            highest_price_since_entry=105.0, current_allocation=0.05, number_of_tranches=1,
            current_stop=85.0, current_state="FIRST TRANCHE"
        )
        # Hack to assign ID for testing (since it's an immutable dataclass, we'll bypass it or let it use the fallback)
        self.context = DecisionContext(stock_snapshot=self.snapshot, portfolio_position=self.position)
        
        self.rec = CaiRecommendation(
            action="ADD",
            confidence=95.0,
            action_score=85.0,
            primary_reason="Momentum continuation",
            secondary_reason="Bullish regime",
            supporting_evidence=[],
            position_size_recommendation=0.10
        )

    def test_record_decision_executes_correct_inserts(self):
        conn = FakeConnection()
        ledger_id = self.repo.record_decision(
            context=self.context,
            recommendation=self.rec,
            conn=conn,
            report_id="test_report_123"
        )
        
        assert ledger_id.startswith("ldg_")
        queries = conn.cursor_obj.executed_queries
        assert len(queries) == 3
        
        # 1. Report Check
        assert "INSERT INTO cai_committee_report" in queries[0][0]
        assert queries[0][1] == ("test_report_123",)
        
        # 2. Decision Check
        assert "INSERT INTO cai_committee_decision" in queries[1][0]
        params = queries[1][1]
        assert params[0] == "test_report_123"
        assert params[1] == "pos_tcs"  # Fallback ID logic
        assert params[2] == "ADD"
        assert params[3] == 0.10
        assert "Momentum continuation" in params[4]
        assert "Confidence: 95.0%" in params[4]
        
        # 3. Ledger Check
        assert "INSERT INTO cai_decision_ledger" in queries[2][0]
        assert queries[2][1][1] == "test_report_123"
        assert queries[2][1][2] == "pos_tcs"
