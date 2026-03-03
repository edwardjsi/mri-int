#!/bin/bash
# ============================================================
# MRI Daily Run — Cost-Conscious Mode
# Starts infrastructure, runs pipeline, serves API, tears down.
# Usage: bash scripts/mri_daily.sh
# ============================================================

set -euo pipefail

REGION="ap-south-1"
RDS_INSTANCE="mri-dev-db"
BASTION_ID="i-01a0923e978370fc9"
RDS_ENDPOINT="mri-dev-db.c9a44u2kqcf8.ap-south-1.rds.amazonaws.com"
LOCAL_DB_PORT="5433"
PROJECT_DIR="/home/edwar/mri-int"
LOG_DIR="$PROJECT_DIR/logs"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

log() { echo -e "${BLUE}[$(date +%H:%M)]${NC} $1"; }
ok()  { echo -e "${GREEN}[$(date +%H:%M)] ✅ $1${NC}"; }
warn(){ echo -e "${YELLOW}[$(date +%H:%M)] ⚠️  $1${NC}"; }
err() { echo -e "${RED}[$(date +%H:%M)] ❌ $1${NC}"; }

mkdir -p "$LOG_DIR"
LOGFILE="$LOG_DIR/daily_$(date +%Y%m%d).log"

# ── Phase 1: Start Infrastructure ──────────────────────────

log "Starting RDS instance..."
aws rds start-db-instance --db-instance-identifier $RDS_INSTANCE --region $REGION >> "$LOGFILE" 2>&1 || warn "RDS may already be running"

log "Starting Bastion host..."
aws ec2 start-instances --instance-ids $BASTION_ID --region $REGION >> "$LOGFILE" 2>&1 || warn "Bastion may already be running"

log "Waiting for RDS to become available (this takes ~5-10 min)..."
aws rds wait db-instance-available --db-instance-identifier $RDS_INSTANCE --region $REGION 2>&1 | tee -a "$LOGFILE"
ok "RDS is available"

log "Waiting for Bastion to pass status checks..."
aws ec2 wait instance-status-ok --instance-ids $BASTION_ID --region $REGION 2>&1 | tee -a "$LOGFILE"
ok "Bastion is ready"

# ── Phase 2: Open DB Tunnel ────────────────────────────────

log "Opening SSM tunnel to RDS (localhost:$LOCAL_DB_PORT → RDS:5432)..."
aws ssm start-session \
  --target $BASTION_ID \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters "{\"host\":[\"$RDS_ENDPOINT\"],\"portNumber\":[\"5432\"],\"localPortNumber\":[\"$LOCAL_DB_PORT\"]}" \
  --region $REGION >> "$LOGFILE" 2>&1 &
TUNNEL_PID=$!
sleep 5
ok "DB tunnel open (PID: $TUNNEL_PID)"

# ── Phase 3: Set up environment ───────────────────────────

cd "$PROJECT_DIR"
source venv/bin/activate

export DB_HOST="localhost"
export DB_PORT="$LOCAL_DB_PORT"
export DB_NAME="mri_db"
export DB_USER="mri_admin"
export DB_PASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id mri-dev-db-credentials \
  --region $REGION \
  --query "SecretString" --output text | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")
export PYTHONPATH="$PROJECT_DIR"
export SES_SENDER_EMAIL="edwardjsi@gmail.com"
export AWS_REGION="$REGION"

# ── Phase 4: Run Pipeline ─────────────────────────────────

echo ""
log "═══════════════════════════════════════"
log "  Running MRI Daily Pipeline"
log "═══════════════════════════════════════"
echo ""

python scripts/pipeline.py 2>&1 | tee -a "$LOGFILE"

echo ""
ok "Pipeline complete!"
echo ""

# ── Phase 5: Serve API for testers ─────────────────────────

log "Starting local API server for testers..."
uvicorn api.main:app --host 0.0.0.0 --port 8000 >> "$LOGFILE" 2>&1 &
API_PID=$!
sleep 2
ok "API running at http://localhost:8000"
echo ""

echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  Testers can log in now!${NC}"
echo -e "${GREEN}  Dashboard: http://localhost:8000${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Press ENTER when everyone is done to tear down...${NC}"
read -r

# ── Phase 6: Tear Down ─────────────────────────────────────

echo ""
log "Tearing down..."

log "Stopping API server..."
kill $API_PID 2>/dev/null || true
ok "API stopped"

log "Closing DB tunnel..."
kill $TUNNEL_PID 2>/dev/null || true
ok "Tunnel closed"

log "Stopping Bastion..."
aws ec2 stop-instances --instance-ids $BASTION_ID --region $REGION >> "$LOGFILE" 2>&1
ok "Bastion stopping"

log "Stopping RDS..."
aws rds stop-db-instance --db-instance-identifier $RDS_INSTANCE --region $REGION >> "$LOGFILE" 2>&1
ok "RDS stopping"

echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  All done! Infrastructure tearing down.${NC}"
echo -e "${GREEN}  Estimated cost today: ~\$0.07${NC}"
echo -e "${GREEN}  Log: $LOGFILE${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
