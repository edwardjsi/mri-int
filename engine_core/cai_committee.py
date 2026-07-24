import logging
import uuid
from datetime import datetime, timedelta
from engine_core.db import get_connection

logger = logging.getLogger(__name__)

def generate_committee_report(portfolio_id: str) -> dict:
    """
    Phase 3a: Investment Committee Engine
    Aggregates pending position reviews from the current week and generates a Committee Report.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Check if there's already an unapproved report for this week
            today = datetime.now().date()
            week_end = today + timedelta(days=(4 - today.weekday()) % 7) # Friday of current week
            
            cur.execute(
                "SELECT id FROM cai_committee_report WHERE week_end = %s AND approved_at IS NULL", 
                (week_end,)
            )
            existing = cur.fetchone()
            if existing:
                return {"status": "error", "message": "Unapproved report already exists for this week.", "report_id": existing['id'] if isinstance(existing, dict) else existing[0]}

            # Find all latest reviews for active positions in this portfolio
            cur.execute(
                """
                SELECT p.id, p.symbol, r.recommendation, r.position_health, r.notes
                FROM cai_position p
                JOIN cai_position_review r ON p.id = r.position_id
                JOIN cai_portfolio port ON p.portfolio_id = port.id
                WHERE port.owner = %s AND p.status = 'ACTIVE'
                  AND r.review_date >= CURRENT_DATE - INTERVAL '7 days'
                ORDER BY r.review_date DESC
                """,
                (portfolio_id,) # Here portfolio_id is actually client_id
            )
            reviews = cur.fetchall()
            
            if not reviews:
                return {"status": "error", "message": "No recent reviews found to generate committee report."}
                
            # Create the report
            report_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO cai_committee_report (id, week_end) VALUES (%s, %s)",
                (report_id, week_end)
            )
            
            # Use a dict to keep only the latest review per position
            processed_positions = set()
            decisions = []
            
            for row in reviews:
                pos_id = row['id'] if isinstance(row, dict) else row[0]
                if pos_id in processed_positions:
                    continue
                processed_positions.add(pos_id)
                
                symbol = row['symbol'] if isinstance(row, dict) else row[1]
                rec = row['recommendation'] if isinstance(row, dict) else row[2]
                health = row['position_health'] if isinstance(row, dict) else row[3]
                notes = row['notes'] if isinstance(row, dict) else row[4]
                reason = f"Based on review. Health: {health}. Notes: {notes or 'None'}"
                
                cur.execute(
                    """
                    INSERT INTO cai_committee_decision (report_id, position_id, recommendation, reason)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (report_id, pos_id, rec, reason)
                )
                decisions.append({
                    "symbol": symbol,
                    "recommendation": rec
                })
                
            conn.commit()
            return {
                "status": "success", 
                "report_id": report_id,
                "decisions": decisions
            }
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to generate committee report: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()

def approve_committee_report(report_id: str) -> dict:
    """
    Approves the report and inserts decisions into the Decision Ledger.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE cai_committee_report SET approved_at = CURRENT_TIMESTAMP WHERE id = %s RETURNING id", (report_id,))
            if not cur.fetchone():
                return {"status": "error", "message": "Report not found."}
                
            cur.execute(
                "SELECT position_id, recommendation FROM cai_committee_decision WHERE report_id = %s",
                (report_id,)
            )
            decisions = cur.fetchall()
            
            for d in decisions:
                pos_id = d['position_id'] if isinstance(d, dict) else d[0]
                ledger_id = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO cai_decision_ledger (id, decision_report_id, decision_position_id, execution_status)
                    VALUES (%s, %s, %s, 'PENDING')
                    """,
                    (ledger_id, report_id, pos_id)
                )
            
            conn.commit()
            return {"status": "success", "message": "Report approved and ledger entries created."}
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to approve report {report_id}: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()
