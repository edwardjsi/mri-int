import json
import operator
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from engine_core.portfolio_os_context import DecisionContext
from engine_core.xai_framework import ExplanationNode, XaiRule


@dataclass(frozen=True)
class RuleEvaluationResult:
    action: Optional[str]
    triggered_rule: Optional[str]
    reason: Optional[str]
    explanation_node: Optional[ExplanationNode] = None
    evaluated_rules: Optional[List[XaiRule]] = None


class RuleEngine:
    """
    Evaluates static JSON rules against a DecisionContext to produce deterministic actions.
    """
    OPERATORS = {
        '==': operator.eq,
        '!=': operator.ne,
        '>': operator.gt,
        '>=': operator.ge,
        '<': operator.lt,
        '<=': operator.le,
        'in': lambda a, b: a in b if b else False,
    }

    def __init__(self, ruleset_json: str):
        self.rules = json.loads(ruleset_json)
        # Sort rules by priority, ascending (lower number = higher priority / evaluated first)
        self.rules.sort(key=lambda r: r.get('priority', 999))

    def evaluate(self, context: DecisionContext) -> RuleEvaluationResult:
        """
        Evaluates rules in priority order. Returns the first action triggered by a rule.
        Builds the explanation tree and tracks all evaluated rules.
        """
        evaluated_rules = []
        explanation = ExplanationNode("Rule Engine", "Evaluated Rules")

        for rule in self.rules:
            rule_name = rule.get('name', 'Unknown Rule')
            rule_id = str(rule.get('id', rule_name))
            
            # For simplicity, we just log that we evaluated it. A full evaluation would track exactly which subcondition matched.
            triggered = self._evaluate_condition(rule.get('condition', {}), context)
            
            xai_rule = XaiRule(
                name=rule_name,
                rule_id=rule_id,
                result="PASS" if triggered else "FAIL",
                threshold=str(rule.get('condition')),
                actual_value="Evaluated context"
            )
            evaluated_rules.append(xai_rule)
            
            if triggered:
                explanation.result = rule.get('action')
                explanation.details["triggered_rule"] = rule_name
                explanation.details["reason"] = rule.get('reason')
                
                return RuleEvaluationResult(
                    action=rule.get('action'),
                    triggered_rule=rule_name,
                    reason=rule.get('reason', f"Triggered rule: {rule_name}"),
                    explanation_node=explanation,
                    evaluated_rules=evaluated_rules
                )
        
        explanation.result = "None"
        explanation.details["reason"] = "No rules triggered"
        return RuleEvaluationResult(action=None, triggered_rule=None, reason="No rules triggered", explanation_node=explanation, evaluated_rules=evaluated_rules)

    def _evaluate_condition(self, condition: Dict[str, Any], context: DecisionContext) -> bool:
        if not condition:
            return False

        if 'AND' in condition:
            return all(self._evaluate_condition(sub, context) for sub in condition['AND'])
        
        if 'OR' in condition:
            return any(self._evaluate_condition(sub, context) for sub in condition['OR'])

        field = condition.get('field')
        op = condition.get('operator')
        value = condition.get('value')

        if not field or not op:
            return False

        actual_value = self._resolve_field(field, context)
        expected_value = self._resolve_value(value, context)

        eval_func = self.OPERATORS.get(op)
        if not eval_func:
            raise ValueError(f"Unsupported operator: {op}")

        try:
            return eval_func(actual_value, expected_value)
        except Exception:
            return False

    def _resolve_field(self, field_path: str, context: DecisionContext) -> Any:
        parts = field_path.split('.')
        current = context
        for part in parts:
            if current is None:
                return None
            
            # If it's a dict (like indicators could be if we converted them, though they are objects here)
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
        return current

    def _resolve_value(self, value: Any, context: DecisionContext) -> Any:
        # If value is a string that looks like a field reference, resolve it
        if isinstance(value, str) and value.startswith('context.'):
            return self._resolve_field(value.replace('context.', ''), context)
        return value
