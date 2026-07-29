from datetime import date
from decimal import Decimal

from engine_core.portfolio_os_snapshot import IndicatorSnapshot, StockSnapshot
from engine_core.portfolio_os_position import PortfolioPosition
from engine_core.portfolio_os_context import DecisionContext
from engine_core.portfolio_os_rule_engine import RuleEngine
from engine_core.portfolio_os_cai_engine import CaiEngine

def run_demo():
    print("--- 🚀 PortfolioOS Demonstration ---")
    print("Setting up a StockSnapshot and PortfolioPosition...")

    # 1. Indicator and Stock Snapshot
    indicators = IndicatorSnapshot(
        close=152.0,
        volume=250000.0,
        ema_10=151.0,
        ema_20=150.0,
        ema_50=140.0,
        ema_100=130.0,
        ema_200=120.0,
        ema_100_slope_5d=1.5,
        ema_200_slope_20=0.5,
        rs_90d=85.0,
        avg_volume_20d=200000.0,
        rolling_high_52w=160.0,
        weekly_trend_score=90.0,
        overhead_supply_score=10.0,
        breakout_state="BROKEN_OUT",
        breakout_age=2,
        condition_breakout_10d=True,
        condition_price_quality=80.0
    )
    
    from datetime import datetime
    snapshot = StockSnapshot(
        symbol="TITAN",
        generated_at=datetime.now(),
        as_of_date=date.today(),
        indicators=indicators,
        market_regime="BULLISH",
        trend_score=92.0,
        breakout_score=88.0,
        quality_score=75.0,
        risk_score=40.0,
        mri_score=82.5,
        mri_grade="HIGH_CONVICTION_BUY",
        supporting_flags=("condition_breakout_10d",)
    )

    # 2. Portfolio Position (Simulate an existing holding)
    position = PortfolioPosition(
        symbol="TITAN",
        entry_price=135.0,
        current_price=152.0,
        quantity=100,
        weeks_held=12,
        highest_price_since_entry=155.0,
        current_allocation=0.05,  # 5%
        number_of_tranches=1,
        current_stop=130.0,
        current_state="FIRST TRANCHE"
    )

    # 3. Context
    context = DecisionContext(
        stock_snapshot=snapshot,
        portfolio_position=position,
        portfolio_context={"cash_reserve": 0.20, "is_averaging_enabled": True},
        rule_set={"hard_stop_loss": 0.08, "take_profit": 0.20}
    )

    print(f"\n[Data] Stock: {snapshot.symbol} | Price: {position.current_price} | MRI: {snapshot.mri_score} ({snapshot.mri_grade})")

    # 4. Rule Engine
    import json
    rules = [
        {
            "name": "Take Profit Triggered",
            "priority": 1,
            "action": "EXIT",
            "condition": {
                "field": "portfolio_position.current_price",
                "operator": ">",
                "value": "context.portfolio_position.entry_price * 1.2"
            }
        },
        {
            "name": "Trend is strong, keep holding",
            "priority": 2,
            "action": "HOLD",
            "condition": {
                "field": "stock_snapshot.trend_score",
                "operator": ">",
                "value": 80
            }
        }
    ]
    rule_engine = RuleEngine(json.dumps(rules))
    rule_result = rule_engine.evaluate(context)

    # 5. CAI Engine
    cai = CaiEngine()
    recommendation = cai.generate_recommendation(context, rule_result)

    print("\n--- 🤖 CAI Recommendation ---")
    print(f"Action:        {recommendation.action}")
    print(f"Confidence:    {recommendation.confidence}%")
    print(f"Action Score:  {recommendation.action_score}")
    print(f"Pos. Size:     {recommendation.position_size_recommendation * 100 if recommendation.position_size_recommendation else 0}%")
    print(f"Primary Reason: {recommendation.primary_reason}")
    if recommendation.supporting_evidence:
        print(f"Evidence:      {', '.join(recommendation.supporting_evidence)}")

if __name__ == '__main__':
    run_demo()
