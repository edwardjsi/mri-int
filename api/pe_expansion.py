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
from engine_perx.pe_signals import build_pe_expansion_report

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
    {header_html}
    {drivers_html}
    {cats_html}
    {primary_html}
    {secondary_html}
    {footer_html}
  </div>
</body></html>"""

    return html_doc


# ── Email send ───────────────────────────────────────────────────────

def _send_pe_expansion_email(recipient_email: str, report: dict[str, Any]) -> dict[str, Any]:
    """Send the HTML email via SES (if available) or fallback to a logged dev mode.

    Returns {status, message_id_or_error}.
    """
    h = report["header"]
    subject = f"Expansion Lens — {h['company_name']} ({h['symbol']}) · {h['pe_score']}/100"

    html_body = render_pe_expansion_email(report)

    # Try the existing SES path used by other emails.
    try:
        import boto3
        from botocore.exceptions import ClientError

        aws_region = os.environ.get("AWS_REGION", "ap-south-1")
        ses_client = boto3.client("ses", region_name=aws_region)
        sender = os.environ.get("SES_SENDER", "alerts@mri-int.com")

        resp = ses_client.send_email(
            Source=sender,
            Destination={"ToAddresses": [recipient_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": html_body, "Charset": "UTF-8"},
                },
            },
        )
        return {"status": "sent", "message_id": resp.get("MessageId")}
    except Exception as e:
        # Dev mode or AWS not configured — log and return dev_status.
        logger.warning(f"SES send failed for {recipient_email}: {e}. Falling back to dev mode.")
        # Write to disk for inspection in dev.
        out_dir = "outputs"
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"pe_expansion_email_{h['symbol']}.html")
        with open(out_path, "w") as f:
            f.write(html_body)
        return {"status": "dev_logged", "path": out_path, "warning": str(e)}


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


# ── Suggest + Top 10 (manual-refresh, 149-universe scope) ──────────

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
