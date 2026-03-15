import logging
import os
from typing import Optional

import boto3

logger = logging.getLogger(__name__)


def aws_credentials_present() -> bool:
    """
    Best-effort check that the environment has AWS credentials available for boto3.
    Does not validate permissions.
    """
    try:
        sess = boto3.Session()
        creds = sess.get_credentials()
        frozen = creds.get_frozen_credentials() if creds else None
        return bool(frozen and frozen.access_key and frozen.secret_key)
    except Exception:
        return False


def resolve_ses_region() -> str:
    """
    Resolve the AWS region used specifically for SES.

    Priority:
      1) SES_REGION
      2) AWS_REGION
      3) AWS_DEFAULT_REGION
      4) ap-south-1 (historical default for this project)
    """
    candidate = (
        os.getenv("SES_REGION")
        or os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or "ap-south-1"
    )
    region = str(candidate).strip()

    try:
        available = boto3.session.Session().get_available_regions("ses") or []
    except Exception:
        available = []

    if available and region not in available:
        sample = ", ".join(sorted(set(available))[:12])
        more = "…" if len(set(available)) > 12 else ""
        raise ValueError(
            f"Invalid SES region '{region}'. "
            f"Set SES_REGION (preferred) or AWS_REGION to a real AWS region like 'ap-south-1'. "
            f"Known SES regions include: {sample}{more}"
        )

    return region


def get_ses_client(region_name: Optional[str] = None):
    region = region_name or resolve_ses_region()
    return boto3.client("ses", region_name=region)

