import os
import sys
import json
from datetime import date, datetime, timezone

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_core.portfolio_os_snapshot import StockSnapshot, IndicatorSnapshot
from engine_core.portfolio_os_position import PortfolioPosition
from engine_core.portfolio_os_context import DecisionContext
from engine_core.portfolio_os_rule_engine import RuleEngine, RuleEvaluationResult  # noqa: E402


class TestRuleEngine:
    def setup_method(self):
        self.indicator = IndicatorSnapshot(
            close=100.0, volume=1000, ema_10=90.0, ema_20=85.0, ema_50=80.0,
            ema_100=75.0, ema_200=70.0, ema_100_slope_5d=1.0, ema_200_slope_20=2.0,
            rs_90d=10.0, avg_volume_20d=900, rolling_high_52w=110.0,
            weekly_trend_score=90.0, overhead_supply_score=0.0,
            breakout_state="BROKEN_OUT", breakout_age=1,
            condition_breakout_10d=True, condition_price_quality=0.8
        )
        self.snapshot = StockSnapshot(
            symbol="TCS", as_of_date=date(2026, 7, 28), generated_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
            market_regime="BULLISH", mri_score=85.0, mri_grade="HIGH_CONVICTION_BUY",
            trend_score=90.0, quality_score=80.0, breakout_score=85.0, risk_score=95.0,
            indicators=self.indicator, supporting_flags=("condition_rs",)
        )
        self.position = PortfolioPosition(
            symbol="TCS", entry_price=90.0, current_price=100.0, quantity=50, weeks_held=2,
            highest_price_since_entry=105.0, current_allocation=0.05, number_of_tranches=1,
            current_stop=85.0, current_state="FIRST TRANCHE"
        )
        self.context = DecisionContext(stock_snapshot=self.snapshot, portfolio_position=self.position)

    def test_evaluates_simple_hard_rule_exit(self):
        rules = [
            {
                "name": "Stop Loss Hit",
                "priority": 1,
                "action": "EXIT",
                "condition": {
                    "field": "portfolio_position.current_price",
                    "operator": "<",
                    "value": "context.portfolio_position.current_stop"
                }
            }
        ]
        
        # Modify the context to simulate stop loss hit
        losing_pos = PortfolioPosition(
            symbol="TCS", entry_price=90.0, current_price=80.0, quantity=50, weeks_held=2,
            highest_price_since_entry=105.0, current_allocation=0.05, number_of_tranches=1,
            current_stop=85.0, current_state="FIRST TRANCHE"
        )
        losing_context = DecisionContext(stock_snapshot=self.snapshot, portfolio_position=losing_pos)
        
        engine = RuleEngine(json.dumps(rules))
        result = engine.evaluate(losing_context)
        
        assert result.action == "EXIT"
        assert result.triggered_rule == "Stop Loss Hit"

    def test_evaluates_and_condition(self):
        rules = [
            {
                "name": "First Tranche Losing, No Averaging",
                "action": "WAIT",
                "condition": {
                    "AND": [
                        {
                            "field": "portfolio_position.current_state",
                            "operator": "==",
                            "value": "FIRST TRANCHE"
                        },
                        {
                            "field": "portfolio_position.current_price",
                            "operator": "<",
                            "value": "context.portfolio_position.entry_price"
                        }
                    ]
                }
            }
        ]
        losing_pos = PortfolioPosition(
            symbol="TCS", entry_price=100.0, current_price=95.0, quantity=50, weeks_held=2,
            highest_price_since_entry=105.0, current_allocation=0.05, number_of_tranches=1,
            current_stop=85.0, current_state="FIRST TRANCHE"
        )
        losing_context = DecisionContext(stock_snapshot=self.snapshot, portfolio_position=losing_pos)
        
        engine = RuleEngine(json.dumps(rules))
        result = engine.evaluate(losing_context)
        
        assert result.action == "WAIT"

    def test_no_rules_triggered_returns_none(self):
        rules = [
            {
                "name": "Only triggers on AVOID",
                "action": "EXIT",
                "condition": {
                    "field": "stock_snapshot.mri_grade",
                    "operator": "==",
                    "value": "AVOID"
                }
            }
        ]
        engine = RuleEngine(json.dumps(rules))
        result = engine.evaluate(self.context)
        
        assert result.action is None
        assert result.triggered_rule is None
        assert result.reason == "No rules triggered"
