import logging
import io
import pandas as pd
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from typing import Optional
from src.db import get_connection
from src.on_demand_ingest import ingest_missing_symbols_sync

# Prefix matches what the frontend is calling in your logs
router = APIRouter(prefix="/api/portfolio-review", tags=["Portfolio Review"])
logger = logging.getLogger(__name__)

@router.get("/holdings-status")
@router.get("/holdings_status")
@router.get("/holdings")  # This fixes the 'Not Found' error
@router.get("/")
async def holdings_status(email: Optional[str] = None):
    """
    Handshake endpoint: Checks if the user has a 'Digital Twin' (holdings) in the DB.
    """
    if not email or email == "undefined" or email == "":
        return {
            "storage_ready": False, 
            "message": "Email parameter is missing.",
            "status": "missing_email"
        }

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
        logger.error(f"Database query failed: {e}")
        return {"storage_ready": False, "error": "Database connection issue"}
    finally:
        cur.close()
        conn.close()

@router.post("/upload-csv")
@router.post("/upload_csv")
@router.post("/")
async def upload_csv(
    background_tasks: BackgroundTasks,
    email: str = Form(...),
    name: str = Form("User"),
    file: UploadFile = File(...)
):
    """
    Processes CSV upload, saves symbols, and triggers the MRI analysis engine.
    """
    try:
        contents = await file.read()
        try:
            decoded = contents.decode('utf-8')
        except UnicodeDecodeError:
            decoded = contents.decode('latin1')
            
        df = pd.read_csv(io.StringIO(decoded))
        df.columns = [c.lower().strip() for c in df.columns]
        symbol_col = next((c for c in df.columns if 'symbol' in c or 'ticker' in c), None)
        
        if not symbol_col:
            raise HTTPException(status_code=400, detail="No symbol column found.")

        symbols = [str(s).upper().strip() for s in df[symbol_col].dropna().unique() if len(str(s)) > 0]

        if not symbols:
            raise HTTPException(status_code=400, detail="The CSV file is empty.")

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (email, name) VALUES (%s, %s) ON CONFLICT (email) DO NOTHING", (email, name))
        for sym in symbols:
            cur.execute("INSERT INTO holdings (email, symbol) VALUES (%s, %s) ON CONFLICT DO NOTHING", (email, sym))
        
        conn.commit()
        cur.close()
        conn.close()

        background_tasks.add_task(ingest_missing_symbols_sync, symbols, 'admin', email)
        
        return {"status": "success", "message": f"Synced {len(symbols)} assets."}
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))