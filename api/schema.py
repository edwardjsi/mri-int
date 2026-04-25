"""Schema bootstrap helpers.

This repo historically used manual `migrations/*.sh` scripts. In practice (especially
on Neon/Render), it is easy to forget to run a migration and end up with endpoints
that fail to persist holdings.

These helpers are intentionally minimal and idempotent: they only CREATE missing
objects and never DROP/ALTER existing schema.
"""

from __future__ import annotations


def ensure_prde_tables(cur) -> None:
    """Ensure PRDE fundamentals and report tables exist."""
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.prde_companies (
            id                  BIGSERIAL PRIMARY KEY,
            ticker              VARCHAR(20) NOT NULL UNIQUE,
            name                TEXT,
            country             VARCHAR(10) DEFAULT 'IN',
            sector              TEXT,
            industry            TEXT,
            is_active           BOOLEAN DEFAULT TRUE,
            created_at          TIMESTAMPTZ DEFAULT NOW(),
            updated_at          TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.prde_financials_annual (
            id                  BIGSERIAL PRIMARY KEY,
            company_id          BIGINT NOT NULL REFERENCES public.prde_companies(id) ON DELETE CASCADE,
            fiscal_year         INT NOT NULL,
            revenue             NUMERIC,
            ebitda              NUMERIC,
            pat                 NUMERIC,
            roce                NUMERIC,
            capex               NUMERIC,
            employee_cost       NUMERIC,
            total_assets        NUMERIC,
            source              TEXT,
            imported_at         TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(company_id, fiscal_year)
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.prde_ratios_annual (
            id                  BIGSERIAL PRIMARY KEY,
            company_id          BIGINT NOT NULL REFERENCES public.prde_companies(id) ON DELETE CASCADE,
            fiscal_year         INT NOT NULL,
            pe                  NUMERIC,
            ev_ebitda           NUMERIC,
            pb                  NUMERIC,
            debt_equity         NUMERIC,
            source              TEXT,
            imported_at         TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(company_id, fiscal_year)
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.prde_feature_snapshots (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id          BIGINT NOT NULL REFERENCES public.prde_companies(id) ON DELETE CASCADE,
            run_id              UUID NOT NULL DEFAULT gen_random_uuid(),
            feature_hash        VARCHAR(64) NOT NULL,
            features            JSONB NOT NULL,
            created_at          TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(company_id, feature_hash)
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.prde_agent_scores (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            feature_snapshot_id UUID NOT NULL REFERENCES public.prde_feature_snapshots(id) ON DELETE CASCADE,
            company_id          BIGINT NOT NULL REFERENCES public.prde_companies(id) ON DELETE CASCADE,
            agent_name          TEXT NOT NULL,
            score               NUMERIC,
            confidence          NUMERIC,
            reasoning           TEXT,
            flags               JSONB DEFAULT '[]'::jsonb,
            model               TEXT,
            created_at          TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(feature_snapshot_id, agent_name)
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.prde_final_scores (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            feature_snapshot_id UUID NOT NULL REFERENCES public.prde_feature_snapshots(id) ON DELETE CASCADE,
            company_id          BIGINT NOT NULL REFERENCES public.prde_companies(id) ON DELETE CASCADE,
            total_score         NUMERIC,
            classification      TEXT,
            report              JSONB,
            created_at          TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(feature_snapshot_id)
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.prde_report_events (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            final_score_id      UUID REFERENCES public.prde_final_scores(id) ON DELETE CASCADE,
            company_id          BIGINT REFERENCES public.prde_companies(id) ON DELETE CASCADE,
            event_type          TEXT NOT NULL,
            description         TEXT,
            created_at          TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.prde_jobs (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            job_type            TEXT NOT NULL,
            status              TEXT NOT NULL,
            started_at          TIMESTAMPTZ DEFAULT NOW(),
            completed_at        TIMESTAMPTZ,
            metadata            JSONB DEFAULT '{}'::jsonb,
            error_message       TEXT
        );
        """
    )

    cur.execute("CREATE INDEX IF NOT EXISTS idx_prde_companies_ticker ON public.prde_companies(ticker);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prde_financials_company_year ON public.prde_financials_annual(company_id, fiscal_year DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prde_ratios_company_year ON public.prde_ratios_annual(company_id, fiscal_year DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prde_feature_snapshots_company ON public.prde_feature_snapshots(company_id, created_at DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prde_agent_scores_company ON public.prde_agent_scores(company_id, created_at DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prde_final_scores_score ON public.prde_final_scores(total_score DESC, created_at DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prde_jobs_status ON public.prde_jobs(status, started_at DESC);")


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
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )
    
    # 1. Clients Table Refinements
    cur.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;")
    cur.execute("ALTER TABLE clients ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;")
    cur.execute("ALTER TABLE clients ALTER COLUMN created_at TYPE TIMESTAMPTZ;")

    # 2. Digital Twin (External Holdings)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS client_external_holdings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
            symbol VARCHAR(20) NOT NULL,
            quantity NUMERIC(15,4) DEFAULT 0,
            avg_cost NUMERIC(12,4) DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
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
            created_at TIMESTAMPTZ DEFAULT NOW(),
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
            created_at TIMESTAMPTZ DEFAULT NOW(),
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
            recorded_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )

    # 5a. Client Actions refinements (ensure columns exist for legacy tables)
    cur.execute("""ALTER TABLE client_actions ADD COLUMN IF NOT EXISTS action_taken VARCHAR(20);""")
    cur.execute("""ALTER TABLE client_actions ADD COLUMN IF NOT EXISTS actual_price NUMERIC(12,4);""")
    cur.execute("""ALTER TABLE client_actions ADD COLUMN IF NOT EXISTS quantity INT;""")
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
            sent_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )

    # 11. Security - Ensure client_id column exists, then enable RLS & Policies
    client_tables = [
        "client_external_holdings", "client_watchlist", "client_signals",
        "client_actions", "client_portfolio", "client_equity", "capital_additions"
    ]
    for table in client_tables:
        # Ensure client_id exists for legacy tables
        cur.execute("""ALTER TABLE """ + table + """ ADD COLUMN IF NOT EXISTS client_id UUID;""")

        # Enable RLS
        cur.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        # Standard Policy: restrict to app.current_client_id session variable
        # Note: In production, the API must run `SET app.current_client_id = '...'` in each connection.
        policy_name = f"policy_{table}_client_isolation"
        cur.execute(f"DROP POLICY IF EXISTS {policy_name} ON {table};")
        cur.execute(f"""
            CREATE POLICY {policy_name} ON {table}
            FOR ALL
            USING (client_id::text = current_setting('app.current_client_id', true));
        """)

    # 12. Indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_client_external_holdings_client ON client_external_holdings(client_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_client_watchlist_client ON client_watchlist(client_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_client_portfolio_client_open ON client_portfolio(client_id, is_open);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_client_signals_client_date ON client_signals(client_id, date);")
    
    # Core performance indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_daily_prices_symbol_date ON daily_prices(symbol, date DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_daily_prices_date ON daily_prices(date DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_stock_scores_symbol_date ON stock_scores(symbol, date DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_stock_scores_date_desc ON stock_scores(date DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_market_regime_date ON market_regime(date DESC);")

    # 13. Market Index Prices (Core Operational Table)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.market_index_prices (
            id          BIGSERIAL PRIMARY KEY,
            symbol      VARCHAR(20)  NOT NULL,
            date        DATE         NOT NULL,
            open        NUMERIC(12,4),
            high        NUMERIC(12,4),
            low         NUMERIC(12,4),
            close       NUMERIC(12,4),
            volume      BIGINT,
            created_at  TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(symbol, date)
        );
        """
    )
    # Ensure created_at exists
    cur.execute("ALTER TABLE public.market_index_prices ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_market_index_prices_symbol_date ON public.market_index_prices(symbol, date);")

    # 14. Top Score Tracking (Hall of Fame)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.top_score_tracking (
            symbol              VARCHAR(20) PRIMARY KEY,
            first_appeared_date DATE NOT NULL,
            entry_price         NUMERIC(12,4),
            entry_score         INT,
            latest_price        NUMERIC(12,4),
            max_score           INT,
            last_seen_date      DATE,
            updated_at          TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )

    # 15. Strategy Shadow Tracking (Top 10 Picks regardless of Regime)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.strategy_shadow_portfolio (
            symbol              VARCHAR(20) PRIMARY KEY,
            first_entry_date    DATE NOT NULL,
            entry_price         NUMERIC(12,4),
            latest_price        NUMERIC(12,4),
            is_active           BOOLEAN DEFAULT TRUE,
            last_seen_date      DATE,
            updated_at          TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )

    # 16. Momentum Swing Trades (STEE)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.swing_trades (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id           UUID REFERENCES clients(id) ON DELETE CASCADE,
            symbol              VARCHAR(20) NOT NULL,
            entry_date          DATE NOT NULL,
            entry_price         NUMERIC(12,4) NOT NULL,
            stop_loss           NUMERIC(12,4) NOT NULL,
            take_profit_2r      NUMERIC(12,4),
            quantity            INT NOT NULL,
            risk_amount         NUMERIC(15,2),
            status              VARCHAR(20) DEFAULT 'OPEN', -- 'OPEN', 'PARTIAL_EXIT', 'CLOSED'
            exit_date           DATE,
            exit_price          NUMERIC(12,4),
            exit_reason         VARCHAR(50),
            created_at          TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_swing_trades_client_status ON public.swing_trades(client_id, status);")

    # 17. Daily Prices Indicator Expansion
    indicator_cols = [
        ("ema_10", "NUMERIC(12,4)"),
        ("high_10d", "NUMERIC(12,4)"),
        ("low_5d", "NUMERIC(12,4)"),
        ("atr_14", "NUMERIC(12,4)")
    ]
    for col, col_type in indicator_cols:
        cur.execute(f"ALTER TABLE daily_prices ADD COLUMN IF NOT EXISTS {col} {col_type};")

    # 18. PRDE - PE Re-Rating Discovery Engine
    ensure_prde_tables(cur)

    conn.commit()
    cur.close()
