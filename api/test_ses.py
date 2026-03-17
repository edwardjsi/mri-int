import boto3
from botocore.exceptions import ClientError

# Initialize the SES client specifically in the Singapore region
ses_client = boto3.client('ses', region_name='ap-southeast-1')

SENDER = "edwardjsi@gmail.com"
RECIPIENT = "edwardjsi@gmail.com"

SUBJECT = "Market Regime Intelligence - System Test"
BODY_TEXT = (
    "System Test Successful\r\n"
    "This email confirms that the AWS SES credentials and IAM permissions "
    "are fully operational."
)

try:
    print("Attempting to send test email...")
    response = ses_client.send_email(
        Destination={
            'ToAddresses': [RECIPIENT],
        },
        Message={
            'Body': {
                'Text': {
                    'Charset': "UTF-8",
                    'Data': BODY_TEXT,
                },
            },
            'Subject': {
                'Charset': "UTF-8",
                'Data': SUBJECT,
            },
        },
        Source=SENDER,
    )
    print(f"Success! Email sent. Message ID: {response['MessageId']}")
    
except ClientError as e:
    print(f"Error sending email: {e.response['Error']['Message']}")