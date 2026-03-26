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

    # 0. Base Extensions & Admin/Core Tables
    cur.execute("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\";")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS clients (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255),
            password_hash TEXT,
            is_active BOOLEAN DEFAULT TRUE,
            is_admin BOOLEAN DEFAULT FALSE,
            initial_capital NUMERIC(15,2) DEFAULT 100000,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """
    )
    
    # 1. Clients Table Refinements
    # Note: ADD COLUMN IF NOT EXISTS is fine, but we've combined it above. 
    # Still keeping it for existing installs.
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

    # 3. Watchlist
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

    # 4. Client Signals (Daily Recommendations)
    cur.execute(
        """
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
        """
    )

    # 5. Client Actions
    cur.execute(
        """
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
        """
    )

    # 6. Client Portfolio (Open Positions)
    cur.execute(
        """
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
        """
    )

    # 7. Client Equity (Daily Snapshots)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS client_equity (
            client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
            date DATE,
            equity NUMERIC(15,2),
            cash NUMERIC(15,2),
            open_positions INT,
            PRIMARY KEY(client_id, date)
        );
        """
    )

    # 8. Capital Additions
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

    # 9. Password Reset Tokens
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

    # 10. Email Log
    cur.execute(
        """
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
        """
    )

    # 11. Indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_client_external_holdings_client ON client_external_holdings(client_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_client_watchlist_client ON client_watchlist(client_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_client_portfolio_client_open ON client_portfolio(client_id, is_open);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_client_signals_client_date ON client_signals(client_id, date);")
    
    # Core performance indexes (added for Digital Twin/Dashboard speed)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_daily_prices_symbol_date ON daily_prices(symbol, date DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_daily_prices_date ON daily_prices(date DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_stock_scores_symbol_date ON stock_scores(symbol, date DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_stock_scores_date_desc ON stock_scores(date DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_market_regime_date ON market_regime(date DESC);")

    conn.commit()
    cur.close()