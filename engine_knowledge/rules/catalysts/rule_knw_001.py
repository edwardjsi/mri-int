from engine_knowledge.rules.base import KnowledgeRule
from engine_knowledge.models import CompanyKnowledge, RuleEvidence

class RuleKNW001(KnowledgeRule):
    id = "RULE-KNW-001"
    version = "1.0"
    description = "Has New Product Catalyst"

    def evaluate(self, knowledge: CompanyKnowledge) -> RuleEvidence:
        observations = knowledge.observations
        facts = {f.fact_id: f for f in knowledge.facts}
        
        matched_obs = []
        matched_quotes = []
        
        for obs in observations:
            if obs.type == "NEW_PRODUCT" and obs.grounding == "VERIFIED":
                matched_obs.append(obs.observation_id)
                
                # Resolve the source quote from the linked fact
                if obs.source_fact and obs.source_fact in facts:
                    fact = facts[obs.source_fact]
                    if fact.source:
                        matched_quotes.append(fact.source)

        if matched_obs:
            return RuleEvidence(
                rule=self.id,
                rule_version=self.version,
                status="PASS",
                observations=matched_obs,
                quotes=matched_quotes
            )
            
        return RuleEvidence(
            rule=self.id,
            rule_version=self.version,
            status="FAIL",
            observations=[],
            quotes=[]
        )
