import sys
import os
from fastapi import APIRouter, HTTPException

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
from engine_core.canslim_model import CanslimModel

router = APIRouter()

@router.get("/screen")
def run_canslim_screen():
    try:
        model = CanslimModel()
        results = model.run_quant_screen()
        return {"status": "success", "candidates": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
