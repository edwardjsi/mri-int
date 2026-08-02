import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
from engine_knowledge.evidence_engine import KnowledgeEvidenceEngine
from engine_knowledge.models import EvidencePayload

class KnowledgeEvidenceService:
    """
    Service boundary for Investment Models (like CANSLIM) to request Evidence.
    This abstraction shields models from knowing whether the Engine is run 
    in-process, via HTTP, or via gRPC.
    """
    def __init__(self):
        # Currently invokes the engine directly in-process.
        # This can be swapped to requests.post(...) tomorrow without breaking consumers.
        self._engine = KnowledgeEvidenceEngine()
        
    def evaluate(self, symbol: str, model: str) -> EvidencePayload:
        return self._engine.evaluate(symbol, model)
