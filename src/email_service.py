"""
Email Service — AWS SES for transactional signal emails.
Sends daily digest to each client with their BUY/SELL signals.
"""
import boto3
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
import logging
import os
from datetime import date

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SENDER_EMAIL = os.getenv("SES_SENDER_EMAIL", "edwardjsi@gmail.com")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")


def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5433"),
        dbname=os.getenv("DB_NAME", "mri_db"),
        user=os.getenv("DB_USER", "mri_admin"),
        password=os.getenv("DB_PASSWORD", ""),
        cursor_factory=RealDictCursor,
    )


def build_signal_email_html(client_name, signals, regime):
    """Build HTML email body for daily signal digest."""
    buy_signals = [s for s in signals if s["action"] == "BUY"]
    sell_signals = [s for s in signals if s["action"] == "SELL"]

    regime_color = {"BULL": "#22c55e", "BEAR": "#ef4444", "NEUTRAL": "#f59e0b"}.get(regime, "#6b7280")

    buy_rows = ""
    for s in buy_signals:
        buy_rows += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:600">{s['symbol']}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb">₹{s['recommended_price']:,.2f}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb">{s['score']}/5</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-size:12px;color:#6b7280">{s['reason']}</td>
        </tr>"""

    sell_rows = ""
    for s in sell_signals:
        sell_rows += f"""
        <tr>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:600">{s['symbol']}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb">₹{s['recommended_price']:,.2f}</td>
            <td style="padding:8px;border-bottom:1px solid #e5e7eb">{s['score']}/5</td>
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
                {sell_rows}"""

    if not buy_signals and not sell_signals:
        html += """<p style="color:#6b7280;font-style:italic;text-align:center;padding:20px">No signals today. Hold current positions.</p>"""

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


def send_signal_emails():
    """Send daily signal digest to all clients with unsent signals."""
    conn = get_connection()
    cur = conn.cursor()

    ses = boto3.client("ses", region_name=AWS_REGION)

    # Get today's unsent signals grouped by client
    cur.execute("""
        SELECT cs.client_id, c.email, c.name,
               json_agg(json_build_object(
                   'symbol', cs.symbol, 'action', cs.action,
                   'recommended_price', cs.recommended_price,
                   'score', cs.score, 'regime', cs.regime, 'reason', cs.reason
               )) AS signals
        FROM client_signals cs
        JOIN clients c ON c.id = cs.client_id
        WHERE cs.email_sent = false
          AND cs.date = (SELECT MAX(date) FROM client_signals)
        GROUP BY cs.client_id, c.email, c.name
    """)
    client_groups = cur.fetchall()

    if not client_groups:
        logger.info("No unsent signals. Nothing to email.")
        conn.close()
        return 0

    sent_count = 0
    for group in client_groups:
        client_id = str(group["client_id"])
        email = group["email"]
        name = group["name"] or "Investor"
        signals = group["signals"]
        regime = signals[0]["regime"] if signals else "NEUTRAL"

        buy_count = sum(1 for s in signals if s["action"] == "BUY")
        sell_count = sum(1 for s in signals if s["action"] == "SELL")
        subject = f"MRI Signals: {buy_count} BUY, {sell_count} SELL — {regime} Market"

        html_body = build_signal_email_html(name, signals, regime)

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
        except Exception as e:
            status_val = "FAILED"
            logger.error(f"  ❌ Failed to send to {email}: {e}")

        # Mark signals as sent
        cur.execute(
            "UPDATE client_signals SET email_sent = true WHERE client_id = %s AND date = (SELECT MAX(date) FROM client_signals WHERE client_id = %s)",
            (client_id, client_id),
        )

        # Log email
        cur.execute("""
            INSERT INTO email_log (client_id, date, email_type, service, subject, status)
            VALUES (%s, CURRENT_DATE, 'DAILY_SIGNAL', 'SES', %s, %s)
        """, (client_id, subject, status_val))

    conn.commit()
    cur.close()
    conn.close()

    logger.info(f"=== Email Service Complete: {sent_count}/{len(client_groups)} emails sent ===")
    return sent_count


if __name__ == "__main__":
    send_signal_emails()
