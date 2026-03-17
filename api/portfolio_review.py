import logging
import io
import pandas as pd
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from typing import Optional
from src.db import get_connection
from src.on_demand_ingest import ingest_missing_symbols_sync

router = APIRouter(prefix="/api/portfolio-review", tags=["Portfolio Review"])
logger = logging.getLogger(__name__)

@router.get("/holdings-status")
@router.get("/holdings_status")
@router.get("/holdings")  # CRITICAL: This alias stops the 404 Not Found error
async def holdings_status(email: Optional[str] = None):
    """
    Checks if a user has existing holdings. 
    Returns storage_ready: True/False for the Digital Twin handshake.
    """
    if not email:
        # Returning a 200 with False is better than a 422 crash
        logger.warning("Handshake requested without an email string.")
        return {"storage_ready": False, "message": "Email is required for status check."}

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM holdings WHERE email = %s", (email,))
        count = cur.fetchone()[0]
        
        return {
            "storage_ready": True if count > 0 else False, 
            "holdings_count": count,
            "email": email,
            "status": "active"
        }
    except Exception as e:
        logger.error(f"Database handshake failed for {email}: {e}")
        return {"storage_ready": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()

@router.post("/upload-csv")
@router.post("/upload_csv")
async def upload_csv(
    background_tasks: BackgroundTasks,
    email: str = Form(...),
    name: str = Form("User"),
    file: UploadFile = File(...)
):
    """
    Processes the uploaded CSV, stores symbols, and triggers the MRI engine.
    """
    try:
        # 1. Read and Parse CSV
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # Standardize column names
        df.columns = [c.lower().strip() for c in df.columns]
        symbol_col = next((c for c in df.columns if 'symbol' in c or 'ticker' in c), None)
        
        if not symbol_col:
            logger.error(f"CSV Upload Error: No symbol column found. Columns: {df.columns.tolist()}")
            raise HTTPException(status_code=400, detail="CSV missing 'symbol' or 'ticker' column.")

        # Extract unique tickers
        symbols = [str(s).upper().strip() for s in df[symbol_col].dropna().unique()]

        if not symbols:
            raise HTTPException(status_code=400, detail="The uploaded CSV contains no valid symbols.")

        # 2. Database Operations
        conn = get_connection()
        cur = conn.cursor()
        
        # Ensure user entry exists
        cur.execute(
            "INSERT INTO users (email, name) VALUES (%s, %s) ON CONFLICT (email) DO NOTHING", 
            (email, name)
        )
        
        # Insert holdings for the user
        for sym in symbols:
            cur.execute(
                "INSERT INTO holdings (email, symbol) VALUES (%s, %s) ON