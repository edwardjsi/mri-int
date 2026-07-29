import os
import sys
from datetime import date, datetime, timezone
from dataclasses import FrozenInstanceError

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_core.portfolio_os_snapshot import StockSnapshot, IndicatorSnapshot
from engine_core.portfolio_os_position import PortfolioPosition
from engine_core.portfolio_os_context import DecisionContext, PortfolioContext  # noqa: E402


class TestDecisionContext:
    def test_creates_valid_context(self):
        indicator = IndicatorSnapshot(
            close=100.0, volume=1000, ema_10=90.0, ema_20=85.0, ema_50=80.0,
            ema_100=75.0, ema_200=70.0, ema_100_slope_5d=1.0, ema_200_slope_20=2.0,
            rs_90d=10.0, avg_volume_20d=900, rolling_high_52w=110.0,
            weekly_trend_score=90.0, overhead_supply_score=0.0,
            breakout_state="BROKEN_OUT", breakout_age=1,
            condition_breakout_10d=True, condition_price_quality=0.8
        )
        
        snapshot = StockSnapshot(
            symbol="TCS",
            as_of_date=date(2026, 7, 28),
            generated_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
            market_regime="BULLISH",
            mri_score=85.0,
            mri_grade="HIGH_CONVICTION_BUY",
            trend_score=90.0,
            quality_score=80.0,
            breakout_score=85.0,
            risk_score=95.0,
            indicators=indicator,
            supporting_flags=("condition_rs",)
        )
        
        position = PortfolioPosition(
            symbol="TCS",
            entry_price=90.0,
            current_price=100.0,
            quantity=50,
            weeks_held=2,
            highest_price_since_entry=105.0,
            current_allocation=0.05,
            number_of_tranches=1,
            current_stop=85.0,
            current_state="FIRST TRANCHE"
        )
        
        portfolio = PortfolioContext(
            cash=10000.0,
            total_value=100000.0,
            health_score=85.0
        )
        
        context = DecisionContext(
            stock_snapshot=snapshot,
            portfolio_position=position,
            portfolio_context=portfolio,
            rule_set="MOMENTUM_V1"
        )
        
        assert context.stock_snapshot.symbol == "TCS"
        assert context.portfolio_position.current_allocation == 0.05
        assert context.portfolio_context.health_score == 85.0
        assert context.rule_set == "MOMENTUM_V1"

    def test_requires_stock_snapshot(self):
        with pytest.raises(ValueError, match="stock_snapshot is required"):
            DecisionContext(stock_snapshot=None)

    def test_is_immutable(self):
        snapshot = StockSnapshot(
            symbol="TCS",
            as_of_date=date(2026, 7, 28),
            generated_at=datetime(2026, 7, 29, tzinfo=timezone.utc),
            market_regime="BULLISH",
            mri_score=85.0,
            mri_grade="HIGH_CONVICTION_BUY",
            trend_score=90.0,
            quality_score=80.0,
            breakout_score=85.0,
            risk_score=95.0,
            indicators=None,
            supporting_flags=()
        )
        context = DecisionContext(stock_snapshot=snapshot)
        with pytest.raises(FrozenInstanceError):
            context.rule_set = "NEW_RULE"
