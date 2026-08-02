import logging
from engine_knowledge.models import EvidencePayload, RuleEvidence, CompanyKnowledge
from engine_knowledge.repository import KnowledgeRepository
from engine_knowledge.registry import get_rules_for_model

logger = logging.getLogger(__name__)

class KnowledgeEvidenceEngine:
    """
    Consumes a typed CompanyKnowledge object, identifies the requesting Model, 
    loads its registered rules, and returns deterministic Evidence.
    """
    def __init__(self, repository: KnowledgeRepository = None):
        self.repository = repository or KnowledgeRepository()
        
    def evaluate(self, symbol: str, model_name: str) -> EvidencePayload:
        knowledge: CompanyKnowledge = self.repository.get_company_knowledge(symbol)
        if not knowledge:
            raise ValueError(f"No knowledge found for symbol: {symbol}")
            
        rule_classes = get_rules_for_model(model_name)
        if not rule_classes:
            raise ValueError(f"No rules registered for model: {model_name}")
            
        evidence_list = []
        
        # We must convert the Pydantic object back into a dict for rule evaluation,
        # or update the rule signature to accept the object. 
        # Since the user requested the rule to accept the typed object, we pass it directly.
        for RuleClass in rule_classes:
            rule_instance = RuleClass()
            
            try:
                # Assuming the rule's evaluate() signature accepts CompanyKnowledge
                # We need to adapt RuleKNW001 slightly since it currently accepts Dict[str, Any]
                # I'll update the base class and RuleKNW001 to expect CompanyKnowledge next.
                evidence: RuleEvidence = rule_instance.evaluate(knowledge)
                evidence_list.append(evidence)
            except Exception as e:
                logger.error(f"Rule {rule_instance.id} failed evaluation for {symbol}: {e}")
                # Optional: return a FAIL fallback if the rule crashes
                
        return EvidencePayload(
            symbol=symbol.upper(),
            evidence=evidence_list
        )
