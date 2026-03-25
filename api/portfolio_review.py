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
from api.schema import ensure_required_tables
from api.deps import get_db, get_current_client

router = APIRouter(prefix="/api/portfolio-review", tags=["Portfolio Review"])
logger = logging.getLogger(__name__)

@router.get("/holdings-status")
@router.get("/holdings_status")
@router.get("/holdings") 
@router.get("/")
async def get_holdings(
    client=Depends(get_current_client),
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        client_id = str(client["id"])
        email = client["email"]
        
        # Schema is ensured at startup, but we keep this as a lightweight safeguard
        ensure_required_tables(conn)
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
                is_dict_legacy = not legacy_rows or isinstance(legacy_rows[0], dict)
                for r in legacy_rows:
                    holdings_list.append({
                        "symbol": r["symbol"] if is_dict_legacy else r[0],
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
                is_dict_holdings = not holdings_list or isinstance(holdings_list[0], dict)
                raw_list = []
                for h in holdings_list:
                    if is_dict_holdings:
                        raw_list.append(dict(h))
                    else:
                        # Manual conversion for tuple
                        raw_list.append({
                            "symbol": h[0],
                            "quantity": h[1],
                            "avg_cost": h[2]
                        })
                analysis = analyze_portfolio(raw_list, conn=conn)
                enriched_holdings = analysis.get("holdings", [])
            except Exception as e:
                logger.error(f"Analysis Error: {e}")
                conn.rollback()
                # Manual conversion for fallback if dict fails
                is_dict_fallback = not holdings_list or isinstance(holdings_list[0], dict)
                if is_dict_fallback:
                    enriched_holdings = [dict(h) for h in holdings_list]
                else:
                    enriched_holdings = [{"symbol": h[0], "quantity": h[1], "avg_cost": h[2]} for h in holdings_list]

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


@router.post("/upload-csv")
@router.post("/upload_csv")
@router.post("/")
async def upload_csv(
    background_tasks: BackgroundTasks,
    email: Optional[str] = Form(None),
    name: str = Form("User"),
    file: UploadFile = File(...),
    conn=Depends(get_db),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
):
    try:
        # Resolve identity from Token or Form
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
                pass

        final_email = client["email"] if client else email
        final_name = client["name"] if client else name

        if not client and final_email:
            cur_find = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur_find.execute("SELECT id, email, name FROM clients WHERE email = %s", (final_email,))
            client = cur_find.fetchone()
            
            # If still not found, check legacy users table and promote to clients
            if not client:
                cur_find.execute("SELECT name FROM users WHERE email = %s", (final_email,))
                legacy_user = cur_find.fetchone()
                # Auto-create Client record so persistence works
                new_id = str(uuid.uuid4())
                try:
                    cur_find.execute(
                        "INSERT INTO clients (id, email, name, initial_capital) VALUES (%s, %s, %s, 100000) ON CONFLICT DO NOTHING",
                        (new_id, final_email, legacy_user['name'] if legacy_user else final_name)
                    )
                    conn.commit()
                    cur_find.execute("SELECT id, email, name FROM clients WHERE id = %s", (new_id,))
                    client = cur_find.fetchone()
                except Exception:
                    conn.rollback()
            cur_find.close()

        if not client:
             raise HTTPException(status_code=403, detail="Could not identify or create client record for persistence.")

        client_id = client["id"]
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8', errors='ignore')))
        df.columns = [c.lower().strip() for c in df.columns]
        
        symbol_col = next((c for c in df.columns if c in ('symbol', 'ticker', 'instrument', 'stock', 'isin')), None)
        qty_col = next((c for c in df.columns if c in ('quantity', 'shares', 'qty', 'qty.')), None)
        cost_col = next((c for c in df.columns if c in ('avg_cost', 'avg cost', 'cost', 'avg_buy_price', 'avg. cost', 'average price', 'buy price')), None)
        
        if not symbol_col:
            raise HTTPException(status_code=400, detail="No symbol column found.")

        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        raw_holdings = []
        symbols = []
        
        ensure_required_tables(conn)
        for _, row in df.iterrows():
            sym = str(row[symbol_col]).upper().strip()
            if not sym or sym == 'NAN': continue
            qty = float(row[qty_col]) if qty_col and pd.notna(row[qty_col]) else 0.0
            cost = float(row[cost_col]) if cost_col and pd.notna(row[cost_col]) else 0.0
            symbols.append(sym)
            raw_holdings.append({"symbol": sym, "quantity": qty, "avg_cost": cost})
            cur.execute("""
                INSERT INTO client_external_holdings (id, client_id, symbol, quantity, avg_cost)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (client_id, symbol) 
                DO UPDATE SET quantity = EXCLUDED.quantity, avg_cost = EXCLUDED.avg_cost, updated_at = NOW()
            """, (str(uuid.uuid4()), client_id, sym, qty, cost))

        conn.commit()

        # ── Synchronous analysis for symbols already in stock_scores ──
        known_symbols = []
        unknown_symbols = []
        if symbols:
            unique_syms = list(set(symbols))
            placeholders = ','.join(['%s'] * len(unique_syms))
            cur.execute(
                f"SELECT DISTINCT symbol FROM stock_scores WHERE symbol IN ({placeholders})",
                unique_syms
            )
            scored_set = {r[0] if not isinstance(r, dict) else r['symbol'] for r in cur.fetchall()}
            for sym in unique_syms:
                (known_symbols if sym in scored_set else unknown_symbols).append(sym)

        analysis = None
        if raw_holdings:
            try:
                from src.portfolio_review_engine import analyze_portfolio
                analysis = analyze_portfolio(raw_holdings, conn=conn)
            except Exception as e:
                logger.warning(f"Sync analysis failed (non-fatal): {e}")
                conn.rollback()

        cur.close()

        # ── Background ingest only for truly unknown symbols ──
        if unknown_symbols:
            background_tasks.add_task(ingest_missing_symbols_sync, unknown_symbols, 'admin', final_email)

        resp = {
            "status": "success",
            "message": f"Synced {len(set(symbols))} symbols",
            "digital_twin_saved": True,
            "digital_twin_row_count": len(set(symbols)),
            "pending_symbols": unknown_symbols,
        }
        if analysis:
            resp["analysis"] = analysis

        return resp

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload fail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save-bulk")
async def save_holdings_bulk(
    holdings: list[dict],
    client=Depends(get_current_client),
    conn=Depends(get_db)
):
    cur = conn.cursor()
    try:
        client_id = str(client["id"])
        ensure_required_tables(conn)
        cur.execute("DELETE FROM client_external_holdings WHERE client_id = %s", (client_id,))
        for h in holdings:
            sym = str(h.get("symbol", "")).upper().strip()
            if not sym: continue
            qty = float(h.get("quantity", 0))
            cost = float(h.get("avg_cost", 0))
            cur.execute("""
                INSERT INTO client_external_holdings (id, client_id, symbol, quantity, avg_cost)
                VALUES (%s, %s, %s, %s, %s)
            """, (str(uuid.uuid4()), client_id, sym, qty, cost))
        conn.commit()
        return {"status": "success", "message": f"Saved {len(holdings)} holdings"}
    except Exception as e:
        logger.error(f"Save bulk fail: {e}")
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()

@router.delete("/holdings/{symbol}")
async def delete_holding(
    symbol: str,
    client=Depends(get_current_client),
    conn=Depends(get_db)
):
    cur = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM client_external_holdings WHERE client_id = %s AND symbol = %s",
            (str(client["id"]), symbol.upper().strip())
        )
        conn.commit()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Delete fail: {e}")
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()

@router.post("/holdings/delete-all")
async def delete_all_holdings(
    client=Depends(get_current_client),
    conn=Depends(get_db)
):
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM client_external_holdings WHERE client_id = %s", (str(client["id"]),))
        conn.commit()
        return {"status": "success", "message": "All holdings deleted"}
    except Exception as e:
        logger.error(f"Delete all fail: {e}")
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()

@router.post("/holdings/regrade")
@router.post("/regrade")
async def regrade_holdings(
    background_tasks: BackgroundTasks,
    send_email: bool = False,
    client=Depends(get_current_client),
    conn=Depends(get_db)
):
    cur = conn.cursor()
    cur.execute("SELECT symbol FROM client_external_holdings WHERE client_id = %s", (str(client["id"]),))
    symbols = [r[0] for r in cur.fetchall()]
    cur.close()
    if symbols:
        background_tasks.add_task(ingest_missing_symbols_sync, symbols, 'admin', client["email"])
    return {"status": "success", "message": "Regrading started"}

@router.post("/holdings/regrade-sync")
@router.post("/regrade-sync")
async def regrade_holdings_sync(
    send_email: bool = False,
    client=Depends(get_current_client),
    conn=Depends(get_db)
):
    cur = conn.cursor()
    cur.execute("SELECT symbol FROM client_external_holdings WHERE client_id = %s", (str(client["id"]),))
    symbols = [r[0] for r in cur.fetchall()]
    cur.close()
    if symbols:
        # Now uses bulk ingestion optimized for speed
        logger.info(f"Regrading {len(symbols)} symbols sync for {client['email']}")
        ingest_missing_symbols_sync(symbols, 'admin', client["email"])
    return {"status": "success", "message": "Regrading complete"}