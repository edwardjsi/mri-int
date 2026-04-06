"""
MailerLite integration — adds new registrants to a mailing list group.
API: MailerLite v2 (connect.mailerlite.com)
"""
import os
import logging
import requests

from engine_core.config import get_mailerlite_credentials

logger = logging.getLogger(__name__)

# Fetch credentials once on module load or inside the function
_creds = get_mailerlite_credentials()
MAILERLITE_API_KEY = _creds["api_key"]
MAILERLITE_GROUP_ID = _creds["group_id"]


def add_subscriber(email: str, name: str) -> bool:
    """
    Add a new user to the MailerLite mailing list.
    Returns True on success, False on any failure (never raises).
    """
    if not MAILERLITE_API_KEY:
        logger.warning("MAILERLITE_API_KEY not set — skipping subscriber add")
        return False

    payload = {
        "email": email,
        "fields": {"name": name},
    }
    # Optional: status "active" skips double opt-in. Link to group if ID provided.
    payload["status"] = "active"
    if MAILERLITE_GROUP_ID:
        payload["groups"] = [MAILERLITE_GROUP_ID]

    try:
        resp = requests.post(
            "https://connect.mailerlite.com/api/subscribers",
            json=payload,
            headers={
                "Authorization": f"Bearer {MAILERLITE_API_KEY}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=5,
        )
        if resp.status_code in (200, 201):
            logger.info(f"MailerLite: added {email} to mailing list")
            return True
        else:
            logger.error(f"MailerLite: failed to add {email} — {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        logger.error(f"MailerLite: exception adding {email} — {e}")
        return False