import os
import sys
from datetime import date, datetime, timezone

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_core.portfolio_os_snapshot import StockSnapshot, IndicatorSnapshot
from engine_core.portfolio_os_position import PortfolioPosition
from engine_core.portfolio_os_context import DecisionContext
from engine_core.portfolio_os_rule_engine import RuleEvaluationResult
from engine_core.portfolio_os_cai_engine import CaiEngine, CaiRecommendation  # noqa: E402


class TestCaiEngine:
    def setup_method(self):
        self.engine = CaiEngine()
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
            indicators=self.indicator, supporting_flags=("condition_rs",)
        )
        self.position = PortfolioPosition(
            symbol="TCS", entry_price=90.0, current_price=100.0, quantity=50, weeks_held=2,
            highest_price_since_entry=105.0, current_allocation=0.05, number_of_tranches=1,
            current_stop=85.0, current_state="FIRST TRANCHE"
        )
        self.context = DecisionContext(stock_snapshot=self.snapshot, portfolio_position=self.position)

    def test_generates_high_confidence_buy(self):
        rule_result = RuleEvaluationResult(action="BUY", triggered_rule="Momentum Breakout", reason="Stock broke out")
        rec = self.engine.generate_recommendation(self.context, rule_result)
        
        assert rec.action == "BUY"
        # Volume exists, Bullish regime, low risk => 100 confidence
        assert rec.confidence == 100.0
        assert rec.action_score == 85.0
        # High confidence BUY => 10% allocation
        assert rec.position_size_recommendation == 0.10
        assert "Stock broke out" in rec.primary_reason

    def test_generates_low_confidence_due_to_regime_and_risk(self):
        # Alter snapshot to bearish and high risk
        bear_snapshot = StockSnapshot(
            symbol="TCS", as_of_date=date(2026, 7, 28), generated_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
            market_regime="BEARISH", mri_score=40.0, mri_grade="HOLD_MONITOR",
            trend_score=40.0, quality_score=80.0, breakout_score=10.0, risk_score=85.0,
            indicators=self.indicator, supporting_flags=()
        )
        bear_context = DecisionContext(stock_snapshot=bear_snapshot, portfolio_position=self.position)
        
        rule_result = RuleEvaluationResult(action="BUY", triggered_rule="Dip Buy", reason="Oversold")
        rec = self.engine.generate_recommendation(bear_context, rule_result)
        
        # 100 - 15 (bearish) - 10 (high risk) = 75
        assert rec.confidence == 75.0
        # Confidence 75 falls in the 5% allocation bracket for BUY
        assert rec.position_size_recommendation == 0.05

    def test_exit_action_results_in_zero_allocation(self):
        rule_result = RuleEvaluationResult(action="EXIT", triggered_rule="Stop Hit", reason="Stop loss")
        rec = self.engine.generate_recommendation(self.context, rule_result)
        
        assert rec.action == "EXIT"
        assert rec.position_size_recommendation == 0.0

    def test_wait_action_maintains_current_allocation(self):
        rule_result = RuleEvaluationResult(action="WAIT", triggered_rule="Consolidating", reason="Wait for setup")
        rec = self.engine.generate_recommendation(self.context, rule_result)
        
        assert rec.action == "WAIT"
        assert rec.position_size_recommendation == 0.05  # from the portfolio_position
