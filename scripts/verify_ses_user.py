import boto3
import argparse
import sys
import os

def verify_email(email: str):
    print(f"🔍 Attempting to send AWS SES Sandbox Verification Email to: {email}")
    
    # Will automatically pick up AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY from .env/environment
    try:
        ses = boto3.client('ses', region_name=os.getenv('AWS_REGION', 'eu-north-1'))
        response = ses.verify_email_identity(
            EmailAddress=email
        )
        print(f"✅ Success! AWS SES has dispatched a verification link to {email}.")
        print("Please ask the user to check their inbox (or spam folder) and click the link to verify their address.")
        print(f"AWS Request ID: {response['ResponseMetadata']['RequestId']}")
    except Exception as e:
        print(f"❌ Error communicating with AWS SES: {e}")
        print("Ensure your AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set correctly!")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trigger an AWS SES Verification Email to a new user.")
    parser.add_argument("email", help="The email address of the new user.")
    args = parser.parse_args()
    verify_email(args.email)
