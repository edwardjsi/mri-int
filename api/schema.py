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
    breakout_candidate BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_id, symbol)
    );
    """
    )
    cur.execute("ALTER TABLE client_external_holdings ADD COLUMN IF NOT EXISTS breakout_candidate BOOLEAN DEFAULT FALSE;")

    # 3. Watchlist
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS client_watchlist (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
            symbol VARCHAR(20) NOT NULL,
            breakout_candidate BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(client_id, symbol)
        );
        """
    )
    cur.execute("ALTER TABLE client_watchlist ADD COLUMN IF NOT EXISTS breakout_candidate BOOLEAN DEFAULT FALSE;")

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
            condition_ema_50_200 BOOLEAN,
            condition_ema_200_slope BOOLEAN,
            condition_rs BOOLEAN,
            condition_6m_high BOOLEAN,
            condition_volume BOOLEAN,
            condition_breakout_10d BOOLEAN,
            condition_price_quality BOOLEAN,
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
    cur.execute("""ALTER TABLE client_actions ADD COLUMN IF NOT EXISTS notes TEXT;""")
    cur.execute("""ALTER TABLE client_actions ADD COLUMN IF NOT EXISTS recorded_at TIMESTAMPTZ DEFAULT NOW();""")
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

    # 12b. Migration: 7-Step System Expansion
    score_cols = [
        ("condition_breakout_10d", "BOOLEAN"),
        ("condition_price_quality", "BOOLEAN")
    ]
    for col, col_type in score_cols:
        cur.execute(f"ALTER TABLE stock_scores ADD COLUMN IF NOT EXISTS {col} {col_type};")
        cur.execute(f"ALTER TABLE client_signals ADD COLUMN IF NOT EXISTS {col} {col_type};")

    # Fundamental Financials (5-10 year history)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.fundamental_financials (
            id SERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            year INT NOT NULL,
            revenue NUMERIC,
            ebitda NUMERIC,
            net_profit NUMERIC,
            total_assets NUMERIC,
            capital_employed NUMERIC,
            receivables NUMERIC,
            inventory NUMERIC,
            debt NUMERIC,
            equity NUMERIC,
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(symbol, year)
        );
        """
    )

    # Quality Investor Verdicts
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.quality_verdicts (
            id SERIAL PRIMARY KEY,
            symbol TEXT UNIQUE NOT NULL,
            score NUMERIC,
            category TEXT,
            prev_score NUMERIC,
            score_change NUMERIC,
            velocity NUMERIC,
            revenue_score NUMERIC,
            margin_score NUMERIC,
            leverage_score NUMERIC,
            wc_score NUMERIC,
            roce_score NUMERIC,
            evolution_score NUMERIC,
            qil_score DECIMAL DEFAULT 0,
            qil_flags TEXT[] DEFAULT '{}',
            flags TEXT[],
            reasoning TEXT,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )
    # Ensure trajectory columns exist for legacy tables
    cur.execute("ALTER TABLE public.quality_verdicts ADD COLUMN IF NOT EXISTS prev_score NUMERIC;")
    cur.execute("ALTER TABLE public.quality_verdicts ADD COLUMN IF NOT EXISTS score_change NUMERIC;")
    cur.execute("ALTER TABLE public.quality_verdicts ADD COLUMN IF NOT EXISTS velocity NUMERIC;")
    cur.execute("ALTER TABLE public.quality_verdicts ADD COLUMN IF NOT EXISTS qil_score DECIMAL DEFAULT 0;")
    cur.execute("ALTER TABLE public.quality_verdicts ADD COLUMN IF NOT EXISTS qil_flags TEXT[] DEFAULT '{}';")

    # Quality Verdicts History (for trajectory and trend detection)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.quality_verdicts_history (
            id SERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            score NUMERIC NOT NULL,
            recorded_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_quality_history_symbol_date ON public.quality_verdicts_history(symbol, recorded_at DESC);")

    # Table for Qualitative Intelligence Layer (QIL) sources
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS qil_sources (
            symbol TEXT PRIMARY KEY,
            concall_url TEXT,
            annual_report_url TEXT,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )

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

    # 17. System Audit Logs
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.system_audit_logs (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_type  VARCHAR(50) NOT NULL,
            severity    VARCHAR(20) DEFAULT 'INFO',
            message     TEXT,
            metadata    JSONB,
            timestamp   TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON public.system_audit_logs(timestamp DESC);")

    # 18. PERX Reports and Latest Score Snapshots
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.perx_reports (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            client_id UUID REFERENCES clients(id) ON DELETE CASCADE,
            symbol VARCHAR(20) NOT NULL,
            company_name VARCHAR(255),
            perx_score NUMERIC(6,2),
            lifecycle_stage VARCHAR(40),
            report_json JSONB NOT NULL,
            summary TEXT,
            include_debate BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_perx_reports_client_created ON public.perx_reports(client_id, created_at DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_perx_reports_symbol_created ON public.perx_reports(symbol, created_at DESC);")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.perx_scores (
            symbol VARCHAR(20) PRIMARY KEY,
            latest_report_id UUID,
            perx_score NUMERIC(6,2) NOT NULL,
            lifecycle_stage VARCHAR(40),
            narrative_intensity VARCHAR(20),
            fragility_level VARCHAR(20),
            generated_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_perx_scores_generated ON public.perx_scores(generated_at DESC);")

    # 21. AAE V3 Foundation
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.aae_governance_metrics (
            symbol VARCHAR(20) NOT NULL,
            fiscal_year INT NOT NULL,
            fiscal_quarter INT NOT NULL,
            promoter_holding_pct NUMERIC(6,2),
            pledged_shares_pct NUMERIC(6,2),
            auditor_flag BOOLEAN DEFAULT FALSE,
            cfo_exit_flag BOOLEAN DEFAULT FALSE,
            related_party_risk BOOLEAN DEFAULT FALSE,
            governance_score NUMERIC(5,2),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (symbol, fiscal_year, fiscal_quarter)
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.aae_quarterly_financials (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            year INT NOT NULL,
            quarter INT NOT NULL,
            revenue NUMERIC,
            gross_profit NUMERIC,
            ebitda NUMERIC,
            operating_income NUMERIC,
            net_profit NUMERIC,
            eps NUMERIC,
            total_assets NUMERIC,
            total_liabilities NUMERIC,
            current_assets NUMERIC,
            current_liabilities NUMERIC,
            inventory NUMERIC,
            receivables NUMERIC,
            debt NUMERIC,
            equity NUMERIC,
            cfo NUMERIC,
            capex NUMERIC,
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(symbol, year, quarter)
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_aae_quarterly_symbol_date ON public.aae_quarterly_financials(symbol, year DESC, quarter DESC);")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.aae_false_positive_graveyard (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            failure_type VARCHAR(50),
            failure_reason TEXT,
            rerating_score NUMERIC(6,2),
            post_failure_return NUMERIC(6,2),
            lessons JSONB,
            bear_thesis TEXT,
            recorded_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
    )

    conn.commit()
    cur.close()
