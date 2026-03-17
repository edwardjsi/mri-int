import logging
import io
import uuid
import pandas as pd
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from typing import Optional
from src.db import get_connection
from src.on_demand_ingest import ingest_missing_symbols_sync
from api.schema import ensure_client_external_holdings_table

router = APIRouter(prefix="/api/portfolio-review", tags=["Portfolio Review"])
logger = logging.getLogger(__name__)

@router.get("/holdings-status")
@router.get("/holdings_status")
@router.get("/holdings") 
@router.get("/")
async def holdings_status(email: Optional[str] = None):
    if not email or email == "undefined" or email == "":
        return {"storage_ready": False, "message": "Email missing"}

    conn = get_connection()
    cur = conn.cursor()
    try:
        # Check both old 'holdings' and new 'client_external_holdings' via client lookup
        cur.execute("SELECT id FROM clients WHERE email = %s", (email,))
        client = cur.fetchone()
        
        count = 0
        if client:
            client_id = client["id"]
            ensure_client_external_holdings_table(conn)
            cur.execute("SELECT COUNT(*) FROM client_external_holdings WHERE client_id = %s", (client_id,))
            count = cur.fetchone()[0]
        
        # Fallback to legacy table if it exists (for transition)
        try:
            cur.execute("SELECT COUNT(*) FROM holdings WHERE email = %s", (email,))
            legacy_count = cur.fetchone()[0]
            count = max(count, legacy_count)
        except Exception:
            conn.rollback()

        return {
            "storage_ready": True if count > 0 else False, 
            "holdings_count": count,
            "email": email
        }
    except Exception as e:
        logger.error(f"DB Error: {e}")
        return {"storage_ready": False, "error": str(e)}
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
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8', errors='ignore')))
        df.columns = [c.lower().strip() for c in df.columns]
        
        symbol_col = next((c for c in df.columns if any(k in c for k in ['symbol', 'ticker', 'instrument'])), None)
        qty_col = next((c for c in df.columns if any(k in c for k in ['quantity', 'qty', 'shares'])), None)
        cost_col = next((c for c in df.columns if any(k in c for k in ['avg_cost', 'cost', 'buy_price', 'price'])), None)
        
        if not symbol_col:
            raise HTTPException(status_code=400, detail="No symbol column found. Please include a 'symbol' column.")

        conn = get_connection()
        cur = conn.cursor()
        
        # 1. Ensure client exists (or legacy user)
        cur.execute("SELECT id FROM clients WHERE email = %s", (email,))
        client = cur.fetchone()
        
        symbols = []
        if client:
            # High-fidelity path: Use client_external_holdings
            client_id = client["id"]
            ensure_client_external_holdings_table(conn)
            
            for _, row in df.iterrows():
                sym = str(row[symbol_col]).upper().strip()
                if not sym or sym == 'NAN': continue
                qty = float(row[qty_col]) if qty_col and pd.notna(row[qty_col]) else 0.0
                cost = float(row[cost_col]) if cost_col and pd.notna(row[cost_col]) else 0.0
                
                symbols.append(sym)
                cur.execute("""
                    INSERT INTO client_external_holdings (id, client_id, symbol, quantity, avg_cost)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (client_id, symbol) 
                    DO UPDATE SET quantity = EXCLUDED.quantity, avg_cost = EXCLUDED.avg_cost, updated_at = NOW()
                """, (str(uuid.uuid4()), client_id, sym, qty, cost))
        else:
            # Legacy path: Still use 'holdings' for unauthenticated users if it exists
            try:
                cur.execute("INSERT INTO users (email, name) VALUES (%s, %s) ON CONFLICT (email) DO NOTHING", (email, name))
                for _, row in df.iterrows():
                    sym = str(row[symbol_col]).upper().strip()
                    if not sym or sym == 'NAN': continue
                    symbols.append(sym)
                    cur.execute("INSERT INTO holdings (email, symbol) VALUES (%s, %s) ON CONFLICT DO NOTHING", (email, sym))
            except Exception as e:
                logger.warning(f"Legacy holdings fail: {e}")
                conn.rollback()
                raise HTTPException(status_code=400, detail="Account not found. Please register first.")

        conn.commit()
        cur.close()
        conn.close()

        if symbols:
            background_tasks.add_task(ingest_missing_symbols_sync, list(set(symbols)), 'admin', email)
            
        return {"status": "success", "message": f"Synced {len(set(symbols))} symbols to your Digital Twin"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload fail: {e}")
        raise HTTPException(status_code=500, detail=str(e))