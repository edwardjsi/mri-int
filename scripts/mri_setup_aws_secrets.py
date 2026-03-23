import boto3
import json
import getpass

def setup_mri_secrets(region_name='ap-south-1'):
    client = boto3.client('secretsmanager', region_name=region_name)
    secret_name = "mri-mailerlite-credentials"

    print(f"--- MRI AWS Secret Setup ({region_name}) ---")
    print(f"This will create/update the secret: {secret_name}")
    
    api_key = getpass.getpass("Enter your MailerLite API Key: ")
    group_id = input("Enter your MailerLite Group ID: ")

    secret_dict = {
        "MAILERLITE_API_KEY": api_key,
        "MAILERLITE_GROUP_ID": group_id
    }

    try:
        # Check if secret exists
        try:
            client.describe_secret(SecretId=secret_name)
            print(f"Updating existing secret: {secret_name}")
            client.update_secret(SecretId=secret_name, SecretString=json.dumps(secret_dict))
        except client.exceptions.ResourceNotFoundException:
            print(f"Creating new secret: {secret_name}")
            client.create_secret(
                Name=secret_name,
                Description="MailerLite API Key and Group ID for MRI-Int App",
                SecretString=json.dumps(secret_dict)
            )
        print("\n✅ Successfully updated AWS Secrets Manager.")
        print(f"You can now use MAILERLITE_SECRET_NAME={secret_name} in your environment.")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == '__main__':
    setup_mri_secrets()
