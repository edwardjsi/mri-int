from typing import Any, Dict, List, Optional
import uuid
from datetime import datetime

class ExplanationNode:
    """A node in the explanation tree."""
    def __init__(self, name: str, result: str, details: Optional[Dict[str, Any]] = None):
        self.name = name
        self.result = result
        self.details = details or {}
        self.children: List['ExplanationNode'] = []

    def add_child(self, node: 'ExplanationNode'):
        self.children.append(node)
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "result": self.result,
            "details": self.details,
            "children": [c.to_dict() for c in self.children]
        }

class XaiRule:
    """A rule that was evaluated."""
    def __init__(self, name: str, rule_id: str, result: str, threshold: str, actual_value: str):
        self.name = name
        self.rule_id = rule_id
        self.result = result
        self.threshold = threshold
        self.actual_value = actual_value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "rule_id": self.rule_id,
            "result": self.result,
            "threshold": self.threshold,
            "actual_value": self.actual_value
        }

class XaiEvidence:
    """Factual evidence supporting a rule."""
    def __init__(self, name: str, value: str, source: str, lookback: str, updated_at: str, formula: str):
        self.name = name
        self.value = value
        self.source = source
        self.lookback = lookback
        self.updated_at = updated_at
        self.formula = formula

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "source": self.source,
            "lookback": self.lookback,
            "updated_at": self.updated_at,
            "formula": self.formula
        }

class XaiCalculation:
    """Detailed calculation layer."""
    def __init__(self, name: str, formula: str, inputs: str, calculation_date: str, output: str, extra_details: Optional[Dict[str, Any]] = None):
        self.name = name
        self.formula = formula
        self.inputs = inputs
        self.calculation_date = calculation_date
        self.output = output
        self.extra_details = extra_details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "formula": self.formula,
            "inputs": self.inputs,
            "calculation_date": self.calculation_date,
            "output": self.output,
            "extra_details": self.extra_details
        }

class XaiDecision:
    """The full transparent decision object."""
    def __init__(
        self,
        stock: str,
        action: str,
        confidence: str,
        summary: str,
        explanation_tree: ExplanationNode,
        rules: List[XaiRule],
        evidence: List[XaiEvidence],
        calculations: List[XaiCalculation],
        raw_data_reference: str
    ):
        self.id = f"CAI-{datetime.now().strftime('%Y%m%d')}-{stock}-{uuid.uuid4().hex[:6].upper()}"
        self.stock = stock
        self.action = action
        self.confidence = confidence
        self.summary = summary
        self.explanation_tree = explanation_tree
        self.rules = rules
        self.evidence = evidence
        self.calculations = calculations
        self.raw_data_reference = raw_data_reference
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "stock": self.stock,
            "action": self.action,
            "confidence": self.confidence,
            "summary": self.summary,
            "explanation_tree": self.explanation_tree.to_dict(),
            "rules": [r.to_dict() for r in self.rules],
            "evidence": [e.to_dict() for e in self.evidence],
            "calculations": [c.to_dict() for c in self.calculations],
            "raw_data_reference": self.raw_data_reference
        }
