from fastapi import APIRouter, HTTPException, Depends
from engine_core.workspace.services.workspace_builder_service import (
    CompanyWorkspaceBuilderService,
    CompanyKnowledgeNotFoundException
)
from engine_core.workspace.dtos.workspace_dto import CompanyWorkspaceDTO
from engine_core.db import get_connection

router = APIRouter(prefix="/api/v1/workspace", tags=["Workspace"])

def get_workspace_service():
    conn = get_connection()
    service = CompanyWorkspaceBuilderService(conn=conn)
    try:
        yield service
    finally:
        service.close()

@router.get("/{company_id}", response_model=CompanyWorkspaceDTO)
def get_company_workspace(company_id: str, service: CompanyWorkspaceBuilderService = Depends(get_workspace_service)):
    try:
        # Build strictly reads the projection layer
        dto = service.build(company_id)
        return dto
    except CompanyKnowledgeNotFoundException:
        raise HTTPException(status_code=404, detail="Company Knowledge not found")
    except Exception as e:
        # Wrap infrastructure exceptions as 503 per PRD
        raise HTTPException(status_code=503, detail=str(e))
