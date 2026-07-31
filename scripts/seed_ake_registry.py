import os
import sys
import logging
from dotenv import load_dotenv

# Add project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine_core.db import get_connection
from engine_core.ake_db_schema import ensure_ake_tables

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_ake_registry():
    load_dotenv()
    conn = get_connection()
    ensure_ake_tables(conn)
    
    cur = conn.cursor()
    try:
        # Check if already seeded
        cur.execute("SELECT COUNT(*) as cnt FROM ake_variable")
        if cur.fetchone()['cnt'] > 0:
            logger.info("AKE Registry already seeded.")
            return

        # Seed Variable 1 (RESERVE)
        cur.execute(
            """
            INSERT INTO ake_variable (id, canonical_name, section, data_type, status)
            VALUES (gen_random_uuid(), 'cdmo_revenue_share', 'Monitoring', 'percentage', 'RESERVE')
            RETURNING id
            """
        )
        var1_id = cur.fetchone()['id']
        
        # Insert occurrences for var1
        companies1 = [('Neuland', 'CDMO Revenue'), ('Syngene', 'CDMO Revenue Contribution'), ("Divi's", 'CDMO Share')]
        for comp, raw in companies1:
            cur.execute(
                """
                INSERT INTO ake_variable_occurrence (variable_id, company_id, source_document_id, raw_name, value, confidence, extractor_version)
                VALUES (%s, %s, gen_random_uuid(), %s, '28%%', 0.97, 'AKE_v1')
                """,
                (var1_id, comp, raw)
            )

        # Seed Variable 2 (RESERVE)
        cur.execute(
            """
            INSERT INTO ake_variable (id, canonical_name, section, data_type, status)
            VALUES (gen_random_uuid(), 'top_customer_exposure', 'Risks', 'percentage', 'RESERVE')
            RETURNING id
            """
        )
        var2_id = cur.fetchone()['id']
        
        companies2 = [('TCS', 'Customer Concentration'), ('Infosys', 'Largest Client Share')]
        for comp, raw in companies2:
            cur.execute(
                """
                INSERT INTO ake_variable_occurrence (variable_id, company_id, source_document_id, raw_name, value, confidence, extractor_version)
                VALUES (%s, %s, gen_random_uuid(), %s, '18%%', 0.88, 'AKE_v1')
                """,
                (var2_id, comp, raw)
            )

        # Seed Variable 3 (CANONICAL)
        cur.execute(
            """
            INSERT INTO ake_variable (id, canonical_name, section, data_type, status)
            VALUES (gen_random_uuid(), 'pricing_power', 'Business Quality', 'string', 'CANONICAL')
            RETURNING id
            """
        )
        var3_id = cur.fetchone()['id']
        
        cur.execute(
            """
            INSERT INTO ake_variable_occurrence (variable_id, company_id, source_document_id, raw_name, value, confidence, extractor_version)
            VALUES (%s, %s, gen_random_uuid(), 'Pricing Power', 'High', 0.99, 'AKE_v1')
            """,
            (var3_id, 'Neuland')
        )

        conn.commit()
        logger.info("✅ Successfully seeded AKE Variable Registry.")
    except Exception as e:
        conn.rollback()
        import traceback
        logger.error(f"Seeding failed: {e}\n{traceback.format_exc()}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    seed_ake_registry()
