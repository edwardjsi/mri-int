import sys
import os
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from engine_core.db import get_connection
from engine_core.cai_position_review import evaluate_position

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_ledger():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Get all active positions
            cur.execute("""
                SELECT p.id as position_id, port.owner as client_id 
                FROM cai_position p 
                JOIN cai_portfolio port ON p.portfolio_id = port.id
                WHERE p.status = 'ACTIVE'
            """)
            positions = cur.fetchall()

            for pos in positions:
                pos_id = pos['position_id']
                client_id = pos['client_id']
                
                # Re-evaluate live
                res = evaluate_position(str(pos_id), str(client_id))
                rec = res.get('recommendation')
                if not rec or rec == 'ERROR':
                    logger.warning(f"Skipping {pos_id}: {res.get('reason')}")
                    continue
                
                # Update latest review
                cur.execute("""
                    UPDATE cai_position_review 
                    SET recommendation = %s 
                    WHERE position_id = %s 
                      AND id = (
                          SELECT id FROM cai_position_review 
                          WHERE position_id = %s 
                          ORDER BY review_date DESC LIMIT 1
                      )
                """, (rec, pos_id, pos_id))
                
                # Update committee decision in latest report
                cur.execute("""
                    UPDATE cai_committee_decision 
                    SET recommendation = %s 
                    WHERE position_id = %s 
                """, (rec, pos_id))
                
                logger.info(f"Updated position {pos_id} recommendation to {rec}")

            conn.commit()
            logger.info("Successfully corrected ledger recommendations based on No Averaging Down rule.")
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Error correcting ledger: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_ledger()
