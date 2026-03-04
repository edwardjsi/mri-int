#!/bin/bash
# ============================================================
# MRI Full Database Rebuild
# Recreates tables, loads CSV backups, bridges recent data,
# and runs the full pipeline.
#
# Prerequisites:
#   - SSM tunnel active (localhost:5433 → RDS:5432)
#   - CSV files at /home/edwar/daily_prices.csv and index_prices.csv
#
# Usage: bash scripts/mri_rebuild_db.sh
# ============================================================

set -euo pipefail

REGION="ap-south-1"
PROJECT_DIR="/home/edwar/mri-int"
DAILY_CSV="/home/edwar/daily_prices.csv"
INDEX_CSV="/home/edwar/index_prices.csv"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

log() { echo -e "${BLUE}[$(date +%H:%M)]${NC} $1"; }
ok()  { echo -e "${GREEN}[$(date +%H:%M)] ✅ $1${NC}"; }
warn(){ echo -e "${YELLOW}[$(date +%H:%M)] ⚠️  $1${NC}"; }
err() { echo -e "${RED}[$(date +%H:%M)] ❌ $1${NC}"; exit 1; }

# Verify CSV files exist
[ -f "$DAILY_CSV" ] || err "Missing: $DAILY_CSV"
[ -f "$INDEX_CSV" ] || err "Missing: $INDEX_CSV"

echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  MRI Database Rebuild${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""

# Get DB password
export DB_HOST="localhost"
export DB_PORT="5433"
export DB_NAME="mri_db"
export DB_USER="mri_admin"
export DB_PASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id mri-dev-db-credentials \
  --region $REGION \
  --query "SecretString" --output text | python3 -c "import sys,json; print(json.load(sys.stdin)['password'])")
export PGPASSWORD="$DB_PASSWORD"

# Quick connectivity test
log "Testing database connection..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1;" > /dev/null 2>&1 \
  || err "Cannot connect to database. Is the SSM tunnel open?"
ok "Database connected"

# ── Step 1: Create base tables (daily_prices, index_prices) ──
log "Step 1: Creating base tables..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME <<'SQL'
  CREATE TABLE IF NOT EXISTS daily_prices (
      id              SERIAL PRIMARY KEY,
      symbol          VARCHAR(20)  NOT NULL,
      date            DATE         NOT NULL,
      open            NUMERIC(12,4),
      high            NUMERIC(12,4),
      low             NUMERIC(12,4),
      close           NUMERIC(12,4),
      adjusted_close  NUMERIC(12,4),
      volume          BIGINT,
      created_at      TIMESTAMP DEFAULT NOW(),
      UNIQUE(symbol, date)
  );
  CREATE INDEX IF NOT EXISTS idx_daily_prices_symbol_date ON daily_prices(symbol, date);
  CREATE INDEX IF NOT EXISTS idx_daily_prices_date ON daily_prices(date);

  CREATE TABLE IF NOT EXISTS index_prices (
      id          SERIAL PRIMARY KEY,
      symbol      VARCHAR(20)  NOT NULL,
      date        DATE         NOT NULL,
      open        NUMERIC(12,4),
      high        NUMERIC(12,4),
      low         NUMERIC(12,4),
      close       NUMERIC(12,4),
      volume      BIGINT,
      created_at  TIMESTAMP DEFAULT NOW(),
      UNIQUE(symbol, date)
  );
  CREATE INDEX IF NOT EXISTS idx_index_prices_symbol_date ON index_prices(symbol, date);
SQL
ok "Base tables created"

# ── Step 2: Load CSV backups ──────────────────────────────
log "Step 2: Loading daily_prices.csv (164MB — this takes a few minutes)..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -c "\COPY daily_prices(id, symbol, date, open, high, low, close, adjusted_close, volume, created_at) FROM '$DAILY_CSV' WITH CSV HEADER;"
ok "daily_prices loaded"

log "Step 2b: Loading index_prices.csv..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
  -c "\COPY index_prices(id, symbol, date, open, high, low, close, volume, created_at) FROM '$INDEX_CSV' WITH CSV HEADER;"
ok "index_prices loaded"

# Fix SERIAL sequences (they'll be out of sync after CSV load)
log "Resetting SERIAL sequences..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME <<'SQL'
  SELECT setval('daily_prices_id_seq', (SELECT COALESCE(MAX(id), 1) FROM daily_prices));
  SELECT setval('index_prices_id_seq', (SELECT COALESCE(MAX(id), 1) FROM index_prices));
SQL
ok "Sequences reset"

# ── Step 3: Create client platform tables ─────────────────
log "Step 3: Creating client platform tables..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME <<'SQL'
  CREATE EXTENSION IF NOT EXISTS "pgcrypto";

  CREATE TABLE IF NOT EXISTS clients (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      email VARCHAR(255) UNIQUE NOT NULL,
      name VARCHAR(100),
      password_hash VARCHAR(255) NOT NULL,
      is_active BOOLEAN DEFAULT true,
      initial_capital NUMERIC(15,2) DEFAULT 100000.00,
      mailerlite_subscriber_id VARCHAR(100),
      created_at TIMESTAMP DEFAULT NOW()
  );

  CREATE TABLE IF NOT EXISTS client_signals (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
      date DATE NOT NULL,
      symbol VARCHAR(20) NOT NULL,
      action VARCHAR(10) NOT NULL,
      recommended_price NUMERIC(12,4),
      score INT,
      regime VARCHAR(20),
      reason TEXT,
      email_sent BOOLEAN DEFAULT false,
      created_at TIMESTAMP DEFAULT NOW(),
      UNIQUE(client_id, date, symbol, action)
  );
  CREATE INDEX IF NOT EXISTS idx_client_signals_client_date ON client_signals(client_id, date);

  CREATE TABLE IF NOT EXISTS client_actions (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
      signal_id UUID REFERENCES client_signals(id) ON DELETE CASCADE,
      action_taken VARCHAR(20) NOT NULL,
      actual_price NUMERIC(12,4),
      quantity INT,
      notes TEXT,
      recorded_at TIMESTAMP DEFAULT NOW()
  );
  CREATE INDEX IF NOT EXISTS idx_client_actions_client ON client_actions(client_id);

  CREATE TABLE IF NOT EXISTS client_portfolio (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
      symbol VARCHAR(20) NOT NULL,
      entry_date DATE,
      entry_price NUMERIC(12,4),
      quantity INT,
      highest_price NUMERIC(12,4),
      is_open BOOLEAN DEFAULT true,
      exit_date DATE,
      exit_price NUMERIC(12,4),
      exit_reason VARCHAR(50),
      UNIQUE(client_id, symbol, entry_date)
  );
  CREATE INDEX IF NOT EXISTS idx_client_portfolio_client_open ON client_portfolio(client_id, is_open);

  CREATE TABLE IF NOT EXISTS client_equity (
      client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
      date DATE,
      equity NUMERIC(15,2),
      cash NUMERIC(15,2),
      open_positions INT,
      PRIMARY KEY(client_id, date)
  );

  CREATE TABLE IF NOT EXISTS email_log (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
      date DATE,
      email_type VARCHAR(30),
      service VARCHAR(20),
      subject VARCHAR(255),
      status VARCHAR(20),
      sent_at TIMESTAMP DEFAULT NOW()
  );
  CREATE INDEX IF NOT EXISTS idx_email_log_client ON email_log(client_id, date);

  CREATE TABLE IF NOT EXISTS capital_additions (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      client_id UUID NOT NULL REFERENCES clients(id),
      amount NUMERIC(14,2) NOT NULL,
      added_at TIMESTAMPTZ DEFAULT NOW()
  );
SQL
ok "Client platform tables created"

# ── Step 4: Quality check ─────────────────────────────────
log "Step 4: Data quality check..."
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME <<'SQL'
  SELECT 'daily_prices' AS table_name, COUNT(*) AS rows,
         COUNT(DISTINCT symbol) AS symbols,
         MIN(date) AS from_date, MAX(date) AS to_date
  FROM daily_prices
  UNION ALL
  SELECT 'index_prices', COUNT(*), COUNT(DISTINCT symbol), MIN(date), MAX(date)
  FROM index_prices;
SQL

echo ""
ok "Database rebuild complete!"
echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  CSV data loaded successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}  Next steps:${NC}"
echo -e "${YELLOW}    1. Bridge recent data:  bash run_bridge_load.sh${NC}"
echo -e "${YELLOW}    2. Run full pipeline:   python scripts/pipeline.py${NC}"
echo -e "${YELLOW}    3. Register clients via API${NC}"
echo -e "${YELLOW}═══════════════════════════════════════${NC}"
