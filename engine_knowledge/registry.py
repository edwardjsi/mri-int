from typing import List, Type
from engine_knowledge.rules.base import KnowledgeRule
from engine_knowledge.rules.catalysts.rule_knw_001 import RuleKNW001

# The definitive mapping of investment models to their required knowledge rules
MODEL_RULES = {
    "CANSLIM": [
        RuleKNW001,
        # RuleKNW002, 
        # RuleKNW003,
    ],
    "MINERVINI": [
        # ...
    ]
}

def get_rules_for_model(model_name: str) -> List[Type[KnowledgeRule]]:
    """Returns the list of Rule classes required by the given model."""
    return MODEL_RULES.get(model_name.upper(), [])
