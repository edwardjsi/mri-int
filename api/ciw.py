from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from engine_core.ciw_repository import CompanyWorkspaceRepository
from engine_core.model_results_repository import ModelResultRepository

router = APIRouter(prefix="/api/ciw", tags=["CIW"])

def calculate_knowledge_health(workspace) -> Dict[str, Any]:
    nodes = list(workspace.state.understanding.values()) + workspace.state.risks + workspace.state.catalysts + workspace.state.monitoring
    open_monitoring = len(workspace.state.monitoring)
    open_risks = len(workspace.state.risks)
    missing_evidence = sum(1 for n in nodes if not n.evidence)
    
    overall = 100 - (missing_evidence * 10)
    overall = max(0, min(100, overall))
    
    return {
        "overall": overall,
        "research_freshness": True if workspace.timeline else False,
        "evidence_completeness": missing_evidence == 0,
        "open_monitoring": open_monitoring,
        "open_risks": open_risks,
        "missing_evidence": missing_evidence,
        "last_update": workspace.state.last_updated.isoformat() if workspace.state.last_updated else "Never"
    }

@router.get("/{symbol}")
def get_company_workspace(symbol: str) -> Dict[str, Any]:
    """
    Fetch the complete Company Intelligence Workspace (CIW) aggregate root for a symbol.
    """
    repo = CompanyWorkspaceRepository()
    model_repo = ModelResultRepository()
    try:
        workspace = repo.get_workspace(symbol.upper())
        if not workspace:
            raise HTTPException(status_code=404, detail=f"Company Workspace not found for {symbol}")
        
        data = workspace.model_dump() if hasattr(workspace, "model_dump") else workspace.dict()
        data["health"] = calculate_knowledge_health(workspace)

        # Add latest model results
        models = model_repo.latest(symbol.upper())
        data["models"] = [
            {
                "id": m.model_id,
                "version": m.model_version,
                "status": m.status,
                "score": float(m.score) if m.score is not None else None,
                "payload": m.payload,
                "evaluation_date": m.evaluation_date.isoformat() if m.evaluation_date else None,
            }
            for m in models
        ]
        
        return data
    finally:
        repo.close()
