from typing import List, Dict, Any, Optional

class RuleEvidence:
    def __init__(self, rule_id: str, rule_version: str, status: str, observations: List[str], quotes: List[str]):
        self.rule = rule_id
        self.rule_version = rule_version
        self.status = status
        self.observations = observations
        self.quotes = quotes
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule": self.rule,
            "rule_version": self.rule_version,
            "status": self.status,
            "observations": self.observations,
            "quotes": self.quotes
        }

from typing import List
from engine_knowledge.models import CompanyKnowledge, RuleEvidence

class KnowledgeRule:
    """
    Base class for all deterministic knowledge rules.
    Rules consume a structured CompanyKnowledge object and produce deterministic Evidence.
    """
    id: str = "UNKNOWN-RULE"
    version: str = "0.0"
    description: str = "Base knowledge rule"

    def evaluate(self, knowledge: CompanyKnowledge) -> RuleEvidence:
        """
        Evaluate the rule against the structured knowledge payload.
        Must return a RuleEvidence object containing PASS/FAIL/UNKNOWN, matched observations, and quotes.
        """
        raise NotImplementedError("Rules must implement the evaluate method.")
