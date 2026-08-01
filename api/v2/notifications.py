from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

router = APIRouter(prefix="/notifications", tags=["CAI V2 Notifications"])

@router.post("/subscriptions", response_model=Dict[str, Any])
def subscribe_notifications(subscription_data: Dict[str, Any]):
    # Registers notification targets
    return {"status": "subscribed", "target": subscription_data.get("target")}
