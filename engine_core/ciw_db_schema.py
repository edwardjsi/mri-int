import logging

logger = logging.getLogger(__name__)

def ensure_ciw_tables(conn) -> None:
    """Ensure all Company Intelligence Workspace (CIW) tables exist.
    
    This follows the idempotent pattern used in api/schema.py.
    """
    cur = conn.cursor()

    try:
        # 1. Source Documents
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ciw_source_document (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                doc_type VARCHAR(50) NOT NULL,
                title VARCHAR(255) NOT NULL,
                author VARCHAR(100),
                uri TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                metadata JSONB DEFAULT '{}'::jsonb
            );
            """
        )

        # 2. Company Workspace Core State
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ciw_company (
                company_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                symbol VARCHAR(20) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                sector VARCHAR(100),
                portfolio_status VARCHAR(50) DEFAULT 'Not Owned',
                portfolio_allocation NUMERIC(5,2) DEFAULT 0.0,
                portfolio_avg_cost NUMERIC(12,4) DEFAULT 0.0,
                last_reviewed TIMESTAMPTZ,
                current_decision VARCHAR(50),
                current_trend VARCHAR(50)
            );
            """
        )

        # 3. Timeline Events
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ciw_timeline_event (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                company_id UUID NOT NULL REFERENCES ciw_company(company_id) ON DELETE CASCADE,
                event_type VARCHAR(50) NOT NULL,
                event_date DATE NOT NULL,
                summary TEXT NOT NULL,
                reference_id VARCHAR(100)
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ciw_timeline_company_date ON ciw_timeline_event(company_id, event_date DESC);")

        # 4. Knowledge Nodes (Understanding, Risks, Catalysts, Monitoring)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ciw_knowledge_node (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                company_id UUID NOT NULL REFERENCES ciw_company(company_id) ON DELETE CASCADE,
                node_type VARCHAR(50) NOT NULL,
                current_text TEXT NOT NULL,
                confidence VARCHAR(20) NOT NULL,
                status VARCHAR(50) NOT NULL,
                evidence JSONB DEFAULT '[]'::jsonb,
                history JSONB DEFAULT '[]'::jsonb,
                metadata JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ciw_knowledge_company_type ON ciw_knowledge_node(company_id, node_type);")

        # 5. Knowledge Update Transactions (Audit Log)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ciw_update_transaction (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                company_id UUID NOT NULL REFERENCES ciw_company(company_id) ON DELETE CASCADE,
                source_document_id UUID REFERENCES ciw_source_document(id) ON DELETE SET NULL,
                executed_at TIMESTAMPTZ DEFAULT NOW(),
                operations_log JSONB NOT NULL
            );
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ciw_transaction_company_date ON ciw_update_transaction(company_id, executed_at DESC);")

        conn.commit()
        logger.info("✅ CIW Schema initialized")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to initialize CIW tables: {e}")
        raise
    finally:
        cur.close()
