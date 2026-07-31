from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List
from engine_core.ake_variable_repository import VariableRegistryRepository
from engine_core.db import get_connection

router = APIRouter(prefix="/api/extractor", tags=["Adaptive Knowledge Extractor"])

def get_repo():
    conn = get_connection()
    return VariableRegistryRepository(conn)

@router.get("/variables")
def get_all_variables(repo: VariableRegistryRepository = Depends(get_repo)):
    return repo.get_by_status("CANONICAL") + repo.get_by_status("RESERVE")

@router.get("/variables/reserve")
def get_reserve_variables(repo: VariableRegistryRepository = Depends(get_repo)):
    return repo.get_by_status("RESERVE")

@router.get("/variables/canonical")
def get_canonical_variables(repo: VariableRegistryRepository = Depends(get_repo)):
    return repo.get_by_status("CANONICAL")

@router.post("/variables/{var_id}/promote")
def promote_variable(var_id: str, repo: VariableRegistryRepository = Depends(get_repo)):
    try:
        repo.promote(var_id, user_id="system", reason="API promote")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/variables/{var_id}/reject")
def reject_variable(var_id: str, repo: VariableRegistryRepository = Depends(get_repo)):
    try:
        repo.reject(var_id, user_id="system", reason="API reject")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class MergeRequest(BaseModel):
    target_canonical_name: str

@router.post("/variables/{var_id}/merge")
def merge_variable(var_id: str, req: MergeRequest, repo: VariableRegistryRepository = Depends(get_repo)):
    try:
        repo.merge(var_id, req.target_canonical_name, user_id="system", reason="API merge")
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

