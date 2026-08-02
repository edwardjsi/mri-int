import sys
import os
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
from engine_knowledge.repository import KnowledgeRepository
from engine_knowledge.evidence_engine import KnowledgeEvidenceEngine

router = APIRouter()

class EvaluateRequest(BaseModel):
    symbol: str
    model: str

@router.get("/{symbol}")
def get_company_knowledge(symbol: str):
    """
    Step 1 of the Knowledge Platform Pipeline:
    Purely returns the strongly typed CompanyKnowledge object from the repository.
    """
    repo = KnowledgeRepository()
    knowledge = repo.get_company_knowledge(symbol)
    
    if not knowledge:
        raise HTTPException(status_code=404, detail=f"No knowledge found for symbol: {symbol}")
        
    return knowledge

@router.post("/evaluate")
def evaluate_knowledge(req: EvaluateRequest):
    """
    Step 2 of the Knowledge Platform Pipeline:
    Evaluates rules bound to the specific model and returns deterministic evidence.
    """
    engine = KnowledgeEvidenceEngine()
    try:
        evidence = engine.evaluate(req.symbol, req.model)
        return evidence
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

