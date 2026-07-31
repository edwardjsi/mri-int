import logging

logger = logging.getLogger(__name__)

def ensure_ake_tables(conn) -> None:
    """Ensure all Adaptive Knowledge Extractor (AKE) tables exist."""
    cur = conn.cursor()

    try:
        # 1. Variable Identity
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ake_variable (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                canonical_name VARCHAR(255) NOT NULL,
                section VARCHAR(100) NOT NULL,
                data_type VARCHAR(50) NOT NULL,
                status VARCHAR(50) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
        # Unique canonical_name + section for CANONICAL variables
        cur.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_ake_variable_canonical_section 
            ON ake_variable(canonical_name, section) 
            WHERE status = 'CANONICAL';
            """
        )
        # Index on status
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ake_variable_status ON ake_variable(status);
            """
        )

        # 2. Variable Occurrence (Evidence)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ake_variable_occurrence (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                variable_id UUID NOT NULL REFERENCES ake_variable(id) ON DELETE CASCADE,
                company_id VARCHAR(50) NOT NULL,
                source_document_id UUID NOT NULL,
                raw_name VARCHAR(255) NOT NULL,
                value TEXT NOT NULL,
                confidence FLOAT NOT NULL,
                extractor_version VARCHAR(50) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ake_occurrence_var_company 
            ON ake_variable_occurrence(variable_id, company_id);
            """
        )

        # 3. Variable Alias (Naming)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ake_variable_alias (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                variable_id UUID NOT NULL REFERENCES ake_variable(id) ON DELETE CASCADE,
                alias VARCHAR(255) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )

        # 4. Promotion History (Lifecycle)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ake_promotion_history (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                variable_id UUID NOT NULL REFERENCES ake_variable(id) ON DELETE CASCADE,
                action VARCHAR(50) NOT NULL,
                user_id VARCHAR(100) NOT NULL,
                reason TEXT,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )

        conn.commit()
        logger.info("✅ AKE tables ensured successfully")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to create AKE tables: {e}")
        raise
    finally:
        cur.close()
