"""
Email Service — AWS SES for transactional signal emails.
Sends daily digest to each client with their BUY/SELL signals.
"""
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
import logging
import os
from datetime import date
from src.db import get_connection as _get_raw_connection
from src.aws_ses import aws_credentials_present, get_ses_client, resolve_ses_region
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SENDER_EMAIL = os.getenv("SES_SENDER_EMAIL", "edwardjsi@gmail.com")
FRONTEND_URL = os.getenv("FRONTEND_URL", os.getenv("PUBLIC_FRONTEND_URL", "https://mri-frontend.onrender.com")).rstrip("/")


def get_connection():
    """Get DB connection with RealDictCursor using shared config (supports DATABASE_URL)."""
    conn = _get_raw_connection()
    conn.cursor_factory = RealDictCursor
    return conn


def build_signal_email_html(client_name, signals, regime, holdings=None, watchlist=None):
    """Build HTML email body for daily signal digest."""
    buy_signals = [s for s in signals if s["action"] == "BUY"]
    sell_signals = [s for s in signals if s["action"] == "SELL"]
    
    # Tracked items (Portfolio/Watchlist)
    holdings = holdings or []
    watchlist = watchlist or []

    regime_color = {"BULL": "#22c55e", "BEAR": "#ef4444", "NEUTRAL": "#f59e0b"}.get(regime, "#6b7280")

    def _score_label(score):
        """Return grade badge string for a 0-100 MRI score."""
        s = score or 0
        if s >= 80: return f'<span style="color:#22c55e;font-weight:700">🟢 {s}/100</span>'
        if s >= 40: return f'<span style="color:#f59e0b;font-weight:700">🟡 {s}/100</span>'
        return f'<span style="color:#ef4444;font-weight:700">🔴 {s}/100</span>'

    buy_rows = ""
    for s in buy_signals:
        buy_rows += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:600">{s['symbol']}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb">₹{s['recommended_price']:,.2f}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb">{_score_label(s['score'])}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-size:12px;color:#6b7280">{s['reason']}</td>
        </tr>"""

    sell_rows = ""
    for s in sell_signals:
        sell_rows += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:600">{s['symbol']}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb">₹{s['recommended_price']:,.2f}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb">{_score_label(s['score'])}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-size:12px;color:#6b7280">{s['reason']}</td>
        </tr>"""

    html = f"""
    <html>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:600px;margin:0 auto;padding:20px;background:#f9fafb">
        <div style="background:white;border-radius:12px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,0.1)">
            <h1 style="margin:0 0 4px;font-size:20px;color:#111827">📊 MRI Daily Signals</h1>
            <p style="margin:0 0 16px;color:#6b7280;font-size:14px">{date.today().strftime('%A, %B %d, %Y')}</p>

            <div style="background:{regime_color}15;border-left:4px solid {regime_color};padding:12px;border-radius:4px;margin-bottom:20px">
                <span style="font-size:13px;color:#6b7280">Market Regime</span>
                <div style="font-size:18px;font-weight:700;color:{regime_color}">{regime}</div>
            </div>

            <p style="color:#374151">Hi {client_name},</p>
            <p style="color:#374151">Here are your signals for today. Log in to your dashboard to mark them as Executed or Skipped.</p>
    """

    if buy_signals:
        html += f"""
            <h2 style="color:#22c55e;font-size:16px;margin:20px 0 8px">🟢 BUY Signals ({len(buy_signals)})</h2>
            <table style="width:100%;border-collapse:collapse;font-size:14px">
                <tr style="background:#f0fdf4">
                    <th style="padding:8px;text-align:left">Symbol</th>
                    <th style="padding:8px;text-align:left">Price</th>
                    <th style="padding:8px;text-align:left">Score</th>
                    <th style="padding:8px;text-align:left">Reason</th>
                </tr>
                {buy_rows}
            </table>"""

    if sell_signals:
        html += f"""
            <h2 style="color:#ef4444;font-size:16px;margin:20px 0 8px">🔴 SELL Signals ({len(sell_signals)})</h2>
            <table style="width:100%;border-collapse:collapse;font-size:14px">
                <tr style="background:#fef2f2">
                    <th style="padding:8px;text-align:left">Symbol</th>
                    <th style="padding:8px;text-align:left">Price</th>
                    <th style="padding:8px;text-align:left">Score</th>
                    <th style="padding:8px;text-align:left">Reason</th>
                </tr>
                {sell_rows}
            </table>"""

    if not buy_signals and not sell_signals:
        html += """<p style="color:#6b7280;font-style:italic;text-align:center;padding:10px 0">No fresh signals today.</p>"""

    # 💼 Portfolio Section
    if holdings:
        html += f"""
            <h2 style="color:#3b82f6;font-size:16px;margin:24px 0 8px">💼 Your Portfolio Status</h2>
            <table style="width:100%;border-collapse:collapse;font-size:13px">
                <tr style="background:#eff6ff">
                    <th style="padding:8px;text-align:left">Symbol</th>
                    <th style="padding:8px;text-align:left">MRI Score</th>
                    <th style="padding:8px;text-align:left">Grade</th>
                    <th style="padding:8px;text-align:left">Regime</th>
                </tr>"""
        for h in holdings:
            sc = h['total_score'] or 0
            grade = '🟢 Strong' if sc >= 80 else ('🟡 Neutral' if sc >= 40 else '🔴 Weak')
            score_color = '#22c55e' if sc >= 80 else ('#f59e0b' if sc >= 40 else '#ef4444')
            html += f"""
                <tr>
                    <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:600">{h['symbol']}</td>
                    <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:700;color:{score_color}">{sc}/100</td>
                    <td style="padding:8px;border-bottom:1px solid #e5e7eb">{grade}</td>
                    <td style="padding:8px;border-bottom:1px solid #e5e7eb">{regime}</td>
                </tr>"""
        html += "</table>"

    # 👀 Watchlist Section
    if watchlist:
        html += f"""
            <h2 style="color:#8b5cf6;font-size:16px;margin:24px 0 8px">👀 Your Watchlist Update</h2>
            <table style="width:100%;border-collapse:collapse;font-size:13px">
                <tr style="background:#f5f3ff">
                    <th style="padding:8px;text-align:left">Symbol</th>
                    <th style="padding:8px;text-align:left">MRI Score</th>
                    <th style="padding:8px;text-align:left">Grade</th>
                    <th style="padding:8px;text-align:left">Trend</th>
                </tr>"""
        for w in watchlist:
            sc = w['total_score'] or 0
            grade = '🟢 Strong' if sc >= 80 else ('🟡 Neutral' if sc >= 40 else '🔴 Weak')
            score_color = '#22c55e' if sc >= 80 else ('#f59e0b' if sc >= 40 else '#ef4444')
            html += f"""
                <tr>
                    <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:600">{w['symbol']}</td>
                    <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:700;color:{score_color}">{sc}/100</td>
                    <td style="padding:8px;border-bottom:1px solid #e5e7eb">{grade}</td>
                    <td style="padding:8px;border-bottom:1px solid #e5e7eb">{regime}</td>
                </tr>"""
        html += "</table>"

    html += """
            <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0">
            <p style="font-size:12px;color:#9ca3af;text-align:center">
                This is not financial advice. Past performance does not guarantee future results.<br>
                Market Regime Intelligence — Quantitative Signal Platform
            </p>
        </div>
    </body>
    </html>"""

    return html


def send_password_reset_email(email: str, name: str, token: str):
    ok, err = send_password_reset_email_detailed(email=email, name=name, token=token)
    if not ok:
        logger.error(f"❌ Password reset email failed: {err}")
    return ok


def send_password_reset_email_detailed(email: str, name: str, token: str) -> tuple[bool, str | None]:
    """Send a password reset link to the user, returning (ok, error_message)."""
    if not aws_credentials_present():
        return (
            False,
            "AWS credentials missing. Set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY on the API service.",
        )

    try:
        ses_region = resolve_ses_region()
    except Exception as e:
        return (False, f"SES region misconfigured: {e}")

    ses = get_ses_client(ses_region)

    reset_link = f"{FRONTEND_URL}/?reset_token={token}"

    subject = "MRI - Password Reset Request"

    html_body = f"""
    <html>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:600px;margin:0 auto;padding:20px;background:#f9fafb">
        <div style="background:white;border-radius:12px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,0.1)">
            <h1 style="margin:0 0 16px;font-size:20px;color:#111827">🔒 Reset Your Password</h1>
            <p style="color:#374151">Hi {name or 'User'},</p>
            <p style="color:#374151">We received a request to reset your password for your MRI account.</p>
            <div style="margin:30px 0;text-align:center">
                <a href="{reset_link}" style="background-color:#3b82f6;color:white;padding:12px 24px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block">Reset Password</a>
            </div>
            <p style="color:#6b7280;font-size:14px">If you didn't request this, you can safely ignore this email. This link will expire in 1 hour.</p>
            <hr style="border:none;border-top:1px solid #e5e7eb;margin:30px 0 20px">
            <p style="font-size:12px;color:#9ca3af;text-align:center">
                Market Regime Intelligence
            </p>
        </div>
    </body>
    </html>
    """
    
    try:
        ses.send_email(
            Source=SENDER_EMAIL,
            Destination={"ToAddresses": [email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
            },
        )
        logger.info(f"✅ Password reset email sent to {email}")
        return (True, None)
    except ClientError as e:
        code = (e.response or {}).get("Error", {}).get("Code", "ClientError")
        msg = (e.response or {}).get("Error", {}).get("Message", str(e))
        hint = ""
        if code == "MessageRejected" and "not verified" in str(msg).lower():
            hint = (
                f" Verify SES_SENDER_EMAIL and recipient in SES sandbox for region '{ses_region}', "
                "or request SES production access in that region."
            )
        return (
            False,
            f"SES send_email failed ({code}) (region={ses_region}, sender={SENDER_EMAIL}): {msg}.{hint}".strip(),
        )
    except Exception as e:
        return (
            False,
            f"SES send_email failed (region={ses_region}, sender={SENDER_EMAIL}): {e}",
        )


def send_signal_emails():
    """Send daily signal digest to ALL active clients, including regime summary."""
    conn = get_connection()
    cur = conn.cursor()

    if not aws_credentials_present():
        logger.error("❌ AWS credentials missing: cannot send SES signal emails. Set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY on the pipeline runner.")
        cur.close()
        conn.close()
        return 0

    try:
        ses_region = resolve_ses_region()
    except Exception as e:
        logger.error(f"❌ SES region misconfigured: {e}")
        cur.close()
        conn.close()
        return 0

    ses = get_ses_client(ses_region)

    # 1. Get current market regime for the latest date
    cur.execute("""
        SELECT classification, date FROM market_regime 
        ORDER BY date DESC LIMIT 1
    """)
    regime_row = cur.fetchone()
    if not regime_row:
        logger.warning("No market regime data found. Cannot send meaningful emails.")
        conn.close()
        return 0
    
    regime = regime_row["classification"]
    latest_date = regime_row["date"]

    # 2. Get all active clients
    cur.execute("SELECT id, email, name FROM clients WHERE is_active = true")
    active_clients = cur.fetchall()

    if not active_clients:
        logger.info("No active clients. Nothing to email.")
        conn.close()
        return 0

    sent_count = 0
    for client in active_clients:
        client_id = str(client["id"])
        email = client["email"]
        name = client["name"] or "Investor"

        # 3. Prevent duplicate emails for the same day
        cur.execute("""
            SELECT id FROM email_log 
            WHERE client_id = %s AND date = CURRENT_DATE 
              AND email_type = 'DAILY_SIGNAL' AND status = 'SENT'
        """, (client_id,))
        if cur.fetchone():
            logger.info(f"  ⏭️ Skipping {email}: Daily email already sent today.")
            continue

        # 4. Fetch signals (if any) for this client on the latest date
        cur.execute("""
            SELECT symbol, action, recommended_price, score, regime, reason
            FROM client_signals
            WHERE client_id = %s AND date = %s
        """, (client_id, latest_date))
        signals = cur.fetchall()

        # 5. Fetch Latest Scores for Portfolio Holdings
        cur.execute("""
            SELECT eh.symbol, ss.total_score
            FROM client_external_holdings eh
            LEFT JOIN stock_scores ss ON eh.symbol = ss.symbol AND ss.date = %s
            WHERE eh.client_id = %s
        """, (latest_date, client_id))
        holdings_scores = cur.fetchall()

        # 6. Fetch Latest Scores for Watchlist
        cur.execute("""
            SELECT cw.symbol, ss.total_score
            FROM client_watchlist cw
            LEFT JOIN stock_scores ss ON cw.symbol = ss.symbol AND ss.date = %s
            WHERE cw.client_id = %s
        """, (latest_date, client_id))
        watchlist_scores = cur.fetchall()

        buy_count = sum(1 for s in signals if s["action"] == "BUY")
        sell_count = sum(1 for s in signals if s["action"] == "SELL")
        
        if signals:
            subject = f"MRI Signals: {buy_count} BUY, {sell_count} SELL — {regime} Market"
        else:
            subject = f"MRI Daily Update: {regime} Market Summary"

        html_body = build_signal_email_html(name, signals, regime, holdings=holdings_scores, watchlist=watchlist_scores)

        try:
            ses.send_email(
                Source=SENDER_EMAIL,
                Destination={"ToAddresses": [email]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
                },
            )
            status_val = "SENT"
            sent_count += 1
            logger.info(f"  ✅ Sent to {email}: {subject}")

            # Mark signals as sent (if they exist)
            if signals:
                cur.execute(
                    "UPDATE client_signals SET email_sent = true WHERE client_id = %s AND date = %s",
                    (client_id, latest_date),
                )
        except ClientError as e:
            status_val = "FAILED"
            code = (e.response or {}).get("Error", {}).get("Code", "ClientError")
            msg = (e.response or {}).get("Error", {}).get("Message", str(e))
            logger.error(f"  ❌ Failed to send to {email} ({code}): {msg}")
        except Exception as e:
            status_val = "FAILED"
            logger.error(f"  ❌ Failed to send to {email}: {str(e)}")

        # 5. Log the email attempt
        cur.execute("""
            INSERT INTO email_log (client_id, date, email_type, service, subject, status)
            VALUES (%s, CURRENT_DATE, 'DAILY_SIGNAL', 'SES', %s, %s)
        """, (client_id, subject, status_val))

    conn.commit()
    cur.close()
    conn.close()

    logger.info(f"=== Email Service Complete: {sent_count}/{len(active_clients)} emails sent ===")
    return sent_count


def send_on_demand_risk_audit_report(email, name, successful, failed):
    """Send a summary email after an on-demand ingestion completes."""
    if not email or not aws_credentials_present():
        return False
        
    try:
        ses_region = resolve_ses_region()
        ses = get_ses_client(ses_region)
        
        subject = f"MRI Risk Audit: {len(successful)} Stocks Graded"
        if failed:
            subject += f" ({len(failed)} Failed/Delisted)"
            
        # Build Table rows for successful
        success_rows = ""
        for s in successful:
             success_rows += f"<tr><td style='padding:8px;border-bottom:1px solid #eee'>{s}</td><td style='padding:8px;border-bottom:1px solid #eee;color:#22c55e'>Graded ✅</td></tr>"
             
        failed_rows = ""
        for s in failed:
             failed_rows += f"<tr><td style='padding:8px;border-bottom:1px solid #eee'>{s}</td><td style='padding:8px;border-bottom:1px solid #eee;color:#ef4444'>Unknown/Delisted ❌</td></tr>"

        html_body = f"""
        <html>
        <body style="font-family:sans-serif;max-width:600px;margin:auto;padding:20px;color:#333">
            <h2 style="color:#111827">📊 MRI Risk Audit Report</h2>
            <p>Hi {name or 'User'},</p>
            <p>We've finished analyzing the custom stocks you added to your Digital Twin.</p>
            
            <table style="width:100%;border-collapse:collapse;margin:20px 0">
                <tr style="background:#f9fafb"><th style="padding:8px;text-align:left">Symbol</th><th style="padding:8px;text-align:left">Status</th></tr>
                {success_rows}
                {failed_rows}
            </table>
            
            <p style="font-size:14px;color:#666">
                <strong>Note:</strong> Failed stocks are usually delisted or incorrectly named. 
                Log in to your dashboard to see the latest trend grades for the accepted stocks.
            </p>
            <hr style="border:1px solid #eee;margin:20px 0">
            <p style="font-size:12px;color:#999;text-align:center">Market Regime Intelligence</p>
        </body>
        </html>
        """
        
        ses.send_email(
            Source=SENDER_EMAIL,
            Destination={"ToAddresses": [email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
            },
        )
        logger.info(f"✅ Risk audit report sent to {email}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send risk audit email: {e}")
        return False


if __name__ == "__main__":
    send_signal_emails()
