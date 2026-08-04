import sys
import os
from fastapi import APIRouter, HTTPException

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
from engine_core.model_results_repository import ModelResultRepository

router = APIRouter()

@router.get("/screen")
def run_canslim_screen():
    try:
        repo = ModelResultRepository()
        results = repo.latest_for_model_all_symbols("CANSLIM")
        
        candidates = []
        for r in results:
            payload = r.payload or {}
            score = r.score or 0
            if score >= 60:
                candidates.append(payload)
                
        candidates.sort(key=lambda x: x.get("canslim_score", 0), reverse=True)
        return {"status": "success", "candidates": candidates[:30]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
