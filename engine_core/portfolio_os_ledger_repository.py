import uuid
from typing import Any
from datetime import datetime, timezone

from engine_core.portfolio_os_context import DecisionContext
from engine_core.portfolio_os_cai_engine import CaiRecommendation


class DecisionLedgerRepository:
    """
    Module 9: Decision Ledger.
    Records generated CAI Recommendations to the database for audit and execution.
    """

    def record_decision(
        self,
        context: DecisionContext,
        recommendation: CaiRecommendation,
        conn: Any,
        report_id: str = None
    ) -> str:
        """
        Persists a CaiRecommendation into the cai_committee_decision and cai_decision_ledger tables.
        Requires a database connection.
        Returns the generated ledger ID.
        """
        # 1. Ensure we have a report ID (usually generated per batch run)
        current_report_id = report_id or f"report_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        
        # 2. Extract context data
        symbol = context.stock_snapshot.symbol
        # Fallback to symbol if no position ID exists (e.g., new BUY)
        position_id = context.portfolio_position.id if getattr(context.portfolio_position, 'id', None) else f"pos_{symbol.lower()}"
        
        reason_text = f"{recommendation.primary_reason} | Confidence: {recommendation.confidence}% | MRI: {recommendation.action_score}"
        
        with conn.cursor() as cursor:
            # 3. Upsert Committee Report (if not exists)
            # In a real batch process, the report is created once. For single inserts, we ensure it exists.
            cursor.execute(
                """
                INSERT INTO cai_committee_report (id, week_end, created_at)
                VALUES (%s, CURRENT_DATE, CURRENT_TIMESTAMP)
                ON CONFLICT (id) DO NOTHING
                """,
                (current_report_id,)
            )
            
            # 4. Insert into Committee Decision
            cursor.execute(
                """
                INSERT INTO cai_committee_decision (report_id, position_id, recommendation, amount, reason)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (report_id, position_id) 
                DO UPDATE SET recommendation = EXCLUDED.recommendation, amount = EXCLUDED.amount, reason = EXCLUDED.reason
                """,
                (
                    current_report_id,
                    position_id,
                    recommendation.action,
                    recommendation.position_size_recommendation or 0.0,
                    reason_text
                )
            )
            
            # 5. Insert into Decision Ledger (Tracking execution)
            ledger_id = f"ldg_{uuid.uuid4().hex[:8]}"
            cursor.execute(
                """
                INSERT INTO cai_decision_ledger (id, decision_report_id, decision_position_id, execution_status)
                VALUES (%s, %s, %s, 'PENDING')
                """,
                (
                    ledger_id,
                    current_report_id,
                    position_id
                )
            )
            
            # Commit handled by the caller or context manager
            
        return ledger_id
