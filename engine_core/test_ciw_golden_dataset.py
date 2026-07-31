import os
import sys
import json
import pytest
from datetime import datetime, date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_core.db import get_connection
from engine_core.portfolio_os_context import DecisionContext
from engine_core.portfolio_os_rule_engine import RuleEngine
from engine_core.portfolio_os_cai_engine import CaiEngine
from engine_core.ciw_repository import CompanyWorkspaceRepository
from engine_core.portfolio_os_position import PortfolioPosition
from engine_core.portfolio_os_snapshot import StockSnapshot, IndicatorSnapshot


rules_json = json.dumps([
    {
        "name": "Structure Broken / Stop Loss Hit",
        "priority": 1,
        "action": "EXIT",
        "condition": {
            "field": "portfolio_position.current_price",
            "operator": "<",
            "value": "context.portfolio_position.current_stop"
        },
        "reason": "Price has fallen below the trailing structure stop loss."
    },
    {
        "name": "Trend intact",
        "priority": 3,
        "action": "HOLD",
        "condition": {
            "field": "stock_snapshot.trend_score",
            "operator": ">=",
            "value": 50
        },
        "reason": "Trend score remains strong above 50, supporting continued ownership."
    }
])


@pytest.fixture
def repo():
    conn = get_connection()
    repo = CompanyWorkspaceRepository(conn=conn)
    yield repo
    repo.close()

@pytest.fixture
def rule_engine():
    return RuleEngine(rules_json)

@pytest.fixture
def cai_engine():
    return CaiEngine()


def build_mock_context(symbol: str, workspace) -> DecisionContext:
    position = PortfolioPosition(
        symbol=symbol,
        quantity=100,
        entry_price=100.0,
        current_price=120.0,
        current_stop=90.0,
        current_allocation=0.05,
        weeks_held=12,
        highest_price_since_entry=125.0,
        number_of_tranches=1,
        current_state="OPEN"
    )

    snapshot = StockSnapshot(
        symbol=symbol,
        generated_at=datetime.now(),
        as_of_date=date.today(),
        market_regime="BULL",
        trend_score=85.0,
        mri_score=82.0,
        risk_score=20.0,
        mri_grade="HIGH_CONVICTION_BUY",
        breakout_score=0.0,
        quality_score=0.0,
        supporting_flags=tuple(),
        indicators=IndicatorSnapshot(
            close=120.0, volume=1000, ema_10=115, ema_20=110, ema_50=100, ema_100=90, ema_200=80,
            ema_100_slope_5d=1.0, ema_200_slope_20=1.0, rs_90d=1.5, avg_volume_20d=1000, rolling_high_52w=125,
            weekly_trend_score=85, overhead_supply_score=0, breakout_state=None, breakout_age=None,
            condition_breakout_10d=False, condition_price_quality=0.0
        )
    )

    ciw_thesis = workspace.state.understanding.get('thesis').text if workspace.state.understanding.get('thesis') else None
    ciw_business_quality = workspace.state.understanding.get('business_quality').text if workspace.state.understanding.get('business_quality') else None
    
    return DecisionContext(
        stock_snapshot=snapshot,
        portfolio_position=position,
        portfolio_context={"cash_reserve": 0.10, "is_averaging_enabled": True},
        rule_set={},
        ciw_thesis=ciw_thesis,
        ciw_business_quality=ciw_business_quality
    )


def test_neulandlab_golden_dataset(repo, rule_engine, cai_engine):
    symbol = "NEULANDLAB"
    workspace = repo.get_workspace(symbol)
    assert workspace is not None, f"Golden dataset missing {symbol}"

    context = build_mock_context(symbol, workspace)
    rule_result = rule_engine.evaluate(context)
    rec = cai_engine.generate_recommendation(context, rule_result)

    assert rec.action == "HOLD"
    assert "CIW Thesis: Transitioning from pure API to high-margin CMS" in rec.primary_reason
    assert "Quality: High switching costs" in rec.secondary_reason
    
    has_ciw_evidence = any(e.name == "CIW Thesis" for e in rec.evidence)
    assert has_ciw_evidence, "CIW Thesis missing from XAI evidence"


def test_sparseco_fallback(repo, rule_engine, cai_engine):
    symbol = "SPARSECO"
    workspace = repo.get_workspace(symbol)
    assert workspace is not None, f"Golden dataset missing {symbol}"

    context = build_mock_context(symbol, workspace)
    rule_result = rule_engine.evaluate(context)
    rec = cai_engine.generate_recommendation(context, rule_result)

    assert rec.action == "HOLD"
    assert "CIW Thesis: Generic thesis" in rec.primary_reason
    assert "Quality" not in rec.secondary_reason
    assert "Market Regime is BULL" in rec.secondary_reason
