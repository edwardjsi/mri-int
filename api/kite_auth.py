import os
import hashlib
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse
import httpx

from api.deps import get_db, get_current_client
from api.schema import ensure_required_tables

router = APIRouter(prefix="/kite", tags=["kite_auth"])
logger = logging.getLogger("mri_api.kite_auth")


@router.get("/login")
def kite_login():
    """Generates the official Kite Connect login URL and redirects the user."""
    api_key = os.getenv("KITE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="KITE_API_KEY not configured")
        
    login_url = f"https://kite.trade/connect/login?v=3&api_key={api_key}"
    return RedirectResponse(url=login_url)


@router.get("/callback")
def kite_callback(
    request_token: str = Query(None),
    status: str = Query(None),
    error_type: str = Query(None),
    client=Depends(get_current_client),
    conn=Depends(get_db)
):
    """
    Receives request_token from Zerodha.
    Exchanges it for access_token and stores it securely.
    """
    if status != "success" or not request_token:
        logger.error(f"Kite Auth Failed: status={status}, error={error_type}")
        raise HTTPException(status_code=400, detail=f"Authentication failed: {error_type or 'Missing request_token'}")

    api_key = os.getenv("KITE_API_KEY")
    api_secret = os.getenv("KITE_API_SECRET")
    
    if not api_key or not api_secret:
        logger.error("KITE_API_KEY or KITE_API_SECRET missing during callback")
        raise HTTPException(status_code=500, detail="Server misconfiguration: missing credentials")

    # SHA-256 checksum (api_key + request_token + api_secret)
    checksum_str = api_key + request_token + api_secret
    checksum = hashlib.sha256(checksum_str.encode("utf-8")).hexdigest()
    
    # Exchange token
    url = "https://api.kite.trade/session/token"
    payload = {
        "api_key": api_key,
        "request_token": request_token,
        "checksum": checksum
    }
    
    try:
        response = httpx.post(url, data=payload, timeout=10.0)
        data = response.json()
    except Exception as e:
        logger.error(f"Failed to reach Kite API: {e}")
        raise HTTPException(status_code=502, detail="Failed to reach Kite API")
        
    if data.get("status") != "success":
        error_message = data.get("message", "Unknown error from Kite")
        logger.error(f"Token exchange failed: {error_message}")
        raise HTTPException(status_code=401, detail=f"Token exchange failed: {error_message}")
        
    token_data = data.get("data", {})
    access_token = token_data.get("access_token")
    kite_user_id = token_data.get("user_id")
    
    if not access_token:
        raise HTTPException(status_code=500, detail="Access token missing in response")
        
    # Securely store in DB
    try:
        cur = conn.cursor()
        # Ensure table exists in case it was missed
        cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'kite_credentials'")
        if not cur.fetchone():
            from api.schema import ensure_kite_credentials_table
            ensure_kite_credentials_table(cur)
            
        client_id = str(client["id"])
        
        # Upsert
        cur.execute(
            """
            INSERT INTO kite_credentials (client_id, access_token, kite_user_id, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (client_id) DO UPDATE 
            SET access_token = EXCLUDED.access_token,
                kite_user_id = EXCLUDED.kite_user_id,
                updated_at = NOW();
            """,
            (client_id, access_token, kite_user_id)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error storing token: {e}")
        raise HTTPException(status_code=500, detail="Failed to store credentials securely")
        
    return {"message": "Authentication successful", "kite_user_id": kite_user_id}


@router.get("/status")
def kite_status(client=Depends(get_current_client), conn=Depends(get_db)):
    """
    Exposes connection status to CAI UI without revealing secrets.
    Kite tokens expire daily at 6 AM IST. We perform a basic date check.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT kite_user_id, updated_at FROM kite_credentials WHERE client_id = %s",
        (str(client["id"]),)
    )
    row = cur.fetchone()
    
    if not row:
        return {"status": "Not Connected", "message": "No credentials found"}
        
    updated_at = row["updated_at"] if isinstance(row, dict) else row[1]
    user_id = row["kite_user_id"] if isinstance(row, dict) else row[0]
    
    # Check if updated today (assuming UTC for simplicity, in a real app might convert to IST)
    # A simple check: if date is different, it's likely expired or close to it.
    is_expired = updated_at.date() < datetime.utcnow().date()
    
    status_str = "Expired" if is_expired else "Connected"
    
    return {
        "status": status_str,
        "kite_user_id": user_id,
        "last_updated": updated_at.isoformat()
    }


@router.get("/config-status")
def kite_config_status():
    """
    Diagnostic endpoint to verify if environment variables are injected successfully.
    Never exposes the actual values.
    """
    api_key = os.getenv("KITE_API_KEY")
    api_secret = os.getenv("KITE_API_SECRET")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    # Safely get all environment variable keys
    all_keys = list(os.environ.keys())
    
    return {
        "KITE_API_KEY_configured": bool(api_key and len(api_key.strip()) > 0),
        "KITE_API_SECRET_configured": bool(api_secret and len(api_secret.strip()) > 0),
        "OPENAI_API_KEY_configured": bool(openai_key and len(openai_key.strip()) > 0),
        "raw_key_length": len(api_key) if api_key else 0,
        "raw_secret_length": len(api_secret) if api_secret else 0,
        "available_env_keys": all_keys,
    }
