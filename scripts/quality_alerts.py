import logging
from engine_core.db import get_connection
from engine_fundamental.trajectory import classify_quality_signal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_quality_alerts():
    """Scan for high-impact quality signals (breakouts, improvers, turnarounds)."""
    conn = get_connection()
    cur = conn.cursor()
    
    # Fetch all stocks with significant velocity or score change
    cur.execute("""
        SELECT symbol, score, score_change, velocity, category
        FROM quality_verdicts
        WHERE score_change > 5 OR velocity > 2
        ORDER BY score_change DESC
    """)
    rows = cur.fetchall()
    
    alerts = []
    for row in rows:
        symbol, score, change, velocity, category = row
        signal = classify_quality_signal(float(score), float(change), float(velocity))
        
        if signal != "WATCH":
            alerts.append({
                "symbol": symbol,
                "score": score,
                "change": change,
                "velocity": velocity,
                "signal": signal
            })
            logger.info(f"🚨 ALERT: {symbol} | Signal: {signal} | Score: {score:.1f} (+{change:.1f}) | Velocity: {velocity:.2f}")

    conn.close()
    return alerts

if __name__ == "__main__":
    check_quality_alerts()
