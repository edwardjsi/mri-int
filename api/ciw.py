from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from engine_core.ciw_repository import CompanyWorkspaceRepository
from engine_core.model_results_repository import ModelResultRepository
from engine_mosi.knowledge_importer import KnowledgeImporter
from datetime import datetime

router = APIRouter(prefix="/api/ciw", tags=["CIW"])

def calculate_knowledge_health(workspace) -> Dict[str, Any]:
    if not workspace:
        return {
            "overall": 0,
            "research_freshness": False,
            "evidence_completeness": False,
            "open_monitoring": 0,
            "open_risks": 0,
            "missing_evidence": 0,
            "last_update": "Never"
        }
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
    Fetch the complete Company Intelligence aggregate for a symbol.
    Provides investor-friendly keys: business, growth, management, risks, models, financials, technical, documents, freshness.
    """
    repo = CompanyWorkspaceRepository()
    model_repo = ModelResultRepository()
    importer = KnowledgeImporter()
    
    try:
        sym = symbol.upper()
        workspace = repo.get_workspace(sym)
        
        # Fetch models
        models = model_repo.latest(sym)
        models_data = [
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
        
        # Fetch knowledge (MOSI)
        artifacts = importer.get_artifacts(sym)
        
        if not workspace and not models and not artifacts:
            raise HTTPException(status_code=404, detail=f"Company Workspace not found for {symbol}")

        # Construct the CompanyIntelligence DTO
        company_knowledge = artifacts.get("company_knowledge", {}) if artifacts else {}
        
        # Freshness calculation
        now = datetime.now()
        knowledge_date = artifacts.get("knowledge_manifest", {}).get("last_updated") if artifacts else None
        
        data = {
            "symbol": sym,
            "business": company_knowledge.get("g1_1_business", {}),
            "growth": company_knowledge.get("g1_2_growth", {}),
            "management": company_knowledge.get("g2_management", {}),
            "risks": company_knowledge.get("g1_3_risks", {}),
            "recent_changes": company_knowledge.get("recent_changes", {}),
            "models": models_data,
            "financials": {}, # Placeholder for actual financials
            "technical": {},  # Placeholder for actual technicals
            "documents": [],  # Placeholder
            "health": calculate_knowledge_health(workspace),
            "freshness": {
                "knowledge": knowledge_date,
                "models": models_data[0]["evaluation_date"] if models_data else None,
                "financials": None,
                "technical": None
            },
            "knowledge_status": 82 if artifacts else 0, # Mocked percentage as in design
            "sources": [],
            "compiler_report": artifacts.get("extraction_report", {}) if artifacts else None,
            "facts": artifacts.get("company_facts", []) if artifacts else [],
            "manifest": artifacts.get("knowledge_manifest", {}) if artifacts else None,
        }
        
        return data
    finally:
        repo.close()
