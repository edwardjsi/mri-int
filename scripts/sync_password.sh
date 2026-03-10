#!/bin/bash
set -euo pipefail
REGION="ap-south-1"

echo "Fetching new password from Secrets Manager..."
DB_PASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id mri-dev-db-credentials \
  --region $REGION \
  --query "SecretString" --output text | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")

echo "Applying new password to RDS instance..."
aws rds modify-db-instance --db-instance-identifier mri-dev-db --master-user-password "$DB_PASSWORD" --apply-immediately --region $REGION > /dev/null

echo "Waiting for RDS modification to complete..."
aws rds wait db-instance-available --db-instance-identifier mri-dev-db --region $REGION

echo "RDS password successfully synchronized with Secrets Manager."
