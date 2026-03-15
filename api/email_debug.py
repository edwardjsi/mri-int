import os

from fastapi import APIRouter

from src.aws_ses import aws_credentials_present, get_ses_client, resolve_ses_region

router = APIRouter(prefix="/api/email", tags=["email"])


def _cred_meta() -> dict:
    access_key = os.getenv("AWS_ACCESS_KEY_ID") or ""
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY") or ""
    session_token = os.getenv("AWS_SESSION_TOKEN") or ""

    def has_ws(s: str) -> bool:
        return bool(s) and (s != s.strip() or any(ch.isspace() for ch in s))

    return {
        "aws_access_key_id_present": bool(access_key),
        "aws_access_key_id_prefix4": access_key[:4] if access_key else "",
        "aws_access_key_id_last4": access_key[-4:] if len(access_key) >= 4 else "",
        "aws_access_key_id_has_whitespace": has_ws(access_key),
        "aws_secret_access_key_present": bool(secret_key),
        "aws_secret_access_key_length": len(secret_key) if secret_key else 0,
        "aws_secret_access_key_has_whitespace": has_ws(secret_key),
        "aws_session_token_present": bool(session_token),
    }


def _hint_for_error(msg: str) -> str | None:
    m = (msg or "").lower()
    if "signaturedoesnotmatch" in m:
        return (
            "SignatureDoesNotMatch usually means AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY are wrong or corrupted "
            "(common: pasted SES SMTP password instead of IAM secret access key, swapped key/secret, or trailing whitespace). "
            "If your access key starts with 'ASIA', also set AWS_SESSION_TOKEN (temporary creds)."
        )
    if "invalidclienttokenid" in m:
        return "InvalidClientTokenId usually means the access key is wrong, disabled, or from the wrong AWS account."
    if "expiredtoken" in m:
        return "ExpiredToken means you are using temporary credentials; refresh them and set AWS_SESSION_TOKEN too."
    if "message rejected" in m and "not verified" in m:
        return (
            "MessageRejected: identity not verified in this region. Verify SES_SENDER_EMAIL (and recipients if sandbox) "
            "in SES for the effective SES region, or request production access."
        )
    return None


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
        "aws_credentials_meta": _cred_meta(),
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
        # Validate credentials independently (helps differentiate signing issues from SES sandbox issues).
        sts = __import__("boto3").client("sts")
        ident = sts.get_caller_identity()
        result["aws_identity"] = {
            "account": ident.get("Account"),
            "arn": ident.get("Arn"),
            "user_id": ident.get("UserId"),
        }

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
        err = str(e)
        result["ses_identity_check"] = {"ok": False, "error": err}
        hint = _hint_for_error(err)
        if hint:
            result["ses_identity_check"]["hint"] = hint

    return result
