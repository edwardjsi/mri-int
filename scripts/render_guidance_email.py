#!/usr/bin/env python3
"""
Offline renderer for the GuidanceCheck email — produces HTML files under
outputs/ for visual spot-check after the email section enhancement.

Usage:
    venv/bin/python3 scripts/render_guidance_email.py [SYMBOL ...]

If no symbols are given, defaults to CGCL, ASHOKA, INFY (known-good stocks
that should have full intonation data per the priming runs on 2026-06-15/16).

Outputs:
    outputs/guidance_email_<SYMBOL>.html  — full HTML email
    outputs/guidance_email_<SYMBOL>.txt   — section presence summary

Requires DB access via engine_core.db.get_connection.
"""

import os
import sys
import json
from datetime import date

# Make repo root importable
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))

from engine_core.db import get_connection
from engine_core.email_service import build_guidance_report_email_html


DEFAULT_SYMBOLS = ["CGCL", "ASHOKA", "INFY"]


def _section_presence(html: str) -> dict:
    """Return a dict of which email sections are present."""
    return {
        "header_card":           "GuidanceCheck · Management Credibility Report" in html,
        "header_metadata_band":  "transcripts analyzed" in html or "promises extracted" in html or "numerical guidance" in html,
        "tone_monitor":          "🎙️ Management Tone" in html,
        "tone_shift_chip":       "🚨 TONE SHIFT" in html,
        "no_verified_warning":   "No verified promises yet" in html,
        "credibility_summary":   "Trust Score" in html or "ADD ZONE" in html or "HOLD ZONE" in html,
        "achieved_section":      "Kept" in html,
        "missed_section":        "Broken" in html,
        "partial_section":       "Partial" in html,
        "upcoming_section":      "Upcoming" in html,
        "integrity_signal":      "integrity" in html.lower() or "MODERATE" in html or "HIGH" in html,
        "quarter_comparison":    "Quarter Comparison" in html,
        "integrity_timeline":    "Integrity by Quarter" in html,
        "tone_trajectory":       "Tone trajectory" in html,
        "size_bytes":            len(html),
    }


def render_symbol(symbol: str, output_dir: str) -> dict:
    sym = symbol.upper().strip()
    print(f"  [{sym}] building payload from live DB...")
    conn = get_connection()
    try:
        # Import here so test/CI paths without DB won't break collection
        from api.guidance import _build_report_payload
        payload = _build_report_payload(conn, sym)
    finally:
        try:
            conn.close()
        except Exception:
            pass

    # Enrich with narrative_credibility (matches what the live /email endpoint
    # does, so we render exactly what gets emailed)
    try:
        from engine_guidance.narrative_credibility_scorer import NarrativeCredibilityScorer
        nc = NarrativeCredibilityScorer().compute_score(sym)
        if nc.get("current_verdict"):
            payload["narrative_credibility"] = nc
    except Exception as e:
        print(f"  [{sym}] narrative_credibility lookup skipped: {e}")

    print(f"  [{sym}] rendering HTML email ({sum(len(str(v)) for v in payload.values())} chars payload)...")
    html = build_guidance_report_email_html(payload)

    os.makedirs(output_dir, exist_ok=True)
    html_path = os.path.join(output_dir, f"guidance_email_{sym}.html")
    summary_path = os.path.join(output_dir, f"guidance_email_{sym}.txt")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    summary = _section_presence(html)
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(summary, indent=2))

    print(f"  [{sym}] ✓ wrote {html_path} ({len(html)} bytes)")
    return summary


def main():
    args = sys.argv[1:]
    symbols = [s.upper() for s in args] if args else DEFAULT_SYMBOLS
    output_dir = os.path.abspath(os.path.join(HERE, "..", "outputs"))

    print(f"\nRendering GuidanceCheck emails for: {', '.join(symbols)}")
    print(f"Output dir: {output_dir}\n")

    results = {}
    for sym in symbols:
        try:
            results[sym] = render_symbol(sym, output_dir)
        except Exception as e:
            print(f"  [{sym}] ✗ FAILED: {e}")
            results[sym] = {"error": str(e)}

    # Print section-presence matrix
    print("\n" + "=" * 70)
    print("Section presence matrix")
    print("=" * 70)
    section_keys = [
        "header_card", "header_metadata_band", "tone_monitor", "tone_shift_chip",
        "no_verified_warning", "credibility_summary", "achieved_section",
        "missed_section", "partial_section", "upcoming_section",
        "integrity_signal", "quarter_comparison", "integrity_timeline",
        "tone_trajectory", "size_bytes",
    ]
    header = f"{'Section':<24}" + "".join(f"{sym:<14}" for sym in symbols)
    print(header)
    print("-" * len(header))
    for key in section_keys:
        row = f"{key:<24}"
        for sym in symbols:
            r = results.get(sym, {})
            if "error" in r:
                row += f"{'ERR':<14}"
            else:
                v = r.get(key, False)
                if isinstance(v, bool):
                    row += f"{'✓' if v else '·':<14}"
                else:
                    row += f"{str(v):<14}"
        print(row)
    print()


if __name__ == "__main__":
    main()
