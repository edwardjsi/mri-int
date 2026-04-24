"""
MRI Pipeline Health Monitor
Runs at the end of the daily pipeline to verify data integrity.
Alerts via SES if thresholds are violated.
"""
import os
import sys
import logging
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# Add parent directory to sys.path to import engine_core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_core.db import get_connection
from engine_core.email_service import send_alert_email

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("health_monitor")

# THRESHOLDS
MAX_ALLOWED_DRIFT_DAYS = 1
MIN_INDICATOR_COVERAGE_PCT = 90.0
MAX_SUSPICIOUS_RS_COUNT = 50  # Allow some for IPOs/gaps
MAX_STALE_INDICATORS_COUNT = 100

def run_health_check():
    logger.info("=== Starting Pipeline Health Audit ===")
    conn = get_connection()
    conn.cursor_factory = RealDictCursor
    
    issues = []
    summary_stats = {}
    
    try:
        with conn.cursor() as cur:
            # 1. CORE METRICS QUERY
            cur.execute("""
                WITH latest_date AS (SELECT MAX(date) FROM daily_prices),
                prev_date AS (SELECT DISTINCT date FROM daily_prices WHERE date < (SELECT MAX(date) FROM daily_prices) ORDER BY date DESC LIMIT 1),
                stats AS (
                    SELECT 
                        COUNT(DISTINCT symbol) as total,
                        COUNT(DISTINCT CASE WHEN ema_50 IS NULL THEN symbol END) as nulls,
                        COUNT(DISTINCT CASE WHEN rs_90d = 0 OR rs_90d IS NULL THEN symbol END) as susp_rs
                    FROM daily_prices
                    WHERE date = (SELECT * FROM latest_date)
                ),
                stale_check AS (
                    SELECT COUNT(DISTINCT curr.symbol) as stale
                    FROM daily_prices curr
                    JOIN daily_prices prev ON curr.symbol = prev.symbol AND prev.date = (SELECT * FROM prev_date)
                    WHERE curr.date = (SELECT * FROM latest_date)
                      AND curr.ema_50 = prev.ema_50
                      AND curr.volume > 0
                ),
                dates AS (
                    SELECT 
                        (SELECT * FROM latest_date) as last_p,
                        (SELECT MAX(date) FROM stock_scores) as last_s,
                        (SELECT MAX(date) FROM market_regime) as last_r,
                        (SELECT MAX(date) FROM market_index_prices) as last_idx
                    )
                SELECT * FROM stats, dates, stale_check
            """)
            row = cur.fetchone()
            
            if not row or not row['last_p']:
                raise Exception("Health Check Failed: No price data found.")

            # Calculate Coverage
            total = row["total"] or 0
            nulls = row["nulls"] or 0
            coverage = ((total - nulls) / total * 100) if total > 0 else 0
            summary_stats['coverage'] = round(coverage, 2)
            summary_stats['nulls'] = nulls
            
            # Calculate Drift
            last_p = row["last_p"]
            last_s = row["last_s"]
            last_r = row["last_r"]
            last_idx = row["last_idx"]
            
            drift_scores = (last_p - last_s).days if last_s else 99
            drift_regime = (last_p - last_r).days if last_r else 99
            drift_idx = (last_p - last_idx).days if last_idx else 99
            
            summary_stats['drift_scores'] = drift_scores
            summary_stats['drift_regime'] = drift_regime
            summary_stats['drift_idx'] = drift_idx
            
            # 2. EVALUATE THRESHOLDS
            if coverage < MIN_INDICATOR_COVERAGE_PCT:
                issues.append(f"<b>CRITICAL COVERAGE</b>: Only {coverage:.1f}% symbols have indicators (Target: {MIN_INDICATOR_COVERAGE_PCT}%). {nulls} symbols missing EMA-50.")
            
            if drift_scores > MAX_ALLOWED_DRIFT_DAYS:
                issues.append(f"<b>SCORE DRIFT</b>: Stock scores are {drift_scores} days behind prices.")
            
            if drift_regime > MAX_ALLOWED_DRIFT_DAYS:
                issues.append(f"<b>REGIME DRIFT</b>: Market regime is {drift_regime} days behind prices.")

            if drift_idx > MAX_ALLOWED_DRIFT_DAYS:
                issues.append(f"<b>INDEX DRIFT</b>: Nifty index prices are {drift_idx} days behind stock prices.")

            if row["susp_rs"] > MAX_SUSPICIOUS_RS_COUNT:
                issues.append(f"<b>SUSPICIOUS RS</b>: {row['susp_rs']} symbols have NULL/0 Relative Strength.")

            if row["stale"] > MAX_STALE_INDICATORS_COUNT:
                issues.append(f"<b>STALE INDICATORS</b>: {row['stale']} symbols have non-moving EMAs despite market volume.")

            # 3. DISPATCH ALERT
            if issues:
                logger.error(f"Integrity check FAILED: {len(issues)} issues found.")
                html_msg = "<ul>" + "".join([f"<li>{issue}</li>" for issue in issues]) + "</ul>"
                html_msg += f"<br><p><b>Pipeline Statistics:</b><br>Total Symbols: {total}<br>Latest Date: {last_p}</p>"
                send_alert_email("Pipeline Integrity Violation", html_msg)
                return False
            else:
                logger.info(f"Integrity check PASSED. Coverage: {coverage:.1f}%, Drift: 0d.")
                return True

    except Exception as e:
        logger.exception("Health check crashed")
        send_alert_email("Health Monitor System Failure", f"<p>The monitor itself crashed: {e}</p>")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    success = run_health_check()
    if not success:
        sys.exit(1)
    sys.exit(0)
