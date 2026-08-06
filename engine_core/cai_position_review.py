import logging
from engine_core.db import get_connection
from engine_core.cai_health_engine import compute_position_health
from typing import Dict, Any

logger = logging.getLogger(__name__)

def evaluate_position(position_id: str, client_id: str) -> Dict[str, Any]:
    """
    Position Review (Post-Ownership)
    Decide what to do with an existing position.
    Returns recommendation: ADD, WAIT, HOLD, REDUCE, EXIT, ROTATE.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Fetch Position and Portfolio Data
            cur.execute(
                """
                SELECT p.symbol, p.quantity, p.average_price, p.tranche, p.status, port.id as portfolio_id,
                       p.add_level, p.alert_level, p.structure_level, p.quit_level
                FROM cai_position p
                JOIN cai_portfolio port ON p.portfolio_id = port.id
                WHERE p.id = %s AND port.owner = %s AND p.status = 'ACTIVE'
                """,
                (position_id, client_id)
            )
            pos = cur.fetchone()
            if not pos:
                return {"recommendation": "ERROR", "reason": "Active position not found"}
                
            symbol = pos['symbol']
            qty = pos['quantity']
            avg_price = float(pos['average_price'])
            tranche = pos['tranche']
            
            # 2. Fetch live price and health
            cur.execute("SELECT close, ema_20, ema_50, ema_200 FROM daily_prices WHERE symbol = %s ORDER BY date DESC LIMIT 1", (symbol,))
            price_data = cur.fetchone()
            if not price_data:
                return {"recommendation": "HOLD", "reason": "Missing live data"}
                
            close_price = float(price_data['close'])
            ema_20 = float(price_data['ema_20']) if price_data['ema_20'] else close_price
            ema_50 = float(price_data['ema_50']) if price_data['ema_50'] else close_price
            ema_200 = float(price_data['ema_200']) if price_data['ema_200'] else close_price
            
            health_score = compute_position_health(symbol)
            
            # 3. Decision Logic
            profit_pct = ((close_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
            
            # Rule: NO Averaging Down
            is_under_water = profit_pct <= 0
            
            if health_score < 30 or close_price < ema_200:
                recommendation = "EXIT"
                reason = "Trend broken or health critically low"
            elif is_under_water:
                # If negative, we cannot add due to No Averaging Down rule.
                recommendation = "WAIT"
                reason = "Position is underwater. Cannot add. Wait for recovery."
            elif health_score >= 80 and tranche < 10:
                recommendation = "ADD"
                reason = "Strong health and profitable trend. Eligible for next tranche."
            elif health_score < 50:
                recommendation = "REDUCE"
                reason = "Deteriorating health. Take partial profits."
            else:
                recommendation = "HOLD"
                reason = "Healthy consolidation. Maintain current tranches."
                
            return {
                "position_id": position_id,
                "symbol": symbol,
                "health_score": health_score,
                "tranche": tranche,
                "profit_pct": round(float(profit_pct), 2),
                "recommendation": recommendation,
                "reason": reason,
                "entry_price": avg_price,
                "pullback_level": ema_20,
                "add_level": float(pos['add_level']) if pos.get('add_level') is not None else None,
                "alert_level": float(pos['alert_level']) if pos.get('alert_level') is not None else None,
                "structure_level": float(pos['structure_level']) if pos.get('structure_level') is not None else None,
                "quit_level": float(pos['quit_level']) if pos.get('quit_level') is not None else None
            }
    except Exception as e:
        logger.error(f"Error evaluating position {position_id}: {e}")
        return {"recommendation": "ERROR", "reason": str(e)}
    finally:
        conn.close()
