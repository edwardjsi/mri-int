#!/bin/bash
# MRI Daily Pipeline — Cloud Version (No AWS Tunnel Required)
# Connects directly to Neon.tech PostgreSQL over the internet.
# Usage: bash scripts/pipeline_cloud.sh
# Schedule: Cron at 4:15 PM IST Mon-Fri (10:45 UTC)

set -e

# These should be set as environment variables (Render, GitHub Actions, etc.)
# DATABASE_URL=postgresql://user:pass@host/dbname
# DB_SSL=true
# SES_SENDER_EMAIL=edwardjsi@gmail.com
# SES_REGION=ap-southeast-1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Activate venv if running locally
if [ -d "venv" ]; then
    source venv/bin/activate
fi

export PYTHONPATH="$PROJECT_DIR"

LOG_FILE="$PROJECT_DIR/logs/pipeline_cloud_$(date +%Y%m%d).log"
mkdir -p "$PROJECT_DIR/logs"

echo "=== MRI Cloud Pipeline — $(date) ===" | tee -a "$LOG_FILE"

# Step 1: Ingest today's data
echo "[1/5] Ingesting today's market data..." | tee -a "$LOG_FILE"
python -c "
from src.ingestion_engine import load_indices, load_stocks
import pandas as pd, requests, io

load_indices()

url = 'https://archives.nseindia.com/content/indices/ind_nifty500list.csv'
headers = {'User-Agent': 'Mozilla/5.0'}
response = requests.get(url, headers=headers, timeout=30)
df = pd.read_csv(io.StringIO(response.text))
symbols = df['Symbol'].dropna().unique().tolist()
load_stocks(symbols)
" 2>&1 | tee -a "$LOG_FILE"

# Step 2: Compute indicators
echo "[2/5] Running Indicator Engine..." | tee -a "$LOG_FILE"
python src/indicator_engine.py 2>&1 | tee -a "$LOG_FILE"

# Step 3: Compute regime + scores
echo "[3/5] Running Regime Engine..." | tee -a "$LOG_FILE"
python src/regime_engine.py 2>&1 | tee -a "$LOG_FILE"

# Step 4: Generate client signals
echo "[4/5] Generating client signals..." | tee -a "$LOG_FILE"
python src/signal_generator.py 2>&1 | tee -a "$LOG_FILE"

# Step 5: Send email notifications
echo "[5/5] Sending signal emails via SES..." | tee -a "$LOG_FILE"
python src/email_service.py 2>&1 | tee -a "$LOG_FILE"

echo "=== Cloud Pipeline Complete — $(date) ===" | tee -a "$LOG_FILE"
