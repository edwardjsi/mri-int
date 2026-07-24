-- Migration 011: CAI V2 Foundation Tables (Decision 104)
-- Date: 2026-07-24

CREATE TABLE IF NOT EXISTS cai_portfolio (
    id VARCHAR(50) PRIMARY KEY,
    owner VARCHAR(100) NOT NULL,
    cash NUMERIC(15,2) DEFAULT 0.00,
    health NUMERIC(5,2) DEFAULT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cai_position (
    id VARCHAR(50) PRIMARY KEY,
    portfolio_id VARCHAR(50) REFERENCES cai_portfolio(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    average_price NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    allocation NUMERIC(5,2) DEFAULT 0.00,
    tranche INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'ACTIVE'
);

CREATE TABLE IF NOT EXISTS cai_position_review (
    id VARCHAR(50) PRIMARY KEY,
    position_id VARCHAR(50) REFERENCES cai_position(id) ON DELETE CASCADE,
    trigger VARCHAR(50),
    review_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    weekly_candle JSONB,
    swing_low JSONB,
    structure_break JSONB,
    story_status VARCHAR(50),
    trend_status VARCHAR(50),
    position_health NUMERIC(5,2),
    recommendation VARCHAR(20),
    notes TEXT
);

CREATE TABLE IF NOT EXISTS cai_committee_report (
    id VARCHAR(50) PRIMARY KEY,
    week_end DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS cai_committee_decision (
    report_id VARCHAR(50) REFERENCES cai_committee_report(id) ON DELETE CASCADE,
    position_id VARCHAR(50) REFERENCES cai_position(id) ON DELETE CASCADE,
    recommendation VARCHAR(20) NOT NULL,
    amount NUMERIC(15,2),
    reason TEXT,
    PRIMARY KEY (report_id, position_id)
);

CREATE TABLE IF NOT EXISTS cai_decision_ledger (
    id VARCHAR(50) PRIMARY KEY,
    decision_report_id VARCHAR(50) NOT NULL,
    decision_position_id VARCHAR(50) NOT NULL,
    execution_status VARCHAR(20) DEFAULT 'PENDING',
    execution_price NUMERIC(10,2),
    execution_date TIMESTAMP WITH TIME ZONE,
    FOREIGN KEY (decision_report_id, decision_position_id) REFERENCES cai_committee_decision(report_id, position_id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_cai_position_portfolio ON cai_position(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_cai_position_symbol ON cai_position(symbol);
CREATE INDEX IF NOT EXISTS idx_cai_position_review_position ON cai_position_review(position_id);
