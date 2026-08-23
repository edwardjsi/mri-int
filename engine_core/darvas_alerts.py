"""
Darvas Screener Alerts
======================
Runs the Darvas deterministic scan and sends email alerts for NEWLY qualifying stocks.
Maintains state in outputs/darvas_alert_state.json.
"""
import json
import os
import logging
from engine_core.db import get_connection
from engine_core.email_service import send_email_custom
from datetime import datetime

logger = logging.getLogger(__name__)

ADMIN_EMAIL = "edward@example.com"  # Using dummy admin email since we don't know the exact one

def run_darvas_scan():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            query = """
            WITH latest_prices AS (
                SELECT DISTINCT ON (symbol)
                    symbol, date, close, high, rolling_high_52w
                FROM daily_prices
                ORDER BY symbol, date DESC
            ),
            latest_mcap AS (
                SELECT DISTINCT ON (symbol)
                    symbol, date, market_cap_cr
                FROM market_cap_history
                ORDER BY symbol, date DESC
            )
            SELECT 
                lp.symbol, 
                COALESCE(c.name, lp.symbol) as company_name, 
                lp.close, 
                lp.high,
                lp.rolling_high_52w,
                lm.market_cap_cr
            FROM latest_prices lp
            JOIN nifty500_universe n5 ON lp.symbol = n5.symbol AND n5.constituent_to IS NULL
            LEFT JOIN latest_mcap lm ON lp.symbol = lm.symbol
            LEFT JOIN prde_companies c ON lp.symbol = c.ticker
            WHERE lm.market_cap_cr > 800
              AND lp.close > 50
              AND lp.high >= lp.rolling_high_52w
            """
            cur.execute(query)
            return cur.fetchall()
    finally:
        if conn:
            conn.close()

def get_admin_email():
    """Fetch admin email from DB, or use fallback."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT email FROM clients WHERE role = 'admin' LIMIT 1")
            row = cur.fetchone()
            if row and 'email' in row:
                return row['email']
    except Exception:
        pass
    finally:
        if conn:
            conn.close()
    return ADMIN_EMAIL

def run():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('outputs/darvas_alerts.log', mode='a')
        ]
    )
    logger.info("Running Darvas Alerts scan...")
    os.makedirs("outputs", exist_ok=True)
    
    current_results = run_darvas_scan()
    current_symbols = {r['symbol']: r for r in current_results}
    
    # Load previous state from DB
    previous_symbols = set()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT symbol FROM darvas_alert_state")
            previous_symbols = {r['symbol'] for r in cur.fetchall()}
    except Exception as e:
        logger.error(f"Error reading state from DB: {e}")
    finally:
        if conn:
            conn.close()
            
    # Find newly qualifying symbols
    new_symbols = set(current_symbols.keys()) - previous_symbols
    
    if new_symbols:
        logger.info(f"Found {len(new_symbols)} new Darvas candidates: {new_symbols}")
        
        # Prepare email content
        html_body = "<h3>New Darvas Screener Candidates</h3><ul>"
        for sym in new_symbols:
            r = current_symbols[sym]
            html_body += f"<li><b>{sym}</b> ({r['company_name']}) - Close: ₹{r['close']:.2f}, 52w High: ₹{r['rolling_high_52w']:.2f}, Mcap: ₹{r['market_cap_cr']:.0f} Cr</li>"
        html_body += "</ul>"
        
        admin_email = get_admin_email()
        try:
            send_email_custom(
                recipient_email=admin_email,
                subject=f"Darvas Screener Alert - {len(new_symbols)} New Candidates",
                html_body=html_body
            )
            logger.info("Alert email sent successfully.")
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            
    else:
        logger.info("No new Darvas candidates today.")
        
    # Save new state to DB
    today_str = datetime.today().strftime("%Y-%m-%d")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # We clear the state and insert the new active ones, or just upsert.
            # Upserting active ones, and maybe deleting ones that are no longer passing if we only want active ones.
            cur.execute("TRUNCATE TABLE darvas_alert_state")
            for sym in current_symbols.keys():
                cur.execute(
                    "INSERT INTO darvas_alert_state (symbol, last_alerted_date) VALUES (%s, %s)",
                    (sym, today_str)
                )
            conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to save state to DB: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    run()
