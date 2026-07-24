import logging
from engine_core.db import get_connection
from typing import Dict, Any

logger = logging.getLogger(__name__)

def evaluate_candidate(symbol: str) -> Dict[str, Any]:
    """
    Candidate Review (Pre-Ownership)
    Decide whether a stock deserves the first tranche.
    Returns recommendation: BUY FIRST TRANCHE, WATCH, or REJECT.
    """
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Fetch MRI Score
            cur.execute("SELECT total_score FROM stock_scores WHERE symbol = %s ORDER BY date DESC LIMIT 1", (symbol,))
            row = cur.fetchone()
            mri_score = row['total_score'] if row else 0
            
            # 2. Fetch Breakout state & Indicators
            cur.execute(
                """
                SELECT close, ema_50, ema_200, breakout_state, rs_90d, volume_confirmed_breakout 
                FROM daily_prices 
                WHERE symbol = %s 
                ORDER BY date DESC LIMIT 1
                """,
                (symbol,)
            )
            price_data = cur.fetchone()
            if not price_data:
                return {"recommendation": "REJECT", "reason": "No price data available"}
                
            close = price_data['close']
            ema_50 = price_data['ema_50']
            ema_200 = price_data['ema_200']
            breakout_state = price_data['breakout_state']
            rs_90d = price_data['rs_90d']
            volume_confirmed = price_data['volume_confirmed_breakout']
            
            # 3. Simple Candidate Logic based on PRD requirements
            # Need high score and strong technicals to risk the First Tranche
            if mri_score >= 10 and breakout_state == 'BROKEN_OUT' and volume_confirmed:
                recommendation = "BUY FIRST TRANCHE"
                reason = "High MRI Score + Volume Confirmed Breakout"
            elif mri_score >= 8 or breakout_state in ['BROKEN_OUT', 'READY_TO_BREAKOUT']:
                recommendation = "WATCH"
                reason = "Good setup, monitor for final confirmation"
            else:
                recommendation = "REJECT"
                reason = f"Weak setup (MRI Score: {mri_score}, State: {breakout_state})"
                
            return {
                "symbol": symbol,
                "mri_score": mri_score,
                "breakout_state": breakout_state,
                "rs_90d": float(rs_90d) if rs_90d else None,
                "volume_confirmed": volume_confirmed,
                "recommendation": recommendation,
                "reason": reason,
                "current_price": float(close) if close else 0.0
            }
    except Exception as e:
        logger.error(f"Error evaluating candidate {symbol}: {e}")
        return {"recommendation": "ERROR", "reason": str(e)}
    finally:
        conn.close()
