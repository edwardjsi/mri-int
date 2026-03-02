"""
Daily Signal Generator — runs after engine pipeline completes.
Generates BUY/SELL signals for each active client based on latest scores and regime.
"""
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
import logging
import os
from datetime import date

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MAX_POSITIONS = 10
MIN_BUY_SCORE = 4
MAX_SELL_SCORE = 2


def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5433"),
        dbname=os.getenv("DB_NAME", "mri_db"),
        user=os.getenv("DB_USER", "mri_admin"),
        password=os.getenv("DB_PASSWORD", ""),
        cursor_factory=RealDictCursor,
    )


def get_latest_regime(cur):
    """Get the most recent market regime classification."""
    cur.execute("SELECT date, classification FROM market_regime ORDER BY date DESC LIMIT 1")
    row = cur.fetchone()
    return row["classification"] if row else "NEUTRAL"


def get_latest_scores(cur, min_score=0):
    """Get the most recent stock scores."""
    cur.execute("""
        SELECT symbol, total_score, date
        FROM stock_scores
        WHERE date = (SELECT MAX(date) FROM stock_scores)
          AND total_score >= %s
        ORDER BY total_score DESC
    """, (min_score,))
    return cur.fetchall()


def get_next_day_open_prices(cur):
    """Get the latest open prices (used as recommended execution price)."""
    cur.execute("""
        SELECT symbol, open, close
        FROM daily_prices
        WHERE date = (SELECT MAX(date) FROM daily_prices)
    """)
    rows = cur.fetchall()
    return {r["symbol"]: {"open": r["open"], "close": r["close"]} for r in rows}


def get_client_open_positions(cur, client_id):
    """Get symbols the client currently holds."""
    cur.execute("""
        SELECT symbol FROM client_portfolio
        WHERE client_id = %s AND is_open = true
    """, (client_id,))
    return {r["symbol"] for r in cur.fetchall()}


def generate_signals_for_client(cur, client_id, regime, scores, prices, signal_date):
    """Generate BUY/SELL signals for one client."""
    open_positions = get_client_open_positions(cur, client_id)
    signals = []

    # ── SELL SIGNALS ──
    # If regime is BEAR, signal SELL for all open positions
    if regime == "BEAR":
        for sym in open_positions:
            price_data = prices.get(sym, {})
            signals.append({
                "client_id": client_id,
                "date": signal_date,
                "symbol": sym,
                "action": "SELL",
                "recommended_price": price_data.get("close"),
                "score": next((s["total_score"] for s in scores if s["symbol"] == sym), None),
                "regime": regime,
                "reason": "REGIME_BEAR: Market in bearish regime, exit all positions",
            })
    else:
        # Check individual scores for SELL
        score_map = {s["symbol"]: s["total_score"] for s in scores}
        for sym in open_positions:
            score = score_map.get(sym, 0)
            price_data = prices.get(sym, {})
            if score <= MAX_SELL_SCORE:
                signals.append({
                    "client_id": client_id,
                    "date": signal_date,
                    "symbol": sym,
                    "action": "SELL",
                    "recommended_price": price_data.get("close"),
                    "score": score,
                    "regime": regime,
                    "reason": f"SCORE_LOW: Score={score} <= {MAX_SELL_SCORE}, trend deteriorating",
                })

    # ── BUY SIGNALS ──
    pending_sells = {s["symbol"] for s in signals if s["action"] == "SELL"}
    effective_positions = len(open_positions - pending_sells)

    if regime == "BULL" and effective_positions < MAX_POSITIONS:
        slots = MAX_POSITIONS - effective_positions
        # Top scoring stocks not already held
        eligible = [
            s for s in scores
            if s["total_score"] >= MIN_BUY_SCORE
            and s["symbol"] not in open_positions
            and s["symbol"] in prices
        ]
        for stock in eligible[:slots]:
            price_data = prices.get(stock["symbol"], {})
            signals.append({
                "client_id": client_id,
                "date": signal_date,
                "symbol": stock["symbol"],
                "action": "BUY",
                "recommended_price": price_data.get("close"),
                "score": stock["total_score"],
                "regime": regime,
                "reason": f"Score={stock['total_score']}, Regime=BULL, top-ranked eligible",
            })

    return signals


def run_signal_generator():
    """Main entry: generate signals for all active clients."""
    conn = get_connection()
    cur = conn.cursor()

    signal_date = date.today()
    logger.info(f"=== Signal Generator — {signal_date} ===")

    # Get market state
    regime = get_latest_regime(cur)
    logger.info(f"Current Regime: {regime}")

    scores = get_latest_scores(cur)
    logger.info(f"Stocks scored: {len(scores)}")

    prices = get_next_day_open_prices(cur)
    logger.info(f"Prices available: {len(prices)}")

    # Get all active clients
    cur.execute("SELECT id FROM clients WHERE is_active = true")
    clients = cur.fetchall()
    logger.info(f"Active clients: {len(clients)}")

    if not clients:
        logger.warning("No active clients. Nothing to do.")
        conn.close()
        return

    total_signals = 0
    for client in clients:
        client_id = str(client["id"])
        signals = generate_signals_for_client(cur, client_id, regime, scores, prices, signal_date)

        if signals:
            sql = """
                INSERT INTO client_signals (client_id, date, symbol, action, recommended_price, score, regime, reason)
                VALUES (%(client_id)s, %(date)s, %(symbol)s, %(action)s, %(recommended_price)s, %(score)s, %(regime)s, %(reason)s)
                ON CONFLICT (client_id, date, symbol, action) DO NOTHING
            """
            execute_batch(cur, sql, signals, page_size=100)
            total_signals += len(signals)
            logger.info(f"  Client {client_id[:8]}...: {len(signals)} signals ({sum(1 for s in signals if s['action']=='BUY')} BUY, {sum(1 for s in signals if s['action']=='SELL')} SELL)")

    conn.commit()
    cur.close()
    conn.close()

    logger.info(f"=== Signal Generation Complete: {total_signals} signals for {len(clients)} clients ===")
    return total_signals


if __name__ == "__main__":
    run_signal_generator()
