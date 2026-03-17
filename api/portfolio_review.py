import logging
import io
import pandas as pd
from typing import List
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from src.db import get_connection
from src.on_demand_ingest import ingest_missing_symbols_sync

router = APIRouter(prefix="/api/portfolio-review", tags=["Portfolio Review"])
logger = logging.getLogger(__name__)

@router.get("/holdings-status")
@router.get("/holdings_status")  # Alias to prevent 404
async def holdings_status(email: str):
    """Checks for existing portfolio data (Digital Twin)."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM holdings WHERE email = %s", (email,))
        count = cur.fetchone()[0]
        return {
            "storage_ready": True if count > 0 else False, 
            "holdings_count": count,
            "email": email,
            "status": "active" if count > 0 else "empty"
        }
    except Exception as e:
        logger.error(f"Status check error: {e}")
        return {"storage_ready": False, "error": str(e)}
    finally:
        cur.close()
        conn.close()

@router.post("/upload-csv")
@router.post("/upload_csv")  # Alias to prevent 404
async def upload_csv(
    background_tasks: BackgroundTasks,
    email: str = Form(...),
    name: str = Form("User"),
    file: UploadFile = File(...)
):
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        df.columns = [c.lower().strip() for c in df.columns]
        symbol_col = next((c for c in df.columns if 'symbol' in c or 'ticker' in c), None)
        
        if not symbol_col:
            raise HTTPException(status_code=400, detail="Missing symbol column.")

        symbols = [str(s).upper().strip() for s in df[symbol_col].dropna().unique()]

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO users (email, name) VALUES (%s, %s) ON CONFLICT (email) DO NOTHING", (email, name))
        for sym in symbols:
            cur.execute("INSERT INTO holdings (email, symbol) VALUES (%s, %s) ON CONFLICT DO NOTHING", (email, sym))
        conn.commit()
        cur.close()
        conn.close()

        background_tasks.add_task(ingest_missing_symbols_sync, symbols, 'admin', email)
        return {"status": "success", "message": f"Synced {len(symbols)} symbols."}
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/holdings")
async def get_holdings(email: str):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT h.symbol, s.total_score, s.date
            FROM holdings h
            LEFT JOIN stock_scores s ON h.symbol = s.symbol 
            AND s.date = (SELECT MAX(date) FROM stock_scores)
            WHERE h.email = %s
            ORDER BY h.symbol ASC
        """, (email,))
        rows = cur.fetchall()
        return [{"symbol": r[0], "score": r[1], "last_updated": r[2]} for r in rows]
    finally:
        cur.close()
        conn.close()