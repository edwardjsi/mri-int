#!/bin/bash
# MRI Daily Pipeline — Cron script
# Runs at 4PM IST Mon-Fri after market close
# Pipeline: Data Ingest → Indicators → Regime → Signals → Emails

set -e

cd /home/edwar/mri-int
source venv/bin/activate

export DB_HOST="localhost"
export DB_PORT="5433"
export DB_NAME="mri_db"
export DB_USER="mri_admin"
export DB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id mri-dev-db-credentials --region ap-south-1 --query "SecretString" --output text | grep -o '"password":"[^"]*' | cut -d'"' -f4)
export PYTHONPATH=.

LOG_FILE="/home/edwar/mri-int/logs/pipeline_$(date +%Y%m%d).log"
mkdir -p /home/edwar/mri-int/logs

echo "=== MRI Daily Pipeline — $(date) ===" | tee -a $LOG_FILE

# Step 1: Ingest today's data (Nifty 500 + User added stocks)
echo "[1/5] Ingesting today's market data..." | tee -a $LOG_FILE
python -c "
from engine_core.ingestion_engine import load_indices, load_stocks
from engine_core.db import get_connection
import pandas as pd, requests, io

# Load indices
load_indices()

# 1. Fetch Nifty 500
url = 'https://archives.nseindia.com/content/indices/ind_nifty500list.csv'
headers = {'User-Agent': 'Mozilla/5.0'}
response = requests.get(url, headers=headers, timeout=30)
df = pd.read_csv(io.StringIO(response.text))
symbols = set(df['Symbol'].dropna().unique().tolist())

# 2. Fetch all user-added stocks (Watchlist + Holdings)
conn = get_connection()
cur = conn.cursor()
cur.execute('SELECT symbol FROM client_watchlist')
symbols.update([r[0] for r in cur.fetchall()])
cur.execute('SELECT symbol FROM client_external_holdings')
symbols.update([r[0] for r in cur.fetchall()])
cur.close()
conn.close()

print(f'Ingesting total universe of {len(symbols)} symbols...')
load_stocks(list(symbols))
" 2>&1 | tee -a $LOG_FILE

# Step 2: Compute indicators
echo "[2/5] Running Indicator Engine..." | tee -a $LOG_FILE
python engine_core/indicator_engine.py 2>&1 | tee -a $LOG_FILE

# Step 3: Compute regime + scores
echo "[3/5] Running Regime Engine..." | tee -a $LOG_FILE
python engine_core/regime_engine.py 2>&1 | tee -a $LOG_FILE

# Step 4: Generate client signals
echo "[4/5] Generating general MRI signals..." | tee -a $LOG_FILE
python engine_core/signal_generator.py 2>&1 | tee -a $LOG_FILE

echo "[4b] Running Swing Execution Engine (STEE)..." | tee -a $LOG_FILE
python engine_core/swing_execution_engine.py 2>&1 | tee -a $LOG_FILE

# Step 5: Send email notifications
echo "[5/5] Sending signal emails via SES..." | tee -a $LOG_FILE
python engine_core/email_service.py 2>&1 | tee -a $LOG_FILE

echo "[5b] Sending STEE Swing Trade Alerts..." | tee -a $LOG_FILE
python -c "from engine_core.email_service import send_stee_signal_emails; send_stee_signal_emails()" 2>&1 | tee -a $LOG_FILE

# Step 6: Final Health & Integrity Audit
echo "[6/6] Running Pipeline Health Audit..." | tee -a $LOG_FILE
python scripts/pipeline_health_monitor.py 2>&1 | tee -a $LOG_FILE

echo "=== Pipeline Complete — $(date) ===" | tee -a $LOG_FILE
