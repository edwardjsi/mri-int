from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any
from engine_mosi.knowledge_importer import KnowledgeImporter
from engine_mosi.mosi_compiler import MosiCompiler
import os

router = APIRouter(prefix="/api/v1/mosi", tags=["MOSI Compiler"])
importer = KnowledgeImporter()

class MosiUploadRequest(BaseModel):
    symbol: str
    report_text: str

@router.get("/library")
def get_mosi_library():
    """Returns a list of all symbols with imported MOSI artifacts."""
    try:
        symbols = importer.get_all_symbols()
        return {"library": symbols}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/knowledge/{symbol}")
def get_company_knowledge(symbol: str) -> Dict[str, Any]:
    artifacts = importer.get_artifacts(symbol.upper())
    if not artifacts:
        raise HTTPException(status_code=404, detail="Knowledge artifacts not found for symbol")
    return artifacts

@router.post("/upload")
def upload_mosi_report(req: MosiUploadRequest):
    """
    Accepts a raw MOSI report text for a symbol, runs it through the compiler, 
    and imports the resulting 4 JSON artifacts into the Knowledge Repository.
    """
    compiler = MosiCompiler()
    doc_metadata = {
        "document_id": f"DOC-{req.symbol.upper()}-UPLOAD",
        "document_type": "MOSI",
        "version": "1.0",
        "published_on": "2026-08-01"  # Or current date
    }
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'output_artifacts', req.symbol.upper()))
    
    try:
        # Compile
        result = compiler.process_report(req.report_text, doc_metadata, output_dir)
        if result['status'] != 'success':
            raise HTTPException(status_code=500, detail="Compilation failed")
            
        # Import
        importer.import_artifacts_from_dir(req.symbol.upper(), output_dir)
        
        return {"status": "success", "message": f"Successfully compiled and imported MOSI for {req.symbol.upper()}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
