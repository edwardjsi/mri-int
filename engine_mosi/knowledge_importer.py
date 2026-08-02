import json
import os
import logging
from engine_core.db import get_connection

logger = logging.getLogger(__name__)

class KnowledgeImporter:
    def __init__(self):
        self._ensure_table()

    def _ensure_table(self):
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS mosi_compiled_artifacts (
                    symbol VARCHAR(20) PRIMARY KEY,
                    company_facts JSONB,
                    company_knowledge JSONB,
                    extraction_report JSONB,
                    knowledge_manifest JSONB,
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create mosi_compiled_artifacts table: {e}")
        finally:
            cur.close()
            conn.close()

    def import_artifacts_from_dir(self, symbol: str, artifact_dir: str):
        """Reads the 4 JSON artifacts from the directory and stores them in the DB."""
        def load_json(filename):
            path = os.path.join(artifact_dir, filename)
            if not os.path.exists(path):
                return None
            with open(path, 'r') as f:
                return json.load(f)

        facts = load_json("company_facts.json")
        knowledge = load_json("company_knowledge.json")
        report = load_json("extraction_report.json")
        manifest = load_json("knowledge_manifest.json")

        if not all([facts is not None, knowledge is not None, report is not None, manifest is not None]):
            raise ValueError(f"Missing one or more artifacts in {artifact_dir}")

        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO mosi_compiled_artifacts (symbol, company_facts, company_knowledge, extraction_report, knowledge_manifest, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (symbol) DO UPDATE SET
                    company_facts = EXCLUDED.company_facts,
                    company_knowledge = EXCLUDED.company_knowledge,
                    extraction_report = EXCLUDED.extraction_report,
                    knowledge_manifest = EXCLUDED.knowledge_manifest,
                    updated_at = NOW();
            """, (symbol.upper(), json.dumps(facts), json.dumps(knowledge), json.dumps(report), json.dumps(manifest)))
            conn.commit()
            logger.info(f"Successfully imported artifacts for {symbol}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to import artifacts for {symbol}: {e}")
            raise
        finally:
            cur.close()
            conn.close()

    def get_artifacts(self, symbol: str):
        """Fetches the artifacts from the DB for a given symbol."""
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT * FROM mosi_compiled_artifacts WHERE symbol = %s", (symbol.upper(),))
            row = cur.fetchone()
            if row:
                return {
                    "company_facts": row["company_facts"],
                    "company_knowledge": row["company_knowledge"],
                    "extraction_report": row["extraction_report"],
                    "knowledge_manifest": row["knowledge_manifest"]
                }
            return None
        finally:
            cur.close()
            conn.close()
