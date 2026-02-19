import boto3
import json
import os

def get_db_credentials():
    """
    Fetch DB credentials from AWS Secrets Manager.
    Falls back to environment variables for local testing.
    """
    secret_arn = os.environ.get("DB_SECRET_ARN")

    # Local dev fallback
    if not secret_arn:
        return {
            "host":     os.environ.get("DB_HOST"),
            "port":     int(os.environ.get("DB_PORT", 5432)),
            "dbname":   os.environ.get("DB_NAME", "mri_db"),
            "username": os.environ.get("DB_USER", "mri_admin"),
            "password": os.environ.get("DB_PASSWORD"),
        }

    client = boto3.client("secretsmanager", region_name="ap-south-1")
    response = client.get_secret_value(SecretId=secret_arn)
    secret = json.loads(response["SecretString"])
    return secret


def get_connection_string():
    creds = get_db_credentials()
    return (
        f"postgresql://{creds['username']}:{creds['password']}"
        f"@{creds['host']}:{creds.get('port', 5432)}/{creds['dbname']}"
    )


# S3 config
S3_BUCKET = os.environ.get("S3_BUCKET", "mri-dev-outputs-251876202726")
AWS_REGION = "ap-south-1"

# Backtest config
START_DATE = "2005-01-01"
END_DATE   = "2024-12-31"

# Strategy config
REGIME_RISK_ON_THRESHOLD  = 60
SCORE_ENTRY_THRESHOLD     = 4
SCORE_EXIT_THRESHOLD      = 2
MAX_PORTFOLIO_STOCKS      = 10
TRANSACTION_COST          = 0.004   # 0.4% round trip
TRAILING_STOP             = 0.20    # 20%
