import json
from engine_core.db import get_connection
from engine_core.portfolio_os_position_repository import PortfolioPositionRepository
from engine_core.portfolio_os_snapshot_repository import StockSnapshotRepository
from engine_core.portfolio_os_context import DecisionContext
from engine_core.portfolio_os_rule_engine import RuleEngine
from engine_core.portfolio_os_cai_engine import CaiEngine

def run_portfolio():
    print("--- 🚀 Live PortfolioOS Run on CAI Portfolio ---")
    
    # 1. Instantiate repositories & engines
    pos_repo = PortfolioPositionRepository()
    snap_repo = StockSnapshotRepository()
    
    # Define a basic ruleset (similar to what an external YAML would load)
    rules = [
        {
            "name": "Take Profit Triggered",
            "priority": 1,
            "action": "EXIT",
            "condition": {
                "field": "portfolio_position.current_price",
                "operator": ">",
                "value": "context.portfolio_position.entry_price * 1.5"
            }
        },
        {
            "name": "Stop Loss Hit",
            "priority": 2,
            "action": "EXIT",
            "condition": {
                "field": "portfolio_position.current_price",
                "operator": "<",
                "value": "context.portfolio_position.entry_price * 0.9"
            }
        },
        {
            "name": "Trend is strong, keep holding",
            "priority": 3,
            "action": "HOLD",
            "condition": {
                "field": "stock_snapshot.trend_score",
                "operator": ">",
                "value": 75
            }
        }
    ]
    rule_engine = RuleEngine(json.dumps(rules))
    cai_engine = CaiEngine()
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Fetch all active positions
            cur.execute("SELECT id, symbol FROM cai_position WHERE status != 'EXITED' LIMIT 15")
            positions = cur.fetchall()
            
            if not positions:
                print("No active positions found in `cai_position` table.")
                return

            print(f"Found {len(positions)} active positions. Evaluating...")
            print("-" * 80)
            
            for row in positions:
                if isinstance(row, dict):
                    pid, symbol = row['id'], row['symbol']
                else:
                    pid, symbol = row[0], row[1]
                try:
                    position = pos_repo.get_position_by_id(pid, conn=conn)
                    snapshot = snap_repo.build_latest_for_symbol(symbol, conn=conn)
                    
                    context = DecisionContext(
                        stock_snapshot=snapshot,
                        portfolio_position=position,
                        portfolio_context={"cash_reserve": 0.10, "is_averaging_enabled": True},
                        rule_set={}
                    )
                    
                    rule_result = rule_engine.evaluate(context)
                    recommendation = cai_engine.generate_recommendation(context, rule_result)
                    
                    mri_score = snapshot.mri_score or 0
                    print(f"[{symbol:<10}] Entry: {position.entry_price:>7.2f} | Current: {position.current_price:>7.2f} | "
                          f"MRI: {mri_score:>5.1f} | Action: {recommendation.action:<5} | "
                          f"Confidence: {recommendation.confidence:>5.1f}% | Reason: {recommendation.primary_reason}")
                except Exception as e:
                    print(f"[{symbol:<10}] Error evaluating: {e}")
            print("-" * 80)
            
    finally:
        conn.close()

if __name__ == '__main__':
    run_portfolio()
