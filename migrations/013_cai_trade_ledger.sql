CREATE TABLE IF NOT EXISTS cai_trade_ledger (
    id VARCHAR(50) PRIMARY KEY,
    portfolio_id VARCHAR(50) NOT NULL,
    position_id VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    event_type VARCHAR(20) NOT NULL,
    allocation_reason VARCHAR(50) NOT NULL,
    execution_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    price NUMERIC(15, 2) NOT NULL,
    quantity INTEGER NOT NULL,
    capital_allocated NUMERIC(15, 2) NOT NULL,
    portfolio_weight NUMERIC(5, 4),
    decision_state VARCHAR(20),
    decision_ladder_version VARCHAR(20),
    notes TEXT,
    idempotency_key VARCHAR(100) UNIQUE,
    reference_event_id VARCHAR(50),
    FOREIGN KEY (portfolio_id) REFERENCES cai_portfolio(id) ON DELETE CASCADE,
    FOREIGN KEY (position_id) REFERENCES cai_position(id) ON DELETE CASCADE,
    FOREIGN KEY (reference_event_id) REFERENCES cai_trade_ledger(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_cai_trade_ledger_position ON cai_trade_ledger(position_id);
CREATE INDEX IF NOT EXISTS idx_cai_trade_ledger_symbol ON cai_trade_ledger(symbol);
CREATE INDEX IF NOT EXISTS idx_cai_trade_ledger_date ON cai_trade_ledger(execution_date);
