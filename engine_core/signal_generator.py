"""
Daily Signal Generator — runs after engine pipeline completes.
Generates BUY/SELL signals for each active client based on latest scores and regime.
"""
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
import logging
import os
from datetime import date
from engine_core.db import get_connection as _get_raw_connection

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

MAX_POSITIONS = 10
MIN_BUY_SCORE = 75            # 75/100 (3 conditions met)
MAX_SELL_SCORE = 40           # Sell if score drops below 40
MIN_ADTV = 100_000_000       # ₹10 Cr minimum avg daily turnover
MAX_SECTOR_STOCKS = 3         # Max stocks from any single sector
MIN_ABSOLUTE_SCORE = 50       # Momentum threshold (at least 2 conditions)


def get_connection():
    """Get DB connection with RealDictCursor using shared config (supports DATABASE_URL)."""
    conn = _get_raw_connection()
    conn.cursor_factory = RealDictCursor
    return conn


def get_latest_regime(cur):
    """Get the most recent market regime classification."""
    cur.execute("SELECT date, classification FROM market_regime ORDER BY date DESC LIMIT 1")
    row = cur.fetchone()
    return row["classification"] if row else "NEUTRAL"


# Cache for sector lookups (populated once per run)
_sector_cache = {}


def _get_sector_proxy(cur, symbol):
    """Get sector/industry for a stock.
    Uses NSE Nifty 500 industry classification cached in memory.
    Falls back to 'UNKNOWN' if not available.
    """
    global _sector_cache
    if not _sector_cache:
        # Try to load from a sector mapping table if it exists
        try:
            cur.execute("""
                SELECT symbol, industry FROM stock_sectors
            """)
            rows = cur.fetchall()
            _sector_cache = {r["symbol"]: r["industry"] for r in rows}
        except Exception:
            # Table doesn't exist yet — use empty cache
            _sector_cache = {"_initialized": True}

    return _sector_cache.get(symbol, "UNKNOWN")


def get_latest_scores(cur, min_score=0):
    """Get the most recent stock scores with RS for ranking.
    Applies ₹10 Cr ADTV liquidity gate to filter illiquid stocks.
    """
    cur.execute("""
        SELECT ss.symbol, ss.total_score, ss.date,
               COALESCE(dp.rs_90d, 0) AS rs_90d,
               COALESCE(dp.avg_volume_20d * dp.close, 0) AS adtv
        FROM stock_scores ss
        LEFT JOIN daily_prices dp
          ON dp.symbol = ss.symbol AND dp.date = ss.date
        WHERE ss.date = (SELECT MAX(date) FROM stock_scores)
          AND ss.total_score >= %s
          AND COALESCE(dp.avg_volume_20d * dp.close, 0) >= %s
        ORDER BY ss.total_score DESC, dp.rs_90d DESC NULLS LAST
    """, (min_score, MIN_ADTV))
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

    if (regime == "BULL" or regime == "NEUTRAL") and effective_positions < MAX_POSITIONS:
        slots = MAX_POSITIONS - effective_positions
        # Top scoring stocks not already held, passing liquidity gate
        # In NEUTRAL regime, we require score >= 85
        current_threshold = MIN_BUY_SCORE if regime == "BULL" else 85
        eligible = [
            s for s in scores
            if s["total_score"] >= current_threshold
            and s["symbol"] not in open_positions
            and s["symbol"] in prices
        ]

        # Track sector concentration for this client's portfolio+new picks
        sector_count = {}  # sector -> count of stocks
        selected = []

        for stock in eligible:
            if len(selected) >= slots:
                break

            # Cash toggle: skip if score below absolute momentum threshold
            if stock["total_score"] < MIN_ABSOLUTE_SCORE:
                logger.info(f"  Cash toggle: skipping {stock['symbol']} (score={stock['total_score']} < {MIN_ABSOLUTE_SCORE})")
                continue

            # Sector concentration cap (use first letter of symbol as proxy
            # until sector data is available; future: use actual GICS sector)
            sector = _get_sector_proxy(cur, stock["symbol"])
            current_sector_count = sector_count.get(sector, 0)
            if current_sector_count >= MAX_SECTOR_STOCKS:
                logger.info(f"  Sector cap: skipping {stock['symbol']} (sector={sector}, already {current_sector_count} stocks)")
                continue

            sector_count[sector] = current_sector_count + 1
            selected.append(stock)

        for stock in selected:
            price_data = prices.get(stock["symbol"], {})
            adtv_cr = stock.get("adtv", 0) / 10_000_000  # Convert to Cr
            signals.append({
                "client_id": client_id,
                "date": signal_date,
                "symbol": stock["symbol"],
                "action": "BUY",
                "recommended_price": price_data.get("close"),
                "score": stock["total_score"],
                "regime": regime,
                "reason": f"Score={stock['total_score']}, RS={stock.get('rs_90d', 0):.1%}, ADTV=₹{adtv_cr:.0f}Cr, Regime=BULL",
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
