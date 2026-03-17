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
@router.get("/holdings")  # This fixes the 'Not Found' error from your logs
@router.get("/")         # Catch-all for the prefix root
async def holdings_status(email: Optional[str] = None):
    """
    Handshake endpoint: Checks if the user has a 'Digital Twin' (holdings) in the DB.
    """
    if not email or email == "undefined" or email == "":
        logger.warning("Handshake requested without a valid email.")
        return {
            "storage_ready": False, 
            "message": "No email provided. Please log in again.",
            "status": "missing_auth"
        }

    conn = get_connection()
    cur = conn.cursor()
    try:
        # Check if this user has any tickers saved
        cur.execute("SELECT COUNT(*) FROM holdings WHERE email = %s", (email,))
        count = cur.fetchone()[0]
        
        return {
            "storage_ready": True if count > 0 else False, 
            "holdings_count": count,
            "email": email,
            "status": "active"
        }
    except Exception as e:
        logger.error(f"Database query failed for {email}: {e}")
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
        # 1. Read the file
        contents = await file.read()
        # Handle potential encoding issues from different Excel/CSV exports
        try:
            decoded = contents.decode('utf-8')
        except UnicodeDecodeError:
            decoded = contents.decode('latin1')
            
        df = pd.read_csv(io.StringIO(decoded))
        
        # 2. Normalize columns to find the 'Symbol' or 'Ticker'
        df.columns = [c.lower().strip() for c in df.columns]
        symbol_col = next((c for c in df.columns if 'symbol' in c or 'ticker' in c or 'instrument' in c), None)
        
        if not symbol_col:
            logger.error(f"Upload failed: Column headers {df.columns.tolist()} don't match.")
            raise HTTPException(status_code=400, detail="Could not find a 'Symbol' or 'Ticker' column.")

        # Clean symbols
        symbols = [str(s).upper().strip() for s in df[symbol_col].dropna().unique() if len(str(s)) > 0]

        if not symbols:
            raise HTTPException(status_code=400, detail="The CSV file is empty or has no valid symbols.")

        # 3. Save to Postgres
        conn = get_connection()
        cur = conn.cursor()
        
        # Ensure user exists
        cur.execute(
            "INSERT INTO users (email, name) VALUES (%s, %s) ON CONFLICT (email) DO NOTHING", 
            (email, name)
        )
        
        # Add holdings
        for sym in symbols:
            cur.execute(
                "INSERT INTO holdings (email, symbol) VALUES (%s, %s) ON CONFLICT DO NOTHING", 
                (email, sym)
            )
        
        conn.commit()
        cur.close()
        conn.close()

        # 4. Background Task: Trigger the MRI Engine (Ingest + Indicators)
        background_tasks.add_task(ingest_missing_symbols_sync, symbols, 'admin', email)
        
        return {
            "status": "success", 
            "message": f"Portfolio synced. {len(symbols)} assets are being analyzed."
        }
        
    except Exception as e:
        logger.error(f"Critical Upload Failure: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")