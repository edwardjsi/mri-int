import logging
import io
import uuid
import pandas as pd
import psycopg2.extras
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
async def get_holdings(email: Optional[str] = None):
    if not email or email == "undefined" or email == "":
        return {"storage_ready": False, "message": "Email missing", "holdings": []}

    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # Check both old 'holdings' and new 'client_external_holdings' via client lookup
        cur.execute("SELECT id FROM clients WHERE email = %s", (email,))
        client = cur.fetchone()
        
        holdings_list = []
        if client:
            client_id = client["id"]
            ensure_client_external_holdings_table(conn)
            cur.execute("""
                SELECT symbol, quantity, avg_cost 
                FROM client_external_holdings 
                WHERE client_id = %s
            """, (client_id,))
            holdings_list = cur.fetchall()
        
        # Fallback to legacy table if it exists and we found nothing yet
        if not holdings_list:
            try:
                cur.execute("SELECT symbol FROM holdings WHERE email = %s", (email,))
                legacy_rows = cur.fetchall()
                for r in legacy_rows:
                    holdings_list.append({
                        "symbol": r["symbol"],
                        "quantity": 0,
                        "avg_cost": 0
                    })
            except Exception:
                conn.rollback()

        # Enrich with analysis if we have holdings
        enriched_holdings = []
        if holdings_list:
            from src.portfolio_review_engine import analyze_portfolio
            try:
                # Convert RealDictRow to plain dict
                raw_list = [dict(h) for h in holdings_list]
                analysis = analyze_portfolio(raw_list, conn=conn)
                enriched_holdings = analysis.get("holdings", [])
            except Exception as e:
                logger.error(f"Analysis Error: {e}")
                conn.rollback()
                # Fallback to raw list if analysis fails
                enriched_holdings = [dict(h) for h in holdings_list]

        return {
            "storage_ready": True if enriched_holdings else False, 
            "holdings_count": len(enriched_holdings),
            "holdings": enriched_holdings,
            "email": email
        }
    except Exception as e:
        logger.error(f"DB Error: {e}")
        return {"storage_ready": False, "error": str(e), "holdings": []}
    finally:
        cur.close()
        conn.close()

@router.post("/upload-csv")
@router.post("/upload_csv")
@router.post("/")
async def upload_csv(
    background_tasks: BackgroundTasks,
    email: Optional[str] = Form(None),
    name: str = Form("User"),
    file: UploadFile = File(...),
    conn=Depends(get_db),
    # Optional security to handle logged-in users who might miss the email form field
    auth: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
):
    try:
        # Determine email/client from either Token or Form
        client = None
        if auth:
            try:
                from jose import jwt
                from api.deps import SECRET_KEY, ALGORITHM
                payload = jwt.decode(auth.credentials, SECRET_KEY, algorithms=[ALGORITHM])
                client_id = payload.get("sub")
                if client_id:
                    cur_auth = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    cur_auth.execute("SELECT id, email, name FROM clients WHERE id = %s", (client_id,))
                    client = cur_auth.fetchone()
                    cur_auth.close()
            except Exception:
                pass # Fallback to Form email if token is invalid or expired

        final_email = client["email"] if client else email
        final_name = client["name"] if client else name

        if not final_email:
            raise HTTPException(status_code=422, detail="Email is required for portfolio analysis.")

        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8', errors='ignore')))
        df.columns = [c.lower().strip() for c in df.columns]
        
        symbol_col = next((c for c in df.columns if any(k in c for k in ['symbol', 'ticker', 'instrument'])), None)
        qty_col = next((c for c in df.columns if any(k in c for k in ['quantity', 'qty', 'shares'])), None)
        cost_col = next((c for c in df.columns if any(k in c for k in ['avg_cost', 'cost', 'buy_price', 'price'])), None)
        
        if not symbol_col:
            raise HTTPException(status_code=400, detail="No symbol column found. Please include a 'symbol' column.")

        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # 1. Ensure client exists (or legacy user)
        if not client:
            cur.execute("SELECT id, name FROM clients WHERE email = %s", (final_email,))
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
                cur.execute("INSERT INTO users (email, name) VALUES (%s, %s) ON CONFLICT (email) DO NOTHING", (final_email, final_name))
                for _, row in df.iterrows():
                    sym = str(row[symbol_col]).upper().strip()
                    if not sym or sym == 'NAN': continue
                    symbols.append(sym)
                    cur.execute("INSERT INTO holdings (email, symbol) VALUES (%s, %s) ON CONFLICT DO NOTHING", (final_email, sym))
            except Exception as e:
                logger.warning(f"Legacy holdings fail: {e}")
                conn.rollback()
                raise HTTPException(status_code=400, detail="Account not found. Please register first.")

        conn.commit()
        cur.close()

        if symbols:
            background_tasks.add_task(ingest_missing_symbols_sync, list(set(symbols)), 'admin', final_email)
            
        return {
            "status": "success", 
            "message": f"Synced {len(set(symbols))} symbols to your Digital Twin",
            "digital_twin_saved": True,
            "digital_twin_row_count": len(set(symbols))
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload fail: {e}")
        raise HTTPException(status_code=500, detail=str(e))