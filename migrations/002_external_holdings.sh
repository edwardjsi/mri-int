#!/bin/bash
# Database migration for Persistent External Holdings
# Run with SSM tunnel active (localhost:5433 → RDS:5432) OR direct to Neon

source venv/bin/activate

# Use existing env or defaults
export DB_HOST=${DB_HOST:-"localhost"}
export DB_PORT=${DB_PORT:-"5433"}
export DB_NAME=${DB_NAME:-"mri_db"}
export DB_USER=${DB_USER:-"mri_admin"}
export DB_PASSWORD=${DB_PASSWORD:-$(aws secretsmanager get-secret-value --secret-id mri-dev-db-credentials --region ap-south-1 --query "SecretString" --output text | grep -o '"password":"[^"]*' | cut -d'"' -f4 2>/dev/null)}

if [ -z "$DB_PASSWORD" ]; then
    echo "Warning: DB_PASSWORD not found. Please set it manually if needed."
fi

# Get the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME < "$DIR/002_external_holdings.sql"

echo "=== Migration Done ==="
