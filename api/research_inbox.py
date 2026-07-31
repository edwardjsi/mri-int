from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Dict, Any, List
import uuid
import datetime

from engine_core.ciw_update_processor import KnowledgeUpdateProcessor, WorkspaceUpdater
from engine_core.ciw_repository import CompanyWorkspaceRepository
from engine_core.ciw_models import SourceDocument

router = APIRouter(prefix="/api/research-inbox", tags=["Research Inbox"])

# In-memory store for the vertical slice
INBOX_STORE: Dict[str, Dict[str, Any]] = {}

class UploadResponse(BaseModel):
    inboxId: str
    status: str
    receivedAt: str

@router.post("/items", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    inbox_id = f"rin_{uuid.uuid4().hex[:8]}"
    INBOX_STORE[inbox_id] = {
        "id": inbox_id,
        "filename": file.filename,
        "status": "Received",
        "receivedAt": datetime.datetime.now().isoformat(),
        "parsedText": "",
        "companyId": None,
        "companySymbol": None,
        "workspaceVersion": None,
        "transaction": None
    }
    return UploadResponse(inboxId=inbox_id, status="Received", receivedAt=INBOX_STORE[inbox_id]["receivedAt"])

@router.post("/items/{inboxId}/detect-company")
def detect_company(inboxId: str):
    if inboxId not in INBOX_STORE:
        raise HTTPException(status_code=404)
    # Stub: Always detect Neuland Labs for the slice
    INBOX_STORE[inboxId]["companySymbol"] = "NEULANDLAB"
    INBOX_STORE[inboxId]["companyId"] = "cmp_neuland"
    return {"companySymbol": "NEULANDLAB", "confidence": "High"}

@router.get("/items/{inboxId}/duplicate-check")
def check_duplicate(inboxId: str):
    if inboxId not in INBOX_STORE:
        raise HTTPException(status_code=404)
    # Stub: No duplicates
    return {"isDuplicate": False}

@router.post("/items/{inboxId}/parse")
def parse_document(inboxId: str):
    if inboxId not in INBOX_STORE:
        raise HTTPException(status_code=404)
    # Mock MarkItDown output
    INBOX_STORE[inboxId]["parsedText"] = "# Neuland Labs Initiation\nDeep dive into margin expansion via CDMO. High switching costs."
    INBOX_STORE[inboxId]["status"] = "Parsed"
    return {"status": "Parsed"}

@router.get("/items/{inboxId}/preview")
def get_preview(inboxId: str):
    if inboxId not in INBOX_STORE:
        raise HTTPException(status_code=404)
    
    item = INBOX_STORE[inboxId]
    if not item["companySymbol"]:
        raise HTTPException(status_code=400, detail="Company not detected yet")
        
    # Generate Preview via Processor
    processor = KnowledgeUpdateProcessor()
    doc = SourceDocument(
        id=item["id"],
        doc_type="PDF",
        title=item["filename"],
        author="System",
        uri=f"local://{item['filename']}",
        created_at=datetime.datetime.now(),
        metadata={"text_content": item["parsedText"]}
    )
    transaction = processor.process(doc)
    
    # Store transaction for commit phase
    INBOX_STORE[inboxId]["transaction"] = transaction
    INBOX_STORE[inboxId]["status"] = "Preview Ready"
    
    return {
        "status": "Preview Ready",
        "companySymbol": item["companySymbol"],
        "extractedMarkdown": item["parsedText"],
        "diff": [op.dict() for op in transaction.node_updates]
    }

@router.post("/items/{inboxId}/update-workspace")
def update_workspace(inboxId: str):
    if inboxId not in INBOX_STORE:
        raise HTTPException(status_code=404)
        
    item = INBOX_STORE[inboxId]
    transaction = item.get("transaction")
    if not transaction:
        raise HTTPException(status_code=400, detail="No preview generated to commit")
        
    repo = CompanyWorkspaceRepository()
    try:
        updater = WorkspaceUpdater(repo)
        updated_workspace = updater.apply(transaction)
        
        item["status"] = "Workspace Updated"
        item["workspaceVersion"] = 44 # Mock version bump
        
        return {
            "inboxId": inboxId,
            "status": "Workspace Updated",
            "companySymbol": item["companySymbol"],
            "workspaceVersion": item["workspaceVersion"],
            "updatedSections": ["Understanding", "Risks", "Catalysts"]
        }
    finally:
        repo.close()
