import boto3
import json

def list_secrets():
    try:
        client = boto3.client("secretsmanager", region_name="ap-south-1")
        response = client.list_secrets()
        for secret in response.get("SecretList", []):
            print(secret["Name"])
    except Exception as e:
        print(f"FAIL: {e}")

if __name__ == '__main__':
    list_secrets()
