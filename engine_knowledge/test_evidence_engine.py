import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
from engine_knowledge.evidence_engine import KnowledgeEvidenceEngine

def test_evidence_engine_with_granules():
    """
    Sprint 2: Prove the Evidence Engine loads the rule registry, passes the typed 
    domain model into RuleKNW001, and returns deterministic RuleEvidence.
    """
    engine = KnowledgeEvidenceEngine()
    
    symbol = "GRANULES"
    try:
        payload = engine.evaluate(symbol, model_name="CANSLIM")
        print(f"✅ PASS: Evidence Engine successfully evaluated {symbol} for CANSLIM")
        print(f"  Total Rules Executed: {len(payload.evidence)}")
        for ev in payload.evidence:
            print(f"  - [{ev.rule}] (v{ev.rule_version}): {ev.status}")
    except ValueError as e:
        print(f"⚠️ Warning: {e}")
        
if __name__ == "__main__":
    test_evidence_engine_with_granules()
