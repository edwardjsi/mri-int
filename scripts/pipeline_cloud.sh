#!/bin/bash
# MRI Daily Pipeline — Cloud Version (No AWS Tunnel Required)
# Connects directly to Neon.tech PostgreSQL over the internet.
# Usage: bash scripts/pipeline_cloud.sh
# Schedule: Cron at 4:15 PM IST Mon-Fri (10:45 UTC)

set -e
set -o pipefail


# These should be set as environment variables (Render, GitHub Actions, etc.)
# DATABASE_URL=postgresql://user:pass@host/dbname
# DB_SSL=true
# SES_SENDER_EMAIL=edwardjsi@gmail.com
# SES_REGION=ap-southeast-1

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

# Activate venv if running locally
if [ -d "venv" ]; then
    source venv/bin/activate
fi

export PYTHONPATH="$PROJECT_DIR"

LOG_FILE="$PROJECT_DIR/logs/pipeline_cloud_$(date +%Y%m%d).log"
mkdir -p "$PROJECT_DIR/logs"

echo "=== MRI Cloud Pipeline — $(date) ===" | tee -a "$LOG_FILE"

# Step 1: Ingest today's data (indices + Nifty 500 symbols)
echo "[1/7] Ingesting today's market data..." | tee -a "$LOG_FILE"
python - <<'PY' 2>&1 | tee -a "$LOG_FILE"
import pandas as pd, requests, io
from engine_core.ingestion_engine import load_indices, load_stocks

load_indices()

url = 'https://archives.nseindia.com/content/indices/ind_nifty500list.csv'
headers = {'User-Agent': 'Mozilla/5.0'}
response = requests.get(url, headers=headers, timeout=30)
df = pd.read_csv(io.StringIO(response.text))
symbols = df['Symbol'].dropna().unique().tolist()
load_stocks(symbols)
PY

# Step 2: Compute indicators
echo "[2/7] Running Indicator Engine..." | tee -a "$LOG_FILE"
python engine_core/indicator_engine.py 2>&1 | tee -a "$LOG_FILE"

# Step 3: Compute regime + scores
echo "[3/7] Running Regime Engine..." | tee -a "$LOG_FILE"
python engine_core/regime_engine.py 2>&1 | tee -a "$LOG_FILE"

# Step 4: Generate client signals
echo "[4/7] Generating client signals..." | tee -a "$LOG_FILE"
python engine_core/signal_generator.py 2>&1 | tee -a "$LOG_FILE"

# Step 5: Send email notifications (Including STEE)
echo "[5/7] Sending signal emails via SES..." | tee -a "$LOG_FILE"
python engine_core/email_service.py 2>&1 | tee -a "$LOG_FILE"

# Step 6: Pipeline Health Monitor (Auto-Alert on Drift)
echo "[6/7] Running Pipeline Health Monitor..." | tee -a "$LOG_FILE"
python scripts/pipeline_health_monitor.py 2>&1 | tee -a "$LOG_FILE"

# Step 7: Fundamental Quality analysis (Top 20 candidates)
echo "[7/7] Running Fundamental Quality Analysis for top candidates..." | tee -a "$LOG_FILE"
python - <<'PY' 2>&1 | tee -a "$LOG_FILE"
from engine_core.db import get_connection
from engine_fundamental.collector import fetch_and_store_financials
from engine_fundamental.pipeline import run_quality_pipeline

conn = get_connection()
cur = conn.cursor()
# Fetch top 20 symbols by score from today
cur.execute("SELECT symbol FROM stock_scores WHERE date = (SELECT MAX(date) FROM stock_scores) ORDER BY score DESC LIMIT 20")
top_symbols = [r['symbol'] for r in cur.fetchall()]
conn.close()

for sym in top_symbols:
    # yfinance needs .NS for NSE stocks
    yf_sym = f"{sym}.NS" if not sym.endswith(".NS") and not sym.endswith(".BO") else sym
    try:
        print(f"Analyzing {yf_sym}...")
        fetch_and_store_financials(yf_sym)
        run_quality_pipeline(yf_sym)
    except Exception as e:
        print(f"Failed analysis for {yf_sym}: {e}")
PY

echo "=== Cloud Pipeline Complete — $(date) ===" | tee -a "$LOG_FILE"