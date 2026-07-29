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
# ConvictionEngine (June 16): narrative timeline-based credibility scoring
# powers the GuidanceCheck report email. Lazy-imported to avoid a circular
# import (engine_guidance does not import engine_core).
def _narrative_scorer():
    from engine_guidance.narrative_credibility_scorer import NarrativeCredibilityScorer
    return NarrativeCredibilityScorer()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SENDER_EMAIL = os.getenv("SES_SENDER_EMAIL", "sales@goalsgap.in")
FRONTEND_URL = os.getenv("FRONTEND_URL", os.getenv("PUBLIC_FRONTEND_URL", "https://mri-frontend.onrender.com")).rstrip("/")


def get_connection():
    """Get DB connection with RealDictCursor using shared config (supports DATABASE_URL)."""
    conn = _get_raw_connection()
    conn.cursor_factory = RealDictCursor
    return conn


def build_signal_email_html(client_name, signals, regime, holdings=None, watchlist=None, hof_debuts=None, shadow_debuts=None):
    """Build HTML email body for daily signal digest. Includes HoF/Shadow debut alerts."""
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

    # 🏛️ Hall of Fame Debuts — first 75+ score TODAY
    if hof_debuts:
        html += """
            <h2 style="color:#f59e0b;font-size:16px;margin:24px 0 8px">🏛️ Hall of Fame — First 75+ Score Today</h2>
            <p style="font-size:12px;color:#6b7280;margin:0 0 8px">These stocks crossed the 75 MRI score threshold for the <b>first time today</b>. The automated pipeline may have filtered them out due to regime/sector/position limits — evaluate manually.</p>
            <table style="width:100%;border-collapse:collapse;font-size:13px">
                <tr style="background:#fffbeb">
                    <th style="padding:8px;text-align:left">Symbol</th>
                    <th style="padding:8px;text-align:left">Entry Score</th>
                    <th style="padding:8px;text-align:left">Entry Price</th>
                    <th style="padding:8px;text-align:left">Current Price</th>
                </tr>"""
        for h in hof_debuts:
            sym = h['symbol'] if isinstance(h, dict) else h[0]
            entry_score = h['entry_score'] if isinstance(h, dict) else h[2]
            entry_price = h['entry_price'] if isinstance(h, dict) else h[1]
            latest_price = h['latest_price'] if isinstance(h, dict) else h[3]
            html += f"""
                <tr>
                    <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:600">{sym}</td>
                    <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:700;color:#f59e0b">{entry_score}/100</td>
                    <td style="padding:8px;border-bottom:1px solid #e5e7eb">₹{entry_price:,.2f}</td>
                    <td style="padding:8px;border-bottom:1px solid #e5e7eb">₹{latest_price:,.2f}</td>
                </tr>"""
        html += "</table>"

    # 🕵️ Strategy Shadow Debuts — first Top 10 appearance TODAY
    if shadow_debuts:
        html += """
            <h2 style="color:#8b5cf6;font-size:16px;margin:24px 0 8px">🕵️ Strategy Shadow — New Top 10 Entry Today</h2>
            <p style="font-size:12px;color:#6b7280;margin:0 0 8px">These stocks entered the <b>Top 10 MRI scorers</b> for the first time today. The Shadow Tracker ignores regime filters — these are pure momentum leaders worth watching.</p>
            <table style="width:100%;border-collapse:collapse;font-size:13px">
                <tr style="background:#f5f3ff">
                    <th style="padding:8px;text-align:left">Symbol</th>
                    <th style="padding:8px;text-align:left">Entry Price</th>
                    <th style="padding:8px;text-align:left">Current Price</th>
                </tr>"""
        for s in shadow_debuts:
            sym = s['symbol'] if isinstance(s, dict) else s[0]
            entry_price = s['entry_price'] if isinstance(s, dict) else s[1]
            latest_price = s['latest_price'] if isinstance(s, dict) else s[2]
            html += f"""
                <tr>
                    <td style="padding:8px;border-bottom:1px solid #e5e7eb;font-weight:600">{sym}</td>
                    <td style="padding:8px;border-bottom:1px solid #e5e7eb">₹{entry_price:,.2f}</td>
                    <td style="padding:8px;border-bottom:1px solid #e5e7eb">₹{latest_price:,.2f}</td>
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
    
    # Data quality warning (if engine layers have insufficient data)
    dq = result.get("data_quality", {})
    dq_warning = dq.get("warning")
    if dq_warning:
        dq_warning_html = f"""<div style="background:#fef3c7;border-radius:12px;padding:16px;margin:18px 0;border:1px solid #fde68a">
            <h3 style="margin:0 0 8px;color:#92400e;font-size:13px">Data Quality Warning</h3>
            <p style="margin:0;font-size:12px;color:#78350f">{dq_warning}</p>
        </div>"""
    else:
        dq_warning_html = ""

    # Layer Breakdown HTML
    layer_rows = ""
    narrative_source = layers.get("narrative", {}).get("source", "SYNTHETIC_PROXY")
    narrative_label = f"Narrative (L4) <span style='font-size:9px;color:#94a3b8;background:#f1f5f9;padding:2px 4px;border-radius:4px'>{narrative_source}</span>"
    
    layer_configs = [
        ("Governance (L0)", layers.get("governance", {}).get("risk_score", "N/A"), "Integrity & Compliance check"),
        ("Structural Delta (L1&2)", layers.get("structural_delta", {}).get("score", "N/A"), "Earnings & Margin inflection"),
        ("Ownership (L3)", layers.get("ownership", {}).get("score", "N/A"), "FII/DII flow trajectory"),
        (narrative_label, layers.get("narrative", {}).get("score", "N/A"), "Market sentiment & Themes"),
        ("Market Confirmation (L5)", layers.get("market", {}).get("score", "N/A"), "Price & Volume leadership"),
        ("Valuation (L6)", layers.get("valuation", {}).get("score", "N/A"), "Risk/Reward asymmetry"),
        ("Forensic Feedback (L7)", None, "Feedback loop & Penalties"),
    ]

    # Count how many layers actually have real data (not N/A / missing)
    real_layers = 0
    for label, score, desc in layer_configs:
        try:
            s_val = float(score)
            real_layers += 1
        except (ValueError, TypeError):
            pass

    # L7 (Forensic) only displays a score if at least 2 other layers have data
    forensic_raw = layers.get("forensic", {})
    if real_layers >= 2 and forensic_raw:
        forensic_score = 100 - forensic_raw.get("penalty", 0)
    else:
        forensic_score = "N/A"

    for label, score, desc in layer_configs:
        # Use forensic_score for L7 instead of the raw calc
        display_score = forensic_score if "L7" in label else score
        try:
            s_val = float(display_score) if display_score is not None and display_score != "N/A" else 0
            s_color = "#22c55e" if s_val >= 75 else "#f59e0b" if s_val >= 40 else "#ef4444"
        except:
            s_color = "#64748b"
        
        layer_rows += f"""
        <tr>
            <td style="padding:10px;border-bottom:1px solid #f1f5f9;font-size:13px;color:#0f172a"><b>{label}</b><br/><span style="font-size:11px;color:#94a3b8">{desc}</span></td>
            <td style="padding:10px;border-bottom:1px solid #f1f5f9;text-align:right;font-weight:700;color:{s_color}">{display_score}</td>
        </tr>"""

    # Identify the "Why Insufficient history" logic for the email
    processed_reasons = []
    for r in reasons:
        if "Trend Confirmation Pending" in r:
            processed_reasons.append(f"<b>{r}</b>: AAE has successfully captured the current institutional state, but requires one more quarter to establish a directional trend (e.g., are promoters buying or selling?).")
        elif "No Ownership Data" in r:
            processed_reasons.append(f"<b>{r}</b>: We are currently awaiting the next exchange filing for this symbol to populate Layer 3.")
        else:
            processed_reasons.append(r)

    div_penalty = result.get("divergence_penalty", 0)
    if div_penalty > 0:
        processed_reasons.append(f"<b style='color:#ef4444'>Narrative Divergence Penalty (-{div_penalty} pts)</b>: Management tone is significantly more bullish than actual financial inflections suggest.")

    reasons_html = "".join([f"<li style='margin-bottom:8px;color:#334155'>{r}</li>" for r in processed_reasons])

    bear_case = result.get("bear_case", "Analysis pending background scan.")
    bull_case = result.get("bull_case", "Analysis pending background scan.")

    return f"""
    <html>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:650px;margin:0 auto;padding:20px;background:#f1f5f9">
        <div style="background:white;border-radius:16px;padding:32px;box-shadow:0 4px 6px -1px rgba(0,0,0,0.1),0 2px 4px -1px rgba(0,0,0,0.06);border-top:8px solid {score_color}">
            
            <div style="text-align:right;font-size:11px;color:#94a3b8;margin-bottom:10px;text-transform:uppercase;letter-spacing:0.1em">
                AAE V3 10-Layer Institutional Intelligence
            </div>

            <h1 style="margin:0 0 4px;font-size:28px;color:#0f172a">{symbol} 10-Layer Institutional Forensic Audit</h1>
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

            {dq_warning_html}

            <p style="color:#334155;line-height:1.6">Hi {client_name},</p>
            <p style="color:#334155;line-height:1.6">Our 10-layer **Amritkaal Alpha Engine (AAE)** has completed a forensic deep-dive into <b>{symbol}</b>. Below is the multi-perspective institutional breakdown:</p>

            <h3 style="color:#0f172a;border-bottom:2px solid #f1f5f9;padding-bottom:8px;margin-top:24px">Institutional Layer Breakdown (L0 - L7)</h3>
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
            <div style="margin:12px 0;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.05em">
                <b>Layer 4 Source:</b> {narrative_source.replace('_', ' ')}
            </div>
            <ul style="padding-left:20px;margin:16px 0">
                {reasons_html}
            </ul>

            <div style="margin-top:32px">
                <h3 style="color:#0f172a;border-bottom:2px solid #f1f5f9;padding-bottom:8px">Institutional Stress Test (Layers 9 & 10)</h3>
                <div style="display:grid;grid-template-columns:1fr;gap:20px;margin-top:16px">
                    <div style="background:#fff1f2;border:1px solid #fecaca;padding:20px;border-radius:12px">
                        <div style="font-size:11px;color:#e11d48;font-weight:800;text-transform:uppercase;margin-bottom:8px">🐻 Layer 9: Bear Agent (Forensic Short)</div>
                        <p style="font-size:13px;color:#4b5563;line-height:1.6;margin:0;white-space:pre-wrap">{bear_case}</p>
                    </div>
                    <div style="background:#f0fdf4;border:1px solid #bbf7d0;padding:20px;border-radius:12px">
                        <div style="font-size:11px;color:#16a34a;font-weight:800;text-transform:uppercase;margin-bottom:8px">🐂 Layer 10: Bull Agent (High Conviction)</div>
                        <p style="font-size:13px;color:#4b5563;line-height:1.6;margin:0;white-space:pre-wrap">{bull_case}</p>
                    </div>
                </div>
            </div>

            <div style="background:#eff6ff;padding:20px;border-radius:12px;border:1px solid #bfdbfe;margin-top:32px">
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
    subject = f"10-Layer Forensic Audit: {symbol} | Master Alpha {master_score}/100"
    html_body = build_aae_report_email_html(client_name, result)
    return send_email_custom(recipient_email=recipient_email, subject=subject, html_body=html_body)


def _build_perx_email_investor_context(inv_ctx: dict) -> str:
    """Build the investor context HTML block for PERX email."""
    if not inv_ctx:
        return ""
    
    inv_grade = inv_ctx.get("investor_grade", {})
    grade = inv_grade.get("grade", "N/A")
    grade_summary = inv_grade.get("summary", "")
    grade_color = "#22c55e" if grade == "A" else "#f59e0b" if grade == "B" else "#ef4444"
    
    valuation = inv_ctx.get("valuation", {})
    earnings = inv_ctx.get("earnings_momentum", {})
    ownership = inv_ctx.get("ownership", {})
    liquidity = inv_ctx.get("liquidity", {})
    peg = inv_ctx.get("peg_ratio", {})
    ev = inv_ctx.get("ev_ebitda", {})
    inst = inv_ctx.get("institutional_flow", {})
    analogs = inv_ctx.get("historical_analogs", {})
    catalyst = inv_ctx.get("catalyst_questions", [])
    pre_mortem = inv_ctx.get("pre_mortem", {})
    risks = pre_mortem.get("risks", [])

    # Grade badge
    # Build extra table rows for PEG, EV/EBITDA, Institutional Flow
    peg_row = ''
    if peg.get('peg_ratio'):
        peg_row = f'<tr><td style="padding:8px;border-bottom:1px solid #e2e8f0"><b>PEG Ratio</b></td>\n'
        peg_row += f'    <td style="padding:8px;border-bottom:1px solid #e2e8f0">{peg["peg_ratio"]}x</td>\n'
        peg_row += f'    <td style="padding:8px;border-bottom:1px solid #e2e8f0;color:#475569">EPS Growth: {peg.get("eps_growth_pct", "N/A")}% | {peg.get("verdict", "")}</td>\n'
        peg_row += '</tr>'

    ev_row = ''
    if ev.get('ev_ebitda'):
        ev_row = f'<tr><td style="padding:8px;border-bottom:1px solid #e2e8f0"><b>EV/EBITDA</b></td>\n'
        ev_row += f'    <td style="padding:8px;border-bottom:1px solid #e2e8f0">{ev["ev_ebitda"]}x</td>\n'
        ev_row += f'    <td style="padding:8px;border-bottom:1px solid #e2e8f0;color:#475569">Net Debt/EBITDA: {ev.get("net_debt_ebitda", "N/A")}x | {ev.get("verdict", "")}</td>\n'
        ev_row += '</tr>'

    inst_row = ''
    if inst.get('fii_holding_pct') or inst.get('dii_holding_pct'):
        fii_label = inst.get('fii_trend', str(inst.get('fii_holding_pct', 'N/A')))
        dii_label = inst.get('dii_trend', str(inst.get('dii_holding_pct', 'N/A')))
        inst_row = f'<tr><td style="padding:8px;border-bottom:1px solid #e2e8f0"><b>Inst. Flow</b></td>\n'
        inst_row += f'    <td style="padding:8px;border-bottom:1px solid #e2e8f0">FII {fii_label}</td>\n'
        inst_row += f'    <td style="padding:8px;border-bottom:1px solid #e2e8f0;color:#475569">DII {dii_label} | {inst.get("verdict", "")}</td>\n'
        inst_row += '</tr>'

    html = f"""
    <div style="background:#f8fafc;border-radius:12px;padding:16px;margin:18px 0;border-top:4px solid {grade_color}">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
            <div style="font-size:28px;font-weight:800;color:{grade_color}">Grade {grade}</div>
            <div style="font-size:12px;color:#64748b;line-height:1.5">{grade_summary}</div>
        </div>
    
        <table style="width:100%;border-collapse:collapse;font-size:13px">
            <tr style="background:#f1f5f9">
                <th style="padding:8px;text-align:left">Factor</th>
                <th style="padding:8px;text-align:left">Metric</th>
                <th style="padding:8px;text-align:left">Detail</th>
            </tr>
            <tr><td style="padding:8px;border-bottom:1px solid #e2e8f0"><b>Valuation</b></td>
                <td style="padding:8px;border-bottom:1px solid #e2e8f0">P/E {valuation.get('pe_ratio', 'N/A')}x</td>
                <td style="padding:8px;border-bottom:1px solid #e2e8f0;color:#475569">Sector median {valuation.get('sector_median_pe', 'N/A')}x | {valuation.get('verdict', '')}</td>
            </tr>
            <tr><td style="padding:8px;border-bottom:1px solid #e2e8f0"><b>Earnings</b></td>
                <td style="padding:8px;border-bottom:1px solid #e2e8f0">{earnings.get('acceleration', 'N/A')}</td>
                <td style="padding:8px;border-bottom:1px solid #e2e8f0;color:#475569">Rev {earnings.get('revenue_growth_4q_pct', 'N/A')}% | Profit {earnings.get('profit_growth_4q_pct', 'N/A')}%</td>
            </tr>
            <tr><td style="padding:8px;border-bottom:1px solid #e2e8f0"><b>Ownership</b></td>
                <td style="padding:8px;border-bottom:1px solid #e2e8f0">Promoter {ownership.get('promoter_trend', 'N/A')}</td>
                <td style="padding:8px;border-bottom:1px solid #e2e8f0;color:#475569">Gov Score {ownership.get('governance_score', 'N/A')}/100 | Pledged {ownership.get('pledged_pct', 'N/A')}%</td>
            </tr>
            <tr><td style="padding:8px;border-bottom:1px solid #e2e8f0"><b>Liquidity</b></td>
                <td style="padding:8px;border-bottom:1px solid #e2e8f0">₹{liquidity.get('avg_daily_turnover_cr', 'N/A')}Cr</td>
                <td style="padding:8px;border-bottom:1px solid #e2e8f0;color:#475569">{liquidity.get('verdict', '')}</td>
            </tr>
{peg_row}
{ev_row}
{inst_row}
        </table>
    """

    # Pre-Mortem Risks
    if risks:
        html += """<div style="background:#fef2f2;border-radius:12px;padding:16px;margin:18px 0;border:1px solid #fecaca">
            <h3 style="margin:0 0 10px;color:#991b1b;font-size:13px">⚠️ Thesis Pre-Mortem</h3>"""
        for risk in risks:
            html += f'<p style="margin:4px 0;font-size:12px;color:#b91c1c">• {risk}</p>'
        html += "</div>"

    # Catalyst Questions
    if catalyst:
        html += """<div style="background:#eff6ff;border-radius:12px;padding:16px;margin:18px 0;border:1px solid #bfdbfe">
            <h3 style="margin:0 0 10px;color:#1e40af;font-size:13px">🔍 Catalyst Checklist</h3>
            <p style="margin:0 0 8px;font-size:12px;color:#1e3a8a">What to investigate next to build (or break) the rerating thesis:</p>"""
        for q in catalyst[:4]:
            html += f'<p style="margin:4px 0;font-size:12px;color:#1e40af">→ {q}</p>'
        homework = inv_ctx.get('homework_note', '')
        if homework:
            html += f'<p style="margin:8px 0 0;font-size:11px;color:#64748b;font-style:italic">{homework}</p>'
        html += "</div>"

    # Historical Analogs
    analog_list = analogs.get("analogs", [])
    if analog_list:
        html += """<div style="background:#f5f3ff;border-radius:12px;padding:16px;margin:18px 0;border:1px solid #ddd6fe">
            <h3 style="margin:0 0 10px;color:#5b21b6;font-size:13px">📈 Historical Rerating Analogs</h3>"""
        for a in analog_list[:3]:
            html += f'<p style="margin:4px 0;font-size:12px;color:#4c1d95">{a.get("symbol", "?")} | Score: {a.get("perx_score", "N/A")}/100 | {a.get("date", "")}</p>'
        hw = analogs.get("homework", "")
        if hw:
            html += f'<p style="margin:8px 0 0;font-size:11px;color:#64748b;font-style:italic">{hw}</p>'
        html += "</div>"

    html += "</div>"
    return html


def build_perx_report_email_html(client_name: str, report: dict) -> str:

    """Build HTML email body for a PERX institutional report."""
    header = report.get("header", {})
    summary = report.get("executive_summary", "")
    narrative = report.get("narrative_transition", {})
    lifecycle = report.get("lifecycle", {})
    verdict = report.get("final_institutional_verdict", "")
    engine_outputs = report.get("engine_outputs", {})
    forensic = report.get("institutional_forensic_review", {})
    investor_context = report.get("investor_context", {})

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

            <!-- Investor Context Block -->
            {_build_perx_email_investor_context(investor_context)}

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

    # 2b. Fetch global Hall of Fame & Strategy Shadow debutants (same for all clients)
    cur.execute("""
        SELECT symbol, entry_price, entry_score, latest_price
        FROM public.top_score_tracking
        WHERE first_appeared_date = %s
        ORDER BY entry_score DESC
    """, (latest_date,))
    hof_debuts = cur.fetchall()

    cur.execute("""
        SELECT symbol, entry_price, latest_price
        FROM public.strategy_shadow_portfolio
        WHERE first_entry_date = %s AND is_active = TRUE
        ORDER BY symbol ASC
    """, (latest_date,))
    shadow_debuts = cur.fetchall()

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

        html_body = build_signal_email_html(name, signals, regime, holdings=holdings_scores, watchlist=watchlist_scores, hof_debuts=hof_debuts, shadow_debuts=shadow_debuts)

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


def send_morning_brief():
    """Send a concise morning brief with HoF & Shadow debuts from the latest pipeline run.
    Designed to be triggered manually or via cron before market open (9:00 AM IST).
    Does NOT re-run the pipeline — queries existing data only."""
    conn = get_connection()
    cur = conn.cursor()

    if not aws_credentials_present():
        logger.error("❌ AWS credentials missing: cannot send morning brief.")
        cur.close()
        conn.close()
        return 0

    try:
        ses_region = resolve_ses_region()
        ses = get_ses_client(ses_region)
    except Exception as e:
        logger.error(f"❌ SES region misconfigured: {e}")
        cur.close()
        conn.close()
        return 0

    def get_val(item, key, index):
        if isinstance(item, dict): return item.get(key)
        if isinstance(item, (list, tuple)):
            return item[index] if len(item) > index else None
        return None

    # 1. Get current regime
    cur.execute("SELECT classification FROM market_regime ORDER BY date DESC LIMIT 1")
    regime_row = cur.fetchone()
    if not regime_row:
        logger.warning("No regime data — cannot send meaningful morning brief.")
        conn.close()
        return 0
    regime = get_val(regime_row, "classification", 0)

    # 2. Get active clients
    cur.execute("SELECT id, email, name FROM clients WHERE is_active = true")
    active_clients = cur.fetchall()
    if not active_clients:
        logger.info("No active clients.")
        conn.close()
        return 0

    # 3. Fetch HoF debuts (most recent first_appeared_date)
    cur.execute("""
        SELECT t.symbol, t.entry_price, t.entry_score, t.latest_price,
               ss.total_score, ss.condition_breakout_10d
        FROM public.top_score_tracking t
        LEFT JOIN public.stock_scores ss ON t.symbol = ss.symbol
          AND ss.date = (SELECT MAX(date) FROM public.stock_scores)
        WHERE t.first_appeared_date = (SELECT MAX(first_appeared_date) FROM public.top_score_tracking)
        ORDER BY t.entry_score DESC
    """)
    hof_debuts = cur.fetchall()

    # 4. Fetch Shadow debuts (most recent first_entry_date)
    cur.execute("""
        SELECT s.symbol, s.entry_price, s.latest_price,
               ss.total_score, ss.condition_breakout_10d
        FROM public.strategy_shadow_portfolio s
        LEFT JOIN public.stock_scores ss ON s.symbol = ss.symbol
          AND ss.date = (SELECT MAX(date) FROM public.stock_scores)
        WHERE s.first_entry_date = (SELECT MAX(first_entry_date) FROM public.strategy_shadow_portfolio)
          AND s.is_active = TRUE
        ORDER BY s.symbol ASC
    """)
    shadow_debuts = cur.fetchall()

    if not hof_debuts and not shadow_debuts:
        logger.info("No HoF or Shadow debuts in latest pipeline run. Skipping morning brief.")
        conn.close()
        return 0

    # 5. Build HTML
    regime_color = {"BULL": "#22c55e", "BEAR": "#ef4444", "NEUTRAL": "#f59e0b"}.get(regime, "#6b7280")

    hof_rows = ""
    for h in hof_debuts:
        sym = get_val(h, "symbol", 0)
        entry_score = get_val(h, "entry_score", 2) or 0
        entry_price = get_val(h, "entry_price", 1) or 0
        current_score = get_val(h, "total_score", 4) or entry_score
        is_breakout = get_val(h, "condition_breakout_10d", 5)
        tag = "🚀" if is_breakout else ""
        hof_rows += f"""
            <tr>
                <td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;font-weight:600">{sym} {tag}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;font-weight:700;color:#f59e0b">{current_score}/100</td>
                <td style="padding:6px 10px;border-bottom:1px solid #e5e7eb">₹{entry_price:,.2f}</td>
            </tr>"""

    shadow_rows = ""
    for s in shadow_debuts:
        sym = get_val(s, "symbol", 0)
        entry_price = get_val(s, "entry_price", 1) or 0
        current_score = get_val(s, "total_score", 3) or 0
        is_breakout = get_val(s, "condition_breakout_10d", 4)
        tag = "🚀" if is_breakout else ""
        shadow_rows += f"""
            <tr>
                <td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;font-weight:600">{sym} {tag}</td>
                <td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;font-weight:700;color:#8b5cf6">{current_score}/100</td>
                <td style="padding:6px 10px;border-bottom:1px solid #e5e7eb">₹{entry_price:,.2f}</td>
            </tr>"""

    brief_date = date.today().strftime('%A, %B %d, %Y')
    sent_count = 0
    for client in active_clients:
        client_id = str(get_val(client, "id", 0))
        email_addr = get_val(client, "email", 1)
        name = get_val(client, "name", 2) or "Investor"

        # Duplicate prevention
        cur.execute("""
            SELECT id FROM email_log
            WHERE client_id = %s AND date = CURRENT_DATE
              AND email_type = 'MORNING_BRIEF' AND status = 'SENT'
        """, (client_id,))
        if cur.fetchone():
            logger.info(f"  ⏭️ Morning brief already sent to {email_addr} today.")
            continue

        html_body = f"""
        <html>
        <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:560px;margin:0 auto;padding:16px;background:#f9fafb">
            <div style="background:white;border-radius:12px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.1);border-top:4px solid {regime_color}">
                <h1 style="margin:0 0 2px;font-size:18px;color:#111827">🌅 MRI Morning Brief</h1>
                <p style="margin:0 0 12px;color:#6b7280;font-size:12px">{brief_date} · Pre-Market</p>

                <div style="background:{regime_color}15;border-left:4px solid {regime_color};padding:10px 12px;border-radius:4px;margin-bottom:16px">
                    <span style="font-size:11px;color:#6b7280">Market Regime</span>
                    <div style="font-size:16px;font-weight:700;color:{regime_color}">{regime}</div>
                </div>

                <p style="color:#374151;font-size:13px">Hi {name},</p>
                <p style="color:#374151;font-size:13px">Here are the <b>new Hall of Fame and Strategy Shadow entries</b> from the latest pipeline run. The full BUY/SELL digest arrives tonight — this is your pre-market scan.</p>"""

        if hof_debuts:
            html_body += f"""
                <h2 style="color:#f59e0b;font-size:14px;margin:20px 0 6px">🏛️ Hall of Fame — First 75+ Score</h2>
                <p style="font-size:11px;color:#6b7280;margin:0 0 8px">These stocks crossed the 75 MRI threshold for the first time. 🚀 = breakout candle.</p>
                <table style="width:100%;border-collapse:collapse;font-size:12px">
                    <tr style="background:#fffbeb">
                        <th style="padding:6px 10px;text-align:left">Symbol</th>
                        <th style="padding:6px 10px;text-align:left">Score</th>
                        <th style="padding:6px 10px;text-align:left">Entry</th>
                    </tr>
                    {hof_rows}
                </table>"""

        if shadow_debuts:
            html_body += f"""
                <h2 style="color:#8b5cf6;font-size:14px;margin:20px 0 6px">🕵️ Strategy Shadow — New Top 10</h2>
                <p style="font-size:11px;color:#6b7280;margin:0 0 8px">These stocks entered the Top 10 MRI scorers (no regime filter).</p>
                <table style="width:100%;border-collapse:collapse;font-size:12px">
                    <tr style="background:#f5f3ff">
                        <th style="padding:6px 10px;text-align:left">Symbol</th>
                        <th style="padding:6px 10px;text-align:left">Score</th>
                        <th style="padding:6px 10px;text-align:left">Entry</th>
                    </tr>
                    {shadow_rows}
                </table>"""

        html_body += f"""
                <div style="margin-top:16px;padding:10px 12px;background:#f0f9ff;border-radius:8px;border:1px solid #bae6fd">
                    <p style="margin:0;font-size:12px;color:#0369a1">
                        <b>💡 Quick rule:</b> In a <b>BEAR</b> market, only consider 🚀 breakout-tagged stocks.<br>
                        <b>BULL/NEUTRAL:</b> Enter at open if score ≥ 80 and breakout confirmed.<br>
                        Run <code>morning brief</code> in DeepSeek TUI for the full 7-condition checklist.
                    </p>
                </div>

                <hr style="border:none;border-top:1px solid #e5e7eb;margin:18px 0">
                <p style="font-size:10px;color:#9ca3af;text-align:center">
                    MRI Morning Brief · Full digest arrives tonight · Not financial advice
                </p>
            </div>
        </body>
        </html>"""

        subject = f"🌅 MRI Morning Brief: {len(hof_debuts)} HoF + {len(shadow_debuts)} Shadow — {regime}"

        try:
            ses.send_email(
                Source=SENDER_EMAIL,
                Destination={"ToAddresses": [email_addr]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
                },
            )
            status_val = "SENT"
            sent_count += 1
            logger.info(f"  ✅ Morning brief sent to {email_addr}")
        except ClientError as e:
            status_val = "FAILED"
            code = (e.response or {}).get("Error", {}).get("Code", "ClientError")
            msg = (e.response or {}).get("Error", {}).get("Message", str(e))
            logger.error(f"  ❌ Morning brief failed for {email_addr} ({code}): {msg}")
        except Exception as e:
            status_val = "FAILED"
            logger.error(f"  ❌ Morning brief failed for {email_addr}: {str(e)}")

        cur.execute("""
            INSERT INTO email_log (client_id, date, email_type, service, subject, status)
            VALUES (%s, CURRENT_DATE, 'MORNING_BRIEF', 'SES', %s, %s)
        """, (client_id, subject, status_val))

    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"=== Morning Brief Complete: {sent_count}/{len(active_clients)} sent ===")
    return sent_count


# ── GuidanceCheck Report Email ────────────────────────────────────────

def _build_promise_row(item: dict, color: str) -> str:
    """Build a single promise table row. Safe — no backslashes in f-string exprs."""
    ptype = item.get('type', 'OTHER')
    ptext = item.get('promise', '')
    ptarget = item.get('target', '')
    pdeadline = item.get('deadline', '')
    ppromised_in = item.get('promised_in', '')
    pverified_in = item.get('verified_in', '')
    pactual = item.get('actual') or '—'

    target_html = '<span style="margin-right:6px">🎯 <b style="color:#94a3b8">' + ptarget + '</b></span>' if ptarget else ''
    deadline_html = '<span>📅 <b style="color:#94a3b8">' + pdeadline + '</b></span>' if pdeadline else ''
    promised_html = '<span>📣 ' + ppromised_in + '</span>' if ppromised_in else ''
    verified_html = '<span>✅ ' + pverified_in + '</span>' if pverified_in else ''

    return (
        '<tr>'
        '<td style="padding:10px 14px; border-left:3px solid ' + color + '; background:#1a1a2e; vertical-align:top">'
        '<div style="color:#e2e8f0; font-size:0.875rem; margin-bottom:4px">' + ptext + '</div>'
        '<div style="color:#64748b; font-size:0.7rem;">'
        '<span style="background:#1e293b; padding:1px 6px; border-radius:3px; color:#94a3b8; margin-right:5px; font-size:0.65rem">' + ptype + '</span>'
        + target_html + deadline_html + promised_html + verified_html +
        '</div></td>'
        '<td style="padding:10px 14px; background:#1a1a2e; text-align:center; vertical-align:top">'
        '<div style="font-size:0.8rem; color:#e2e8f0">' + pactual + '</div>'
        '</td></tr>'
    )


def _build_pending_row(item: dict, color: str) -> str:
    """Build a pending promise row (shows deadline, not actual)."""
    ptype = item.get('type', 'OTHER')
    ptext = item.get('promise', '')
    pdeadline = item.get('deadline', '')

    deadline_html = ''
    if pdeadline:
        deadline_html = '<span>📅 <b style="color:#94a3b8">' + pdeadline + '</b></span>'

    return (
        '<tr>'
        '<td style="padding:10px 14px; border-left:3px solid ' + color + '; background:#1a1a2e; vertical-align:top">'
        '<div style="color:#e2e8f0; font-size:0.875rem; margin-bottom:4px">' + ptext + '</div>'
        '<div style="color:#64748b; font-size:0.72rem;">'
        '<span style="background:#1e293b; padding:1px 6px; border-radius:3px; color:#94a3b8; margin-right:6px">' + ptype + '</span>'
        + deadline_html +
        '</div></td>'
        '<td style="padding:10px 14px; background:#1a1a2e; text-align:center; vertical-align:top">'
        '<div style="font-size:0.8rem; color:#64748b">—</div>'
        '</td></tr>'
    )


# ── GuidanceCheck email screen-mirror helpers (June 17, 2026) ──────────────
# These three sections are visible on the GuidanceCheck screen
# (frontend/src/GuidanceCheck.tsx) but were missing from the email until now:
# the header metadata chip strip, the intonation "tone monitor" card, and
# the "no verified promises yet" fallback panel. The payload built by
# api/guidance.py::_build_report_payload already contains all required data;
# these helpers just render it for email.

def _build_header_metadata_band(payload: dict) -> str:
    """Header chips strip: transcript count, promises extracted, numerical %,
    dominant guidance type, DIRECTIONAL ONLY chip.

    Mirrors GuidanceCheck.tsx:644-672. Each chip is conditional — absent when
    the corresponding payload field is empty/zero.
    """
    chips = []

    tc = int(payload.get("transcript_count", 0) or 0)
    if tc > 0:
        rng = payload.get("transcript_date_range", {}) or {}
        earliest = rng.get("earliest")
        latest = rng.get("latest")
        date_span = ""
        if earliest and latest:
            date_span = (
                ' <span style="color:#64748b;font-weight:400;margin-left:6px">'
                '· ' + str(earliest) + ' → ' + str(latest) + '</span>'
            )
        chips.append(
            '<span style="background:#1e293b;color:#cbd5e1;padding:4px 10px;'
            'border-radius:14px;font-weight:600;font-size:0.72rem">'
            '📊 ' + str(tc) + ' transcript' + ('s' if tc != 1 else '')
            + ' analyzed' + date_span + '</span>'
        )

    tpe = int(payload.get("total_promises_extracted", 0) or 0)
    if tpe > 0:
        chips.append(
            '<span style="background:#1e293b;color:#cbd5e1;padding:4px 10px;'
            'border-radius:14px;font-weight:600;font-size:0.72rem">'
            + str(tpe) + ' promises extracted</span>'
        )

    num_pct = payload.get("numerical_guidance_pct", 0) or 0
    if num_pct or num_pct == 0:
        bg = '#7f1d1d' if num_pct < 30 else '#451a03' if num_pct < 70 else '#14532d'
        fg = '#fca5a5' if num_pct < 30 else '#fbbf24' if num_pct < 70 else '#4ade80'
        chips.append(
            '<span style="background:' + bg + ';color:' + fg + ';padding:4px 10px;'
            'border-radius:14px;font-weight:600;font-size:0.72rem">'
            + str(round(num_pct, 1)) + '% numerical guidance</span>'
        )

    dom = payload.get("dominant_guidance_type")
    if dom:
        chips.append(
            '<span style="background:#1e293b;color:#94a3b8;padding:4px 10px;'
            'border-radius:14px;font-weight:600;font-size:0.72rem">'
            '🎯 Dominant: ' + str(dom) + '</span>'
        )

    if payload.get("guidance_quality_signal") == "DIRECTIONAL ONLY":
        chips.append(
            '<span style="background:#1e3a8a;color:#60a5fa;padding:4px 10px;'
            'border-radius:14px;font-weight:700;font-size:0.72rem;letter-spacing:0.04em">'
            '📐 DIRECTIONAL ONLY</span>'
        )

    if not chips:
        return ""
    return (
        '<div style="display:flex;flex-wrap:wrap;gap:8px;margin:0 0 16px 0;'
        'font-size:0.72rem;align-items:center">'
        + ''.join(chips) +
        '</div>'
    )


def _build_intonation_email_section(intonation: dict) -> str:
    """Tone monitor card: latest-quarter summary + 9-dimension grid +
    Q-o-Q deltas + 8-quarter trajectory table.

    Mirrors GuidanceCheck.tsx:675-742. Returns '' when no intonation data is
    available so the email is unchanged for symbols without transcripts.
    """
    if not intonation or intonation.get("quarters_observed", 0) < 1:
        return ""
    latest = intonation.get("latest") or {}
    if not latest:
        return ""
    previous = intonation.get("previous") or {}

    DIMS = [
        ("Confidence",        "confidence",        "#4ade80"),
        ("Hedging",           "hedging",           "#fbbf24"),
        ("Aggression",        "aggression",        "#f87171"),
        ("Transparency",      "transparency",      "#60a5fa"),
        ("Optimism",          "optimism",          "#4ade80"),
        ("Pessimism",         "pessimism",         "#94a3b8"),
        ("Accountability",    "accountability",    "#a78bfa"),
        ("Numerical density", "numerical_density", "#22d3ee"),
    ]

    q_label = latest.get("quarter_label", "")
    summary = latest.get("summary", "") or "—"
    headwinds = latest.get("headwinds_named") or []
    tone_shift = bool(intonation.get("tone_shift_detected", False))

    headwinds_html = ""
    if headwinds:
        headwinds_html = (
            '<div style="font-size:0.72rem;color:#94a3b8;margin-top:6px">'
            '<b style="color:#fbbf24">Headwinds named:</b> '
            + ' · '.join(str(h) for h in headwinds) +
            '</div>'
        )

    shift_chip = ""
    if tone_shift:
        shift_chip = (
            '<div style="background:#1e3a8a;color:#60a5fa;padding:4px 10px;'
            'border-radius:12px;font-size:0.7rem;font-weight:700;'
            'letter-spacing:0.04em;white-space:nowrap;margin-left:auto">'
            '🚨 TONE SHIFT</div>'
        )

    dim_rows = ""
    for label, key, color in DIMS:
        v = float(latest.get(key, 0) or 0)
        pct = max(0, min(100, round(v * 100)))
        pv = float(previous.get(key, 0) or 0)
        delta = v - pv
        arrow = ""
        if delta > 0.01:
            arrow = ' <span style="color:' + color + '">↑</span>'
        elif delta < -0.01:
            arrow = ' <span style="color:' + color + '">↓</span>'
        dim_rows += (
            '<tr><td style="padding:3px 0;font-size:0.72rem;color:#94a3b8;'
            'width:42%">' + str(label) + '</td>'
            '<td style="padding:3px 8px;width:18%">'
            '<div style="height:5px;background:#1f2937;border-radius:2px;overflow:hidden">'
            '<div style="height:100%;width:' + str(pct) + '%;background:' + color + '"></div>'
            '</div></td>'
            '<td style="padding:3px 0;font-size:0.72rem;color:' + color + ';'
            'font-weight:700;text-align:right;width:40%">'
            + str(pct) + '%' + arrow + '</td></tr>'
        )

    dim_grid = (
        '<table style="width:100%;border-collapse:collapse;margin-top:12px">'
        + dim_rows + '</table>'
    )

    timeline = intonation.get("timeline", []) or []
    trajectory_html = ""
    if len(timeline) >= 2:
        rows = ""
        max_conf = max(
            (float(t.get("confidence", 0) or 0) for t in timeline), default=1
        ) or 1
        for t in timeline[-8:]:
            ql = t.get("quarter_label", "")
            conf = float(t.get("confidence", 0) or 0)
            hedge = float(t.get("hedging", 0) or 0)
            conf_pct = round(conf * 100)
            hedge_pct = round(hedge * 100)
            bar_pct = round((conf / max_conf) * 100) if max_conf > 0 else 0
            bar_color = "#22c55e" if conf >= 0.7 else "#f59e0b" if conf >= 0.4 else "#ef4444"
            rows += (
                '<tr>'
                '<td style="padding:5px 8px;font-size:0.72rem;color:#94a3b8;'
                'font-weight:600;min-width:50px">' + str(ql) + '</td>'
                '<td style="padding:5px 8px">'
                '<div style="background:#1f2937;border-radius:3px;height:5px;width:100%">'
                '<div style="height:5px;border-radius:3px;background:' + bar_color + ';'
                'width:' + str(bar_pct) + '%"></div></div></td>'
                '<td style="padding:5px 8px;font-size:0.72rem;text-align:right;'
                'white-space:nowrap;color:#4ade80">' + str(conf_pct) + '%</td>'
                '<td style="padding:5px 8px;font-size:0.72rem;text-align:right;'
                'white-space:nowrap;color:#fbbf24">' + str(hedge_pct) + '%</td>'
                '</tr>'
            )
        trajectory_html = (
            '<div style="margin-top:14px;border-top:1px solid #1a2236;padding-top:10px">'
            '<div style="font-size:0.68rem;color:#94a3b8;text-transform:uppercase;'
            'letter-spacing:0.06em;margin-bottom:8px;font-weight:700">'
            'Tone trajectory — confidence over time</div>'
            '<table style="width:100%;border-collapse:collapse"><thead>'
            '<tr style="color:#475569;font-size:0.62rem;text-transform:uppercase;'
            'letter-spacing:0.06em">'
            '<th style="padding:2px 8px;text-align:left">Quarter</th>'
            '<th style="padding:2px 8px;text-align:left">Confidence</th>'
            '<th style="padding:2px 8px;text-align:right">Conf%</th>'
            '<th style="padding:2px 8px;text-align:right">Hedge%</th>'
            '</tr></thead><tbody>' + rows + '</tbody></table></div>'
        )

    return (
        '<div style="background:#0d1421;border:1px solid #1a2236;border-radius:10px;'
        'padding:16px 18px;margin:0 0 16px 0">'
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;'
        'gap:10px;flex-wrap:wrap">'
        '<div style="flex:1;min-width:200px">'
        '<div style="font-size:0.7rem;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.07em;color:#94a3b8">'
        '🎙️ Management Tone — ' + str(q_label) + '</div>'
        '<div style="font-size:0.85rem;color:#cbd5e1;margin-top:4px;line-height:1.5">'
        + summary + '</div>'
        + headwinds_html +
        '</div>'
        + shift_chip +
        '</div>'
        + dim_grid
        + trajectory_html +
        '</div>'
    )


def _build_no_verified_promises_warning(payload: dict) -> str:
    """Fallback panel: when no promises are verified yet, show the
    guidance-quality signal so the reader understands why the email is sparse.

    Mirrors GuidanceCheck.tsx:625-642. No-op when total_verified > 0 or
    there's nothing to explain.
    """
    if payload.get("total_verified", 0) > 0:
        return ""
    total_unable = int(payload.get("total_unable", 0) or 0)
    upcoming_len = len(payload.get("upcoming", []) or [])
    if upcoming_len == 0 and total_unable == 0:
        return ""
    parts = []
    if total_unable > 0 or upcoming_len > 0:
        parts.append(
            '⏳ No verified promises yet — ' + str(total_unable) + ' of ' + str(upcoming_len)
            + " pending couldn't be matched to financials."
        )
    if payload.get("guidance_quality_signal") == "DIRECTIONAL ONLY":
        parts.append(
            '<div style="font-size:0.78rem;color:#fbbf24;margin-top:6px">'
            '⚠️ This management team gives directional / qualitative guidance only — '
            "they don't typically commit to numbers. Verification requires numeric targets."
            '</div>'
        )
    if payload.get("all_future_promises") and payload.get("dominant_guidance_type"):
        parts.append(
            '<div style="font-size:0.78rem;color:#94a3b8;margin-top:4px">'
            'Most-frequent topic: <b style="color:#cbd5e1">'
            + str(payload["dominant_guidance_type"])
            + '</b>. Future quarters will verify as results land.</div>'
        )
    if not parts:
        return ""
    return (
        '<div style="background:#0d1421;border:1px solid #1a2236;border-radius:10px;'
        'padding:14px 18px;margin:0 0 16px 0;color:#94a3b8;font-size:0.85rem">'
        '<div style="font-weight:600;color:#cbd5e1;margin-bottom:6px">'
        + parts[0] + '</div>'
        + ''.join(parts[1:]) +
        '</div>'
    )


def build_guidance_report_email_html(payload: dict) -> str:
    """Build a professional GuidanceCheck report HTML email from a report payload."""
    sym = payload["symbol"]
    achieved = payload.get("achieved", [])
    missed = payload.get("missed", [])
    partial = payload.get("partial", [])
    upcoming = payload.get("upcoming", [])
    total_verified = payload.get("total_verified", 0)
    integrity_signal = payload.get("integrity_signal", "") or ""
    qc = payload.get("quarter_comparison", {}) or {}
    timeline = payload.get("integrity_timeline", {}) or {}
    report_date = payload.get("report_date", str(date.today()))

    # ── ConvictionEngine (June 16): narrative-timeline-based credibility ──
    # Supersedes the old accuracy_pct which only counted ACHIEVED/MISSED/PARTIAL
    # from external-financial verification (51 actionable signals universe-wide).
    # The new scorer reads management's own later statements as the verification
    # source (796 actionable signals, 29.3% of the universe).
    # If the endpoint pre-computed and passed narrative_credibility in payload,
    # reuse it; otherwise compute here.
    nc = payload.get("narrative_credibility")
    if not nc:
        try:
            nc = _narrative_scorer().compute_score(sym)
        except Exception as _e:
            logger.warning(f"Narrative credibility lookup failed for {sym}: {_e}")
            nc = {}
    narr_score = nc.get("score")
    narr_verdict = nc.get("current_verdict") or "WATCHING"
    narr_prev_verdict = nc.get("previous_verdict")
    narr_trend = nc.get("trend") or ""
    narr_lag = nc.get("consecutive_miss_quarters") or 0
    narr_counts = nc.get("counts") or {}
    narr_n_total = nc.get("total_promises") or 0
    narr_n_actionable = nc.get("actionable_promises") or 0
    narr_unverified = nc.get("unverified_count") or 0

    # Backward-compat fallback values (used if narrative scorer unavailable)
    verdict = narr_verdict or payload.get("verdict", "WATCHING")
    trend = narr_trend or (payload.get("credibility") or {}).get("trend", "") or ""
    accuracy = float(narr_score) if narr_score is not None else float(payload.get("accuracy_pct", 0.0) or 0.0)

    # Verdict zone color mapping (matches the UI CredibilityHero)
    _ZONE_BG = {
        'ADD ZONE': '#14532d', 'HOLD ZONE': '#451a03',
        'REDUCE ZONE': '#7f1d1d', 'THESIS BROKEN': '#500724',
        'WATCHING': '#1e293b',
    }
    _ZONE_FG = {
        'ADD ZONE': '#4ade80', 'HOLD ZONE': '#fbbf24',
        'REDUCE ZONE': '#f87171', 'THESIS BROKEN': '#fda4af',
        'WATCHING': '#94a3b8',
    }
    verdict_bg = _ZONE_BG.get(verdict, '#1e293b')
    verdict_color = _ZONE_FG.get(verdict, '#94a3b8')

    # Build row strings
    achieved_rows = "".join(_build_promise_row(p, "#22c55e") for p in achieved)
    missed_rows = "".join(_build_promise_row(p, "#ef4444") for p in missed)
    partial_rows = "".join(_build_promise_row(p, "#f59e0b") for p in partial)
    upcoming_rows = "".join(_build_pending_row(p, "#3b82f6") for p in upcoming[:8])

    upcoming_note = ""
    if len(upcoming) > 8:
        upcoming_note = '<p style="color:#475569; font-size:0.78rem; margin-top:8px">+' + str(len(upcoming) - 8) + ' more upcoming promises not shown</p>'

    # Verified section
    achieved_section = ""
    if achieved:
        p_label = "promise" if len(achieved) == 1 else "promises"
        achieved_section = (
            '<div style="margin-top:16px">'
            '<div style="color:#4ade80; font-size:0.78rem; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; padding:6px 0; border-bottom:1px solid #14532d; margin-bottom:8px">'
            '✅ Kept — ' + str(len(achieved)) + ' ' + p_label + '</div>'
            '<table style="width:100%; border-collapse:collapse; font-size:0.85rem">'
            '<thead><tr style="color:#475569; font-size:0.68rem; text-transform:uppercase; letter-spacing:0.06em">'
            '<th style="padding:4px 14px; text-align:left">Promise</th>'
            '<th style="padding:4px 14px; text-align:center">Actual</th></tr></thead>'
            '<tbody>' + achieved_rows + '</tbody></table></div>'
        )

    missed_section = ""
    if missed:
        p_label = "promise" if len(missed) == 1 else "promises"
        missed_section = (
            '<div style="margin-top:16px">'
            '<div style="color:#ef4444; font-size:0.78rem; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; padding:6px 0; border-bottom:1px solid #450a0a; margin-bottom:8px">'
            '❌ Broken — ' + str(len(missed)) + ' ' + p_label + '</div>'
            '<table style="width:100%; border-collapse:collapse; font-size:0.85rem">'
            '<thead><tr style="color:#475569; font-size:0.68rem; text-transform:uppercase; letter-spacing:0.06em">'
            '<th style="padding:4px 14px; text-align:left">Promise</th>'
            '<th style="padding:4px 14px; text-align:center">Actual</th></tr></thead>'
            '<tbody>' + missed_rows + '</tbody></table></div>'
        )

    partial_section = ""
    if partial:
        p_label = "promise" if len(partial) == 1 else "promises"
        partial_section = (
            '<div style="margin-top:16px">'
            '<div style="color:#f59e0b; font-size:0.78rem; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; padding:6px 0; border-bottom:1px solid #451a03; margin-bottom:8px">'
            '⚠️ Partial — ' + str(len(partial)) + ' ' + p_label + '</div>'
            '<table style="width:100%; border-collapse:collapse; font-size:0.85rem">'
            '<thead><tr style="color:#475569; font-size:0.68rem; text-transform:uppercase; letter-spacing:0.06em">'
            '<th style="padding:4px 14px; text-align:left">Promise</th>'
            '<th style="padding:4px 14px; text-align:center">Actual</th></tr></thead>'
            '<tbody>' + partial_rows + '</tbody></table></div>'
        )

    upcoming_section = ""
    if upcoming:
        p_label = "promise" if len(upcoming) == 1 else "promises"
        upcoming_section = (
            '<div style="margin-top:16px">'
            '<div style="color:#60a5fa; font-size:0.78rem; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; padding:6px 0; border-bottom:1px solid #1e3a5f; margin-bottom:8px">'
            '⏳ Upcoming — ' + str(len(upcoming)) + ' ' + p_label + ' to watch</div>'
            '<table style="width:100%; border-collapse:collapse; font-size:0.85rem">'
            '<thead><tr style="color:#475569; font-size:0.68rem; text-transform:uppercase; letter-spacing:0.06em">'
            '<th style="padding:4px 14px; text-align:left">Promise</th>'
            '<th style="padding:4px 14px; text-align:center">Deadline</th></tr></thead>'
            '<tbody>' + upcoming_rows + '</tbody></table>'
            + upcoming_note + '</div>'
        )

    # ── ConvictionEngine Credibility section (replaces old Accuracy Track Record) ──
    # Built from the narrative timeline, not external-financial verification.
    score_str = (str(round(accuracy, 0)).split('.')[0] + '%') if narr_score is not None else '—'
    ring_circumference = 2 * 3.14159 * 36
    ring_offset_val = ring_circumference - (accuracy / 100.0) * ring_circumference if narr_score is not None else ring_circumference

    # Verdict flip chip
    flip_chip = ''
    if narr_prev_verdict and narr_prev_verdict != narr_verdict:
        is_promo = narr_verdict in ('ADD ZONE', 'HOLD ZONE') and narr_prev_verdict in ('WATCHING', 'REDUCE ZONE', 'THESIS BROKEN')
        is_demo = narr_verdict in ('REDUCE ZONE', 'THESIS BROKEN') and narr_prev_verdict in ('ADD ZONE', 'HOLD ZONE', 'WATCHING')
        arrow = '↑' if is_promo and not is_demo else '↓' if is_demo else '→'
        flip_color = '#4ade80' if (is_promo and not is_demo) else '#f87171' if is_demo else '#94a3b8'
        flip_chip = (
            '<span style="background:#0f172a; color:' + flip_color + '; padding:4px 10px; '
            'border-radius:12px; font-size:0.7rem; font-weight:700; letter-spacing:0.04em; '
            'border:1px solid ' + flip_color + '40; white-space:nowrap">'
            + arrow + ' ' + narr_prev_verdict + ' → ' + narr_verdict + '</span>'
        )

    # Trend chip color
    _TREND_FG = {
        'IMPROVING': '#4ade80', 'STABLE': '#94a3b8', 'DETERIORATING': '#f87171',
        'INSUFFICIENT_DATA': '#64748b',
    }
    trend_fg = _TREND_FG.get(narr_trend, '#64748b')

    # Status counts row (only show non-zero statuses)
    status_chip_html = ''
    _STATUS_LABEL = {
        'FULFILLED': ('#4ade80', '✅ Kept'),
        'REVISED_UP': ('#5eead4', '↑ Revised Up'),
        'ON_TRACK': ('#60a5fa', 'On Track'),
        'PARTIALLY_FULFILLED': ('#fbbf24', '⚠️ Partial'),
        'REVISED_DOWN': ('#fb923c', '↓ Revised Down'),
        'MISSED': ('#f87171', '❌ Broken'),
        'PENDING': ('#94a3b8', '⏳ Pending'),
        'NEW': ('#a5b4fc', '🆕 New'),
    }
    for _s, (_c, _lbl) in _STATUS_LABEL.items():
        _n = narr_counts.get(_s, 0)
        if _n:
            status_chip_html += '<span style="color:' + _c + '; font-weight:600">' + _lbl + ': <b>' + str(_n) + '</b></span>'

    if narr_n_total > 0:
        sample_size_html = (
            '<div style="font-size:0.78rem; color:#cbd5e1; margin-bottom:6px">'
            'Based on <b style="color:#e2e8f0">' + str(narr_n_actionable) + ' of ' + str(narr_n_total) + '</b> actionable promises.'
            + (' <span style="color:#f59e0b">' + str(narr_unverified) + ' quote-unverified</span>.' if narr_unverified else '')
            + '</div>'
        )
    else:
        sample_size_html = '<div style="font-size:0.78rem; color:#64748b">No narrative timeline yet for this symbol.</div>'

    summary_bar = (
        '<div style="background:linear-gradient(135deg,#0a1f1a 0%,#0a1929 100%); border:1px solid #1e3a5f; border-radius:14px; padding:20px; margin:16px 0">'
        '<div style="display:flex; align-items:flex-start; gap:16px; flex-wrap:wrap">'
        '<div style="position:relative; flex-shrink:0">'
        '<svg width="88" height="88" viewBox="0 0 88 88" style="transform:rotate(-90deg)">'
        '<circle cx="44" cy="44" r="36" fill="none" stroke="#1f2937" stroke-width="7"/>'
        '<circle cx="44" cy="44" r="36" fill="none" stroke="' + verdict_color + '" stroke-width="7" '
        'stroke-dasharray="' + str(round(ring_circumference, 1)) + '" '
        'stroke-dashoffset="' + str(round(ring_offset_val, 1)) + '" '
        'stroke-linecap="round" style="transition:stroke-dashoffset 1s ease"/>'
        '</svg>'
        '<div style="position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center">'
        '<div style="font-size:1.4rem; font-weight:800; color:' + verdict_color + '; line-height:1">' + score_str + '</div>'
        '<div style="font-size:0.55rem; color:#64748b; text-transform:uppercase; letter-spacing:0.08em; margin-top:2px">Trust Score</div>'
        '</div>'
        '</div>'
        '<div style="flex:1; min-width:200px">'
        '<div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:8px">'
        '<span style="background:' + verdict_bg + '; color:' + verdict_color + '; padding:5px 12px; border-radius:14px; '
        'font-size:0.78rem; font-weight:700; letter-spacing:0.06em; text-transform:uppercase; border:1px solid ' + verdict_color + '40">' + narr_verdict + '</span>'
        + flip_chip +
        '<span style="background:#0f172a; color:' + trend_fg + '; padding:5px 12px; border-radius:14px; '
        'font-size:0.72rem; font-weight:700; letter-spacing:0.04em; border:1px solid ' + trend_fg + '40">'
        '📈 ' + (narr_trend.replace('_', ' ') if narr_trend else 'INSUFFICIENT_DATA') + '</span>'
        + (('<span style="background:#1f0a0a; color:#f87171; padding:5px 12px; border-radius:14px; '
            'font-size:0.72rem; font-weight:700; letter-spacing:0.04em; border:1px solid #ef444440">'
            '⚠ ' + str(narr_lag) + 'Q miss streak</span>') if narr_lag and narr_lag > 0 else '')
        + '</div>'
        + sample_size_html +
        '<div style="display:flex; gap:10px; flex-wrap:wrap; font-size:0.74rem">' + status_chip_html + '</div>'
        '</div>'
        '</div>'
        '</div>'
    )

    # Verified count in header
    verified_html = (
        '<div style="color:#475569; font-size:0.72rem; margin-top:4px; text-align:right">'
        + str(total_verified) + ' promises verified</div>' if total_verified > 0 else
        '<div style="color:#475569; font-size:0.72rem; margin-top:4px">No verified promises yet</div>'
    )

    # P2 Phase 3: embed debate section (cache-aware, no LLM in email path)
    debate_section = ''
    try:
        from engine_debate.cache import get_latest_debate_for_symbol
        debate = get_latest_debate_for_symbol(sym, 'guidance')
        if debate:
            debate_section = (
                '<div style="margin-top:24px; padding:20px; background:#0b1220; border:1px solid #1e293b; border-radius:10px;">'
                + '<div style="font-size:11px; color:#64748b; letter-spacing:0.15em; text-transform:uppercase; margin-bottom:12px;">🗣️ Bear vs Bull Synthesis</div>'
                + '<div style="display:flex; gap:16px; flex-wrap:wrap;">'
                + '<div style="flex:1; min-width:220px; border-left:3px solid #ef4444; padding:10px 14px; background:#1a0a0a;">'
                + '<div style="font-size:10px; color:#ef4444; font-weight:800; text-transform:uppercase; margin-bottom:6px;">Bear Case</div>'
                + '<div style="font-size:12px; color:#e2e8f0; line-height:1.5;">' + _html_escape(debate['bear']) + '</div></div>'
                + '<div style="flex:1; min-width:220px; border-left:3px solid #22c55e; padding:10px 14px; background:#0a1a0a;">'
                + '<div style="font-size:10px; color:#22c55e; font-weight:800; text-transform:uppercase; margin-bottom:6px;">Bull Case</div>'
                + '<div style="font-size:12px; color:#e2e8f0; line-height:1.5;">' + _html_escape(debate['bull']) + '</div></div>'
                + '</div>'
                + '<div style="margin-top:8px; font-size:10px; color:#475569;">' + _html_escape(debate['model_used']) + ' · cache hits ' + str(debate.get('cache_hits', 0)) + '</div>'
                + '</div>'
            )
        else:
            debate_section = (
                '<div style="margin-top:24px; padding:16px; background:#0b1220; border:1px solid #1e293b; border-radius:10px;">'
                + '<div style="font-size:11px; color:#64748b; letter-spacing:0.15em; text-transform:uppercase; margin-bottom:8px;">🗣️ Bear vs Bull Synthesis</div>'
                + '<div style="font-size:12px; color:#64748b;">Open in the MRI app for the live debate → <a href="https://mri.railway.app/guidance/' + _html_escape(sym) + '" style="color:#0ea5e9;">View Report</a></div>'
                + '</div>'
            )
    except Exception:
        debate_section = ''

    # NOTE: parenthesized string-concat chain below uses explicit '+' on every
    # line. Comments are deliberately placed AFTER the '+' on each line so they
    # do not break implicit string concatenation across newlines.
    html_body = (
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">' +  # doctype+head
        '<title>GuidanceCheck — ' + sym + '</title></head>' +
        '<body style="background:#0a0e1a; color:#e2e8f0; font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif; padding:0; margin:0">' +
        '<div style="max-width:600px; margin:0 auto; padding:24px 16px">'
        + '<div style="background:#111827; border:1px solid #1f2937; border-radius:14px; padding:24px; margin-bottom:16px">'  # header card open
        + '<div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:16px">'
        + '<div>'
        + '<div style="color:#3b82f6; font-size:0.7rem; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:6px">'
        + '🔍 GuidanceCheck · Management Credibility Report</div>'
        + '<h1 style="font-size:1.8rem; font-weight:800; letter-spacing:-0.02em; margin:0 0 4px 0; color:#f1f5f9">' + sym + '</h1>'
        + '<div style="color:#475569; font-size:0.8rem">Report date: ' + report_date + '</div>'
        + '</div>'
        + '<div style="text-align:right">'
        + '<div style="background:' + verdict_bg + '; color:' + verdict_color + '; font-size:0.75rem; font-weight:700;'
        + 'padding:6px 14px; border-radius:20px; letter-spacing:0.06em; text-transform:uppercase">' + verdict + '</div>'
        + verified_html
        + '</div></div></div>'
        + summary_bar  # ConvictionEngine credibility section
        + _build_header_metadata_band(payload)  # chips strip: transcripts, promises, numerical %, dominant, DIRECTIONAL
        + _build_intonation_email_section(payload.get("intonation", {}))  # tone monitor (latest + 9 dims + trajectory)
        + _build_no_verified_promises_warning(payload)  # fallback panel when total_verified == 0
        + achieved_section + missed_section + partial_section + upcoming_section  # promise lists
        + debate_section
        + '<div style="margin-top:24px; padding:14px; background:#0d1421; border:1px solid #1a2236; border-radius:10px">'  # footer
        + '<div style="color:#475569; font-size:0.72rem; text-align:center; line-height:1.6">'
        + 'GuidanceCheck tracks forward-looking statements from earnings calls and investor presentations.<br>'
        + 'Promises are verified against actual quarterly financials. Built on MRI Platform.'
        + '</div></div>'
        + _build_integrity_signal_email_section(integrity_signal, accuracy)  # integrity signal
        + _build_quarter_comparison_email_section(qc)  # quarter comparison
        + _build_integrity_timeline_email_section(timeline)  # integrity timeline
        + '</div></body></html>'
    )

    return html_body


def _build_integrity_signal_email_section(integrity_signal: str, accuracy: float) -> str:
    if not integrity_signal:
        return ''
    sig_class = 'high' if accuracy >= 75 else 'moderate' if accuracy >= 60 else 'low' if accuracy >= 40 else 'insufficient'
    sig_icon  = {'high':'🟢','moderate':'🟡','low':'🔴','insufficient':'⚪'}[sig_class]
    bg_colors = {'high':'#14532d30','moderate':'#451a0320','low':'#7f1d1d20','insufficient':'#1e293b'}
    bd_colors = {'high':'#22c55e40','moderate':'#f59e0b30','low':'#f8717140','insufficient':'#334155'}
    tx_colors = {'high':'#86efac','moderate':'#fde68a','low':'#fca5a5','insufficient':'#94a3b8'}
    return (
        '<div style="border-radius:10px; padding:14px 16px; margin:16px 0; '
        'background:' + bg_colors[sig_class] + '; border:1px solid ' + bd_colors[sig_class] + '; '
        'color:' + tx_colors[sig_class] + '; font-size:0.82rem; line-height:1.5; '
        'display:flex; gap:12px; align-items:flex-start">'
        '<div style="font-size:1.1rem; flex-shrink:0">' + sig_icon + '</div>'
        '<div>' + integrity_signal + '</div>'
        '</div>'
    )


def _build_quarter_comparison_email_section(qc: dict) -> str:
    if not qc or not qc.get('older_quarter'):
        return ''
    older = qc.get('older_promises', [])
    newer = qc.get('newer_promises', [])
    os = qc.get('older_summary', {})
    sig = qc.get('integrity_signal', '') or ''

    def status_badge(s):
        if s == 'ACHIEVED': return '<span style="color:#4ade80;font-weight:700">✅</span>'
        if s == 'MISSED':   return '<span style="color:#f87171;font-weight:700">❌</span>'
        if s == 'PARTIAL':  return '<span style="color:#fbbf24;font-weight:700">⚠️</span>'
        return '<span style="color:#475569">⏳</span>'

    older_rows = ''.join(
        '<div style="font-size:0.75rem;padding:3px 0;border-bottom:1px solid #1f2937">'
        + status_badge(p.get('status'))
        + ' <span style="background:#1e293b;color:#94a3b8;padding:0 4px;border-radius:2px;margin:0 4px;font-size:0.62rem">' + (p.get('type') or 'OTHER') + '</span>'
        + ' ' + (p.get('promise') or '')[:55]
        + '</div>' for p in older
    ) if older else '<div style="color:#475569;font-size:0.75rem;padding:4px 0">No extracted promises for this quarter</div>'

    newer_rows = ''.join(
        '<div style="font-size:0.75rem;padding:3px 0;border-bottom:1px solid #1f2937">'
        + '<span style="color:#60a5fa;font-weight:700">NEW </span>'
        + ' <span style="background:#1e293b;color:#94a3b8;padding:0 4px;border-radius:2px;margin:0 4px;font-size:0.62rem">' + (p.get('type') or 'OTHER') + '</span>'
        + ' ' + (p.get('promise') or '')[:50]
        + '</div>' for p in newer
    ) if newer else '<div style="color:#475569;font-size:0.75rem;padding:4px 0">No extracted promises for this quarter</div>'

    return (
        '<div style="background:#111827;border:1px solid #1f2937;border-radius:14px;padding:20px;margin:16px 0">'
        '<div style="color:#60a5fa;font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.07em;margin-bottom:12px">'
        '📊 Quarter Comparison — Management Track Record</div>'
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">'
        # Older quarter
        '<div style="background:#0d1421;border:1px solid #1f2937;border-radius:8px;padding:12px">'
        '<div style="color:#94a3b8;font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px">'
        '📣 ' + qc.get('older_quarter','') + ' · What they committed</div>'
        '<div style="font-size:0.75rem;color:#475569;margin-bottom:6px">'
        '<span>Total: <b style="color:#e2e8f0">' + str(os.get('total',0)) + '</b></span>'
        '<span style="margin-left:10px;color:#4ade80">✅ ' + str(os.get('achieved',0)) + '</span>'
        '<span style="margin-left:8px;color:#f87171">❌ ' + str(os.get('missed',0)) + '</span>'
        '<span style="margin-left:8px;color:#475569">⏳ ' + str(os.get('pending',0)) + '</span>'
        '</div>'
        + older_rows +
        '</div>'
        # Newer quarter
        '<div style="background:#0d1421;border:1px solid #1e3a5f;border-radius:8px;padding:12px">'
        '<div style="color:#94a3b8;font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px">'
        '📣 ' + qc.get('newer_quarter','') + ' · Latest commitments</div>'
        '<div style="font-size:0.75rem;color:#475569;margin-bottom:6px">'
        '<span>New promises: <b style="color:#60a5fa">' + str(len(newer)) + '</b></span>'
        '</div>'
        + newer_rows +
        '</div>'
        '</div>'
        + ('<div style="color:#475569;font-size:0.72rem;margin-top:8px;font-style:italic">' + sig + '</div>' if sig else '') +
        '</div>'
    )


def _build_integrity_timeline_email_section(timeline: dict) -> str:
    if not timeline:
        return ''
    keys = sorted(timeline.keys(), reverse=True)
    max_total = max((timeline[k].get('total', 0) for k in keys), default=1)
    rows = ''
    for q in keys:
        d = timeline[q]
        total = d.get('total', 0)
        achieved = d.get('achieved', 0)
        missed   = d.get('missed', 0)
        bar_pct  = (total / max_total) * 100 if max_total > 0 else 0
        bar_color = '#22c55e' if total > 0 and achieved/total >= 0.7 else '#f59e0b' if total > 0 and achieved/total >= 0.4 else '#ef4444'
        rows += (
            '<tr>'
            '<td style="padding:5px 8px;font-size:0.75rem;color:#94a3b8;font-weight:600;min-width:60px">' + q + '</td>'
            '<td style="padding:5px 8px;flex:1">'
            '<div style="background:#1f2937;border-radius:3px;height:6px;width:' + str(bar_pct) + '%;margin:auto 0">'
            '<div style="height:6px;border-radius:3px;background:' + bar_color + ';width:100%;opacity:0.7"></div>'
            '</div>'
            '</td>'
            '<td style="padding:5px 8px;font-size:0.72rem;text-align:right;white-space:nowrap">'
            '<span style="color:#4ade80">' + str(achieved) + '✅</span>'
            '<span style="color:#f87171;margin-left:4px">' + str(missed) + '❌</span>'
            '<span style="color:#475569;margin-left:4px">' + str(total) + ' tot</span>'
            '</td></tr>'
        )
    return (
        '<div style="background:#111827;border:1px solid #1f2937;border-radius:14px;padding:20px;margin:16px 0">'
        '<div style="color:#94a3b8;font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.07em;margin-bottom:10px">'
        '📈 Integrity by Quarter</div>'
        '<table style="width:100%;border-collapse:collapse">' + rows + '</table>'
        '</div>'
    )


def send_weekly_portfolio_review(email: str, name: str, results: dict):
    if not email or not aws_credentials_present():
        return False
        
    try:
        ses_region = resolve_ses_region()
        ses = get_ses_client(ses_region)
        
        summary = results.get("portfolio_summary", {})
        decision = results.get("highest_priority_decision", {})
        holdings = results.get("holdings", [])
        action_queue = results.get("action_queue", [])
        review_queue = results.get("review_queue", [])
        
        subject = f"MRI Weekly Portfolio Review: {summary.get('market_regime', 'Bull')} Market"
        
        # Build Highest Priority Decision Box
        decision_html = ""
        if decision:
            color = "#ef4444" if decision.get("action") == "EXIT" else \
                    "#f97316" if decision.get("action") == "REDUCE" else \
                    "#22c55e" if decision.get("action") in ["ADD", "BUY"] else "#3b82f6"
            decision_html = f"""
            <div style="background:{color}10; border:2px solid {color}; border-radius:12px; padding:20px; margin-bottom:24px;">
                <h3 style="margin:0 0 8px; color:{color}; font-size:14px; text-transform:uppercase;">⭐ This Week's Decision</h3>
                <div style="font-size:24px; font-weight:bold; margin-bottom:12px; color:#111827;">
                    <span style="color:{color}">{decision.get("action")}</span> {decision.get("stock")}
                </div>
                <p style="margin:0 0 12px; font-size:14px; color:#4b5563;">{decision.get("reason")}</p>
                <div style="display:flex; gap:16px;">
                    <div><span style="font-size:12px; color:#6b7280;">Confidence:</span> <b style="color:#111827">{decision.get("confidence")}%</b></div>
                    <div><span style="font-size:12px; color:#6b7280;">MRI Score:</span> <b style="color:#111827">{decision.get("mri_score")}</b></div>
                    <div><span style="font-size:12px; color:#6b7280;">CAI Score:</span> <b style="color:#111827">{decision.get("cai_score")}</b></div>
                </div>
            </div>
            """

        # Build Action Queue
        action_rows = ""
        for a in action_queue:
            color = "#ef4444" if a.get("action") in ["EXIT", "REDUCE"] else \
                    "#22c55e" if a.get("action") in ["ADD", "BUY"] else "#6b7280"
            action_rows += f"""
            <tr style="border-bottom:1px solid #e5e7eb;">
                <td style="padding:12px; font-weight:bold; color:{color}">{a.get("action")}</td>
                <td style="padding:12px; font-weight:bold; color:#111827">{a.get("stock")}</td>
                <td style="padding:12px; color:#4b5563; font-size:13px;">{a.get("reason")}</td>
                <td style="padding:12px; text-align:right; font-weight:bold; color:#111827">{a.get("confidence")}%</td>
            </tr>
            """
            
        # Build Review Queue
        review_rows = ""
        for r in review_queue:
            r_color = "#ef4444" if r.get("status") == "URGENT_REVIEW" else "#f97316"
            r_status = "URGENT" if r.get("status") == "URGENT_REVIEW" else "REVIEW"
            review_rows += f"""
            <tr style="border-bottom:1px solid #e5e7eb;">
                <td style="padding:12px; font-weight:bold; color:{r_color}">{r_status}</td>
                <td style="padding:12px; font-weight:bold; color:#111827">{r.get("stock")}</td>
                <td style="padding:12px; color:#4b5563; font-size:13px;">{r.get("reason")}</td>
            </tr>
            """
        
        # Build Holdings Status
        holdings_rows = ""
        for h in holdings:
            pl_color = "#22c55e" if h.get("pl_pct", 0) >= 0 else "#ef4444"
            pl_sign = "+" if h.get("pl_pct", 0) >= 0 else ""
            act_color = "#ef4444" if h.get("current_action") in ["EXIT", "REDUCE"] else \
                    "#22c55e" if h.get("current_action") in ["ADD", "BUY"] else "#6b7280"
            holdings_rows += f"""
            <tr style="border-bottom:1px solid #e5e7eb;">
                <td style="padding:10px; font-weight:bold; color:#111827">{h.get("ticker")}</td>
                <td style="padding:10px; text-align:right; color:{pl_color}">{pl_sign}{h.get("pl_pct")}%</td>
                <td style="padding:10px; text-align:center; color:#111827">{h.get("mri_score")}</td>
                <td style="padding:10px; text-align:center; font-weight:bold; color:{act_color}">{h.get("current_action")}</td>
                <td style="padding:10px; text-align:center; font-weight:bold; color:#f97316">{h.get("review_status") if h.get("review_status") != "NONE" else ""}</td>
            </tr>
            """

        html_body = f"""
        <html>
        <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:600px;margin:auto;padding:20px;color:#333;background:#f9fafb;">
            <div style="background:white; border-radius:12px; padding:24px; box-shadow:0 1px 3px rgba(0,0,0,0.1);">
                <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #e5e7eb; padding-bottom:16px; margin-bottom:24px;">
                    <h2 style="margin:0; color:#111827; font-size:20px;">💼 Weekly Portfolio Review</h2>
                    <span style="background:#e0e7ff; color:#4338ca; padding:4px 12px; border-radius:12px; font-size:12px; font-weight:bold;">{summary.get('market_regime')} Regime</span>
                </div>
                
                <p style="font-size:15px; color:#4b5563; margin-bottom:24px;">Hi {name or 'Investor'},</p>
                <p style="font-size:15px; color:#4b5563; margin-bottom:24px;">Your weekly portfolio analysis is complete. Below are the data-driven actions recommended for this week.</p>
                
                {decision_html}
                
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:32px;">
                    <div style="background:#f3f4f6; padding:16px; border-radius:8px;">
                        <div style="font-size:12px; color:#6b7280; margin-bottom:4px; text-transform:uppercase;">Portfolio Health</div>
                        <div style="font-size:24px; font-weight:bold; color:#111827;">{summary.get('portfolio_health')}</div>
                    </div>
                    <div style="background:#f3f4f6; padding:16px; border-radius:8px;">
                        <div style="font-size:12px; color:#6b7280; margin-bottom:4px; text-transform:uppercase;">Deployment</div>
                        <div style="font-size:24px; font-weight:bold; color:#111827;">{summary.get('deployment_pct')}%</div>
                    </div>
                </div>
                
                <h3 style="margin:0 0 12px; color:#111827; font-size:16px;">📈 Action Queue</h3>
                <table style="width:100%; border-collapse:collapse; margin-bottom:32px; font-size:14px;">
                    {action_rows if action_rows else '<tr><td colspan="4" style="padding:16px; text-align:center; color:#6b7280;">No actions required this week.</td></tr>'}
                </table>
                
                {f'''
                <h3 style="margin:0 0 12px; color:#111827; font-size:16px;">⚠️ Review Required</h3>
                <table style="width:100%; border-collapse:collapse; margin-bottom:32px; font-size:14px;">
                    {review_rows}
                </table>
                ''' if review_rows else ''}
                
                <h3 style="margin:0 0 12px; color:#111827; font-size:16px;">🛡️ Current Holdings</h3>
                <table style="width:100%; border-collapse:collapse; font-size:13px; background:#f9fafb; border-radius:8px;">
                    <tr style="background:#f3f4f6; text-transform:uppercase; font-size:11px; color:#6b7280;">
                        <th style="padding:10px; text-align:left; border-radius:8px 0 0 0;">Stock</th>
                        <th style="padding:10px; text-align:right;">P/L</th>
                        <th style="padding:10px; text-align:center;">MRI</th>
                        <th style="padding:10px; text-align:center;">Action</th>
                        <th style="padding:10px; text-align:center; border-radius:0 8px 0 0;">Review</th>
                    </tr>
                    {holdings_rows}
                </table>
                
                <div style="margin-top:32px; padding-top:24px; border-top:1px solid #e5e7eb; text-align:center;">
                    <a href="https://your-domain.com/caiportfolio" style="background:#4f46e5; color:white; padding:12px 24px; border-radius:8px; text-decoration:none; font-weight:bold; font-size:14px;">View Live Dashboard</a>
                </div>
            </div>
            <p style="font-size:11px; color:#9ca3af; text-align:center; margin-top:24px;">Market Regime Intelligence · Weekly Analysis Engine</p>
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
        logger.info(f"✅ Weekly Portfolio Review sent to {email}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send Weekly Portfolio Review email: {e}")
        return False


if __name__ == "__main__":
    send_signal_emails()
    send_stee_signal_emails()
