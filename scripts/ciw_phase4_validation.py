import json
import logging
from datetime import datetime
from engine_core.db import get_connection
from engine_core.ciw_repository import CompanyWorkspaceRepository
from engine_core.ciw_update_processor import KnowledgeUpdateProcessor, WorkspaceUpdater
from engine_core.ciw_models import SourceDocument

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Phase4Validation")

def reset_neuland(cur):
    logger.info("Resetting NEULANDLAB CIW data...")
    cur.execute("DELETE FROM ciw_company WHERE symbol = 'NEULANDLAB'")
    cur.execute("""
        INSERT INTO ciw_company (symbol, name, sector, portfolio_status, portfolio_allocation, portfolio_avg_cost)
        VALUES ('NEULANDLAB', 'Neuland Laboratories', 'Pharma', 'Owned', 0.08, 4500.0) RETURNING company_id
    """)
    return cur.fetchone()['company_id']

def run_validation():
    conn = get_connection()
    repo = CompanyWorkspaceRepository(conn=conn)
    processor = KnowledgeUpdateProcessor()
    updater = WorkspaceUpdater(repo)

    try:
        cur = conn.cursor()
        reset_neuland(cur)
        conn.commit()

        # Mock incoming MOSI SourceDocument
        source_doc = SourceDocument(
            id="DOC-MOSI-NEULAND-001",
            doc_type="MOSI_REPORT",
            title="Neuland Labs Initiation",
            author="System",
            uri="s3://reports/neuland.pdf",
            created_at=datetime.now(),
            metadata={"text_content": "Deep dive into margin expansion via CDMO"}
        )

        logger.info("Processing Source Document...")
        transaction = processor.process(source_doc)
        
        logger.info("Applying Knowledge Update Transaction...")
        updated_workspace = updater.apply(transaction)
        
        # Validating output
        logger.info("Validating Workspace Update...")
        assert updated_workspace is not None
        assert updated_workspace.identity.symbol == "NEULANDLAB"
        assert updated_workspace.state.understanding.get('thesis') is not None
        assert "Transitioning from pure API" in updated_workspace.state.understanding['thesis'].text
        assert len(updated_workspace.state.risks) >= 1
        assert len(updated_workspace.state.catalysts) >= 1
        assert len(updated_workspace.state.monitoring) >= 1
        assert len(updated_workspace.timeline) >= 1
        
        logger.info("✅ Phase 4.5 Validation Successful: Pipeline processed document and enforced invariants.")
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        conn.rollback()
    finally:
        repo.close()

if __name__ == "__main__":
    run_validation()
