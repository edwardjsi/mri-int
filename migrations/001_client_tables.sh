#!/bin/bash
# Database migration for Client Signal Platform tables
# Run with SSM tunnel active (localhost:5433 → RDS:5432)

source venv/bin/activate
export DB_HOST="localhost"
export DB_PORT="5433"
export DB_NAME="mri_db"
export DB_USER="mri_admin"
export DB_PASSWORD=$(aws secretsmanager get-secret-value --secret-id mri-dev-db-credentials --region ap-south-1 --query "SecretString" --output text | grep -o '"password":"[^"]*' | cut -d'"' -f4)

echo "=== Client Signal Platform — Database Migration ==="

PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME <<'SQL'

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- 1. CLIENTS — User accounts for testers
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

-- ============================================================
-- 2. CLIENT_SIGNALS — Daily BUY/SELL recommendations
-- ============================================================
CREATE TABLE IF NOT EXISTS client_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    action VARCHAR(10) NOT NULL,          -- 'BUY' or 'SELL'
    recommended_price NUMERIC(12,4),      -- Next-day open price
    score INT,                             -- Stock score at signal time
    regime VARCHAR(20),                    -- Market regime at signal time
    reason TEXT,                           -- "Score=5, Regime=BULL"
    email_sent BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(client_id, date, symbol, action)
);

CREATE INDEX IF NOT EXISTS idx_client_signals_client_date
    ON client_signals(client_id, date);

-- ============================================================
-- 3. CLIENT_ACTIONS — What the client actually did
-- ============================================================
CREATE TABLE IF NOT EXISTS client_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    signal_id UUID REFERENCES client_signals(id) ON DELETE CASCADE,
    action_taken VARCHAR(20) NOT NULL,    -- 'EXECUTED', 'SKIPPED', 'PARTIAL'
    actual_price NUMERIC(12,4),           -- Self-reported or default
    quantity INT,
    notes TEXT,
    recorded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_client_actions_client
    ON client_actions(client_id);

-- ============================================================
-- 4. CLIENT_PORTFOLIO — Running open positions per client
-- ============================================================
CREATE TABLE IF NOT EXISTS client_portfolio (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    entry_date DATE,
    entry_price NUMERIC(12,4),
    quantity INT,
    highest_price NUMERIC(12,4),          -- For trailing stop tracking
    is_open BOOLEAN DEFAULT true,
    exit_date DATE,
    exit_price NUMERIC(12,4),
    exit_reason VARCHAR(50),
    UNIQUE(client_id, symbol, entry_date)
);

CREATE INDEX IF NOT EXISTS idx_client_portfolio_client_open
    ON client_portfolio(client_id, is_open);

-- ============================================================
-- 5. CLIENT_EQUITY — Daily equity snapshots per client
-- ============================================================
CREATE TABLE IF NOT EXISTS client_equity (
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    date DATE,
    equity NUMERIC(15,2),
    cash NUMERIC(15,2),
    open_positions INT,
    PRIMARY KEY(client_id, date)
);

-- ============================================================
-- 6. EMAIL_LOG — Audit trail for all emails sent
-- ============================================================
CREATE TABLE IF NOT EXISTS email_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    date DATE,
    email_type VARCHAR(30),               -- 'DAILY_SIGNAL', 'WELCOME', 'WEEKLY_SUMMARY'
    service VARCHAR(20),                  -- 'SES' or 'MAILERLITE'
    subject VARCHAR(255),
    status VARCHAR(20),                   -- 'SENT', 'FAILED', 'BOUNCED'
    sent_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_log_client
    ON email_log(client_id, date);

-- ============================================================
-- Verification
-- ============================================================
SELECT 'Migration complete. Tables created:' AS status;
SELECT tablename FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('clients', 'client_signals', 'client_actions',
                     'client_portfolio', 'client_equity', 'email_log')
ORDER BY tablename;

SQL

echo "=== Migration Done ==="
