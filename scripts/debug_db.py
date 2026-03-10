import boto3
import json
import psycopg2
import sys

def debug_connection():
    region = "ap-south-1"
    secret_id = "mri-dev-db-credentials"

    print(f"Fetching secret from {secret_id}...")
    try:
        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=secret_id)
        secret = json.loads(response["SecretString"])
        password = secret.get("password")
        print(f"Password length: {len(password) if password else 0}")
    except Exception as e:
        print(f"Failed to fetch secret: {e}")
        sys.exit(1)

    print("\nTesting connection WITH explicit sslmode='require'...")
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5433,
            dbname="mri_db",
            user="mri_admin",
            password=password,
            connect_timeout=10,
            sslmode="require"
        )
        print("✅ Connection SUCCESSFUL with sslmode='require'!")
        conn.close()
    except Exception as e:
        print(f"❌ Connection failed with sslmode='require': {e}")

    print("\nTesting connection WITH default sslmode (prefer)...")
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5433,
            dbname="mri_db",
            user="mri_admin",
            password=password,
            connect_timeout=10
        )
        print("✅ Connection SUCCESSFUL with default sslmode!")
        conn.close()
    except Exception as e:
        print(f"❌ Connection failed with default sslmode: {e}")

if __name__ == "__main__":
    debug_connection()
