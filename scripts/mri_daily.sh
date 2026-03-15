#!/bin/bash
# ============================================================
# MRI Daily Run — Cost-Conscious Mode
# Rebuilds infrastructure, runs pipeline, serves API, tears down.
#
# SAFE: Automatically handles RDS import if missing from state.
# Usage: bash scripts/mri_daily.sh
# ============================================================

set -euo pipefail

REGION="ap-south-1"
RDS_INSTANCE="mri-dev-db"
RDS_ENDPOINT="mri-dev-db.c9a44u2kqcf8.ap-south-1.rds.amazonaws.com"
LOCAL_DB_PORT="5433"
PROJECT_DIR="/home/edwar/mri-int"
TF_DIR="$PROJECT_DIR/terraform/environments/dev"
LOG_DIR="$PROJECT_DIR/logs"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

log() { echo -e "${BLUE}[$(date +%H:%M)]${NC} $1"; }
ok()  { echo -e "${GREEN}[$(date +%H:%M)] ✅ $1${NC}"; }
warn(){ echo -e "${YELLOW}[$(date +%H:%M)] ⚠️  $1${NC}"; }
err() { echo -e "${RED}[$(date +%H:%M)] ❌ $1${NC}"; }

mkdir -p "$LOG_DIR"
LOGFILE="$LOG_DIR/daily_$(date +%Y%m%d).log"

echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  MRI Daily Run — $(date +%Y-%m-%d)${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""

# ── Phase 0: Start RDS ─────────────────────────────────────────
cd "$PROJECT_DIR"
log "Starting RDS instance (needs to be available for Terraform)..."
aws rds start-db-instance --db-instance-identifier $RDS_INSTANCE --region $REGION >> "$LOGFILE" 2>&1 || warn "RDS may already be running"

log "Waiting for RDS to become available (this takes ~5-10 min)..."
aws rds wait db-instance-available --db-instance-identifier $RDS_INSTANCE --region $REGION 2>&1 | tee -a "$LOGFILE"
ok "RDS is available"

# ── Phase 1: Rebuild Infrastructure ────────────────────────

log "Phase 1: Rebuilding infrastructure with Terraform..."
cd "$TF_DIR"

# Check if RDS is in terraform state — if not, import it
if ! terraform state list 2>/dev/null | grep -q "module.rds.aws_db_instance.main"; then
    warn "RDS not in Terraform state — importing existing instance..."
    terraform import module.rds.aws_db_instance.main "$RDS_INSTANCE" >> "$LOGFILE" 2>&1 || true

    # Import other RDS-related resources if needed
    terraform import module.rds.aws_db_subnet_group.main "mri-dev-db-subnet-group" >> "$LOGFILE" 2>&1 || true
    terraform import module.rds.aws_secretsmanager_secret.db "mri-dev-db-credentials" >> "$LOGFILE" 2>&1 || true
    terraform import module.rds.random_password.db "ignored" >> "$LOGFILE" 2>&1 || true
    ok "RDS imported into state"
fi

log "Running terraform apply (this may take 1-2 minutes)..."
terraform apply -auto-approve >> "$LOGFILE" 2>&1
ok "Infrastructure ready"

log "Syncing database password..."
bash "$PROJECT_DIR/scripts/sync_password.sh" >> "$LOGFILE" 2>&1
ok "Database password synced"

# Get the current bastion ID from terraform output
BASTION_ID=$(terraform output -raw bastion_id 2>/dev/null)
log "Bastion ID: $BASTION_ID"

# ── Phase 2: Start Bastion ──────────────────────────

cd "$PROJECT_DIR"

log "Starting Bastion host..."
aws ec2 start-instances --instance-ids $BASTION_ID --region $REGION >> "$LOGFILE" 2>&1 || warn "Bastion may already be running"

log "Waiting for RDS to become available (this takes ~5-10 min)..."
aws rds wait db-instance-available --db-instance-identifier $RDS_INSTANCE --region $REGION 2>&1 | tee -a "$LOGFILE"
ok "RDS is available"

log "Waiting for Bastion to pass status checks..."
aws ec2 wait instance-status-ok --instance-ids $BASTION_ID --region $REGION 2>&1 | tee -a "$LOGFILE"
ok "Bastion is ready"

# ── Phase 3: Open DB Tunnel ────────────────────────────────

log "Opening SSM tunnel to RDS (localhost:$LOCAL_DB_PORT → RDS:5432)..."
aws ssm start-session \
  --target $BASTION_ID \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters "{\"host\":[\"$RDS_ENDPOINT\"],\"portNumber\":[\"5432\"],\"localPortNumber\":[\"$LOCAL_DB_PORT\"]}" \
  --region $REGION >> "$LOGFILE" 2>&1 &
TUNNEL_PID=$!
sleep 5
ok "DB tunnel open (PID: $TUNNEL_PID)"

# ── Phase 4: Set up environment ───────────────────────────

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
export SES_REGION="${SES_REGION:-$AWS_REGION}"

# ── Phase 5: Run Pipeline ─────────────────────────────────

echo ""
log "═══════════════════════════════════════"
log "  Running MRI Daily Pipeline"
log "═══════════════════════════════════════"
echo ""

python scripts/pipeline.py 2>&1 | tee -a "$LOGFILE"

echo ""
ok "Pipeline complete!"
echo ""

# ── Phase 6: Serve API & Frontend for testers ─────────────────────────

log "Starting local API server for testers..."
uvicorn api.main:app --host 0.0.0.0 --port 8000 >> "$LOGFILE" 2>&1 &
API_PID=$!
sleep 2
ok "API running at http://localhost:8000"

log "Starting local Frontend server for testers..."
cd "$PROJECT_DIR/frontend"
npm run dev -- --host >> "$LOGFILE" 2>&1 &
FRONTEND_PID=$!
sleep 2
ok "Frontend running at http://localhost:5173"
cd "$PROJECT_DIR"
echo ""

echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  Testers can log in now!${NC}"
echo -e "${GREEN}  Dashboard: http://localhost:5173${NC}"
echo -e "${GREEN}  API:       http://localhost:8000${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}Press ENTER when everyone is done to tear down...${NC}"
read -r

# ── Phase 7: Safe Tear Down ────────────────────────────────

echo ""
log "Starting safe teardown..."
bash "$PROJECT_DIR/scripts/mri_safe_teardown.sh"
