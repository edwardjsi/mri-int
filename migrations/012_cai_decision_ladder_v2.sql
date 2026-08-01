-- Migration 012: CAI Decision Ladder V2.1 Tables
-- Date: 2026-08-01
-- Objective: Support the deterministic Decision Ladder V2.1 execution plan (Decision 109)

CREATE TABLE IF NOT EXISTS cai_v2_decision_snapshots (
    id VARCHAR(50) PRIMARY KEY,
    position_id VARCHAR(50) NOT NULL REFERENCES cai_position(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    decision_state VARCHAR(20) NOT NULL,
    decision_confidence NUMERIC(5,4) NOT NULL,
    decision_stability NUMERIC(5,4) NOT NULL,
    decision_expiry TIMESTAMP WITH TIME ZONE NOT NULL,
    rule_satisfaction_score NUMERIC(5,4) NOT NULL,
    why TEXT NOT NULL,
    why_not_add TEXT,
    triggered_rules JSONB DEFAULT '[]'::jsonb,
    rule_categories JSONB DEFAULT '[]'::jsonb,
    portfolio_context JSONB DEFAULT '{}'::jsonb,
    engine_version VARCHAR(20) NOT NULL,
    rule_set_version VARCHAR(20) NOT NULL,
    schema_version VARCHAR(20) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cai_v2_threshold_definitions (
    id VARCHAR(50) PRIMARY KEY,
    position_id VARCHAR(50) NOT NULL REFERENCES cai_position(id) ON DELETE CASCADE,
    threshold_type VARCHAR(50) NOT NULL,
    value NUMERIC(15,4) NOT NULL,
    confidence NUMERIC(5,4) NOT NULL,
    reason TEXT NOT NULL,
    triggered_rules JSONB DEFAULT '[]'::jsonb,
    valid_from TIMESTAMP WITH TIME ZONE NOT NULL,
    valid_until TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cai_v2_state_transitions (
    id VARCHAR(50) PRIMARY KEY,
    position_id VARCHAR(50) NOT NULL REFERENCES cai_position(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    from_state VARCHAR(20),
    to_state VARCHAR(20) NOT NULL,
    transition_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reasoning_snapshot JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS cai_v2_decision_ledger (
    id VARCHAR(50) PRIMARY KEY,
    position_id VARCHAR(50) NOT NULL REFERENCES cai_position(id) ON DELETE CASCADE,
    symbol VARCHAR(50) NOT NULL,
    from_state VARCHAR(20),
    to_state VARCHAR(20) NOT NULL,
    reasoning_snapshot JSONB NOT NULL,
    confidence NUMERIC(5,4) NOT NULL,
    stability NUMERIC(5,4) NOT NULL,
    rule_satisfaction_score NUMERIC(5,4) NOT NULL,
    expiry TIMESTAMP WITH TIME ZONE NOT NULL,
    triggered_rules JSONB DEFAULT '[]'::jsonb,
    threshold_references JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cai_v2_portfolio_health_snapshots (
    id VARCHAR(50) PRIMARY KEY,
    portfolio_id VARCHAR(50) NOT NULL REFERENCES cai_portfolio(id) ON DELETE CASCADE,
    total_positions INTEGER NOT NULL,
    state_distribution JSONB NOT NULL,
    health_score NUMERIC(5,2) NOT NULL,
    snapshot_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cai_v2_notification_locks (
    id SERIAL PRIMARY KEY,
    idempotency_key VARCHAR(255) UNIQUE NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    to_state VARCHAR(20) NOT NULL,
    event_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_cai_v2_decision_snapshots_position ON cai_v2_decision_snapshots(position_id);
CREATE INDEX IF NOT EXISTS idx_cai_v2_threshold_definitions_position ON cai_v2_threshold_definitions(position_id);
CREATE INDEX IF NOT EXISTS idx_cai_v2_state_transitions_position ON cai_v2_state_transitions(position_id);
CREATE INDEX IF NOT EXISTS idx_cai_v2_decision_ledger_position ON cai_v2_decision_ledger(position_id);
CREATE INDEX IF NOT EXISTS idx_cai_v2_notification_locks_key ON cai_v2_notification_locks(idempotency_key);
