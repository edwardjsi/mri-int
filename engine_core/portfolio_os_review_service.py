import json
from datetime import datetime, timezone
from typing import Dict, Any, List

from engine_core.db import get_connection
from engine_core.portfolio_os_position_repository import PortfolioPositionRepository
from engine_core.portfolio_os_snapshot_repository import StockSnapshotRepository
from engine_core.portfolio_os_context import DecisionContext
from engine_core.portfolio_os_rule_engine import RuleEngine
from engine_core.portfolio_os_cai_engine import CaiEngine
from engine_core.ciw_repository import CompanyWorkspaceRepository


class PortfolioOsReviewService:
    def __init__(self):
        self.pos_repo = PortfolioPositionRepository()
        self.snap_repo = StockSnapshotRepository()
        self.cai_engine = CaiEngine()
        
        # Load external rules (hardcoded for MVP V1 based on PRD requirements)
        rules = [
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
                        {
                            "field": "stock_snapshot.trend_score",
                            "operator": ">=",
                            "value": 80
                        },
                        {
                            "field": "stock_snapshot.mri_score",
                            "operator": ">=",
                            "value": 80
                        }
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
            },
            {
                "name": "Trend weakening",
                "priority": 4,
                "action": "HOLD",
                "condition": {
                    "field": "stock_snapshot.trend_score",
                    "operator": "<",
                    "value": 50
                },
                "reason": "Trend is weakening (score below 50). Holding but monitoring closely for exit triggers."
            }
        ]
        self.rule_engine = RuleEngine(json.dumps(rules))

    def generate_weekly_review(self, client_id: str) -> Dict[str, Any]:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                # 1. Fetch all active positions for the user's CAI portfolio
                # For V1, we assume client_external_holdings or cai_position. 
                # According to the PRD, we use cai_position linked to cai_portfolio.
                cur.execute(
                    """
                    SELECT p.id, p.symbol
                    FROM cai_position p
                    JOIN cai_portfolio port ON p.portfolio_id = port.id
                    WHERE port.owner = %s AND p.status != 'CLOSED'
                    """,
                    (client_id,)
                )
                positions_data = cur.fetchall()

                holdings = []
                action_queue = []
                review_queue = []
                
                total_invested = 0.0
                total_current = 0.0
                
                market_regime = "Bull"  # Default / Fallback
                
                for row in positions_data:
                    # Handle both DictCursor and Tuple Cursor gracefully
                    if isinstance(row, dict):
                        pid, symbol = row['id'], row['symbol']
                    else:
                        pid, symbol = row[0], row[1]
                        
                    try:
                        position = self.pos_repo.get_position_by_id(pid, conn=conn)
                        snapshot = self.snap_repo.build_latest_for_symbol(symbol, conn=conn)
                        
                        market_regime = snapshot.market_regime or market_regime
                        
                        # Set a dummy stop if 0 for demo purposes to avoid instant exits on everything
                        if position.current_stop == 0.0:
                            position = type(position)(**{**position.__dict__, "current_stop": position.entry_price * 0.85})

                        # Phase 2: Fetch CIW Knowledge as preferred context
                        ciw_repo = CompanyWorkspaceRepository(conn=conn)
                        workspace = ciw_repo.get_workspace(symbol)

                        ciw_thesis = None
                        ciw_business_quality = None
                        ciw_risks = None
                        ciw_catalysts = None
                        ciw_monitoring = None

                        if workspace:
                            ciw_thesis = workspace.state.understanding.get('thesis').text if workspace.state.understanding.get('thesis') else None
                            ciw_business_quality = workspace.state.understanding.get('business_quality').text if workspace.state.understanding.get('business_quality') else None
                            ciw_risks = [r.dict() for r in workspace.state.risks] if hasattr(workspace.state.risks, '__iter__') else None
                            ciw_catalysts = [c.dict() for c in workspace.state.catalysts] if hasattr(workspace.state.catalysts, '__iter__') else None
                            ciw_monitoring = [m.dict() for m in workspace.state.monitoring] if hasattr(workspace.state.monitoring, '__iter__') else None

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
                        
                        rule_result = self.rule_engine.evaluate(context)
                        rec = self.cai_engine.generate_recommendation(context, rule_result)
                        
                        invested = position.quantity * position.entry_price
                        current_val = position.quantity * position.current_price
                        total_invested += invested
                        total_current += current_val
                        
                        pl_pct = ((current_val - invested) / invested * 100) if invested > 0 else 0.0
                        
                        mri_score = snapshot.mri_score or 0.0
                        cai_score = rec.action_score or 0.0
                        
                        holdings.append({
                            "ticker": symbol,
                            "quantity": position.quantity,
                            "avg_price": position.entry_price,
                            "current_price": position.current_price,
                            "pl_pct": round(pl_pct, 2),
                            "mri_score": round(mri_score, 1),
                            "cai_score": round(cai_score, 1),
                            "current_action": rec.action,
                            "review_status": rec.review_status,
                            "review_reason": rec.review_reason,
                            "next_tranche": "N/A",
                            "structure_stop": position.current_stop,
                            "confidence": rec.confidence,
                            "primary_reason": rec.primary_reason,
                            "secondary_reason": rec.secondary_reason,
                            "supporting_evidence": rec.supporting_evidence,
                            "last_reviewed": snapshot.as_of_date.isoformat(),
                            "explanation_tree": rec.explanation_tree.to_dict() if rec.explanation_tree else None
                        })
                        
                        if rec.action in ["BUY", "ADD", "REDUCE", "ROTATE", "EXIT"]:
                            action_queue.append({
                                "stock": symbol,
                                "mri": round(mri_score, 1),
                                "cai": round(cai_score, 1),
                                "action": rec.action,
                                "confidence": rec.confidence,
                                "reason": rec.primary_reason,
                                "explanation_tree": rec.explanation_tree.to_dict() if rec.explanation_tree else None
                            })
                            
                        if rec.review_status in ["REVIEW_REQUIRED", "URGENT_REVIEW"]:
                            review_queue.append({
                                "stock": symbol,
                                "status": rec.review_status,
                                "reason": rec.review_reason
                            })
                            
                    except Exception as e:
                        # Log error but continue processing other positions
                        print(f"Error processing {symbol}: {e}")

                # Sort Action Queue: EXIT > REDUCE > ADD > BUY > HOLD (WAIT/REVIEW)
                action_priority = {"EXIT": 1, "REDUCE": 2, "ADD": 3, "BUY": 4, "HOLD": 5, "REVIEW": 6, "WAIT": 7}
                action_queue.sort(key=lambda x: (action_priority.get(x["action"], 99), -x["confidence"]))
                
                # Determine Highest Priority Decision
                highest_priority_decision = {}
                if action_queue:
                    top_action = action_queue[0]
                    highest_priority_decision = {
                        "action": top_action["action"],
                        "stock": top_action["stock"],
                        "recommended_amount": "Based on Allocation",
                        "reason": top_action["reason"],
                        "confidence": top_action["confidence"],
                        "mri_score": top_action["mri"],
                        "cai_score": top_action["cai"]
                    }
                
                # Calculate Portfolio Health and Summary
                overall_health = 90  # Placeholder for complex computation
                total_portfolio_value = total_current + 315000  # Assume some cash
                deployment_pct = (total_current / total_portfolio_value * 100) if total_portfolio_value > 0 else 0
                
                portfolio_summary = {
                    "market_regime": market_regime,
                    "portfolio_health": overall_health,
                    "deployment_pct": round(deployment_pct, 1),
                    "cash_available": 315000,
                    "cash_target_pct": 20,
                    "holdings_count": len(holdings),
                    "action_items_count": len(action_queue),
                    "review_items_count": len(review_queue),
                    "analysis_time": datetime.now(timezone.utc).isoformat()
                }
                
                # Generate Warnings
                warnings = []
                if deployment_pct > 80:
                    warnings.append("Cash below target.")
                
                # V1: Return the exact JSON contract
                return {
                    "portfolio_summary": portfolio_summary,
                    "highest_priority_decision": highest_priority_decision,
                    "action_queue": action_queue,
                    "review_queue": review_queue,
                    "holdings": holdings,
                    "opportunities": [],  # Deferred to V2 or separate scan
                    "warnings": warnings,
                    "decision_history": [] # Deferred to Decision Ledger integration
                }

        finally:
            conn.close()

    def approve_weekly_review(self, client_id: str) -> Dict[str, Any]:
        """
        Executes a weekly review and records all generated decisions to the Decision Ledger.
        Returns the number of recorded decisions.
        """
        from engine_core.portfolio_os_ledger_repository import DecisionLedgerRepository
        
        # 1. Run the analysis to get the latest recommendations
        review_data = self.generate_weekly_review(client_id)
        action_queue = review_data.get("action_queue", [])
        
        if not action_queue:
            return {"status": "success", "recorded_count": 0, "message": "No actions to record"}
            
        conn = get_connection()
        ledger_repo = DecisionLedgerRepository()
        recorded_count = 0
        
        try:
            # Generate a single report ID for this batch of decisions
            report_id = f"report_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
            
            with conn.cursor() as cur:
                # Ensure the committee report exists
                cur.execute(
                    """
                    INSERT INTO cai_committee_report (id, week_end, created_at)
                    VALUES (%s, CURRENT_DATE, CURRENT_TIMESTAMP)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (report_id,)
                )
                
                # Fetch positions to get position IDs for the symbols
                cur.execute(
                    """
                    SELECT p.id, p.symbol
                    FROM cai_position p
                    JOIN cai_portfolio port ON p.portfolio_id = port.id
                    WHERE port.owner = %s AND p.status != 'CLOSED'
                    """,
                    (client_id,)
                )
                pos_map = {row['symbol'] if isinstance(row, dict) else row[1]: row['id'] if isinstance(row, dict) else row[0] for row in cur.fetchall()}
                
                for action in action_queue:
                    symbol = action["stock"]
                    position_id = pos_map.get(symbol, f"pos_{symbol.lower()}")
                    
                    # Log into Committee Decision
                    cur.execute(
                        """
                        INSERT INTO cai_committee_decision (report_id, position_id, recommendation, amount, reason)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (report_id, position_id) 
                        DO UPDATE SET recommendation = EXCLUDED.recommendation, amount = EXCLUDED.amount, reason = EXCLUDED.reason
                        """,
                        (
                            report_id,
                            position_id,
                            action["action"],
                            0.0, # Placeholder for amount
                            f"{action['reason']} | Confidence: {action['confidence']}% | MRI: {action['mri']}"
                        )
                    )
                    
                    # Log into Decision Ledger
                    ledger_id = f"ldg_{datetime.now(timezone.utc).strftime('%H%M%S')}_{symbol}"
                    cur.execute(
                        """
                        INSERT INTO cai_decision_ledger (id, decision_report_id, decision_position_id, execution_status)
                        VALUES (%s, %s, %s, 'PENDING')
                        ON CONFLICT DO NOTHING
                        """,
                        (ledger_id, report_id, position_id)
                    )
                    recorded_count += 1
            
            conn.commit()
            return {"status": "success", "recorded_count": recorded_count, "report_id": report_id}
            
        except Exception as e:
            conn.rollback()
            print(f"Error recording decisions: {e}")
            raise e
        finally:
            conn.close()
