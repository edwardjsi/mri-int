#!/bin/bash
# ============================================================
# MRI Teardown — Stop all AWS resources for the day
# Usage: bash scripts/mri_teardown.sh
# ============================================================

set -euo pipefail

REGION="ap-south-1"
RDS_INSTANCE="mri-dev-db"
BASTION_ID="i-060624f65152387a1"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

log() { echo -e "${BLUE}[$(date +%H:%M)]${NC} $1"; }
ok()  { echo -e "${GREEN}[$(date +%H:%M)] ✅ $1${NC}"; }

echo ""
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo -e "${YELLOW}  MRI Teardown — Shutting everything down${NC}"
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
echo ""

# Kill any local API servers
log "Stopping local API servers..."
pkill -f "uvicorn api.main" 2>/dev/null && ok "API server stopped" || ok "No API server running"

# Kill any SSM tunnels
log "Closing SSM tunnels..."
pkill -f "aws ssm start-session" 2>/dev/null && ok "SSM tunnel closed" || ok "No tunnels open"

# Stop Bastion
log "Stopping Bastion host ($BASTION_ID)..."
aws ec2 stop-instances --instance-ids $BASTION_ID --region $REGION > /dev/null 2>&1 \
  && ok "Bastion stopping" \
  || ok "Bastion already stopped"

# Stop RDS
log "Stopping RDS instance ($RDS_INSTANCE)..."
aws rds stop-db-instance --db-instance-identifier $RDS_INSTANCE --region $REGION > /dev/null 2>&1 \
  && ok "RDS stopping" \
  || ok "RDS already stopped"

echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  All done! Everything is shutting down.${NC}"
echo -e "${GREEN}  RDS + Bastion will be fully off in ~2 min.${NC}"
echo -e "${GREEN}  Run tomorrow: bash scripts/mri_daily.sh${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""
