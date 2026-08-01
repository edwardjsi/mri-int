from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple, Optional
from engine_core.cai_v2_models import (
    DecisionState, DecisionEvaluation, Threshold, RuleCategory, ThresholdType
)

class CaiV2Engine:
    """
    Deterministic rule engine for CAI Decision Ladder V2.1.
    Evaluates positions in strict precedence: QUIT > STRUCTURE > ALERT > ADD > HOLD.
    """

    def __init__(self):
        # In a full implementation, these rules would be loaded from config/cai_v2_rules.yaml
        pass

    def evaluate_position(self, position_id: str, symbol: str, context: Dict[str, Any], ledger_history: List[Dict[str, Any]]) -> DecisionEvaluation:
        # Step 1: Compute thresholds
        thresholds = self._compute_thresholds(context)
        
        # Step 2: Evaluate hierarchy
        state, why, why_not_add, triggered, categories, satisfaction = self._evaluate_hierarchy(thresholds)
        
        # Step 3: Compute stability and expiry
        stability = self._compute_stability(ledger_history)
        confidence = self._compute_confidence(thresholds, state)
        expiry = datetime.now(timezone.utc) + timedelta(days=1)  # Expires in 24 hours

        # Step 4: Validate transition and fail closed if illegal
        state, why_not_add = self._validate_transition(state, ledger_history, why_not_add)

        return DecisionEvaluation(
            position_id=position_id,
            symbol=symbol,
            decision_state=state,
            decision_confidence=confidence,
            decision_stability=stability,
            decision_expiry=expiry,
            rule_satisfaction_score=satisfaction,
            why=why,
            why_not_add=why_not_add,
            thresholds=thresholds,
            triggered_rules=triggered,
            rule_categories=list(categories),
            portfolio_context=context.get("portfolio", {}),
            last_updated=datetime.now(timezone.utc),
            history=[],  # Normally map ledger_history to StateTransition
            engine_version="2.1.0",
            rule_set_version="1.0.0",
            schema_version="1.0.0"
        )

    def _compute_thresholds(self, context: Dict[str, Any]) -> List[Threshold]:
        # Dummy computation mapping context directly to thresholds for testing Golden Scenarios
        thresholds = []
        now = datetime.now(timezone.utc)
        if context.get("price_below_200_ema"):
            thresholds.append(Threshold(
                threshold_type=ThresholdType.PRICE, value=1.0, confidence=1.0,
                reason="Price is below 200 EMA", triggered_rules=["R_QUIT_EMA200"],
                valid_from=now, valid_until=now + timedelta(days=1)
            ))
        if context.get("high_overhead_supply"):
            thresholds.append(Threshold(
                threshold_type=ThresholdType.PRICE, value=80.0, confidence=0.9,
                reason="High overhead supply detected", triggered_rules=["R_STRUC_OVERHEAD"],
                valid_from=now, valid_until=now + timedelta(days=1)
            ))
        if context.get("expired_stability"):
            thresholds.append(Threshold(
                threshold_type=ThresholdType.EVENT, value=0.1, confidence=1.0,
                reason="Stability has expired", triggered_rules=["R_ALERT_STABILITY"],
                valid_from=now, valid_until=now + timedelta(days=1)
            ))
        if context.get("high_growth_fundamentals"):
            thresholds.append(Threshold(
                threshold_type=ThresholdType.EVENT, value=95.0, confidence=0.8,
                reason="Strong fundamentals and growth", triggered_rules=["R_ADD_FUNDAMENTALS"],
                valid_from=now, valid_until=now + timedelta(days=1)
            ))
        return thresholds

    def _evaluate_hierarchy(self, thresholds: List[Threshold]) -> Tuple[DecisionState, str, Optional[str], List[str], set, float]:
        triggered_all = set()
        categories = set()
        
        for t in thresholds:
            triggered_all.update(t.triggered_rules)
            
        # 1. QUIT
        if "R_QUIT_EMA200" in triggered_all:
            return DecisionState.QUIT, "Thesis invalidated: Price below 200 EMA", "Thesis invalidated", list(triggered_all), {RuleCategory.TECHNICAL}, 1.0

        # 2. STRUCTURE
        if "R_STRUC_OVERHEAD" in triggered_all:
            return DecisionState.STRUCTURE, "Trend quality broken: High overhead supply", "High overhead supply blocks addition", list(triggered_all), {RuleCategory.TECHNICAL}, 1.0

        # 3. ALERT
        if "R_ALERT_STABILITY" in triggered_all:
            return DecisionState.ALERT, "Early warning: Stability has dropped", "Stability warning active", list(triggered_all), {RuleCategory.RISK}, 1.0

        # 4. ADD
        if "R_ADD_FUNDAMENTALS" in triggered_all:
            return DecisionState.ADD, "Position deserves new capital: Strong fundamentals", None, list(triggered_all), {RuleCategory.FUNDAMENTAL}, 1.0

        # 5. HOLD (Fallback)
        return DecisionState.HOLD, "Trend is healthy, doing nothing", "No strong ADD signals present", list(triggered_all), set(), 1.0

    def _compute_stability(self, ledger_history: List[Dict[str, Any]]) -> float:
        if not ledger_history:
            return 1.0
        
        flip_count = 0
        days_since_last_flip = 30
        now = datetime.now(timezone.utc)
        
        for entry in ledger_history:
            if entry.get("from_state") != entry.get("to_state"):
                flip_count += 1
                entry_date = entry.get("timestamp")
                if entry_date:
                    days = (now - entry_date).days
                    if days < days_since_last_flip:
                        days_since_last_flip = max(0, days)
                        
        recency_penalty = 1.0 / (days_since_last_flip + 1)
        stability = max(0.0, 1.0 - (flip_count * 0.1) - (recency_penalty * 0.5))
        return round(stability, 4)

    def _compute_confidence(self, thresholds: List[Threshold], state: DecisionState) -> float:
        if not thresholds:
            return 0.5
        avg = sum(t.confidence for t in thresholds) / len(thresholds)
        return round(avg, 4)

    def _validate_transition(self, new_state: DecisionState, ledger_history: List[Dict[str, Any]], why_not_add: Optional[str]) -> Tuple[DecisionState, Optional[str]]:
        if not ledger_history:
            return new_state, why_not_add
            
        last_state_val = ledger_history[-1].get("to_state")
        
        # Rule: Cannot jump from QUIT directly to ADD
        if last_state_val == DecisionState.QUIT.value and new_state == DecisionState.ADD:
            import logging
            logging.error(f"Illegal transition violation: Cannot jump from {last_state_val} to {new_state.value}. Failing closed to {last_state_val}.")
            return DecisionState.QUIT, f"Transition violation: {last_state_val} -> {new_state.value} rejected."
            
        return new_state, why_not_add
