import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
from engine_knowledge.models import CompanyKnowledge, Fact, Observation, KnowledgeMetadata
from engine_knowledge.rules.catalysts.rule_knw_001 import RuleKNW001

def test_rule_knw_001_synthetic_pass():
    """
    Validates that RULE-KNW-001 deterministically outputs a PASS 
    when provided with a valid, typed CompanyKnowledge object.
    """
    rule = RuleKNW001()
    
    # Create a synthetic TESTCO object
    synthetic_knowledge = CompanyKnowledge(
        symbol="TESTCO",
        metadata=KnowledgeMetadata(
            knowledge_version=1,
            compiler_version="1.0",
            knowledge_age_days=1,
            last_refresh="2026-08-01T00:00:00Z",
            is_stale=False
        ),
        facts=[
            Fact(
                fact_id="KNW-0001",
                category="Catalyst",
                value="Launched new oncology API platform.",
                source="Launched new oncology API platform."
            )
        ],
        entities=[],
        observations=[
            Observation(
                observation_id="OBS-SEM-001",
                type="NEW_PRODUCT",
                value=True,
                source_fact="KNW-0001",
                grounding="VERIFIED"
            )
        ]
    )
    
    evidence = rule.evaluate(synthetic_knowledge)
    
    print(f"✅ Evaluating TESTCO with {rule.id}")
    assert evidence.status == "PASS", f"Expected PASS, got {evidence.status}"
    assert "OBS-SEM-001" in evidence.observations, "Failed to map Observation ID"
    assert "Launched new oncology API platform." in evidence.quotes, "Failed to resolve quote from Fact"
    
    print("✅ TESTCO Passed - RuleKNW001 logic is sound and deterministic.")
    
if __name__ == "__main__":
    test_rule_knw_001_synthetic_pass()
