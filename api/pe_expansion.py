"""PE Expansion API — JSON for screen + HTML email send.

Two endpoints:
    GET  /api/pe-expansion/{symbol}              -> report JSON for the screen
    POST /api/pe-expansion/email/{symbol}        -> build report + send HTML email

The email uses AWS SES via the existing engine_core.email_service helpers,
logs to the same `email_log` table the rest of the platform uses.
"""
from __future__ import annotations

import html
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from engine_core.db import get_connection
from engine_core.aws_ses import aws_credentials_present, get_ses_client, resolve_ses_region
from engine_core.email_service import SENDER_EMAIL
from engine_perx.pe_signals import build_pe_expansion_report
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("pe_expansion_api")

router = APIRouter(prefix="/api/pe-expansion", tags=["pe-expansion"])


# ── Helpers ──────────────────────────────────────────────────────────

def _esc(s: Any) -> str:
    """HTML-escape + truncate to safe length."""
    if s is None:
        return ""
    return html.escape(str(s))


def _bucket_color(bucket: str) -> str:
    return {
        "Strong": "#22c55e",
        "Moderate": "#3b82f6",
        "Watch": "#f59e0b",
        "Weak": "#ef4444",
        "Negligible": "#64748b",
    }.get(bucket, "#64748b")


def _strength_bar(strength: int, max_width: int = 5) -> str:
    """5-cell visual strength bar using Unicode blocks."""
    filled = "█" * max(0, min(max_width, strength))
    empty = "░" * (max_width - len(filled))
    return filled + empty


# ── HTML email renderer ──────────────────────────────────────────────

def render_pe_expansion_email(report: dict[str, Any]) -> str:
    """Render the institutional dark-theme HTML email.

    Single-file inline styles (no external CSS — works in all clients).
    Section order matches the screen layout so recipients see what they
    would have seen if they opened the URL.
    """
    h = report["header"]
    cov = report["coverage"]
    cats = report["category_breakdown"]
    drivers = report["top_drivers"]
    primary = report["primary_detail"]
    secondary = report["secondary_detail"]
    totals = report["totals"]

    # Section A0: Manager Track Record strip (above the header).
    # Pulled from management_credibility_scores — verdict zone + accuracy
    # + trend + miss streak + summary. Renders nothing if no track record.
    cred = report.get("credibility")
    if cred and cred.get("verdict_zone"):
        verdict_color = {
            "ADD ZONE": "#22c55e",
            "HOLD ZONE": "#f59e0b",
            "REDUCE ZONE": "#fb923c",
            "WATCH ZONE": "#94a3b8",
            "THESIS BROKEN": "#ef4444",
            "DISTRUSTED": "#ef4444",
        }.get(str(cred["verdict_zone"]).upper(), "#94a3b8")
        trend_color = {
            "IMPROVING": "#22c55e",
            "STABLE": "#94a3b8",
            "DETERIORATING": "#ef4444",
        }.get(str(cred.get("trend") or "").upper(), "#94a3b8")
        miss_streak = int(cred.get("consecutive_miss_quarters") or 0)
        accuracy = cred.get("accuracy_pct")
        accuracy_str = f"{accuracy:.0f}%" if accuracy is not None else "—"
        lag = cred.get("lag_score")
        lag_str = f"{lag:.0f}" if lag is not None else "—"
        n_total = cred.get("total_promises") or 0
        n_achieved = cred.get("achieved_count") or 0
        n_missed = cred.get("missed_count") or 0

        credibility_html = f"""
    <div style="padding:20px 40px;background:#0b1220;border-bottom:1px solid #1e293b;">
      <div style="font-size:11px;color:#64748b;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:14px;">
        Manager Track Record
      </div>
      <table cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
        <tr>
          <td style="padding-right:36px;vertical-align:top;">
            <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.15em;">Accuracy</div>
            <div style="font-size:32px;font-weight:800;color:#f1f5f9;line-height:1;margin-top:6px;">{accuracy_str}</div>
          </td>
          <td style="padding-right:36px;vertical-align:top;">
            <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.15em;">Verdict</div>
            <div style="font-size:14px;font-weight:700;color:{verdict_color};margin-top:14px;">{_esc(cred['verdict_zone'])}</div>
          </td>
          <td style="padding-right:36px;vertical-align:top;">
            <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.15em;">Trend</div>
            <div style="font-size:14px;font-weight:700;color:{trend_color};margin-top:14px;">{_esc(cred.get('trend') or '—')}</div>
          </td>
          <td style="padding-right:36px;vertical-align:top;">
            <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.15em;">Miss Streak</div>
            <div style="font-size:14px;font-weight:700;color:{(miss_streak or 0) >= 4 and '#ef4444' or (miss_streak or 0) >= 2 and '#f59e0b' or '#cbd5e1'};margin-top:14px;">{miss_streak}Q</div>
          </td>
          <td style="padding-right:36px;vertical-align:top;">
            <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.15em;">Lag Score</div>
            <div style="font-size:14px;font-weight:700;color:#cbd5e1;margin-top:14px;">{lag_str}</div>
          </td>
          <td style="vertical-align:top;">
            <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.15em;">Promises</div>
            <div style="font-size:13px;color:#cbd5e1;line-height:1.5;margin-top:12px;">{n_achieved} achieved · {n_missed} missed<br><span style="color:#64748b;">of {n_total} total</span></div>
          </td>
        </tr>
      </table>
      <div style="font-size:12px;color:#94a3b8;margin-top:12px;font-style:italic;line-height:1.5;">
        {_esc(cred.get('summary') or '')}
      </div>
    </div>
    """
    else:
        credibility_html = ""

    # Helper: bucket a 0-100 score into a human-readable verdict + color
    def _bucket_label(score: float | int | None) -> tuple[str, str]:
        if score is None:
            return ("No data", "#64748b")
        if score >= 80:
            return ("Strong", "#22c55e")
        if score >= 60:
            return ("Holding up", "#3b82f6")
        if score >= 40:
            return ("Mixed", "#f59e0b")
        return ("Weak", "#ef4444")

    # ── Independent Checks strip (3 side-by-side cards) ──
    ic = report.get("independent_check")
    fq = report.get("financial_quality")
    pa = report.get("price_action")

    def _card_html(title: str, score: float | int | None,
                   label_override: str | None = None,
                   extra_html: str = "",
                   score_unit: str = "/100") -> str:
        """Render one of the three cross-check cards."""
        label, color = _bucket_label(score)
        if label_override:
            label = label_override
        score_str = f"{score:.0f}{score_unit}" if score is not None else "—"
        return f"""
        <div style="flex:1;min-width:240px;padding:18px 20px;background:#0b1220;border:1px solid #1e293b;border-radius:6px;">
          <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.2em;margin-bottom:10px;">{_esc(title)}</div>
          <div style="display:flex;align-items:baseline;gap:10px;margin-bottom:8px;">
            <div style="font-size:36px;font-weight:800;color:#f1f5f9;line-height:1;">{score_str}</div>
            <div style="font-size:13px;font-weight:700;color:{color};">{_esc(label)}</div>
          </div>
          {extra_html}
        </div>
        """

    ic_extra = ""
    if ic and ic.get("reasons"):
        bullets = "".join(
            f'<li style="margin:3px 0;color:#94a3b8;font-size:11px;line-height:1.5;">{_esc(r)}</li>'
            for r in ic["reasons"][:3]
        )
        ic_extra = f'<ul style="margin:8px 0 0 0;padding-left:18px;">{bullets}</ul>'

    fq_extra = ""
    if fq and fq.get("category"):
        fq_extra = f'<div style="font-size:11px;color:#94a3b8;margin-top:4px;">Category: <span style="color:#f1f5f9;font-weight:600;">{_esc(fq["category"])}</span></div>'

    pa_extra = ""
    if pa and pa.get("breakout_state"):
        pa_extra = f'<div style="font-size:11px;color:#94a3b8;margin-top:4px;">State: <span style="color:#f1f5f9;font-weight:600;">{_esc(pa["breakout_state"])}</span></div>'

    indep_card = _card_html("Independent Check", ic["master_score"] if ic else None, extra_html=ic_extra) if ic else _card_html("Independent Check", None, label_override="No data", extra_html='<div style="font-size:11px;color:#64748b;margin-top:4px;">No audit available</div>')
    fin_card = _card_html("Financial Quality", fq["score"] if fq else None, extra_html=fq_extra) if fq else _card_html("Financial Quality", None, label_override="No data", extra_html='<div style="font-size:11px;color:#64748b;margin-top:4px;">No verdict available</div>')
    price_card = _card_html("Price Action", pa["total_score"] if pa else None, extra_html=pa_extra) if pa else _card_html("Price Action", None, label_override="No data", extra_html='<div style="font-size:11px;color:#64748b;margin-top:4px;">No data available</div>')

    checks_html = f"""
    <div style="padding:24px 40px;background:#0f172a;border-bottom:1px solid #1e293b;">
      <div style="font-size:11px;color:#64748b;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:14px;">
        What Other Checks Say
      </div>
      <div style="display:flex;gap:14px;flex-wrap:wrap;">
        {indep_card}
        {fin_card}
        {price_card}
      </div>
    </div>
    """

    # ── Where the Signals Agree (5-row matrix) ──
    cross_check = report.get("cross_check", [])
    if cross_check:
        alignment_label = {
            "all_agree": "All agree",
            "mostly_agree": "Mostly agree",
            "mixed": "Mixed signals",
            "split": "Split",
            "no_data": "No data",
        }
        alignment_color = {
            "all_agree": "#22c55e",
            "mostly_agree": "#3b82f6",
            "mixed": "#f59e0b",
            "split": "#ef4444",
            "no_data": "#64748b",
        }
        matrix_rows = ""
        for row in cross_check:
            a = row.get("alignment", "no_data")
            label = alignment_label.get(a, "No data")
            color = alignment_color.get(a, "#64748b")
            matrix_rows += f"""
        <tr style="border-bottom:1px solid #1e293b;">
          <td style="padding:10px 12px;color:#f1f5f9;font-weight:700;">{_esc(row['dimension'])}</td>
          <td style="padding:10px 12px;color:#94a3b8;font-size:11px;">{_esc(row['pe_view'])}</td>
          <td style="padding:10px 12px;color:#94a3b8;font-size:11px;">{_esc(row['indep_view'])}</td>
          <td style="padding:10px 12px;color:#94a3b8;font-size:11px;">{_esc(row['fin_view'])}</td>
          <td style="padding:10px 12px;color:#94a3b8;font-size:11px;">{_esc(row['price_view'])}</td>
          <td style="padding:10px 12px;color:{color};font-weight:700;font-size:12px;">{_esc(label)}</td>
        </tr>
        """
        cross_check_html = f"""
    <div style="padding:24px 40px;background:#0b1220;border-bottom:1px solid #1e293b;">
      <div style="font-size:11px;color:#64748b;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:6px;">
        Where the Signals Agree
      </div>
      <div style="font-size:12px;color:#94a3b8;margin-bottom:14px;font-style:italic;">
        A plain-English read on whether the four engines back each other up.
      </div>
      <table cellpadding="0" cellspacing="0" width="100%" style="border-collapse:collapse;font-size:12px;color:#cbd5e1;">
        <thead>
          <tr style="background:#020617;border-bottom:1px solid #334155;">
            <th align="left"  style="padding:8px 12px;color:#64748b;font-size:9px;text-transform:uppercase;letter-spacing:0.1em;">Dimension</th>
            <th align="left"  style="padding:8px 12px;color:#64748b;font-size:9px;text-transform:uppercase;letter-spacing:0.1em;">Narrative</th>
            <th align="left"  style="padding:8px 12px;color:#64748b;font-size:9px;text-transform:uppercase;letter-spacing:0.1em;">Independent Check</th>
            <th align="left"  style="padding:8px 12px;color:#64748b;font-size:9px;text-transform:uppercase;letter-spacing:0.1em;">Financial Quality</th>
            <th align="left"  style="padding:8px 12px;color:#64748b;font-size:9px;text-transform:uppercase;letter-spacing:0.1em;">Price Action</th>
            <th align="left"  style="padding:8px 12px;color:#64748b;font-size:9px;text-transform:uppercase;letter-spacing:0.1em;">Verdict</th>
          </tr>
        </thead>
        <tbody>{matrix_rows}</tbody>
      </table>
    </div>
    """
    else:
        cross_check_html = ""

    # ── Financial Quality breakdown (7 agents) ──
    fin_breakdown_html = ""
    if fq and fq.get("agents"):
        agent_labels = [
            ("revenue", "Revenue Quality"),
            ("margin", "Margin Quality"),
            ("leverage", "Leverage"),
            ("wc", "Working Capital"),
            ("roce", "Capital Efficiency (ROCE)"),
            ("evolution", "Business Evolution"),
            ("translation", "Financial Translation"),
        ]
        rows_html = ""
        for key, label in agent_labels:
            score = fq["agents"].get(key)
            if score is None:
                row_color = "#475569"
                score_text = "—"
                bar = "░░░░░░░░░░"
            else:
                row_color = "#22c55e" if score >= 7 else ("#f59e0b" if score >= 4 else "#ef4444")
                score_text = f"{score}/10"
                bar = "█" * score + "░" * (10 - score)
            rows_html += f"""
        <tr style="border-bottom:1px solid #1e293b;">
          <td style="padding:8px 12px;color:#f1f5f9;">{_esc(label)}</td>
          <td style="padding:8px 12px;font-family:monospace;color:{row_color};font-weight:700;">{_esc(score_text)}</td>
          <td style="padding:8px 12px;font-family:monospace;color:{row_color};letter-spacing:0.05em;">{bar}</td>
        </tr>
        """
        fin_breakdown_html = f"""
    <div style="padding:24px 40px;background:#0f172a;border-bottom:1px solid #1e293b;">
      <div style="font-size:11px;color:#64748b;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:14px;">
        Financial Quality — 7-Agent Breakdown
      </div>
      <table cellpadding="0" cellspacing="0" width="100%" style="border-collapse:collapse;font-size:12px;color:#cbd5e1;">
        <thead>
          <tr style="background:#020617;border-bottom:1px solid #334155;">
            <th align="left" style="padding:6px 12px;color:#64748b;font-size:9px;text-transform:uppercase;letter-spacing:0.1em;">Agent</th>
            <th align="left" style="padding:6px 12px;color:#64748b;font-size:9px;text-transform:uppercase;letter-spacing:0.1em;">Score</th>
            <th align="left" style="padding:6px 12px;color:#64748b;font-size:9px;text-transform:uppercase;letter-spacing:0.1em;">Strength</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    """
    else:
        fin_breakdown_html = ""

    # ── Price Action 7-step checklist ──
    price_html = ""
    if pa and pa.get("conditions"):
        cond_labels = [
            ("ema_50_200", "EMA 50 above 200"),
            ("ema_200_slope", "200-day EMA slope positive"),
            ("six_m_high", "Near 6-month high"),
            ("volume", "Volume confirmation (1.3x)"),
            ("rs", "Relative strength vs Nifty"),
            ("breakout_10d", "Close above 10-day high"),
            ("price_quality", "Strong close (70%+ of day's range)"),
        ]
        rows_html = ""
        n_pass = 0
        for key, label in cond_labels:
            passed = bool(pa["conditions"].get(key))
            if passed:
                n_pass += 1
            mark = "✓" if passed else "✗"
            color = "#22c55e" if passed else "#ef4444"
            rows_html += f"""
        <tr style="border-bottom:1px solid #1e293b;">
          <td style="padding:8px 12px;font-family:monospace;color:{color};font-weight:700;font-size:14px;">{mark}</td>
          <td style="padding:8px 12px;color:#f1f5f9;">{_esc(label)}</td>
        </tr>
        """
        price_html = f"""
    <div style="padding:24px 40px;background:#0f172a;border-bottom:1px solid #1e293b;">
      <div style="font-size:11px;color:#64748b;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:6px;">
        Price Action — 7-Step Checklist
      </div>
      <div style="font-size:12px;color:#94a3b8;margin-bottom:14px;font-style:italic;">
        {_esc(pa.get('breakout_state', ''))} · {n_pass} of 7 momentum signals on
      </div>
      <table cellpadding="0" cellspacing="0" width="100%" style="border-collapse:collapse;font-size:12px;color:#cbd5e1;">
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    """
    else:
        price_html = ""

    # ── Bottom Line (executive synthesis at the top of the report) ──
    bl = report.get("bottom_line") or {}
    if bl.get("summary"):
        action = bl.get("action", "no_data")
        action_styles = {
            "positive": ("Strong setup", "#22c55e", "#052e16"),
            "watch":    ("Watch",        "#3b82f6", "#0c2541"),
            "cautious": ("Caution",      "#f59e0b", "#3a2410"),
            "negative": ("Avoid",        "#ef4444", "#3b0a0a"),
            "no_data":  ("Insufficient", "#64748b", "#1c1c1c"),
        }
        label, color, bg = action_styles.get(action, action_styles["no_data"])
        highlights_html = ""
        for hl in bl.get("highlights", []):
            hl_color = {
                "all_agree":    "#22c55e",
                "mostly_agree": "#3b82f6",
                "mixed":        "#f59e0b",
                "split":        "#ef4444",
                "no_data":      "#64748b",
            }.get(hl["status"], "#64748b")
            highlights_html += (
                f'<span style="display:inline-block;padding:4px 10px;margin:3px 4px 3px 0;'
                f'background:#0b1220;border:1px solid {hl_color};border-radius:4px;'
                f'font-size:11px;color:#f1f5f9;">'
                f'<span style="color:{hl_color};font-weight:700;">{_esc(hl["status_label"])}</span>'
                f' &middot; <span style="color:#94a3b8;">{_esc(hl["signal"])}</span>'
                f'</span>'
            )
        bottom_line_html = f"""
    <div style="padding:24px 40px;background:{bg};border-bottom:3px solid {color};">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
        <span style="display:inline-block;padding:4px 10px;background:{color};color:#020617;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:0.15em;border-radius:3px;">BOTTOM LINE</span>
        <span style="font-size:13px;font-weight:700;color:{color};">{_esc(label)}</span>
      </div>
      <div style="font-size:14px;color:#f1f5f9;line-height:1.55;font-weight:500;margin-bottom:14px;">
        {_esc(bl["summary"])}
      </div>
      <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.15em;margin-bottom:6px;">Across the 5 dimensions:</div>
      <div>{highlights_html}</div>
    </div>
    """
    else:
        bottom_line_html = ""

    # Section A: header
    bar_color = _bucket_color(h["bucket"])
    header_html = f"""
    <div style="padding:32px 40px;background:#0f172a;border-bottom:3px solid {bar_color};">
      <div style="font-size:11px;color:#64748b;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:6px;">
        MRI · Expansion Lens
      </div>
      <div style="font-size:28px;font-weight:800;color:#f1f5f9;letter-spacing:-0.02em;margin-bottom:4px;">
        {_esc(h['company_name'])}
      </div>
      <div style="font-size:13px;color:#94a3b8;margin-bottom:20px;">
        {_esc(h['sector'] or '—')} · {_esc(h['symbol'])} · {_esc(h['generated_at_ist'])}
      </div>
      <table cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
        <tr>
          <td style="padding-right:32px;vertical-align:top;">
            <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.15em;">PE Score</div>
            <div style="font-size:48px;font-weight:800;color:{bar_color};line-height:1;margin-top:4px;">
              {h['pe_score']}<span style="font-size:18px;color:#475569;font-weight:400;">/100</span>
            </div>
          </td>
          <td style="padding-right:32px;vertical-align:top;">
            <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.15em;">Universe Rank</div>
            <div style="font-size:24px;font-weight:700;color:#f1f5f9;line-height:1;margin-top:8px;">
              #{h['rank']} <span style="font-size:14px;color:#64748b;font-weight:400;">of {h['total']}</span>
            </div>
          </td>
          <td style="padding-right:32px;vertical-align:top;">
            <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.15em;">Classification</div>
            <div style="font-size:18px;font-weight:700;color:{bar_color};line-height:1;margin-top:12px;">
              {h['bucket']}
            </div>
          </td>
          <td style="vertical-align:top;">
            <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:0.15em;">Coverage</div>
            <div style="font-size:13px;color:#cbd5e1;line-height:1.4;margin-top:8px;">
              {cov['n_promises_total']} promises ({cov['n_quote_verified']} verified)<br>
              {cov['n_transcripts']} transcripts · {cov['n_quarter_span']} quarters
            </div>
          </td>
        </tr>
      </table>
    </div>
    """

    # Section B: top drivers strip
    drivers_html = """
    <div style="padding:20px 40px;background:#1e293b;border-bottom:1px solid #334155;">
      <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.2em;margin-bottom:10px;">
        Top Expansion Drivers
      </div>
      <div style="font-size:14px;color:#f1f5f9;font-weight:600;line-height:1.6;">
    """
    for i, d in enumerate(drivers[:5]):
        drivers_html += f'<span style="color:#3b82f6;">{i+1}.</span> {_esc(d)} &nbsp; '
    drivers_html += "</div></div>"

    # Section C: category breakdown table
    cats_html = """
    <div style="padding:32px 40px;background:#0f172a;">
      <div style="font-size:14px;color:#f1f5f9;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:16px;">
        Category Breakdown
      </div>
      <table cellpadding="0" cellspacing="0" width="100%" style="border-collapse:collapse;font-size:13px;color:#cbd5e1;">
        <tr style="background:#1e293b;">
          <th align="left"  style="padding:10px 12px;color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:0.1em;border-bottom:1px solid #334155;">Category</th>
          <th align="center" style="padding:10px 12px;color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:0.1em;border-bottom:1px solid #334155;">Weight</th>
          <th align="center" style="padding:10px 12px;color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:0.1em;border-bottom:1px solid #334155;">Strength</th>
          <th align="right" style="padding:10px 12px;color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:0.1em;border-bottom:1px solid #334155;">Contribution</th>
          <th align="left"  style="padding:10px 12px;color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:0.1em;border-bottom:1px solid #334155;">Sources</th>
        </tr>
    """
    for c in cats:
        if c["missing"]:
            row_bg = "transparent"
            weight_cell = f'<span style="color:#475569;">{c["weight"]}</span>'
            bar = _strength_bar(0)
            bar_cell = f'<span style="color:#334155;letter-spacing:0.1em;">{bar}</span>'
            contrib_cell = '<span style="color:#475569;">—</span>'
            sources_cell = '<span style="color:#475569;font-style:italic;">no evidence</span>'
            label_color = "#475569"
        else:
            row_bg = "transparent"
            weight_cell = f'<span style="color:#cbd5e1;font-weight:600;">{c["weight"]}</span>'
            bar = _strength_bar(c["signal_strength"])
            bar_color_str = "#22c55e" if c["signal_strength"] >= 4 else ("#3b82f6" if c["signal_strength"] >= 3 else "#64748b")
            bar_cell = f'<span style="color:{bar_color_str};letter-spacing:0.1em;font-family:monospace;">{bar}</span>'
            contrib_cell = f'<span style="color:#f1f5f9;font-weight:700;">{c["contribution"]}</span>'
            sources_pills = " ".join(
                f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;background:{"#1e40af" if s=="primary" else "#7c2d12"};color:#f1f5f9;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;margin-right:4px;">{s}</span>'
                for s in c["sources"]
            )
            sources_cell = sources_pills or '<span style="color:#475569;">—</span>'
            label_color = "#f1f5f9"
        cats_html += f"""
        <tr style="background:{row_bg};">
          <td style="padding:10px 12px;border-bottom:1px solid #1e293b;color:{label_color};">{_esc(c['label'])}</td>
          <td align="center" style="padding:10px 12px;border-bottom:1px solid #1e293b;">{weight_cell}</td>
          <td align="center" style="padding:10px 12px;border-bottom:1px solid #1e293b;">{bar_cell}</td>
          <td align="right" style="padding:10px 12px;border-bottom:1px solid #1e293b;">{contrib_cell}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #1e293b;">{sources_cell}</td>
        </tr>
        """
        # Inline evidence quote (verbatim from transcript) under each
        # non-missing category — grounds the abstract score with citation.
        if not c["missing"] and c.get("quote"):
            q = c["quote"]
            attribution = q.get("source", "")
            if q.get("quarter"):
                attribution = f"{attribution} ({q['quarter']})" if attribution else q["quarter"]
            attribution_html = (
                f'<div style="color:#64748b;font-style:normal;font-size:10px;margin-top:4px;">— {_esc(attribution) if attribution else "transcript"}</div>'
                if attribution else ""
            )
            cats_html += f"""
        <tr>
          <td colspan="5" style="padding:0 12px 14px 12px;border-bottom:1px solid #1e293b;">
            <div style="border-left:3px solid {bar_color};padding:8px 12px;color:#94a3b8;font-size:11px;font-style:italic;line-height:1.55;background:#0b1220;border-radius:0 4px 4px 0;">
              &ldquo;{_esc(q['text'])}&rdquo;
              {attribution_html}
            </div>
          </td>
        </tr>
        """
        # Per-category promise-status grid: last 4 quarters of FULFILLED /
        # ON_TRACK / MISSED / REVISED counts, sourced from
        # management_narrative_timeline via GUIDANCE_TYPE_TO_CATEGORY.
        # Renders nothing for categories with no grid data.
        if not c["missing"] and c.get("status_grid"):
            grid_rows_html = []
            status_colors = {
                "FULFILLED": "#22c55e", "REVISED_UP": "#22c55e",
                "ON_TRACK": "#3b82f6", "PARTIALLY_FULFILLED": "#f59e0b",
                "PENDING": "#64748b", "NEW": "#64748b",
                "REVISED_DOWN": "#ef4444", "MISSED": "#ef4444",
            }
            for g in c["status_grid"]:
                counts = g.get("counts", {})
                nz = [(k, v) for k, v in counts.items() if v > 0]
                if not nz:
                    continue
                cells = "".join(
                    f'<td align="center" style="padding:4px 8px;color:{status_colors.get(k, "#94a3b8")};font-family:monospace;font-size:11px;font-weight:600;">{v}</td>'
                    for k, v in nz
                )
                grid_rows_html.append(
                    f'<tr><td style="padding:4px 8px;color:#cbd5e1;font-family:monospace;font-size:11px;border-right:1px solid #1e293b;">{_esc(g["quarter"])}</td>{cells}</tr>'
                )
            if grid_rows_html:
                cats_html += f"""
        <tr>
          <td colspan="5" style="padding:0 12px 12px 12px;border-bottom:1px solid #1e293b;">
            <div style="background:#020617;border:1px solid #1e293b;border-radius:4px;padding:8px 10px;margin-top:2px;">
              <div style="font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:0.15em;margin-bottom:6px;">Promise Status — last {len(grid_rows_html)} quarters</div>
              <table cellpadding="0" cellspacing="0" style="border-collapse:collapse;font-size:11px;">
                <thead>
                  <tr style="border-bottom:1px solid #1e293b;">
                    <th align="left" style="padding:4px 8px;color:#64748b;font-size:9px;text-transform:uppercase;letter-spacing:0.1em;font-weight:600;">Quarter</th>
                    <th align="center" style="padding:4px 6px;color:#22c55e;font-size:9px;text-transform:uppercase;letter-spacing:0.1em;font-weight:600;">FUL</th>
                    <th align="center" style="padding:4px 6px;color:#3b82f6;font-size:9px;text-transform:uppercase;letter-spacing:0.1em;font-weight:600;">ON&nbsp;TRK</th>
                    <th align="center" style="padding:4px 6px;color:#f59e0b;font-size:9px;text-transform:uppercase;letter-spacing:0.1em;font-weight:600;">PART</th>
                    <th align="center" style="padding:4px 6px;color:#ef4444;font-size:9px;text-transform:uppercase;letter-spacing:0.1em;font-weight:600;">MISS</th>
                    <th align="center" style="padding:4px 6px;color:#22c55e;font-size:9px;text-transform:uppercase;letter-spacing:0.1em;font-weight:600;">R↑</th>
                    <th align="center" style="padding:4px 6px;color:#ef4444;font-size:9px;text-transform:uppercase;letter-spacing:0.1em;font-weight:600;">R↓</th>
                  </tr>
                </thead>
                <tbody>
                  {"".join(grid_rows_html)}
                </tbody>
              </table>
            </div>
          </td>
        </tr>
        """
    cats_html += f"""
        <tr>
          <td colspan="3" style="padding:14px 12px;color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:0.15em;">Total</td>
          <td align="right" style="padding:14px 12px;color:#f1f5f9;font-weight:800;font-size:15px;">{totals['raw_score']} / {totals['max_possible']}</td>
          <td style="padding:14px 12px;color:{bar_color};font-weight:700;">{totals['scaled_percent']}%</td>
        </tr>
      </table>
    </div>
    """

    # Section D: primary source — promise-level evidence
    primary_html = """
    <div style="padding:32px 40px;background:#0b1220;border-top:1px solid #1e293b;">
      <div style="font-size:14px;color:#f1f5f9;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">
        Primary Source — Promise Tracker
      </div>
      <div style="font-size:12px;color:#64748b;margin-bottom:16px;">
        LLM-extracted commitments from management commentary, cross-traced across transcripts.
      </div>
      <table cellpadding="0" cellspacing="0" width="100%" style="border-collapse:collapse;font-size:12px;color:#cbd5e1;">
        <tr style="background:#1e293b;">
          <th align="left"  style="padding:8px 10px;color:#94a3b8;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;border-bottom:1px solid #334155;">Quarter</th>
          <th align="left"  style="padding:8px 10px;color:#94a3b8;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;border-bottom:1px solid #334155;">Type</th>
          <th align="left"  style="padding:8px 10px;color:#94a3b8;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;border-bottom:1px solid #334155;">Status</th>
          <th align="left"  style="padding:8px 10px;color:#94a3b8;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;border-bottom:1px solid #334155;">Target</th>
          <th align="left"  style="padding:8px 10px;color:#94a3b8;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;border-bottom:1px solid #334155;">Commitment</th>
        </tr>
    """
    status_colors = {
        "FULFILLED": "#22c55e", "REVISED_UP": "#22c55e", "ON_TRACK": "#3b82f6",
        "PARTIALLY_FULFILLED": "#f59e0b", "PENDING": "#64748b", "NEW": "#64748b",
        "REVISED_DOWN": "#ef4444", "MISSED": "#ef4444",
    }
    for p in primary[:15]:
        q = _esc(p.get("first_seen_quarter") or "?")[:10]
        gt = _esc(p.get("guidance_type") or "?")[:18]
        st = _esc(p.get("current_status") or "?")[:22]
        st_color = status_colors.get(p.get("current_status"), "#64748b")
        target = ""
        if p.get("target_value") is not None:
            target = f"{p['target_value']}{p.get('target_unit') or ''}"
        elif p.get("target_date"):
            target = _esc(p["target_date"])
        target = _esc(target)[:14]
        text = _esc(p.get("guidance_text") or "")[:80]
        primary_html += f"""
        <tr>
          <td style="padding:8px 10px;border-bottom:1px solid #1e293b;color:#94a3b8;font-family:monospace;">{q}</td>
          <td style="padding:8px 10px;border-bottom:1px solid #1e293b;color:#cbd5e1;">{gt}</td>
          <td style="padding:8px 10px;border-bottom:1px solid #1e293b;color:{st_color};font-weight:600;">{st}</td>
          <td style="padding:8px 10px;border-bottom:1px solid #1e293b;color:#cbd5e1;font-family:monospace;">{target}</td>
          <td style="padding:8px 10px;border-bottom:1px solid #1e293b;color:#f1f5f9;">{text}</td>
        </tr>
        """
    primary_html += "</table></div>"

    # Section E: secondary source — keyword scan stats
    secondary_html = """
    <div style="padding:32px 40px;background:#0f172a;border-top:1px solid #1e293b;">
      <div style="font-size:14px;color:#f1f5f9;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px;">
        Secondary Source — Transcript Keyword Scan
      </div>
      <div style="font-size:12px;color:#64748b;margin-bottom:16px;">
        Environmental categories scanned across the full transcript corpus.
      </div>
      <table cellpadding="0" cellspacing="0" width="100%" style="border-collapse:collapse;font-size:12px;color:#cbd5e1;">
        <tr style="background:#1e293b;">
          <th align="left"  style="padding:8px 10px;color:#94a3b8;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;border-bottom:1px solid #334155;">Category</th>
          <th align="right" style="padding:8px 10px;color:#94a3b8;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;border-bottom:1px solid #334155;">Mentions</th>
          <th align="right" style="padding:8px 10px;color:#94a3b8;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;border-bottom:1px solid #334155;">Transcripts</th>
          <th align="center" style="padding:8px 10px;color:#94a3b8;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;border-bottom:1px solid #334155;">Execution?</th>
          <th align="center" style="padding:8px 10px;color:#94a3b8;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;border-bottom:1px solid #334155;">Strength</th>
        </tr>
    """
    for s in secondary:
        exec_cell = '<span style="color:#22c55e;font-weight:700;">YES</span>' if s.get("has_execution") else '<span style="color:#475569;">—</span>'
        bar = _strength_bar(s.get("signal_strength", 0))
        s_color = "#22c55e" if s["signal_strength"] >= 4 else ("#3b82f6" if s["signal_strength"] >= 3 else "#64748b")
        secondary_html += f"""
        <tr>
          <td style="padding:8px 10px;border-bottom:1px solid #1e293b;color:#f1f5f9;">{_esc(s['label'])}</td>
          <td align="right" style="padding:8px 10px;border-bottom:1px solid #1e293b;color:#cbd5e1;font-family:monospace;">{s['mentions']}</td>
          <td align="right" style="padding:8px 10px;border-bottom:1px solid #1e293b;color:#cbd5e1;font-family:monospace;">{s['transcripts_with_hits']}</td>
          <td align="center" style="padding:8px 10px;border-bottom:1px solid #1e293b;">{exec_cell}</td>
          <td align="center" style="padding:8px 10px;border-bottom:1px solid #1e293b;color:{s_color};font-family:monospace;letter-spacing:0.1em;">{bar}</td>
        </tr>
        """
    secondary_html += "</table></div>"

    # Section F: footer
    footer_html = f"""
    <div style="padding:24px 40px;background:#020617;border-top:1px solid #1e293b;">
      <div style="font-size:10px;color:#475569;line-height:1.6;">
        MRI — Market Regime Intelligence. Decision-support analytics; not SEBI-registered investment advice.
        Generated by the MRI Expansion Lens engine from the {h['symbol']} transcript corpus.<br>
        No buy/sell signals. No price targets. No trading calls. PE Score is a relative rerating-probability indicator.
      </div>
      <div style="font-size:10px;color:#334155;margin-top:12px;">
        Report {h['generated_at_iso']} · perx_pe_scores v1
      </div>
    </div>
    """

    html_doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Expansion Lens — {_esc(h['company_name'])} ({_esc(h['symbol'])})</title>
</head>
<body style="margin:0;padding:0;background:#020617;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;color:#cbd5e1;">
  <div style="max-width:920px;margin:0 auto;background:#0f172a;">
    {bottom_line_html}
    {credibility_html}
    {checks_html}
    {header_html}
    {drivers_html}
    {cats_html}
    {cross_check_html}
    {fin_breakdown_html}
    {price_html}
    {primary_html}
    {secondary_html}
    {footer_html}
  </div>
</body></html>"""

    return html_doc


# ── Email send ───────────────────────────────────────────────────────

def _send_pe_expansion_email(recipient_email: str, report: dict[str, Any]) -> dict[str, Any]:
    """Send the Expansion Lens HTML email via SES, surfacing real errors.

    Uses the platform's shared SES configuration (SENDER_EMAIL,
    resolve_ses_region, get_ses_client) — same as PERX / GuidanceCheck /
    RiskAudit — but does its own try/except so the actual SES error
    message can be returned to the caller. Falls back to writing the
    HTML to outputs/ for QA when sending fails.

    Returns one of:
      {status: 'sent', message_id}
      {status: 'send_failed', warning: '<SES error>'}
      {status: 'dev_logged', path: '...', warning: '<SES error>'}
    """
    h = report["header"]
    subject = f"Expansion Lens — {h['company_name']} ({h['symbol']}) · {h['pe_score']}/100"
    html_body = render_pe_expansion_email(report)

    # Pre-flight checks — surface common config issues before hitting SES
    if not recipient_email:
        return {"status": "send_failed", "warning": "recipient_email is empty"}
    if not SENDER_EMAIL:
        return {"status": "send_failed",
                "warning": "SENDER_EMAIL is not configured (set SES_SENDER_EMAIL env var)"}
    if not aws_credentials_present():
        return {"status": "send_failed",
                "warning": "AWS credentials not present in environment"}

    try:
        ses_region = resolve_ses_region()
        ses = get_ses_client(ses_region)
        resp = ses.send_email(
            Source=SENDER_EMAIL,
            Destination={"ToAddresses": [recipient_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
            },
        )
        return {"status": "sent", "message_id": resp.get("MessageId")}
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        warning = f"SES {error_code}: {error_msg}"
        logger.error(f"SES ClientError sending to {recipient_email}: {warning}")
    except Exception as e:
        warning = f"{type(e).__name__}: {e}"
        logger.error(f"SES send failed for {recipient_email}: {warning}")

    # SES send failed — keep a local copy for QA / debugging.
    out_dir = "outputs"
    try:
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"pe_expansion_email_{h['symbol']}.html")
        with open(out_path, "w") as f:
            f.write(html_body)
        return {"status": "dev_logged", "path": out_path, "warning": warning}
    except Exception as write_err:
        logger.error(f"Could not write dev fallback file: {write_err}")
        return {"status": "send_failed", "warning": warning}


def _log_email(client_id: str | None, recipient: str, report: dict[str, Any],
               send_result: dict[str, Any]) -> None:
    """Append to email_log so this is auditable alongside GuidanceCheck / PERX emails."""
    h = report["header"]
    # Coerce to plain str/None in case the caller passed a FastAPI Query/Depends object.
    # Query/Depends objects have a non-trivial str() repr that breaks psycopg2,
    # so we only accept plain strings or None.
    if client_id is not None and not isinstance(client_id, str):
        client_id = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO email_log
                 (client_id, date, email_type, service, subject, status)
               VALUES (%s, NOW(), 'pe_expansion_report', 'ses', %s, %s)""",
            (client_id, f"Expansion Lens — {h['company_name']} ({h['symbol']}) · {h['pe_score']}/100",
             send_result.get("status", "unknown")),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.warning(f"email_log insert failed: {e}")


# ── Routes ───────────────────────────────────────────────────────────

# IMPORTANT: /suggest and /top10 must be registered BEFORE the /{symbol}
# catch-all, otherwise FastAPI's route-order matching would hijack them as
# symbol names ("suggest", "top10") and return PE reports for non-existent
# companies instead of the autocomplete/top-10 responses.

@router.get("/suggest")
def suggest_pe_expansion(q: str = Query("", description="Symbol or company name prefix"),
                         limit: int = Query(10, ge=1, le=500)) -> dict[str, Any]:
    """Autocomplete from the 149-symbol universe (perx_pe_scores JOIN stock_sectors).

    Empty `q` returns top N by pe_score desc. Non-empty `q` filters by
    `symbol ILIKE '%q%'` OR `company_name ILIKE '%q%'` (case-insensitive substring).
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        like = f"%{q.strip()}%"
        cur.execute(
            """SELECT p.symbol,
                      COALESCE(s.company_name, p.symbol) AS company_name,
                      p.pe_score,
                      s.industry AS sector
               FROM perx_pe_scores p
               LEFT JOIN stock_sectors s ON s.symbol = p.symbol
               WHERE p.symbol ILIKE %s OR s.company_name ILIKE %s
               ORDER BY p.pe_score DESC NULLS LAST
               LIMIT %s""",
            (like, like, limit),
        )
        rows = cur.fetchall()
        return {
            "results": [
                {
                    "symbol": r["symbol"],
                    "company_name": r["company_name"],
                    "pe_score": float(r["pe_score"]) if r["pe_score"] is not None else None,
                    "sector": r.get("sector"),
                }
                for r in rows
            ]
        }
    finally:
        conn.close()


@router.get("/top10")
def top10_pe_expansion() -> dict[str, Any]:
    """Top 10 by PE Expansion score from the 149-universe snapshot.

    `as_of` = MAX(generated_at) from perx_pe_scores — the timestamp of the
    last `--persist` run. Manual refresh only: run
    `python -m engine_perx.pe_signals --persist` to update.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT p.symbol,
                      COALESCE(s.company_name, p.symbol) AS company_name,
                      p.pe_score,
                      s.industry AS sector
               FROM perx_pe_scores p
               LEFT JOIN stock_sectors s ON s.symbol = p.symbol
               ORDER BY p.pe_score DESC NULLS LAST
               LIMIT 10"""
        )
        rows = cur.fetchall()
        cur.execute("SELECT COUNT(*) AS c, MAX(generated_at) AS as_of FROM perx_pe_scores")
        meta = cur.fetchone()
        return {
            "as_of": meta["as_of"].isoformat() if meta["as_of"] else None,
            "total_in_universe": meta["c"],
            "results": [
                {
                    "rank": i + 1,
                    "symbol": r["symbol"],
                    "company_name": r["company_name"],
                    "pe_score": float(r["pe_score"]) if r["pe_score"] is not None else None,
                    "sector": r.get("sector"),
                }
                for i, r in enumerate(rows)
            ],
        }
    finally:
        conn.close()


@router.get("/{symbol}")
def get_pe_expansion(symbol: str) -> dict[str, Any]:
    """Return the full PE Expansion report JSON for a symbol."""
    sym = symbol.upper().replace(".NS", "").replace(".BO", "").strip()
    if not sym:
        raise HTTPException(status_code=400, detail="symbol is required")
    try:
        report = build_pe_expansion_report(sym)
    except Exception as e:
        logger.error(f"build_pe_expansion_report({sym}) failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to build report: {e}")

    # Light cache hint: caller should set If-None-Match handling if needed.
    return report


# ── Bear vs Bull Debate (FeatureRequest 2026-06-19, Phase 3) ────────

@router.post("/{symbol}/debate")
def run_pe_expansion_debate(
    symbol: str,
    include_adjudicator: bool = Query(
        False,
        description="Fire a 3rd LLM call to pick a winner. Costs +$0.001 and +5s.",
    ),
):
    """Generate bear vs bull debate for the PE Expansion rerating thesis of a symbol.

    Same caching contract as /api/guidance/{symbol}/debate: first call fires
    ~2 LLM calls (~$0.002), re-opens with unchanged data are instant + free.
    Cache key = sha256 of the deterministic context payload (built from
    build_pe_expansion_context, which wraps engine_perx.pe_signals).
    """
    from engine_debate.context_pe_expansion import build_pe_expansion_context
    from engine_debate.debate_engine import run_debate

    sym = symbol.upper().replace(".NS", "").replace(".BO", "").strip()
    if not sym:
        raise HTTPException(status_code=400, detail="symbol is required")

    context_payload = build_pe_expansion_context(sym)
    result = run_debate(
        sym,
        context_kind="pe_expansion",
        context_payload=context_payload,
        include_adjudicator=include_adjudicator,
    )
    return result.to_dict()


@router.post("/email/{symbol}")
def email_pe_expansion(symbol: str, to: str = Query(..., description="Recipient email"),
                       client_id: str | None = Query(None)) -> dict[str, Any]:
    """Build the report, render the HTML email, send via SES, log to email_log."""
    sym = symbol.upper().replace(".NS", "").replace(".BO", "").strip()
    if not sym:
        raise HTTPException(status_code=400, detail="symbol is required")
    if "@" not in to or "." not in to:
        raise HTTPException(status_code=400, detail="invalid 'to' email address")

    try:
        report = build_pe_expansion_report(sym)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to build report: {e}")

    send_result = _send_pe_expansion_email(to, report)
    _log_email(client_id, to, report, send_result)

    return {
        "status": send_result.get("status"),
        "symbol": sym,
        "to": to,
        "pe_score": report["header"]["pe_score"],
        "message_id": send_result.get("message_id"),
        "dev_path": send_result.get("path"),
        "warning": send_result.get("warning"),
    }


@router.get("/email/preview/{symbol}", response_class=HTMLResponse)
def preview_pe_expansion_email(symbol: str) -> HTMLResponse:
    """Render the HTML email in a browser without sending. Useful for QA."""
    sym = symbol.upper().replace(".NS", "").replace(".BO", "").strip()
    report = build_pe_expansion_report(sym)
    return HTMLResponse(content=render_pe_expansion_email(report))
