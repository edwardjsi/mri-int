#!/bin/bash
# Bridge data ingestion script — Nifty 50 ONLY (2024 to March 2026)
# Safe: does NOT drop/recreate tables, only inserts new data via upsert

source venv/bin/activate
export DB_HOST="localhost"
export DB_PORT="5433"
export DB_NAME="mri_db"
export DB_USER="mri_admin"
export DB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id mri-dev-db-credentials --region ap-south-1 --query "SecretString" --output text | grep -o '"password":"[^"]*' | cut -d'"' -f4)
export PYTHONPATH=.

echo "=== MRI Bridge Data Ingestion (NIFTY 50 ONLY) ==="
echo "This script loads NEW data (2024-2026) without dropping existing tables."
echo "Using upsert (ON CONFLICT DO NOTHING) for safe incremental load."
echo ""

python -c "
import psycopg2
import pandas as pd
import requests
import io
from src.data_loader import load_stocks, load_indices
from src.db import get_connection, run_quality_checks
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('bridge_loader')

# Step 0: Fix SERIAL sequences (out of sync after CSV restore)
logger.info('Step 0: Resetting SERIAL sequences...')
conn = get_connection()
cur = conn.cursor()
cur.execute(\"SELECT setval('daily_prices_id_seq', (SELECT COALESCE(MAX(id), 1) FROM daily_prices));\")
cur.execute(\"SELECT setval('index_prices_id_seq', (SELECT COALESCE(MAX(id), 1) FROM index_prices));\")
conn.commit()
cur.close()
conn.close()
logger.info('Sequences reset successfully.')

# Step 1: Load index data
logger.info('=== Bridge Data Ingestion Starting ===')
logger.info('Step 1: Loading index data (NIFTY50, NIFTYMID)...')
load_indices()

# Step 2: Fetch Nifty 50 stock list (NOT Nifty 500)
logger.info('Step 2: Fetching Nifty 50 stock list...')
url = 'https://archives.nseindia.com/content/indices/ind_nifty50list.csv'
headers = {'User-Agent': 'Mozilla/5.0', 'Accept': 'text/html,application/xhtml+xml'}
try:
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    df = pd.read_csv(io.StringIO(response.text))
    symbols = df['Symbol'].dropna().unique().tolist()
    logger.info(f'Fetched {len(symbols)} Nifty 50 symbols: {symbols[:10]}...')
except Exception as e:
    logger.error(f'Failed to fetch Nifty 50 list: {e}')
    exit(1)

# Step 3: Load bridge data for Nifty 50 stocks only
logger.info(f'Step 3: Loading bridge data for {len(symbols)} Nifty 50 stocks...')
failed = load_stocks(symbols)

# Step 4: Quality checks
logger.info('Step 4: Running data quality checks...')
run_quality_checks()

logger.info('=== Bridge Data Ingestion Complete (Nifty 50) ===')
"
