import logging
from engine_core.db import get_connection

logger = logging.getLogger(__name__)

def fetch_replay_data(review_id: str, client_id: str):
    """
    Fetch historical review data to reconstruct the chart context.
    Includes the saved swing_low, structure_break, and recommendation.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT r.id, r.position_id, r.trigger, r.review_date, r.weekly_candle, r.swing_low, 
                       r.structure_break, r.recommendation, r.notes,
                       p.symbol, p.quantity, p.average_price, p.tranche
                FROM cai_position_review r
                JOIN cai_position p ON r.position_id = p.id
                JOIN cai_portfolio port ON p.portfolio_id = port.id
                WHERE r.id = %s AND port.owner = %s
                """,
                (review_id, client_id)
            )
            row = cur.fetchone()
            if not row:
                return None
                
            return {
                "review_id": row["id"],
                "position_id": row["position_id"],
                "symbol": row["symbol"],
                "review_date": row["review_date"].isoformat() if row["review_date"] else None,
                "weekly_candle": row["weekly_candle"],
                "swing_low": row["swing_low"],
                "structure_break": row["structure_break"],
                "recommendation": row["recommendation"],
                "notes": row["notes"],
                "quantity": row["quantity"],
                "average_price": float(row["average_price"]) if row["average_price"] else 0,
                "tranche": row["tranche"]
            }
    except Exception as e:
        logger.error(f"Error fetching replay data for review {review_id}: {e}")
        return None
    finally:
        conn.close()
