from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from engine_core.ciw_repository import CompanyWorkspaceRepository
from engine_core.model_results_repository import ModelResultRepository
from engine_mosi.knowledge_importer import KnowledgeImporter
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

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


def _val(enum_attr):
    if enum_attr is None:
        return ""
    if hasattr(enum_attr, "value"):
        return enum_attr.value
    return str(enum_attr)


def serialize_knowledge_node(node) -> dict:
    if not node:
        return {}
    
    updated_at = getattr(node, "updated_at", None)
    updated_at_str = ""
    if updated_at:
        updated_at_str = updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at)

    return {
        "id": getattr(node, "id", ""),
        "node_type": _val(getattr(node, "node_type", "")),
        "text": getattr(node, "text", ""),
        "confidence": _val(getattr(node, "confidence", "")),
        "status": _val(getattr(node, "status", "")),
        "evidence": getattr(node, "evidence", []) or [],
        "history": getattr(node, "history", []) or [],
        "updated_at": updated_at_str,
        "metadata": getattr(node, "metadata", {}) or {}
    }


def serialize_debug_workspace(workspace, models, health) -> dict:
    identity = getattr(workspace, "identity", None)
    portfolio = getattr(workspace, "portfolio", None)
    state = getattr(workspace, "state", None)
    timeline = getattr(workspace, "timeline", []) or []
    
    # Sort timeline: newest event_date first
    sorted_timeline = []
    if timeline:
        try:
            sorted_timeline = sorted(
                timeline,
                key=lambda x: getattr(x, "event_date", datetime.min) or datetime.min,
                reverse=True
            )
        except Exception:
            sorted_timeline = timeline

    serialized_timeline = []
    for evt in sorted_timeline:
        evt_date = getattr(evt, "event_date", None)
        serialized_timeline.append({
            "id": getattr(evt, "id", ""),
            "event_date": evt_date.isoformat() if hasattr(evt_date, "isoformat") else str(evt_date or ""),
            "event_type": _val(getattr(evt, "event_type", "")),
            "summary": getattr(evt, "summary", "")
        })

    understanding_data = {}
    risks_data = []
    catalysts_data = []
    monitoring_data = []

    if state:
        understanding = getattr(state, "understanding", {}) or {}
        risks = getattr(state, "risks", []) or []
        catalysts = getattr(state, "catalysts", []) or []
        monitoring = getattr(state, "monitoring", []) or []

        for k, v in understanding.items():
            understanding_data[k] = serialize_knowledge_node(v)
        
        risks_data = [serialize_knowledge_node(r) for r in risks]
        catalysts_data = [serialize_knowledge_node(c) for c in catalysts]
        monitoring_data = [serialize_knowledge_node(m) for m in monitoring]

    return {
        "identity": {
            "symbol": getattr(identity, "symbol", "") if identity else "",
            "name": getattr(identity, "name", "") if identity else "",
            "sector": getattr(identity, "sector", "") if identity else ""
        },
        "portfolio": {
            "status": getattr(portfolio, "status", "Unknown") if portfolio else "Unknown",
            "allocation": getattr(portfolio, "allocation", 0.0) if portfolio else 0.0,
            "average_cost": getattr(portfolio, "average_cost", 0.0) if portfolio else 0.0
        },
        "state": {
            "understanding": understanding_data,
            "risks": risks_data,
            "catalysts": catalysts_data,
            "monitoring": monitoring_data
        } if state is not None else None,
        "timeline": serialized_timeline,
        "health": health,
        "models": models
    }


@router.get("/{symbol}/workspace")
def get_company_workspace_raw(symbol: str) -> Dict[str, Any]:
    """
    Fetch the raw CompanyWorkspace aggregate root for a symbol (for debugger page).
    Strictly read-only, does not trigger compiler/recompiles.
    """
    repo = CompanyWorkspaceRepository()
    model_repo = ModelResultRepository()
    sym = symbol.upper()
    try:
        workspace = repo.get_workspace(sym)
        if not workspace:
            logger.info(f"Workspace debug request: Symbol={sym} | Result=Missing")
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "WORKSPACE_NOT_FOUND",
                    "message": f"Company Workspace has not yet been generated for {sym}.",
                    "symbol": sym
                }
            )
        
        logger.info(f"Workspace debug request: Symbol={sym} | Result=Found")
        
        # Models payload
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
        
        # Calculate health
        health = calculate_knowledge_health(workspace)
        
        # Serialize with defensive attributes
        serialized_data = serialize_debug_workspace(workspace, models_data, health)
        return serialized_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Workspace debug error for {sym}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        repo.close()

