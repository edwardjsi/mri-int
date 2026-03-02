"""
Action recording endpoints: mark signals as executed/skipped.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from api.deps import get_db, get_current_client

router = APIRouter(prefix="/api/actions", tags=["actions"])


class RecordActionRequest(BaseModel):
    signal_id: str
    action_taken: str          # 'EXECUTED', 'SKIPPED', 'PARTIAL'
    actual_price: Optional[float] = None
    quantity: Optional[int] = None
    notes: Optional[str] = None


@router.post("/record")
def record_action(
    req: RecordActionRequest,
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Record a client's action on a signal (executed, skipped, partial)."""
    cur = conn.cursor()

    # Verify signal belongs to this client
    cur.execute(
        "SELECT id, symbol, action, recommended_price FROM client_signals WHERE id = %s AND client_id = %s",
        (req.signal_id, str(client["id"])),
    )
    signal = cur.fetchone()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    # Use recommended price if no actual price provided
    actual_price = req.actual_price or float(signal["recommended_price"])

    # Check for duplicate action
    cur.execute(
        "SELECT id FROM client_actions WHERE signal_id = %s AND client_id = %s",
        (req.signal_id, str(client["id"])),
    )
    if cur.fetchone():
        raise HTTPException(status_code=400, detail="Action already recorded for this signal")

    # Insert action
    cur.execute("""
        INSERT INTO client_actions (client_id, signal_id, action_taken, actual_price, quantity, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (str(client["id"]), req.signal_id, req.action_taken, actual_price, req.quantity, req.notes))
    action_id = str(cur.fetchone()["id"])

    # If EXECUTED, update client_portfolio
    if req.action_taken == "EXECUTED" and req.quantity and req.quantity > 0:
        if signal["action"] == "BUY":
            cur.execute("""
                INSERT INTO client_portfolio (client_id, symbol, entry_date, entry_price, quantity, highest_price)
                VALUES (%s, %s, CURRENT_DATE, %s, %s, %s)
                ON CONFLICT (client_id, symbol, entry_date) DO NOTHING
            """, (str(client["id"]), signal["symbol"], actual_price, req.quantity, actual_price))
        elif signal["action"] == "SELL":
            # Close the open position
            cur.execute("""
                UPDATE client_portfolio
                SET is_open = false, exit_date = CURRENT_DATE, exit_price = %s, exit_reason = 'SIGNAL'
                WHERE client_id = %s AND symbol = %s AND is_open = true
            """, (actual_price, str(client["id"]), signal["symbol"]))

    conn.commit()

    return {
        "id": action_id,
        "signal_id": req.signal_id,
        "action_taken": req.action_taken,
        "actual_price": actual_price,
        "quantity": req.quantity,
        "message": "Action recorded successfully",
    }


@router.get("/history")
def get_action_history(
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Full audit trail of all client actions."""
    cur = conn.cursor()
    cur.execute("""
        SELECT ca.id, ca.action_taken, ca.actual_price, ca.quantity, ca.notes, ca.recorded_at,
               cs.date AS signal_date, cs.symbol, cs.action AS signal_action,
               cs.recommended_price, cs.score, cs.regime
        FROM client_actions ca
        JOIN client_signals cs ON cs.id = ca.signal_id
        WHERE ca.client_id = %s
        ORDER BY ca.recorded_at DESC
    """, (str(client["id"]),))
    actions = cur.fetchall()

    return [
        {
            "id": str(a["id"]),
            "signal_date": str(a["signal_date"]),
            "symbol": a["symbol"],
            "signal_action": a["signal_action"],
            "action_taken": a["action_taken"],
            "recommended_price": float(a["recommended_price"]) if a["recommended_price"] else None,
            "actual_price": float(a["actual_price"]) if a["actual_price"] else None,
            "quantity": a["quantity"],
            "score": a["score"],
            "regime": a["regime"],
            "notes": a["notes"],
            "recorded_at": str(a["recorded_at"]),
        }
        for a in actions
    ]
