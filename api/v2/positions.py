from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from engine_core.cai_v2_engine import CaiV2Engine
from engine_core.cai_v2_repository import CaiV2Repository
from engine_core.cai_v2_models import DecisionEvaluation, DecisionLedgerEntry

router = APIRouter(prefix="/positions", tags=["CAI V2 Positions"])

# Dependency injection for easy testing
def get_engine():
    return CaiV2Engine()

def get_repo():
    return CaiV2Repository()

@router.post("/{position_id}/evaluate", response_model=DecisionEvaluation)
def evaluate_position(
    position_id: str,
    context: Dict[str, Any],
    symbol: str = "UNKNOWN",
    engine: CaiV2Engine = Depends(get_engine),
    repo: CaiV2Repository = Depends(get_repo)
):
    # In a real scenario, ledger_history would be queried from the database.
    # For now, we pass an empty list to satisfy the method signature.
    ledger_history = []
    
    evaluation = engine.evaluate_position(
        position_id=position_id,
        symbol=symbol,
        context=context,
        ledger_history=ledger_history
    )
    
    # Save snapshot
    repo.save_decision_snapshot(evaluation)
    
    # Save thresholds
    if evaluation.thresholds:
        repo.save_thresholds(position_id, evaluation.thresholds)
        
    return evaluation

@router.get("/{position_id}/decisions", response_model=List[Dict[str, Any]])
def get_decisions(position_id: str, repo: CaiV2Repository = Depends(get_repo)):
    # Placeholder for fetching decision snapshots
    return []

@router.get("/{position_id}/ledger", response_model=List[Dict[str, Any]])
def get_ledger(position_id: str, repo: CaiV2Repository = Depends(get_repo)):
    # Placeholder for fetching the ledger
    return []
