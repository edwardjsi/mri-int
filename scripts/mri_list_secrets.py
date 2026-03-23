import boto3
import sys

def list_secrets(region_name='ap-south-1'):
    print(f"--- Secrets in {region_name} ---")
    try:
        client = boto3.client('secretsmanager', region_name=region_name)
        response = client.list_secrets()
        secrets = response.get('SecretList', [])
        if not secrets:
            print("  No secrets found.")
        for secret in secrets:
            print(f"  - Name: {secret['Name']} | ARN: {secret['ARN']}")
    except Exception as e:
        print(f"  Error: {e}")

if __name__ == '__main__':
    # Checking both major regions used in this project
    list_secrets('ap-south-1')
    print()
    list_secrets('ap-southeast-1')
