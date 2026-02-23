source venv/bin/activate
export DB_HOST="localhost"
export DB_PORT="5433"
export DB_NAME="mri_db"
export DB_USER="mri_admin"
export DB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id mri-dev-db-credentials --region ap-south-1 --query "SecretString" --output text | grep -o '"password":"[^"]*' | cut -d'"' -f4)
export PYTHONPATH=.
python -c "from src.db import get_connection; import pandas as pd; conn=get_connection(); print(pd.read_sql('SELECT distinct symbol FROM index_prices', conn))"
