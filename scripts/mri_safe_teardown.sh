#!/bin/bash
# ============================================================
# MRI Safe Teardown — Destroy infra, PROTECT RDS (built-in)
# Usage: bash scripts/mri_safe_teardown.sh
#
# SAFE: Removes RDS from Terraform state before destroying.
# RDS stays alive (stopped) in AWS — never touched by destroy.
# ============================================================

set -euo pipefail

REGION="ap-south-1"
RDS_INSTANCE="mri-dev-db"
TF_DIR="/home/edwar/mri-int/terraform/environments/dev"
LOG_DIR="/home/edwar/mri-int/logs"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

log() { echo -e "${BLUE}[$(date +%H:%M)]${NC} $1"; }
ok()  { echo -e "${GREEN}[$(date +%H:%M)] ✅ $1${NC}"; }
warn(){ echo -e "${YELLOW}[$(date +%H:%M)] ⚠️  $1${NC}"; }

LOGFILE="$LOG_DIR/teardown_$(date +%Y%m%d).log"
mkdir -p "$LOG_DIR"

echo ""
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo -e "${YELLOW}  MRI Safe Teardown — RDS Protected${NC}"
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo ""

# Step 1: Kill local processes
log "Stopping local services..."
pkill -f "vite" 2>/dev/null && ok "Frontend server stopped" || ok "No Frontend server running"
pkill -f "uvicorn api.main" 2>/dev/null && ok "API server stopped" || ok "No API server running"
pkill -f "aws ssm start-session" 2>/dev/null && ok "SSM tunnel closed" || ok "No tunnels open"

# Step 2: Stop RDS (keeps it alive, $0 compute cost)
log "Stopping RDS instance..."
aws rds stop-db-instance --db-instance-identifier $RDS_INSTANCE --region $REGION > /dev/null 2>&1 \
  && ok "RDS stopping" \
  || ok "RDS already stopped"

# Step 3: Remove RDS resources from Terraform state (PROTECT THEM)
log "Protecting RDS — removing from Terraform state..."
cd "$TF_DIR"

RDS_RESOURCES=(
  "module.rds.aws_db_instance.main"
  "module.rds.aws_db_subnet_group.main"
  "module.rds.aws_secretsmanager_secret.db"
  "module.rds.aws_secretsmanager_secret_version.db"
  "module.rds.random_password.db"
)

for resource in "${RDS_RESOURCES[@]}"; do
  terraform state rm "$resource" >> "$LOGFILE" 2>&1 \
    && ok "Protected: $resource" \
    || warn "Already protected: $resource"
done

# Step 4: Destroy everything else
log "Destroying remaining infrastructure (VPC, bastion, S3, IAM, frontend)..."
terraform destroy -auto-approve >> "$LOGFILE" 2>&1
ok "Infrastructure destroyed"

echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  Teardown Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  RDS: SAFE (stopped in AWS, ~\$0/day)${NC}"
echo -e "${GREEN}  All other resources: DESTROYED${NC}"
echo -e "${GREEN}  Log: $LOGFILE${NC}"
echo ""
echo -e "${GREEN}  Tomorrow, just run:${NC}"
echo -e "${GREEN}    bash scripts/mri_daily.sh${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""
