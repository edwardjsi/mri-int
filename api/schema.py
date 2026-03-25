"""Schema bootstrap helpers.

This repo historically used manual `migrations/*.sh` scripts. In practice (especially
on Neon/Render), it is easy to forget to run a migration and end up with endpoints
that fail to persist holdings.

These helpers are intentionally minimal and idempotent: they only CREATE missing
objects and never DROP/ALTER existing schema.
"""

from __future__ import annotations


def ensure_required_tables(conn) -> None:
    """Ensure all client-specific and operational tables exist.
    
    This consolidates ad-hoc 'CREATE TABLE' statements from throughout the API
    to ensure consistent schemas (specifically missing IDs and UNIQUE constraints).
    """
    cur = conn.cursor()

    # 1. Clients Admin Flag
    cur.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;")
    cur.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;")

    # 2. Digital Twin (External Holdings) - Fixes missing ID and Unique constraint
    cur.execute(
        """
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
        """
    )
    cur.execute("ALTER TABLE client_external_holdings ALTER COLUMN id SET DEFAULT gen_random_uuid();")

    # 3. Watchlist - Fixes missing Unique constraint for ON CONFLICT logic
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS client_watchlist (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
            symbol VARCHAR(20) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(client_id, symbol)
        );
        """
    )
    cur.execute("ALTER TABLE client_watchlist ALTER COLUMN id SET DEFAULT gen_random_uuid();")

    # 4. Capital Additions
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS capital_additions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES clients(id),
            amount NUMERIC(14,2) NOT NULL,
            added_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )

    # 5. Password Reset Tokens
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID NOT NULL REFERENCES clients(id),
            token VARCHAR(255) UNIQUE NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            used BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )

    # 6. Indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_client_external_holdings_client ON client_external_holdings(client_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_client_watchlist_client ON client_watchlist(client_id);")

    conn.commit()
    cur.close()