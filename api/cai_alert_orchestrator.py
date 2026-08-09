import os
import json
import uuid
import logging
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from api.deps import get_current_client, get_db
from api.zerodha_adapter import KiteAlertAdapter
from engine_core.cai_decision_ladder_engine import load_mri_inputs, compute_thresholds

router = APIRouter(prefix="/api/cai/alerts", tags=["cai_alerts"])

load_dotenv()
db_url = os.getenv("DATABASE_URL")

def get_db():
    conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()

# Models
class CAIConfigDraft(BaseModel):
    pullback_lower_bound: Optional[float] = None
    pullback_upper_bound: Optional[float] = None
    breakout_confirmation_price: Optional[float] = None
    next_add_price: Optional[float] = None
    structural_break_price: Optional[float] = None

class PreviewResponse(BaseModel):
    changes: List[Dict]
    unchanged_count: int
    unrelated_count: int

# Helpers
def _get_admin_client(cur):
    cur.execute("SELECT id FROM clients WHERE is_admin = TRUE ORDER BY created_at ASC LIMIT 1")
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=400, detail="Admin client not found")
    return str(row["id"])

def _get_position_id(cur, symbol):
    cur.execute("""
        SELECT p.id 
        FROM cai_position p
        JOIN cai_portfolio port ON p.portfolio_id = port.id
        WHERE p.symbol = %s AND p.status = 'ACTIVE'
    """, (symbol,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=400, detail=f"No active MRI position found for {symbol}")
    return str(row["id"]) if isinstance(row, dict) else str(row[0])

@router.get("/{symbol}")
def get_alert_configs(symbol: str, conn = Depends(get_db)):
    cur = conn.cursor()
    client_id = _get_admin_client(cur)
    
    cur.execute("""
        SELECT * FROM cai_alert_config_versions 
        WHERE client_id = %s AND symbol = %s 
        ORDER BY created_at DESC
    """, (client_id, symbol))
    versions = cur.fetchall()
    
    approved = next((v for v in versions if v["status"] == "APPROVED"), None)
    draft = next((v for v in versions if v["status"] in ["DRAFT", "SYNC_FAILED"]), None)
    
    # Sync status
    sync_count = 0
    if approved:
        cur.execute("SELECT COUNT(*) as c FROM cai_alert_mappings WHERE config_version_id = %s AND active = TRUE", (approved["id"],))
        sync_count = cur.fetchone()["c"]
        
    return {
        "symbol": symbol,
        "approved": approved,
        "draft": draft,
        "sync_count": sync_count
    }

@router.post("/{symbol}/draft")
def upsert_draft(symbol: str, req: CAIConfigDraft, conn=Depends(get_db)):
    draft_data = req.dict()
    
    cur = conn.cursor()
    client_id = _get_admin_client(cur)
    
    # Get the position's current tranche
    cur.execute("SELECT tranche FROM cai_position WHERE symbol = %s AND status = 'ACTIVE'", (symbol,))
    pos_row = cur.fetchone()
    if not pos_row:
        raise HTTPException(status_code=404, detail="Active position not found for symbol")
    tranche = pos_row["tranche"] or 1
    
    validation_result = validate_config(draft_data, tranche)
    if validation_result["validation_status"] == "INVALID":
        raise HTTPException(status_code=400, detail=" | ".join(validation_result["validation_reasons"]))
        
    val_status = validation_result["validation_status"]
    
    # Delete existing draft or failed sync
    cur.execute("DELETE FROM cai_alert_config_versions WHERE client_id = %s AND symbol = %s AND status IN ('DRAFT', 'SYNC_FAILED')", (client_id, symbol))
    
    # Calculate next version number for this client_id and symbol
    cur.execute("SELECT MAX(version) FROM cai_alert_config_versions WHERE client_id = %s AND symbol = %s", (client_id, symbol))
    max_version = cur.fetchone()["max"]
    next_version = (max_version or 0) + 1
    
    # Insert new draft
    cur.execute("""
        INSERT INTO cai_alert_config_versions 
        (client_id, symbol, version, status, pullback_lower_bound, pullback_upper_bound, breakout_confirmation_price, next_add_price, structural_break_price, origin, validation_status)
        VALUES (%s, %s, %s, 'DRAFT', %s, %s, %s, %s, %s, 'HUMAN_EDITED', %s)
        RETURNING *
    """, (client_id, symbol, next_version,
          draft_data.get("pullback_lower_bound"),
          draft_data.get("pullback_upper_bound"),
          draft_data.get("breakout_confirmation_price"),
          draft_data.get("next_add_price"),
          draft_data.get("structural_break_price"),
          val_status))
    new_draft = cur.fetchone()
    conn.commit()
    return {"status": "success", "draft": new_draft, "validation_result": validation_result}

def validate_config(config: dict, tranche: int) -> dict:
    reasons = []
    status = "READY"
    
    sb = config.get("structural_break_price")
    pl = config.get("pullback_lower_bound")
    pu = config.get("pullback_upper_bound")
    bc = config.get("breakout_confirmation_price")
    na = config.get("next_add_price")
    
    # 1. Structural Validation (Hard constraints)
    from decimal import Decimal
    
    if sb is not None and pl is not None and sb >= pl:
        reasons.append("STRUCTURE_BREAK_ABOVE_PULLBACK")
    if pl is not None and pu is not None and pl > pu:
        reasons.append("PULLBACK_LOWER_ABOVE_UPPER")
    if pu is not None and bc is not None and pu >= bc:
        reasons.append("PULLBACK_UPPER_ABOVE_BREAKOUT")
    if bc is not None and na is not None and Decimal(str(bc)) > Decimal(str(na)):
        reasons.append("BREAKOUT_ABOVE_NEXT_ADD")
        
    prices = [p for p in [sb, pl, pu, bc, na] if p is not None]
    if any(p <= 0 for p in prices):
        reasons.append("NEGATIVE_OR_ZERO_PRICE")

    # If any structural violations exist, it's INVALID
    if reasons:
        return {"validation_status": "INVALID", "validation_reasons": reasons}
        
    # 2. Completeness Validation & Logical Warnings (Soft constraints)
    
    # Base mandatory levels
    if sb is None:
        reasons.append("MISSING_STRUCTURE_BREAK")
    if pl is None or pu is None:
        reasons.append("MISSING_PULLBACK_ZONE")
        
    # Tranche-dependent levels
    if tranche < 5:
        if bc is None:
            reasons.append("MISSING_BREAKOUT")
        if na is None:
            reasons.append("MISSING_NEXT_ADD")
        if bc is not None and na is not None and Decimal(str(bc)) == Decimal(str(na)):
            reasons.append("BREAKOUT_EQUALS_NEXT_ADD")
            
    # Check for any exact duplicate non-null values
    values = [val for key, val in config.items() if val is not None and "price" in key]
    if len(values) != len(set(values)):
        if "BREAKOUT_EQUALS_NEXT_ADD" not in reasons:
            reasons.append("MULTIPLE_ALERTS_SHARE_THRESHOLD")

    if reasons:
        status = "REVIEW_REQUIRED"
        
    return {"validation_status": status, "validation_reasons": reasons}

def create_kite_alert_payloads(symbol: str, config: dict) -> List[dict]:
    payloads = []
    
    if config.get("structural_break_price"):
        payloads.append({
            "role": "STRUCTURE_BREAK",
            "name": f"{symbol} - 🔴 Structure Break",
            "condition": "<=",
            "price": float(config["structural_break_price"])
        })
        
    if config.get("pullback_upper_bound"):
        payloads.append({
            "role": "HEALTHY_PULLBACK",
            "name": f"{symbol} - 🟢 Healthy Pullback",
            "condition": "<=",
            "price": float(config["pullback_upper_bound"])
        })
        
    if config.get("breakout_confirmation_price"):
        payloads.append({
            "role": "BREAKOUT_CONFIRMATION",
            "name": f"{symbol} - 🚀 Breakout Confirmation",
            "condition": ">=",
            "price": float(config["breakout_confirmation_price"])
        })
        
    if config.get("next_add_price"):
        payloads.append({
            "role": "NEXT_ADD",
            "name": f"{symbol} - ➕ Next ADD",
            "condition": ">=",
            "price": float(config["next_add_price"])
        })
        
    return payloads

@router.post("/{symbol}/preview")
def preview_sync(symbol: str, conn = Depends(get_db)):
    cur = conn.cursor()
    client_id = _get_admin_client(cur)
    
    cur.execute("SELECT * FROM cai_alert_config_versions WHERE client_id = %s AND symbol = %s AND status IN ('DRAFT', 'SYNC_FAILED') ORDER BY created_at DESC LIMIT 1", (client_id, symbol))
    draft = cur.fetchone()
    if not draft:
        raise HTTPException(status_code=404, detail="No draft configuration found for symbol")
    
    warnings, val_status = validate_config(draft)
    
    cur.execute("SELECT * FROM cai_alert_config_versions WHERE client_id = %s AND symbol = %s AND status = 'APPROVED'", (client_id, symbol))
    approved = cur.fetchone()
    
    
    return {
        "message": "Preview functionality ready",
        "changes": [
            {"role": "STRUCTURE_BREAK", "old": approved.get("structural_break_price") if approved else None, "new": draft.get("structural_break_price")},
            {"role": "HEALTHY_PULLBACK", "old": approved.get("pullback_upper_bound") if approved else None, "new": draft.get("pullback_upper_bound")},
            {"role": "BREAKOUT_CONFIRMATION", "old": approved.get("breakout_confirmation_price") if approved else None, "new": draft.get("breakout_confirmation_price")},
            {"role": "NEXT_ADD", "old": approved.get("next_add_price") if approved else None, "new": draft.get("next_add_price")}
        ],
        "unchanged_count": 0,
        "unrelated_count": 51 # Mock total existing alerts
    }

@router.post("/{symbol}/approve-sync")
def approve_and_sync(symbol: str, conn = Depends(get_db)):
    cur = conn.cursor()
    client_id = _get_admin_client(cur)
    pos_id = _get_position_id(cur, symbol)
    
    cur.execute("SELECT * FROM cai_alert_config_versions WHERE client_id = %s AND symbol = %s AND status IN ('DRAFT', 'SYNC_FAILED') ORDER BY created_at DESC LIMIT 1", (client_id, symbol))
    draft = cur.fetchone()
    if not draft:
        raise HTTPException(status_code=400, detail="No draft configuration available to approve.")
        
    warnings, val_status = validate_config(draft)
    
    if val_status == 'WARNING_DUPLICATE_THRESHOLD':
        raise HTTPException(status_code=400, detail="Cannot approve and sync because Breakout equals Next ADD. Please manually resolve duplicate thresholds.")
    
    # 1. Update State to SYNC_IN_PROGRESS
    cur.execute("UPDATE cai_alert_config_versions SET status = 'SYNC_IN_PROGRESS' WHERE id = %s", (draft["id"],))
    conn.commit()
    
    adapter = KiteAlertAdapter()
    if not adapter.authenticate(client_id, conn):
        raise HTTPException(status_code=401, detail="Zerodha authentication failed.")
        
    payloads = create_kite_alert_payloads(symbol, draft)
    
    # Pre-sync: fetch all active mappings
    cur.execute("SELECT * FROM cai_alert_mappings WHERE client_id = %s AND cai_position_id = %s AND active = TRUE", (client_id, pos_id))
    active_mappings = cur.fetchall()
    
    try:
        active_zerodha_alerts = adapter.get_all_alerts()
    except Exception as e:
        conn.rollback()
        cur.execute("UPDATE cai_alert_config_versions SET status = 'SYNC_FAILED' WHERE id = %s", (draft["id"],))
        conn.commit()
        raise HTTPException(status_code=500, detail=f"Failed to fetch active alerts from Zerodha: {str(e)}")
        
    if len(active_zerodha_alerts) + len(payloads) > 500:
        conn.rollback()
        cur.execute("UPDATE cai_alert_config_versions SET status = 'SYNC_FAILED' WHERE id = %s", (draft["id"],))
        conn.commit()
        raise HTTPException(status_code=400, detail="Cannot synchronize CAI alerts: Zerodha active-alert limit would be exceeded.")
    
    created_alerts = []
    new_alerts_to_rollback = []
    
    try:
        # 2. Reconcile new alerts on Kite FIRST
        for p in payloads:
            mapped_role = next((m for m in active_mappings if m["alert_role"] == p["role"]), None)
            uuid_for_payload = None
            
            if mapped_role:
                # MRI mapping exists -> UPDATE that exact UUID with PUT
                uuid_for_payload = mapped_role["kite_uuid"]
                success = adapter.modify_alert(alert_uuid=uuid_for_payload, new_condition=p["condition"], new_price=p["price"], new_name=p["name"])
                if not success:
                    # Not found in Zerodha, recreate
                    uuid_for_payload = adapter.create_alert(alert_name=p["name"], symbol=symbol, condition=p["condition"], price=p["price"])
                    new_alerts_to_rollback.append(uuid_for_payload)
            else:
                # No MRI mapping exists -> check for matching CAI name
                matching_orphan = next((a for a in active_zerodha_alerts if a["name"] == p["name"]), None)
                if matching_orphan:
                    raise RuntimeError(f"Orphaned CAI alert found in Zerodha matching name '{p['name']}'. Please reconcile manually.")
                    
                # Create a new alert
                uuid_for_payload = adapter.create_alert(alert_name=p["name"], symbol=symbol, condition=p["condition"], price=p["price"])
                new_alerts_to_rollback.append(uuid_for_payload)
                
            if not isinstance(uuid_for_payload, str) or not uuid_for_payload:
                raise RuntimeError("Kite adapter returned invalid alert UUID")
                
            created_alerts.append({
                "role": p["role"],
                "kite_uuid": uuid_for_payload
            })
            
        # 3. Retrieve + Verify ALL 4
        for ca in created_alerts:
            verified = adapter.retrieve_alert(ca["kite_uuid"])
            if not verified:
                raise RuntimeError(f"Failed to verify alert {ca['kite_uuid']} in Zerodha")
            
        # 4. Remove obsolete CAI-owned alerts for this symbol
        for om in active_mappings:
            if om["kite_uuid"] not in [ca["kite_uuid"] for ca in created_alerts]:
                try:
                    adapter.delete_alert(om["kite_uuid"])
                except Exception as e:
                    logging.warning(f"Failed to delete obsolete alert {om['kite_uuid']}: {str(e)}")
            
            cur.execute("""
                UPDATE cai_alert_mappings 
                SET active = FALSE, superseded_at = NOW(), status = 'SUPERSEDED'
                WHERE id = %s
            """, (om["id"],))
            
        # 5. Insert new mappings
        for ca in created_alerts:
            cur.execute("""
                INSERT INTO cai_alert_mappings 
                (client_id, cai_position_id, alert_role, config_version_id, kite_uuid, status, active)
                VALUES (%s, %s, %s, %s, %s, 'ACTIVE', TRUE)
            """, (client_id, pos_id, ca["role"], draft["id"], ca["kite_uuid"]))
            
        # 6. Mark Draft as APPROVED, mark old as SUPERSEDED
        cur.execute("UPDATE cai_alert_config_versions SET status = 'SUPERSEDED' WHERE client_id = %s AND symbol = %s AND status = 'APPROVED'", (client_id, symbol))
        cur.execute("UPDATE cai_alert_config_versions SET status = 'APPROVED' WHERE id = %s", (draft["id"],))
        
        conn.commit()
        
        return {"status": "success", "message": f"Successfully synchronized {len(created_alerts)} alerts"}
        
    except Exception as e:
        # If it fails, update draft to SYNC_FAILED
        for u in new_alerts_to_rollback:
            try:
                adapter.delete_alert(u)
            except Exception as del_err:
                logging.error(f"Failed to cleanup orphaned alert {u} during rollback: {str(del_err)}")
                
        conn.rollback()
        cur.execute("UPDATE cai_alert_config_versions SET status = 'SYNC_FAILED' WHERE id = %s", (draft["id"],))
        conn.commit()
        raise HTTPException(status_code=500, detail=f"Synchronization failed: {str(e)}. Old config remains authoritative.")

@router.post("/generate-saturday-drafts")
def generate_saturday_drafts(client=Depends(get_current_client), conn=Depends(get_db)):
    """
    Saturday Generation Pipeline:
    Iterates over all ACTIVE CAI positions, fetches the latest MRI technicals,
    computes algorithmic thresholds, maps them to the canonical roles,
    and persists them as DRAFTs.
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    client_id = _get_admin_client(cur)
    
    generated_count = 0
    skipped_approved = 0
    skipped_draft = 0
    errors = []
    
    try:
        # 1. Fetch Active Positions
        cur.execute("""
            SELECT p.id, p.symbol 
            FROM cai_position p
            JOIN cai_portfolio port ON p.portfolio_id = port.id
            WHERE port.owner = %s AND p.status = 'ACTIVE'
        """, (client_id,))
        positions = cur.fetchall()
        
        for pos in positions:
            symbol = pos["symbol"]
            
            try:
                # 2. Load technicals and compute
                inputs = load_mri_inputs(conn, symbol)
                print(f"DEBUG: symbol={symbol}, inputs={inputs}")
                if not inputs or inputs.get("current_price") is None:
                    continue # Leaves it UNRESOLVED / UNCONFIGURED
                    
                thresholds = compute_thresholds(inputs)
                
                # 3. Map to CAI Draft using Canonical Schema
                pl = thresholds.get("structure_level")
                pu = thresholds.get("alert_level")
                bc = thresholds.get("add_level")
                na = thresholds.get("add_level")
                sb = thresholds.get("quit_level")
                
                # 4. Enforce Immutability Lifecycle
                cur.execute("SELECT status FROM cai_alert_config_versions WHERE client_id = %s AND symbol = %s", (client_id, symbol))
                versions = cur.fetchall()
                
                has_approved = any(v["status"] == "APPROVED" for v in versions)
                has_draft = any(v["status"] == "DRAFT" for v in versions)
                
                if has_approved:
                    skipped_approved += 1
                    continue
                if has_draft:
                    skipped_draft += 1
                    continue # Lifecycle rule: never overwrite DRAFT or APPROVED
                    
                # 5. Save as Auto-Generated Draft
                cur.execute("""
                    INSERT INTO cai_alert_config_versions 
                    (client_id, symbol, status, 
                     pullback_lower_bound, pullback_upper_bound, 
                     breakout_confirmation_price, 
                     next_add_price, structural_break_price)
                    VALUES (%s, %s, 'DRAFT', %s, %s, %s, %s, %s)
                """, (
                    client_id, symbol,
                    pl, pu, bc, na, sb
                ))
                generated_count += 1
                
            except Exception as inner_e:
                logging.error(f"Failed to generate draft for {symbol}: {str(inner_e)}")
                errors.append(symbol)
                
        conn.commit()
        
        summary = {
            "CREATED": generated_count,
            "SKIPPED_APPROVED": skipped_approved,
            "SKIPPED_DRAFT": skipped_draft,
            "FAILED": len(errors),
            "failed_symbols": errors
        }
        
        if len(errors) > 0:
            raise HTTPException(status_code=500, detail={"message": "Saturday generator completed with failures.", "summary": summary})
            
        return {
            "status": "success",
            "message": "Saturday generator completed successfully.",
            "summary": summary
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
