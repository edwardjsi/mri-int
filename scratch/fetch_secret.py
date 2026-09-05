import boto3
import json

def fetch_secret():
    try:
        client = boto3.client("secretsmanager", region_name="ap-south-1")
        response = client.get_secret_value(SecretId="mri-dev-db-credentials")
        secret = json.loads(response["SecretString"])
        print(f"Secret username: {secret.get('username')}")
        print(f"Secret password: {secret.get('password')}")
    except Exception as e:
        print(f"FAIL: {e}")

if __name__ == '__main__':
    fetch_secret()
