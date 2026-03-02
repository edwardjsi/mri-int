#!/bin/bash
# Run the FastAPI server locally for development
# Requires SSM tunnel active on port 5433

source venv/bin/activate
export DB_HOST="localhost"
export DB_PORT="5433"
export DB_NAME="mri_db"
export DB_USER="mri_admin"
export DB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id mri-dev-db-credentials --region ap-south-1 --query "SecretString" --output text | grep -o '"password":"[^"]*' | cut -d'"' -f4)
export PYTHONPATH=.
export JWT_SECRET="mri-dev-secret-change-in-prod"

echo "Starting MRI API Server on http://localhost:8000"
echo "Docs: http://localhost:8000/docs"
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
