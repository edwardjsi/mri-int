"""
ConvictionEngine alert email builder (Decision 097).

Lives in its own module so it doesn't depend on engine_core.email_service
(which may have unrelated in-progress edits).
"""

from __future__ import annotations
from typing import Iterable

# Zone colors used by the alert email — match the React UI palette.
ZONE_COLOR: dict[str, tuple[str, str]] = {
    "ADD ZONE":      ("#14532d", "#4ade80"),
    "HOLD ZONE":     ("#451a03", "#fbbf24"),
    "REDUCE ZONE":   ("#7f1d1d", "#f87171"),
    "THESIS BROKEN": ("#500",    "#fff"),
    "WATCHING":      ("#1e293b", "#94a3b8"),
}


def build_conviction_alert_email_html(flips: Iterable[dict]) -> str:
    """Build an HTML email summarising management verdict flips.

    `flips` is an iterable of dicts with keys:
        symbol, old_verdict, new_verdict, accuracy_pct, lag_score,
        consecutive_miss_quarters, sources (list[str])
    """
    flips = list(flips)
    rows_html = ""
    for f in flips:
        new_bg, new_fg = ZONE_COLOR.get(f.get("new_verdict", "WATCHING"), ("#1e293b", "#94a3b8"))
        old_bg, old_fg = ZONE_COLOR.get(f.get("old_verdict", "WATCHING"), ("#1e293b", "#94a3b8"))
        sources_html = "".join(
            '<span style="background:#1e293b;color:#94a3b8;font-size:0.7rem;'
            'padding:2px 8px;border-radius:10px;margin-right:4px;">'
            + str(s) + '</span>'
            for s in f.get("sources", [])
        )
        rows_html += (
            '<tr>'
            '<td style="padding:12px 14px;border-bottom:1px solid #1e293b;font-weight:700;color:#f8fafc;">'
            + str(f.get("symbol", "?"))
            + '<div style="margin-top:4px;font-size:0.7rem;font-weight:500;">' + sources_html + '</div>'
            '</td>'
            '<td style="padding:12px 14px;border-bottom:1px solid #1e293b;text-align:center;">'
            '<span style="background:' + old_bg + ';color:' + old_fg + ';font-size:0.7rem;font-weight:700;'
            'padding:4px 10px;border-radius:14px;text-transform:uppercase;letter-spacing:0.06em;">'
            + str(f.get("old_verdict", "?")) + '</span>'
            '</td>'
            '<td style="padding:12px 14px;border-bottom:1px solid #1e293b;text-align:center;color:#64748b;font-size:1.2rem;">→</td>'
            '<td style="padding:12px 14px;border-bottom:1px solid #1e293b;text-align:center;">'
            '<span style="background:' + new_bg + ';color:' + new_fg + ';font-size:0.7rem;font-weight:700;'
            'padding:4px 10px;border-radius:14px;text-transform:uppercase;letter-spacing:0.06em;">'
            + str(f.get("new_verdict", "?")) + '</span>'
            '</td>'
            '<td style="padding:12px 14px;border-bottom:1px solid #1e293b;text-align:center;color:#cbd5e1;">'
            + f'{float(f.get("accuracy_pct", 0)):.1f}%'
            '</td>'
            '<td style="padding:12px 14px;border-bottom:1px solid #1e293b;text-align:center;color:#f87171;font-weight:700;">'
            + str(int(f.get("consecutive_miss_quarters", 0))) + 'q'
            '</td>'
            '</tr>'
        )

    n = len(flips)
    plural = "s" if n != 1 else ""
    return (
        '<html><body style="margin:0;padding:0;background:#020617;font-family:system-ui,-apple-system,sans-serif;color:#e2e8f0;">'
        '<div style="max-width:720px;margin:0 auto;padding:24px;">'
        '<h1 style="margin:0 0 8px;font-size:1.6rem;color:#f8fafc;">'
        '🚨 Conviction Alert — ' + str(n) + ' verdict flip' + plural + '</h1>'
        '<p style="margin:0 0 24px;color:#94a3b8;font-size:0.95rem;">'
        'The following companies crossed a zone boundary in this quarter\u2019s run. '
        'Zone changes indicate a meaningful shift in management credibility — '
        'review before the next earnings call.</p>'
        '<table style="width:100%;border-collapse:collapse;background:#0f172a;border-radius:8px;overflow:hidden;border:1px solid #1e293b;">'
        '<thead><tr style="background:#1e293b;">'
        '<th style="padding:10px 14px;text-align:left;color:#cbd5e1;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;">Symbol</th>'
        '<th style="padding:10px 14px;color:#cbd5e1;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;">Old</th>'
        '<th style="padding:10px 14px;"></th>'
        '<th style="padding:10px 14px;color:#cbd5e1;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;">New</th>'
        '<th style="padding:10px 14px;color:#cbd5e1;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;">Acc</th>'
        '<th style="padding:10px 14px;color:#cbd5e1;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;">Lag</th>'
        '</tr></thead>'
        '<tbody>' + rows_html + '</tbody>'
        '</table>'
        '<p style="margin:24px 0 0;color:#475569;font-size:0.75rem;">'
        'You\u2019re receiving this because conviction_alerts is enabled in your alert preferences. '
        'Manage in Settings → Alerts.</p>'
        '</div></body></html>'
    )
