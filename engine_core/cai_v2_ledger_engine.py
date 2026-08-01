from datetime import datetime, timezone
import logging
from typing import Dict, Any, Optional

from engine_core.cai_v2_engine import CaiV2Engine
from engine_core.cai_v2_repository import CaiV2Repository
from engine_core.cai_v2_models import (
    DecisionEvaluation, StateTransition, DecisionLedgerEntry, DecisionState
)

logger = logging.getLogger("cai_v2_ledger_engine")

class CaiV2LedgerEngine:
    def __init__(self, engine: CaiV2Engine = None, repo: CaiV2Repository = None):
        self.engine = engine or CaiV2Engine()
        self.repo = repo or CaiV2Repository()

    def process_daily_evaluation(self, position_id: str, symbol: str, context: Dict[str, Any], conn=None) -> DecisionEvaluation:
        """
        Orchestrates the evaluation of a position, handles ledger persistence,
        state transition tracking, and idempotent notifications.
        """
        now = datetime.now(timezone.utc)
        
        # 1. Fetch previous state from the ledger (Normally via repo, mocking for this implementation)
        # previous_entry = self.repo.get_latest_ledger_entry(position_id, conn)
        # previous_state = previous_entry.to_state if previous_entry else None
        # ledger_history = self.repo.get_ledger_history(position_id, conn)
        previous_state = None
        ledger_history = []
        
        # 2. Run Engine Evaluation
        evaluation = self.engine.evaluate_position(position_id, symbol, context, ledger_history)
        
        # 3. Append to Decision Ledger
        ledger_entry = DecisionLedgerEntry(
            position_id=position_id,
            symbol=symbol,
            from_state=previous_state,
            to_state=evaluation.decision_state,
            reasoning_snapshot={
                "why": evaluation.why,
                "why_not_add": evaluation.why_not_add,
                "portfolio_context": evaluation.portfolio_context
            },
            confidence=evaluation.decision_confidence,
            stability=evaluation.decision_stability,
            rule_satisfaction_score=evaluation.rule_satisfaction_score,
            timestamp=now,
            expiry=evaluation.decision_expiry,
            triggered_rules=evaluation.triggered_rules,
            threshold_references=[{"type": t.threshold_type.value, "reason": t.reason} for t in evaluation.thresholds]
        )
        self.repo.save_decision_ledger_entry(ledger_entry, conn=conn)

        # 4. Check for State Transition
        if previous_state != evaluation.decision_state:
            transition = StateTransition(
                from_state=previous_state,
                to_state=evaluation.decision_state,
                timestamp=now,
                reasoning_snapshot=ledger_entry.reasoning_snapshot
            )
            # Record State Transition
            self.repo.save_state_transition(position_id, symbol, transition, conn=conn)
            
            # 5. Trigger Idempotent Notification
            self._trigger_notification(symbol, evaluation.decision_state, now.date(), conn=conn)
            
        return evaluation

    def _trigger_notification(self, symbol: str, to_state: DecisionState, event_date, conn=None):
        """
        Fires a notification only if the idempotency lock is successfully acquired.
        """
        lock_acquired = self.repo.try_acquire_notification_lock(symbol, to_state.value, event_date, conn=conn)
        
        if lock_acquired:
            logger.info(f"NOTIFICATION TRIGGERED: {symbol} transitioned to {to_state.value} on {event_date}")
            # In a full system, publish event to SNS / Kafka / AWS SES here.
        else:
            logger.info(f"NOTIFICATION SUPPRESSED: {symbol} already notified for {to_state.value} on {event_date}")
