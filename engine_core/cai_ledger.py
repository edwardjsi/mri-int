import logging
from engine_core.db import get_connection

logger = logging.getLogger(__name__)

def execute_ledger_decisions() -> dict:
    """
    Phase 3c: Monday Execution Engine
    Executes pending decisions in the cai_decision_ledger based on latest prices.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Get all pending ledger entries
            cur.execute(
                """
                SELECT l.id, l.decision_position_id, d.recommendation, p.symbol
                FROM cai_decision_ledger l
                JOIN cai_committee_decision d ON l.decision_report_id = d.report_id AND l.decision_position_id = d.position_id
                JOIN cai_position p ON l.decision_position_id = p.id
                WHERE l.execution_status = 'PENDING'
                """
            )
            pending = cur.fetchall()
            
            if not pending:
                return {"status": "success", "message": "No pending decisions to execute.", "executed": 0}
                
            executed_count = 0
            
            for row in pending:
                ledger_id = row[0]
                pos_id = row[1]
                rec = row[2]
                symbol = row[3]
                
                # Fetch latest price
                cur.execute("SELECT close FROM daily_prices WHERE symbol = %s ORDER BY date DESC LIMIT 1", (symbol,))
                price_data = cur.fetchone()
                if not price_data:
                    continue
                    
                exec_price = price_data[0]
                
                # Update position based on recommendation
                if rec == 'ADD':
                    cur.execute("UPDATE cai_position SET tranche = tranche + 1, average_price = ((average_price * quantity) + %s) / (quantity + 1), quantity = quantity + 1 WHERE id = %s", (exec_price, pos_id))
                elif rec == 'REDUCE':
                    cur.execute("UPDATE cai_position SET quantity = GREATEST(quantity - 1, 1) WHERE id = %s", (pos_id,))
                elif rec == 'EXIT':
                    cur.execute("UPDATE cai_position SET status = 'CLOSED', quantity = 0 WHERE id = %s", (pos_id,))
                
                # Update ledger
                status = 'EXECUTED' if rec in ['ADD', 'REDUCE', 'EXIT'] else 'SKIPPED'
                cur.execute(
                    "UPDATE cai_decision_ledger SET execution_status = %s, execution_price = %s, execution_date = CURRENT_TIMESTAMP WHERE id = %s",
                    (status, exec_price, ledger_id)
                )
                executed_count += 1
                
            conn.commit()
            return {"status": "success", "executed": executed_count}
            
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to execute ledger: {e}")
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()

def get_ledger_history(portfolio_id: str):
    """Fetches the immutable ledger history for a portfolio."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=__import__('psycopg2').extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT l.id, p.symbol, d.recommendation, l.execution_status, l.execution_price, l.execution_date, d.reason
                FROM cai_decision_ledger l
                JOIN cai_committee_decision d ON l.decision_report_id = d.report_id AND l.decision_position_id = d.position_id
                JOIN cai_position p ON l.decision_position_id = p.id
                JOIN cai_portfolio port ON p.portfolio_id = port.id
                WHERE port.owner = %s
                ORDER BY l.execution_date DESC NULLS LAST
                """,
                (portfolio_id,)
            )
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching ledger: {e}")
        return []
    finally:
        conn.close()
