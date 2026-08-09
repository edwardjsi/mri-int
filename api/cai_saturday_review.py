import datetime
from fastapi import APIRouter, Depends, HTTPException
import psycopg2.extras
import logging

from api.deps import get_db, get_current_client
from api.cai_alert_orchestrator import _get_admin_client, validate_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cai", tags=["cai_saturday_review"])

@router.get("/saturday-review")
def get_saturday_review(client=Depends(get_current_client), conn=Depends(get_db)):
    """
    Returns exactly the active MRI positions and their current CAI state.
    Does not generate or mutate anything.
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        client_id = _get_admin_client(cur)

        # 1. Fetch active MRI positions
        cur.execute("""
            SELECT p.id, p.symbol, p.tranche 
            FROM cai_position p
            JOIN cai_portfolio port ON p.portfolio_id = port.id
            WHERE p.status = 'ACTIVE'
            ORDER BY p.symbol ASC
        """)
        positions = cur.fetchall()

        # 2. Fetch all configs for these symbols
        symbols = [p["symbol"] for p in positions]
        if not symbols:
            return {
                "review_date": datetime.date.today().isoformat(),
                "total_positions": 0,
                "reviewed": 0,
                "approved_and_synced": 0,
                "remaining": 0,
                "positions": []
            }

        cur.execute("""
            SELECT id, symbol, status, pullback_lower_bound, pullback_upper_bound, 
                   breakout_confirmation_price, next_add_price, structural_break_price,
                   validation_status, created_at
            FROM cai_alert_config_versions
            WHERE client_id = %s AND symbol = ANY(%s)
            ORDER BY created_at DESC
        """, (client_id, symbols))
        all_configs = cur.fetchall()

        # Group configs by symbol and status
        configs_by_symbol = {s: {"DRAFT": None, "APPROVED": None} for s in symbols}
        for config in all_configs:
            sym = config["symbol"]
            status = config["status"]
            if status in ("DRAFT", "APPROVED") and configs_by_symbol[sym][status] is None:
                configs_by_symbol[sym][status] = config

        # 3. Fetch alert mappings to check sync status
        cur.execute("""
            SELECT config_version_id
            FROM cai_alert_mappings
            WHERE client_id = %s AND active = TRUE
        """, (client_id,))
        active_mappings = cur.fetchall()
        synced_config_ids = {m["config_version_id"] for m in active_mappings}

        # 4. Assemble payload
        response_positions = []
        approved_and_synced = 0
        reviewed = 0
        remaining = 0

        for pos in positions:
            sym = pos["symbol"]
            draft_config = configs_by_symbol[sym]["DRAFT"]
            approved_config = configs_by_symbol[sym]["APPROVED"]
            
            selected_config = draft_config if draft_config else approved_config
            
            pos_data = {
                "id": pos["id"],
                "symbol": sym,
                "tranche": pos.get("tranche", 1),
                "config_status": "UNCONFIGURED",
                "validation_status": None,
                "pullback_lower": None,
                "pullback_upper": None,
                "breakout": None,
                "next_add": None,
                "structure_break": None,
                "zerodha_sync_status": None
            }

            if selected_config:
                pos_data["config_status"] = selected_config["status"]
                pos_data["pullback_lower"] = selected_config["pullback_lower_bound"]
                pos_data["pullback_upper"] = selected_config["pullback_upper_bound"]
                pos_data["breakout"] = selected_config["breakout_confirmation_price"]
                pos_data["next_add"] = selected_config["next_add_price"]
                pos_data["structure_break"] = selected_config["structural_break_price"]
                
                # Check duplicate thresholds
                config_dict = dict(selected_config)
                try:
                    warnings, val_status = validate_config(config_dict)
                    pos_data["validation_status"] = val_status
                except HTTPException:
                    pos_data["validation_status"] = "FAIL"
                
                if selected_config["status"] == "APPROVED":
                    if selected_config["id"] in synced_config_ids:
                        pos_data["zerodha_sync_status"] = "SYNCED"
                        approved_and_synced += 1
                        reviewed += 1
                    else:
                        pos_data["zerodha_sync_status"] = "PENDING"
                        remaining += 1
                elif selected_config["status"] == "DRAFT":
                    remaining += 1
            else:
                remaining += 1

            response_positions.append(pos_data)

        return {
            "review_date": datetime.date.today().isoformat(),
            "total_positions": len(positions),
            "reviewed": reviewed,
            "approved_and_synced": approved_and_synced,
            "remaining": remaining,
            "positions": response_positions
        }

    except Exception as e:
        logger.error(f"Error fetching Saturday Review: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch Saturday Review")
    finally:
        cur.close()
