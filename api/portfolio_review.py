import logging
import io
import pandas as pd
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from typing import Optional
from src.db import get_connection

router = APIRouter(prefix="/api/portfolio-review", tags=["Portfolio Review"])
logger = logging.getLogger(__name__)

# This handles EVERY variation the frontend might call
@router.get("/holdings-status")
@router.get("/holdings_status")
@router.get("/holdings") 
@router.get("/")
async def holdings_status(email: Optional[str] = None):
    if not email:
        return {"storage_ready": False, "message": "Email required"}

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM holdings WHERE email = %s", (email,))
        count = cur.fetchone()[0]
        return {
            "storage_ready": True if count > 0 else False, 
            "holdings_count": count,
            "email": email,
            "status": "ready"
        }
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"storage_ready": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()

# Add a specific POST alias too
@router.post("/upload-csv")
@router.post("/upload_csv")
@router.post("/")
async def upload_csv(
    background_tasks: BackgroundTasks,
    email: str = Form(...),
    file: UploadFile = File(...)
):
    # ... (Keep your existing upload logic here) ...
    return {"status": "success"}