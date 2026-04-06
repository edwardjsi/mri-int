# src/config.py
import boto3
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load local .env file if it exists
load_dotenv()

def get_db_credentials():
    """
    Fetch DB credentials. Priority:
    1. DATABASE_URL env var (Neon.tech / Render.com / Heroku style)
    2. AWS Secrets Manager (ECS Fargate production)
    3. Individual DB_* env vars (local dev)
    """
    # Cloud-native: single connection string (Neon, Render, etc.)
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        from urllib.parse import urlparse
        parsed = urlparse(database_url)
        return {
            "host":     parsed.hostname,
            "port":     parsed.port or 5432,
            "dbname":   parsed.path.lstrip("/"),
            "username": parsed.username,
            "password": parsed.password,
        }

    # AWS Secrets Manager (ECS/Fargate)
    secret_arn = os.environ.get("DB_SECRET_ARN")
    if secret_arn:
        client = boto3.client("secretsmanager", region_name="ap-south-1")
        response = client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(response["SecretString"])
        return secret

    # Local dev fallback
    return {
        "host":     os.environ.get("DB_HOST"),
        "port":     int(os.environ.get("DB_PORT", 5432)),
        "dbname":   os.environ.get("DB_NAME", "mri_db"),
        "username": os.environ.get("DB_USER", "mri_admin"),
        "password": os.environ.get("DB_PASSWORD"),
    }


def get_mailerlite_credentials():
    """
    Fetch MailerLite API Key and Group ID. Priority:
    1. Environment variables (MAILERLITE_API_KEY, MAILERLITE_GROUP_ID)
    2. AWS Secrets Manager (mri-mailerlite-credentials)
    """
    api_key = os.environ.get("MAILERLITE_API_KEY")
    group_id = os.environ.get("MAILERLITE_GROUP_ID")

    if api_key:
        return {"api_key": api_key, "group_id": group_id}

    # Fallback to AWS Secrets Manager
    secret_name = os.environ.get("MAILERLITE_SECRET_NAME", "mri-mailerlite-credentials")
    try:
        client = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "ap-south-1"))
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response["SecretString"])
        return {
            "api_key":  secret.get("MAILERLITE_API_KEY", ""),
            "group_id": secret.get("MAILERLITE_GROUP_ID", ""),
        }
    except Exception as e:
        # If we fail to fetch from AWS and have no env var, return empty
        return {"api_key": "", "group_id": ""}


# SSL required for cloud PostgreSQL providers (Neon, Supabase, etc.)
DB_SSL = os.environ.get("DB_SSL", "false").lower() == "true"


def get_connection_string():
    creds = get_db_credentials()
    base = (
        f"postgresql://{creds['username']}:{creds['password']}"
        f"@{creds['host']}:{creds.get('port', 5432)}/{creds['dbname']}"
    )
    if DB_SSL:
        base += "?sslmode=require"
    return base


# S3 and General AWS config
S3_BUCKET = os.environ.get("S3_BUCKET", "mri-dev-outputs-251876202726")
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")

# SES Email Config
SES_REGION = os.environ.get("SES_REGION", "ap-southeast-1")
SES_SENDER_EMAIL = os.environ.get("SES_SENDER_EMAIL", "edwardjsi@gmail.com")

# Backtest config
START_DATE = "2022-01-01"
from datetime import timedelta
END_DATE   = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

# Strategy config
REGIME_RISK_ON_THRESHOLD  = 60
SCORE_ENTRY_THRESHOLD     = 4
SCORE_EXIT_THRESHOLD      = 2
MAX_PORTFOLIO_STOCKS      = 10
TRANSACTION_COST          = 0.004   # 0.4% round trip
TRAILING_STOP             = 0.20    # 20%