import os

from fastapi import APIRouter

from src.aws_ses import aws_credentials_present, get_ses_client, resolve_ses_region

router = APIRouter(prefix="/api/email", tags=["email"])


@router.get("/debug")
def email_debug(check_identity: bool = False):
    """
    Safe diagnostics endpoint for SES configuration on the running API container.

    - By default, does not call AWS.
    - If `check_identity=true`, attempts a small SES API call to confirm sender verification
      status in the configured region (requires AWS credentials).
    """
    sender = os.getenv("SES_SENDER_EMAIL", "unset")
    frontend_url = os.getenv("FRONTEND_URL") or os.getenv("PUBLIC_FRONTEND_URL") or ""

    result = {
        "aws_credentials_present": bool(aws_credentials_present()),
        "ses_sender_email": sender,
        "ses_region_env": os.getenv("SES_REGION"),
        "aws_region_env": os.getenv("AWS_REGION"),
        "aws_default_region_env": os.getenv("AWS_DEFAULT_REGION"),
        "frontend_url_env": frontend_url,
    }

    try:
        region = resolve_ses_region()
        result["ses_region_effective"] = region
        result["ses_region_valid"] = True
    except Exception as e:
        result["ses_region_effective"] = None
        result["ses_region_valid"] = False
        result["ses_region_error"] = str(e)
        return result

    if not check_identity:
        return result

    if not aws_credentials_present():
        result["ses_identity_check"] = {
            "ok": False,
            "error": "AWS credentials missing; cannot call SES APIs.",
        }
        return result

    try:
        ses = get_ses_client(region)
        attrs = ses.get_identity_verification_attributes(Identities=[sender])
        quota = ses.get_send_quota()
        result["ses_identity_check"] = {
            "ok": True,
            "verification_attributes": attrs.get("VerificationAttributes", {}),
            "send_quota": {
                "max_24_hour_send": quota.get("Max24HourSend"),
                "max_send_rate": quota.get("MaxSendRate"),
                "sent_last_24_hours": quota.get("SentLast24Hours"),
            },
        }
    except Exception as e:
        result["ses_identity_check"] = {"ok": False, "error": str(e)}

    return result

