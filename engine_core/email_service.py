"""
Email Service — AWS SES for transactional signal emails.
Sends daily digest to each client with their BUY/SELL signals.
"""
import psycopg2
from psycopg2.extras import RealDictCursor, execute_batch
import logging
import os
from datetime import date
from engine_core.db import get_connection as _get_raw_connection
from engine_core.aws_ses import aws_credentials_present, get_ses_client, resolve_ses_region
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


def build_stee_signal_email_html(client_name, trades, regime):
    """Build HTML email body for STEE swing trading signals."""
    regime_color = {"BULLISH": "#22c55e", "BEARISH": "#ef4444", "SIDEWAYS": "#f59e0b"}.get(regime, "#6b7280")
    
    trade_rows = ""
    for t in trades:
        aae_val = t.get('aae_score')
        aae_display = f"<b>{aae_val}</b>" if aae_val else "N/A"
        trade_rows += f"""
        <tr>
            <td style="padding:12px;border-bottom:1px solid #e5e7eb;font-weight:600">{t['symbol']}</td>
            <td style="padding:12px;border-bottom:1px solid #e5e7eb">₹{t['entry_price']:,.2f}</td>
            <td style="padding:12px;border-bottom:1px solid #e5e7eb;color:#ef4444;font-weight:600">₹{t['stop_loss']:,.2f}</td>
            <td style="padding:12px;border-bottom:1px solid #e5e7eb">{aae_display}</td>
            <td style="padding:12px;border-bottom:1px solid #e5e7eb;color:#3b82f6">₹{t['risk_amount']:,.0f}</td>
        </tr>"""

    html = f"""
    <html>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:600px;margin:0 auto;padding:20px;background:#f9fafb">
        <div style="background:white;border-radius:12px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,0.1);border-top:4px solid #3b82f6">
            <h1 style="margin:0 0 4px;font-size:20px;color:#111827">🚀 STEE Swing Trade Signals</h1>
            <p style="margin:0 0 16px;color:#6b7280;font-size:14px">{date.today().strftime('%A, %B %d, %Y')}</p>

            <div style="background:{regime_color}15;border-left:4px solid {regime_color};padding:12px;border-radius:4px;margin-bottom:20px">
                <span style="font-size:13px;color:#6b7280">STEE Market Regime</span>
                <div style="font-size:18px;font-weight:700;color:{regime_color}">{regime}</div>
            </div>

            <p style="color:#374151">Hi {client_name},</p>
            <p style="color:#374151">The <b>Momentum Swing Trading Execution Engine (STEE)</b> has identified new breakout opportunities. Follow the risk parameters strictly.</p>
            
            <h2 style="color:#3b82f6;font-size:16px;margin:24px 0 8px">📈 New Trade Entries</h2>
            <table style="width:100%;border-collapse:collapse;font-size:14px">
                <tr style="background:#f8fafc">
                    <th style="padding:12px;text-align:left">Symbol</th>
                    <th style="padding:12px;text-align:left">Entry</th>
                    <th style="padding:12px;text-align:left">Stop Loss</th>
                    <th style="padding:12px;text-align:left">AAE Score</th>
                    <th style="padding:12px;text-align:left">Risk</th>
                </tr>
                {trade_rows}
            </table>

            <div style="margin-top:24px;padding:16px;background:#fff7ed;border-radius:8px;border:1px solid #ffedd5">
                <p style="margin:0;font-size:13px;color:#9a3412;font-weight:600">⚠️ Risk Management Rule:</p>
                <p style="margin:4px 0 0;font-size:12px;color:#c2410c">Exit 50% at 2R Profit Target. Exit remaining 50% on a Close below EMA-10.</p>
            </div>

            <hr style="border:none;border-top:1px solid #e5e7eb;margin:30px 0 20px">
            <p style="font-size:12px;color:#9ca3af;text-align:center">
                Market Regime Intelligence — STEE Automated Execution
            </p>
        </div>
    </body>
    </html>"""

    return html


    return html


def build_aae_report_email_html(client_name: str, result: dict) -> str:
    """
    Build a high-conviction institutional email for an AAE V3 Forensic Scan.
    Includes numerical scores, thematic drivers, and human-readable jargon explanations.
    """
    symbol = result.get("symbol", "UNKNOWN")
    master_score = result.get("master_score", 0)
    sector = result.get("sector", "General")
    market_confirmation = result.get("market_confirmation", "PENDING")
    debate_conviction = result.get("debate_conviction", "N/A")
    risk_summary = result.get("risk_summary", "N/A")
    reasons = result.get("reasons", [])
    
    score_color = "#22c55e" if master_score >= 75 else "#f59e0b" if master_score >= 60 else "#ef4444"
    
    layers = result.get("layers", {})
    
    # Layer Breakdown HTML
    layer_rows = ""
    layer_configs = [
        ("Governance (L0)", layers.get("governance", {}).get("risk_score", "N/A"), "Integrity & Compliance check"),
        ("Structural Delta (L1&2)", layers.get("structural_delta", {}).get("score", "N/A"), "Earnings & Margin inflection"),
        ("Ownership (L3)", layers.get("ownership", {}).get("score", "N/A"), "FII/DII flow trajectory"),
        ("Narrative (L4)", layers.get("narrative", {}).get("score", "N/A"), "Market sentiment & Themes"),
        ("Market Confirmation (L5)", layers.get("market", {}).get("score", "N/A"), "Price & Volume leadership"),
        ("Valuation (L6)", layers.get("valuation", {}).get("score", "N/A"), "Risk/Reward asymmetry"),
        ("Forensic Feedback (L7)", 100 - layers.get("forensic", {}).get("penalty", 0), "Feedback loop & Penalties"),
    ]

    for label, score, desc in layer_configs:
        try:
            s_val = float(score) if score is not None and score != "N/A" else 0
            s_color = "#22c55e" if s_val >= 75 else "#f59e0b" if s_val >= 40 else "#ef4444"
        except:
            s_color = "#64748b"
        
        layer_rows += f"""
        <tr>
            <td style="padding:10px;border-bottom:1px solid #f1f5f9;font-size:13px;color:#0f172a"><b>{label}</b><br/><span style="font-size:11px;color:#94a3b8">{desc}</span></td>
            <td style="padding:10px;border-bottom:1px solid #f1f5f9;text-align:right;font-weight:700;color:{s_color}">{score}</td>
        </tr>"""

    return f"""
    <html>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:650px;margin:0 auto;padding:20px;background:#f1f5f9">
        <div style="background:white;border-radius:16px;padding:32px;box-shadow:0 4px 6px -1px rgba(0,0,0,0.1),0 2px 4px -1px rgba(0,0,0,0.06);border-top:8px solid {score_color}">
            
            <div style="text-align:right;font-size:11px;color:#94a3b8;margin-bottom:10px;text-transform:uppercase;letter-spacing:0.1em">
                AAE V3 Forensic Intelligence
            </div>

            <h1 style="margin:0 0 4px;font-size:28px;color:#0f172a">{symbol} Institutional Review</h1>
            <p style="margin:0 0 24px;color:#64748b;font-size:14px">Sector: {sector} | Date: {date.today().strftime('%B %d, %Y')}</p>

            <div style="display:flex;align-items:center;background:#f8fafc;padding:20px;border-radius:12px;margin-bottom:28px">
                <div style="flex:1">
                    <div style="font-size:12px;color:#64748b;text-transform:uppercase;font-weight:700">Master Alpha Score</div>
                    <div style="font-size:48px;font-weight:800;color:{score_color}">{master_score}<span style="font-size:20px;color:#94a3b8">/100</span></div>
                </div>
                <div style="flex:1;text-align:right">
                    <div style="font-size:12px;color:#64748b;text-transform:uppercase;font-weight:700">Market Status</div>
                    <div style="font-size:18px;font-weight:700;color:{'#22c55e' if market_confirmation == 'CONFIRMED' else '#f59e0b'}">{market_confirmation}</div>
                </div>
            </div>

            <p style="color:#334155;line-height:1.6">Hi {client_name},</p>
            <p style="color:#334155;line-height:1.6">Our 8-layer **Amritkaal Alpha Engine (AAE)** has completed a forensic deep-dive into <b>{symbol}</b>. Below is the multi-layered institutional scorecard breakdown:</p>

            <h3 style="color:#0f172a;border-bottom:2px solid #f1f5f9;padding-bottom:8px;margin-top:24px">Institutional Layer Breakdown</h3>
            <table style="width:100%;border-collapse:collapse;margin:16px 0">
                <thead>
                    <tr style="background:#f8fafc">
                        <th style="padding:10px;text-align:left;font-size:12px;color:#64748b;text-transform:uppercase">Intelligence Layer</th>
                        <th style="padding:10px;text-align:right;font-size:12px;color:#64748b;text-transform:uppercase">Conviction</th>
                    </tr>
                </thead>
                <tbody>
                    {layer_rows}
                </tbody>
            </table>

            <h3 style="color:#0f172a;border-bottom:2px solid #f1f5f9;padding-bottom:8px;margin-top:32px">Key Drivers & Inflections</h3>
            <ul style="padding-left:20px;margin:16px 0">
                {reasons_html}
            </ul>

            {f'''
            <div style="background:#0f172a;color:#f8fafc;padding:24px;border-radius:12px;margin:32px 0">
                <h3 style="margin:0 0 12px;color:#38bdf8;font-size:14px;text-transform:uppercase;letter-spacing:0.05em">Layer 8: Forensic Stress Test (Debate)</h3>
                <div style="display:flex;margin-bottom:16px;border-bottom:1px solid #1e293b;padding-bottom:12px">
                    <div style="flex:1">
                        <span style="font-size:11px;color:#94a3b8;text-transform:uppercase">AI Conviction</span>
                        <div style="font-size:24px;font-weight:700;color:#f8fafc">{debate_conviction}/100</div>
                    </div>
                    <div style="flex:2;text-align:right">
                        <span style="font-size:11px;color:#ef4444;text-transform:uppercase">Critical Risk</span>
                        <div style="font-size:14px;font-weight:700;color:#fca5a5">{risk_summary}</div>
                    </div>
                </div>
                <p style="margin:0;font-size:15px;line-height:1.7;font-style:italic;color:#e2e8f0">"{result.get('debate_summary', 'Forensic stress test complete.')}"</p>
            </div>
            ''' if master_score > 70 else ''}

            <div style="background:#eff6ff;padding:20px;border-radius:12px;border:1px solid #bfdbfe">
                <h4 style="margin:0 0 10px;color:#1e40af;font-size:13px;text-transform:uppercase">Understanding Your Report</h4>
                <div style="font-size:13px;color:#1e3a8a;line-height:1.5">
                    <p style="margin:0 0 8px"><b>Structural Delta</b>: Measures if the company's fundamentals are actually improving (margins, growth) or if it's just price momentum.</p>
                    <p style="margin:0 0 8px"><b>Governance (L0)</b>: A pass/fail filter. We look for pledges, high debt, or promoter exits before recommending.</p>
                    <p style="margin:0"><b>Ownership</b>: Tracks the "Big Hands" (FII/DII). We only want to be where institutions are currently accumulating.</p>
                </div>
            </div>

            <div style="margin-top:32px;text-align:center">
                <a href="{FRONTEND_URL}/watchlist" style="background:#0f172a;color:white;padding:12px 24px;text-decoration:none;border-radius:8px;font-weight:700;display:inline-block">Open Digital Twin Dashboard</a>
            </div>

            <hr style="border:none;border-top:1px solid #e2e8f0;margin:40px 0 20px">
            <p style="font-size:11px;color:#94a3b8;text-align:center;line-height:1.5">
                DISCLAIMER: This is a quantitative forensic report generated by MRI AAE V3. It is not financial advice.
            </p>
        </div>
    </body>
    </html>
    """


def send_aae_report_email(recipient_email: str, client_name: str, result: dict) -> bool:
    """
    Send an AAE Forensic Report email.
    """
    symbol = result.get("symbol", "UNKNOWN")
    master_score = result.get("master_score", 0)
    subject = f"AAE Forensic Review: {symbol} | Master Alpha {master_score}/100"
    html_body = build_aae_report_email_html(client_name, result)
    return send_email_custom(recipient_email=recipient_email, subject=subject, html_body=html_body)


def build_perx_report_email_html(client_name: str, report: dict) -> str:

    """Build HTML email body for a PERX institutional report."""
    header = report.get("header", {})
    summary = report.get("executive_summary", "")
    narrative = report.get("narrative_transition", {})
    lifecycle = report.get("lifecycle", {})
    verdict = report.get("final_institutional_verdict", "")
    engine_outputs = report.get("engine_outputs", {})
    forensic = report.get("institutional_forensic_review", {})

    symbol = header.get("symbol") or report.get("symbol", "UNKNOWN")
    company_name = header.get("company_name") or report.get("company_name") or symbol
    perx_score = header.get("perx_score", "N/A")
    lifecycle_phase = header.get("lifecycle_phase", "UNKNOWN")
    sector = header.get("sector", "UNKNOWN")
    report_timestamp = header.get("report_timestamp", date.today().isoformat())

    perx_color = "#22c55e" if float(perx_score or 0) >= 75 else "#f59e0b" if float(perx_score or 0) >= 60 else "#ef4444"
    mri = engine_outputs.get("mri", {})
    qif = engine_outputs.get("qif", {})
    stee = engine_outputs.get("stee", {})
    fragility = engine_outputs.get("fragility", {})

    forensic_block = ""
    if forensic and not forensic.get("unavailable"):
        forensic_verdict = forensic.get("verdict", {})
        forensic_block = f"""
            <div style="background:#f8fafc;border-radius:12px;padding:16px;margin:16px 0">
                <h3 style="margin:0 0 8px 0;color:#334155">Institutional Forensic Review</h3>
                <p style="margin:0 0 10px;color:#475569;line-height:1.6">{forensic.get('guidance_vs_reality', 'No forensic summary available.')}</p>
                <p style="margin:0;color:#0f172a;font-weight:600">
                    Verdict: {forensic_verdict.get('buy_recommendation', 'UNDER REVIEW')} | Score: {forensic_verdict.get('score', 'N/A')}/10
                </p>
            </div>
        """
    elif forensic:
        forensic_block = f"""
            <div style="background:#fff7ed;border-radius:12px;padding:16px;margin:16px 0;border:1px solid #fed7aa">
                <h3 style="margin:0 0 8px 0;color:#9a3412">Institutional Forensic Review</h3>
                <p style="margin:0;color:#9a3412;line-height:1.6">{forensic.get('message', 'Forensic review not available for this report.')}</p>
            </div>
        """

    return f"""
    <html>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:700px;margin:0 auto;padding:20px;background:#f8fafc">
        <div style="background:white;border-radius:16px;padding:28px;box-shadow:0 1px 3px rgba(0,0,0,0.08)">
            <div style="border-left:6px solid {perx_color};padding-left:16px;margin-bottom:20px">
                <div style="font-size:12px;color:#64748b;font-weight:700;letter-spacing:0.04em">PERX INSTITUTIONAL REPORT</div>
                <h1 style="margin:6px 0 4px;font-size:28px;color:#0f172a">{company_name}</h1>
                <p style="margin:0;color:#475569">{symbol} | {sector} | Generated {report_timestamp}</p>
            </div>

            <div style="display:inline-block;padding:8px 16px;border-radius:999px;background:{perx_color};color:white;font-weight:700;margin-bottom:18px">
                PERX {perx_score}/100 | {lifecycle_phase}
            </div>

            <p style="color:#334155;line-height:1.7">Hi {client_name},</p>
            <p style="color:#64748b;font-size:12px;font-style:italic">This report was automatically generated following your institutional scan.</p>
            <p style="color:#334155;line-height:1.7">{summary}</p>

            <div style="background:#f8fafc;border-radius:12px;padding:16px;margin:16px 0">
                <h3 style="margin:0 0 10px;color:#334155">Narrative Transition</h3>
                <p style="margin:0 0 8px;color:#475569"><b>Previous:</b> {narrative.get('previous_market_perception', 'N/A')}</p>
                <p style="margin:0 0 8px;color:#475569"><b>Emerging:</b> {narrative.get('emerging_market_perception', 'N/A')}</p>
                <p style="margin:0;color:#475569;line-height:1.6">{narrative.get('why_this_matters', '')}</p>
            </div>

            <h3 style="margin:24px 0 10px;color:#0f172a">Engine Snapshot</h3>
            <table style="width:100%;border-collapse:collapse;font-size:14px">
                <tr style="background:#f1f5f9">
                    <th style="padding:10px;text-align:left">Layer</th>
                    <th style="padding:10px;text-align:left">Signal</th>
                </tr>
                <tr><td style="padding:10px;border-bottom:1px solid #e2e8f0">MRI</td><td style="padding:10px;border-bottom:1px solid #e2e8f0">Score {mri.get('total_score', 'N/A')}/100 | Breakout {mri.get('breakout_structure', 'N/A')} | RS {mri.get('relative_strength', 'N/A')}</td></tr>
                <tr><td style="padding:10px;border-bottom:1px solid #e2e8f0">STEE</td><td style="padding:10px;border-bottom:1px solid #e2e8f0">Setup {stee.get('setup_quality_score', 'N/A')} | Breakout Ready {stee.get('breakout_ready', 'N/A')}</td></tr>
                <tr><td style="padding:10px;border-bottom:1px solid #e2e8f0">QIF</td><td style="padding:10px;border-bottom:1px solid #e2e8f0">Score {qif.get('score', 'N/A')}/100 | Category {qif.get('category', 'N/A')}</td></tr>
                <tr><td style="padding:10px;border-bottom:1px solid #e2e8f0">Fragility</td><td style="padding:10px;border-bottom:1px solid #e2e8f0">Level {fragility.get('level', 'N/A')} | {fragility.get('summary', 'No summary available.')}</td></tr>
                <tr><td style="padding:10px;border-bottom:1px solid #e2e8f0">Lifecycle</td><td style="padding:10px;border-bottom:1px solid #e2e8f0">{lifecycle.get('stage', lifecycle_phase)} | Narrative Intensity {lifecycle.get('narrative_intensity', 'N/A')}</td></tr>
            </table>

            {forensic_block}

            <div style="background:#ecfeff;border-radius:12px;padding:16px;margin:18px 0;border:1px solid #a5f3fc">
                <h3 style="margin:0 0 8px;color:#155e75">Final Institutional Verdict</h3>
                <p style="margin:0;color:#164e63;line-height:1.7">{verdict}</p>
            </div>

            <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0">
            <p style="font-size:12px;color:#94a3b8;text-align:center">
                PERX is an institutional intelligence layer built on MRI, QIF, STEE, and forensic review. It is not a trading instruction.
            </p>
        </div>
    </body>
    </html>
    """


def send_perx_report_email(recipient_email: str, client_name: str, report: dict) -> bool:
    """Send a PERX institutional report email using the shared SES path."""
    header = report.get("header", {})
    symbol = header.get("symbol") or report.get("symbol", "UNKNOWN")
    company_name = header.get("company_name") or report.get("company_name") or symbol
    perx_score = header.get("perx_score", "N/A")
    subject = f"PERX Report: {company_name} ({symbol}) | {perx_score}/100"
    html_body = build_perx_report_email_html(client_name, report)
    return send_email_custom(recipient_email=recipient_email, subject=subject, html_body=html_body)


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

    def get_val(item, key, index):
        if isinstance(item, dict): return item.get(key)
        if isinstance(item, (list, tuple)):
            return item[index] if len(item) > index else None
        return None

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
    
    regime = get_val(regime_row, "classification", 0)
    latest_date = get_val(regime_row, "date", 1)

    # 2. Get all active clients
    cur.execute("SELECT id, email, name FROM clients WHERE is_active = true")
    active_clients = cur.fetchall()

    if not active_clients:
        logger.info("No active clients. Nothing to email.")
        conn.close()
        return 0

    sent_count = 0
    for client in active_clients:
        client_id = str(get_val(client, "id", 0))
        email = get_val(client, "email", 1)
        name = get_val(client, "name", 2) or "Investor"

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


def send_stee_signal_emails():
    """Send STEE-specific swing trade signals to active clients."""
    conn = get_connection()
    cur = conn.cursor()

    if not aws_credentials_present():
        logger.error("❌ AWS credentials missing for STEE emails.")
        conn.close()
        return 0

    try:
        ses_region = resolve_ses_region()
        ses = get_ses_client(ses_region)

        def get_val(item, key, index):
            if isinstance(item, dict): return item.get(key)
            if isinstance(item, (list, tuple)):
                return item[index] if len(item) > index else None
            return None

        # 1. Get Regime
        cur.execute("SELECT classification, date FROM market_regime ORDER BY date DESC LIMIT 1")
        reg_row = cur.fetchone()
        if not reg_row: return 0
        regime = get_val(reg_row, "classification", 0)
        latest_date = get_val(reg_row, "date", 1)

        # 2. Get active clients
        cur.execute("SELECT id, email, name FROM clients WHERE is_active = true")
        clients = cur.fetchall()

        sent_count = 0
        for client in clients:
            client_id = str(get_val(client, "id", 0))
            email = get_val(client, "email", 1)
            name = get_val(client, "name", 2) or "Investor"

            # 3. Fetch new STEE trades for today + AAE Score
            cur.execute("""
                SELECT st.symbol, st.entry_price, st.stop_loss, st.quantity, st.risk_amount,
                       ar.master_score as aae_score
                FROM swing_trades st
                LEFT JOIN aae_results_snapshot ar ON st.symbol = ar.symbol
                WHERE st.client_id = %s AND st.entry_date = %s AND st.status = 'OPEN'
            """, (client_id, latest_date))
            trades = cur.fetchall()

            if not trades:
                continue

            subject = f"🚀 STEE Trade Alert: {len(trades)} New Breakouts — {regime} Market"
            html_body = build_stee_signal_email_html(name, trades, regime)

            try:
                ses.send_email(
                    Source=SENDER_EMAIL,
                    Destination={"ToAddresses": [email]},
                    Message={
                        "Subject": {"Data": subject, "Charset": "UTF-8"},
                        "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
                    },
                )
                sent_count += 1
                logger.info(f"  🚀 STEE Email sent to {email}")
            except Exception as e:
                logger.error(f"  ❌ Failed to send STEE email to {email}: {e}")

        conn.commit()
        return sent_count
    finally:
        conn.close()


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

def send_portfolio_review(email: str, name: str, results: dict):
    if not email or not aws_credentials_present():
        return False
        
    try:
        ses_region = resolve_ses_region()
        ses = get_ses_client(ses_region)
        
        subject = f"MRI Portfolio Regrade Complete"
        html_body = f"""
        <html>
        <body style="font-family:sans-serif;max-width:600px;margin:auto;padding:20px;color:#333">
            <h2 style="color:#111827">📊 MRI Portfolio Regrade</h2>
            <p>Hi {name or 'User'},</p>
            <p>Your portfolio has been manually regraded. The new risk score is <b>{results.get('risk_level', 'UNKNOWN')}</b>.</p>
            <p>Log in to your dashboard to see the latest trend grades for your stocks.</p>
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
        logger.info(f"✅ Portfolio review report sent to {email}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send portfolio review email: {e}")
        return False


def send_alert_email(subject: str, message_html: str):
    """Generic alert email for pipeline failures or data quality warnings."""
    return send_email_custom(SENDER_EMAIL, f"MRI ALERT: {subject}", message_html)

def send_email_custom(recipient_email: str, subject: str, html_body: str):
    """Send a custom HTML email to a specific recipient."""
    if not recipient_email or not SENDER_EMAIL or not aws_credentials_present():
        logger.warning(f"Email disabled: recipient={recipient_email}, sender={SENDER_EMAIL}")
        return False
        
    try:
        ses_region = resolve_ses_region()
        ses = get_ses_client(ses_region)
        
        ses.send_email(
            Source=SENDER_EMAIL,
            Destination={"ToAddresses": [recipient_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
            },
        )
        logger.info(f"✅ Custom email sent to {recipient_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send custom email to {recipient_email}: {e}")
        return False


if __name__ == "__main__":
    send_signal_emails()
    send_stee_signal_emails()
