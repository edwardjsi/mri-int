import logging
import io
import pandas as pd
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from src.db import get_connection
from src.on_demand_ingest import ingest_missing_symbols_sync

router = APIRouter(prefix="/api/portfolio-review", tags=["Portfolio Review"])
logger = logging.getLogger(__name__)

@router.get("/holdings-status")
@router.get("/holdings_status")
@router.get("/holdings")  # Alias to fix frontend 404
async def holdings_status(email: str = None):
    """
    Checks if the user has any holdings in the database.
    Returns storage_ready: True if holdings exist.
    """
    if not email:
        logger.warning("Holdings check requested without email")
        return {"storage_ready": False, "message": "Email parameter is required"}

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
        logger.error(f"Handshake failed for {email}: {e}")
        return {"storage_ready": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()

@router.post("/upload-csv")
@router.post("/upload_csv") # Alias for compatibility
async def upload_csv(
    background_tasks: BackgroundTasks,
    email: str = Form(...),
    name: str = Form("User"),
    file: UploadFile = File(...)
):
    """
    Handles CSV upload, saves symbols to the database, 
    and triggers background data ingestion.
    """
    try:
        # Read the uploaded CSV
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # Normalize column names to find the symbols
        df.columns = [c.lower().strip() for c in df.columns]
        symbol_col = next((c for c in df.columns if 'symbol' in c or 'ticker' in c), None)
        
        if not symbol_col:
            logger.error(f"Upload failed: No symbol column found in {df.columns}")
            raise HTTPException(status_code=400, detail="No symbol/ticker column found in CSV")

        # Extract unique symbols
        symbols = [str(s).upper().strip() for s in df[symbol_col].dropna().unique()]

        if not symbols:
            raise HTTPException(status_code=400, detail="CSV contains no valid symbols")

        conn = get_connection()
        cur = conn.cursor()
        
        # 1. Ensure User exists
        cur.execute(
            "INSERT INTO users (email, name) VALUES (%s, %s) ON CONFLICT (email) DO NOTHING", 
            (email, name)
        )
        
        # 2. Insert Holdings
        for sym in symbols:
            cur.execute(
                "INSERT INTO holdings (email, symbol) VALUES (%s, %s) ON CONFLICT DO NOTHING", 
                (email, sym)
            )
        
        conn.commit()
        cur.close()
        conn.close()

        # 3. Trigger background data fetch and indicator calculation
        background_tasks.add_task(ingest_missing_symbols_sync, symbols, 'admin', email)
        
        logger.info(f"Successfully processed upload for {email}: {len(symbols)} symbols")
        return {
            "status": "success", 
            "message": f"Synced {len(symbols)} symbols. Analysis starting in background."
        }
        
    except Exception as e:
        logger.error(f"Upload processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")