#!/bin/bash
# ============================================================
# MRI — Initialize Neon.tech Database (Fresh Setup)
# Creates all tables needed by the MRI platform.
# Usage: bash scripts/init_neon.sh
# ============================================================

set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

if [ -z "${DATABASE_URL:-}" ]; then
    echo -e "${YELLOW}Enter your Neon.tech DATABASE_URL:${NC}"
    read -r DATABASE_URL
    export DATABASE_URL
fi

echo -e "${BLUE}Creating tables on Neon.tech...${NC}"

psql "$DATABASE_URL" <<'SQL'

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- CORE DATA TABLES (populated by pipeline)
-- ============================================================

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
    ema_50          NUMERIC(12,4),
    ema_200         NUMERIC(12,4),
    ema_200_slope   NUMERIC(12,6),
    rolling_high_126d NUMERIC(12,4),
    avg_volume_20d  NUMERIC(15,2),
    relative_strength_90d NUMERIC(12,6),
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

-- ============================================================
-- ENGINE TABLES (populated by regime_engine.py)
-- ============================================================

CREATE TABLE IF NOT EXISTS market_regime (
    date DATE PRIMARY KEY,
    sma_200 NUMERIC(12,4),
    regime VARCHAR(10) NOT NULL
);

CREATE TABLE IF NOT EXISTS stock_scores (
    date DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    score INT NOT NULL,
    ema_cross BOOLEAN, volume_spike BOOLEAN, momentum BOOLEAN,
    rs_positive BOOLEAN, above_200 BOOLEAN,
    adx_strong BOOLEAN, rsi_healthy BOOLEAN, near_high BOOLEAN,
    PRIMARY KEY(date, symbol)
);

CREATE TABLE IF NOT EXISTS stock_sectors (
    symbol VARCHAR(20) PRIMARY KEY,
    company_name VARCHAR(255),
    industry VARCHAR(100),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- CLIENT PLATFORM TABLES
-- ============================================================

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
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    amount NUMERIC(15,2) NOT NULL,
    added_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    token VARCHAR(64) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- Verification
-- ============================================================
SELECT '✅ Schema initialized. Tables:' AS status;
SELECT tablename FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

SQL

echo ""
echo -e "${GREEN}✅ Neon.tech database ready!${NC}"
echo ""
echo -e "${BLUE}Next: Run the pipeline to populate data:${NC}"
echo "  export DATABASE_URL=\"$DATABASE_URL\""
echo "  export DB_SSL=true"
echo "  export PYTHONPATH=~/mri-int"
echo "  source ~/mri-int/venv/bin/activate"
echo "  python scripts/pipeline.py"
