import os
import json
from engine_core.db import get_connection
from engine_core.portfolio_os_context import DecisionContext
from engine_core.portfolio_os_rule_engine import RuleEngine
from engine_core.portfolio_os_cai_engine import CaiEngine
from engine_core.ciw_repository import CompanyWorkspaceRepository
from engine_core.portfolio_os_position import PortfolioPosition
from engine_core.portfolio_os_snapshot import StockSnapshot, IndicatorSnapshot
from datetime import datetime, date

# Basic rules matching production MVP
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
        "name": "First tranche earned next tranche",
        "priority": 2,
        "action": "ADD",
        "condition": {
            "AND": [
                {"field": "stock_snapshot.trend_score", "operator": ">=", "value": 80},
                {"field": "stock_snapshot.mri_score", "operator": ">=", "value": 80}
            ]
        },
        "reason": "Strong MRI and trend score indicate ideal conditions to add next tranche."
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

def run_validation():
    conn = get_connection()
    ciw_repo = CompanyWorkspaceRepository(conn=conn)
    rule_engine = RuleEngine(rules_json)
    cai_engine = CaiEngine()

    symbols = ['NEULANDLAB', 'POLYCAB', 'DIVISLAB', 'DELHIVERY', 'TORNTPHARM', 'WELCORP', 'POONAWALLA', 'HOMEFIRST', 'SPARSECO']
    
    report_lines = [
        "# CIW Golden Dataset Validation Report",
        "",
        "This report validates that the Decision Engine gracefully consumes CIW abstractions.",
        ""
    ]

    try:
        for symbol in symbols:
            workspace = ciw_repo.get_workspace(symbol)
            if not workspace:
                continue

            # Mock portfolio position (simulating a healthy ongoing position)
            position = PortfolioPosition(
                symbol=symbol,
                quantity=100,
                entry_price=100.0,
                current_price=120.0,  # 20% profit
                current_stop=90.0,
                current_allocation=0.05,
                weeks_held=12,
                highest_price_since_entry=125.0,
                number_of_tranches=1,
                current_state="OPEN"
            )

            # Mock snapshot 
            snapshot = StockSnapshot(
                symbol=symbol,
                generated_at=datetime.now(),
                as_of_date=date.today(),
                market_regime="BULL",
                trend_score=85.0,  # Strong trend
                mri_score=82.0,    # Strong MRI
                risk_score=20.0,   # Low risk
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

            # Extract CIW fields
            ciw_thesis = workspace.state.understanding.get('thesis').text if workspace.state.understanding.get('thesis') else None
            ciw_business_quality = workspace.state.understanding.get('business_quality').text if workspace.state.understanding.get('business_quality') else None
            ciw_risks = [r.dict() for r in workspace.state.risks] if workspace.state.risks else None
            ciw_catalysts = [c.dict() for c in workspace.state.catalysts] if workspace.state.catalysts else None
            ciw_monitoring = [m.dict() for m in workspace.state.monitoring] if workspace.state.monitoring else None

            # Build context
            context = DecisionContext(
                stock_snapshot=snapshot,
                portfolio_position=position,
                portfolio_context={"cash_reserve": 0.10, "is_averaging_enabled": True},
                rule_set={},
                ciw_thesis=ciw_thesis,
                ciw_business_quality=ciw_business_quality,
                ciw_risks=ciw_risks,
                ciw_catalysts=ciw_catalysts,
                ciw_monitoring=ciw_monitoring
            )

            rule_result = rule_engine.evaluate(context)
            rec = cai_engine.generate_recommendation(context, rule_result)

            # Format the output
            report_lines.extend([
                f"## {symbol}",
                f"- **Actual Decision**: {rec.action} (Confidence: {rec.confidence})",
                f"- **Primary Reason**: {rec.primary_reason}",
                f"- **Secondary Reason**: {rec.secondary_reason}",
                f"- **Evidence Points**: {', '.join(rec.supporting_evidence) if rec.supporting_evidence else 'None'}",
                f"- **XAI Tree Node Count**: {len(rec.evidence) if rec.evidence else 0} CIW context objects detected.",
                "---"
            ])

        os.makedirs("artifacts", exist_ok=True)
        with open("artifacts/ciw_validation_report.md", "w") as f:
            f.write("\n".join(report_lines))
        
        print("✅ Validation report generated at artifacts/ciw_validation_report.md")

    finally:
        ciw_repo.close()

if __name__ == "__main__":
    run_validation()
