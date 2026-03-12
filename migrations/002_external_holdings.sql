-- Database migration for Persistent External Holdings
-- Table for user-uploaded assets to track against MRI intelligence

CREATE TABLE IF NOT EXISTS client_external_holdings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    quantity NUMERIC(15,4) DEFAULT 0,
    avg_cost NUMERIC(12,4) DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(client_id, symbol)
);

CREATE INDEX IF NOT EXISTS idx_client_external_holdings_client
    ON client_external_holdings(client_id);
