#!/bin/bash
# ============================================================
# MRI Cloud Deployment — Neon.tech + Render.com + S3/CloudFront
# 
# This script handles data migration and frontend deployment.
# Prerequisites: 
#   1. Neon.tech account created, DATABASE_URL obtained
#   2. Render.com account created, repo connected
#   3. RDS + bastion tunnel currently active (for data export)
# 
# Usage: bash scripts/deploy_cloud.sh
# ============================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

log() { echo -e "${BLUE}[$(date +%H:%M)]${NC} $1"; }
ok()  { echo -e "${GREEN}[$(date +%H:%M)] ✅ $1${NC}"; }
warn(){ echo -e "${YELLOW}[$(date +%H:%M)] ⚠️  $1${NC}"; }
err() { echo -e "${RED}[$(date +%H:%M)] ❌ $1${NC}"; }

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TF_DIR="$PROJECT_DIR/terraform/environments/dev"
REGION="ap-south-1"

echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  MRI Cloud Deployment${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""

# ── Step 1: Check for DATABASE_URL ────────────────────────
if [ -z "${NEON_DATABASE_URL:-}" ]; then
    echo -e "${YELLOW}Enter your Neon.tech DATABASE_URL:${NC}"
    echo -e "${YELLOW}(format: postgresql://user:pass@host/dbname?sslmode=require)${NC}"
    read -r NEON_DATABASE_URL
fi

echo ""
log "Testing Neon.tech connection..."
PGPASSWORD="" psql "$NEON_DATABASE_URL" -c "SELECT 1 AS connected;" 2>/dev/null && ok "Neon.tech connected!" || {
    err "Failed to connect to Neon.tech. Check your DATABASE_URL."
    exit 1
}

# ── Step 2: Export from RDS (if tunnel active) ────────────
echo ""
echo -e "${YELLOW}Do you want to migrate data from RDS? (y/n)${NC}"
echo -e "${YELLOW}(Requires RDS + bastion tunnel active on port 5433)${NC}"
read -r MIGRATE

if [ "$MIGRATE" = "y" ] || [ "$MIGRATE" = "Y" ]; then
    log "Step 2: Exporting database from RDS..."
    
    export DB_PASSWORD=$(aws secretsmanager get-secret-value \
        --secret-id mri-dev-db-credentials \
        --region $REGION \
        --query "SecretString" --output text | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")
    
    DUMP_FILE="/tmp/mri_db_dump.sql"
    
    log "Dumping RDS database to $DUMP_FILE..."
    PGPASSWORD="$DB_PASSWORD" pg_dump \
        -h localhost -p 5433 -U mri_admin -d mri_db \
        --no-owner --no-privileges --no-acl \
        --clean --if-exists \
        > "$DUMP_FILE"
    
    DUMP_SIZE=$(du -sh "$DUMP_FILE" | cut -f1)
    ok "Database exported ($DUMP_SIZE)"
    
    log "Restoring to Neon.tech..."
    psql "$NEON_DATABASE_URL" < "$DUMP_FILE"
    ok "Data restored to Neon.tech"
    
    log "Verifying data integrity..."
    NEON_COUNT=$(psql "$NEON_DATABASE_URL" -t -c "SELECT COUNT(*) FROM daily_prices;" 2>/dev/null | tr -d ' ')
    RDS_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -h localhost -p 5433 -U mri_admin -d mri_db -t -c "SELECT COUNT(*) FROM daily_prices;" | tr -d ' ')
    
    echo "  RDS rows:  $RDS_COUNT"
    echo "  Neon rows: $NEON_COUNT"
    
    if [ "$NEON_COUNT" = "$RDS_COUNT" ]; then
        ok "Data integrity verified! Counts match."
    else
        warn "Row counts differ. Check the migration."
    fi
else
    log "Skipping RDS migration. You can re-run the full pipeline on Neon later."
fi

# ── Step 3: Build and deploy frontend ────────────────────
echo ""
log "Step 3: Building frontend..."

# Check for RENDER_API_URL
if [ -z "${RENDER_API_URL:-}" ]; then
    echo -e "${YELLOW}Enter your Render.com API URL:${NC}"
    echo -e "${YELLOW}(format: https://mri-api.onrender.com/api)${NC}"
    read -r RENDER_API_URL
fi

cd "$PROJECT_DIR/frontend"
log "Installing dependencies..."
npm install --silent

log "Building with API URL: $RENDER_API_URL"
VITE_API_URL="$RENDER_API_URL" npm run build

ok "Frontend built!"

# Deploy to S3 + CloudFront
echo ""
echo -e "${YELLOW}Deploy frontend to S3/CloudFront? (y/n)${NC}"
read -r DEPLOY_FE

if [ "$DEPLOY_FE" = "y" ] || [ "$DEPLOY_FE" = "Y" ]; then
    cd "$TF_DIR"
    
    # Get terraform outputs
    FRONTEND_BUCKET=$(terraform output -raw frontend_bucket_name 2>/dev/null || echo "")
    CF_DIST_ID=$(terraform output -raw cloudfront_distribution_id 2>/dev/null || echo "")
    CF_DOMAIN=$(terraform output -raw cloudfront_domain 2>/dev/null || echo "")
    
    if [ -z "$FRONTEND_BUCKET" ]; then
        log "Frontend S3/CloudFront not yet created. Running terraform apply..."
        terraform apply -auto-approve
        FRONTEND_BUCKET=$(terraform output -raw frontend_bucket_name)
        CF_DIST_ID=$(terraform output -raw cloudfront_distribution_id)
        CF_DOMAIN=$(terraform output -raw cloudfront_domain)
    fi
    
    cd "$PROJECT_DIR"
    
    log "Syncing to S3: s3://$FRONTEND_BUCKET/"
    aws s3 sync frontend/dist/ "s3://$FRONTEND_BUCKET/" --delete --region $REGION
    
    log "Invalidating CloudFront cache..."
    aws cloudfront create-invalidation \
        --distribution-id "$CF_DIST_ID" \
        --paths "/*" \
        --region us-east-1 \
        --no-cli-pager > /dev/null
    
    ok "Frontend deployed!"
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════${NC}"
    echo -e "${GREEN}  🎉 Deployment Complete!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════${NC}"
    echo ""
    echo -e "  Frontend: ${GREEN}https://$CF_DOMAIN${NC}"
    echo -e "  API:      ${GREEN}$RENDER_API_URL${NC}"
    echo ""
else
    ok "Frontend build ready at frontend/dist/"
    echo "  Run 'aws s3 sync frontend/dist/ s3://<bucket>/ --delete' to deploy manually."
fi
