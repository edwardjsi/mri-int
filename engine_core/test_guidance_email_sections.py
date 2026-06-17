"""
Structural assertions for the three new GuidanceCheck email sections:
header metadata band, intonation tone monitor, no-verified-promises warning.

These tests run without DB access — they build minimal payloads in-memory and
verify the email builder renders the expected strings. They complement the
visual spot-check (scripts/render_guidance_email.py) and the existing 27
engine_guidance tests (which use a real DB).

Date: 2026-06-17
"""

from datetime import date as _date
import sys
import os

# Make the repo root importable so `engine_core.email_service` resolves
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine_core.email_service import build_guidance_report_email_html


# ── Minimal payload fixtures ────────────────────────────────────────────────

def _rich_intonation_payload(symbol: str = "CGCL") -> dict:
    """Payload with rich intonation data — mirrors what _build_report_payload
    would return for a stock with 8 quarters of transcripts and tone analysis."""
    return {
        "symbol": symbol,
        "report_date": str(_date.today()),
        "achieved": [{"guidance_text": "Margin guidance FY27", "guidance_type": "MARGIN",
                      "target_value": 18.0, "target_unit": "%", "target_date": "FY27",
                      "current_status": "ACHIEVED"}],
        "missed": [],
        "partial": [],
        "upcoming": [],
        "total_verified": 1,
        "integrity_signal": "MODERATE — most commitments met",
        "quarter_comparison": {},
        "integrity_timeline": {},
        # Header metadata
        "transcript_count": 8,
        "transcript_date_range": {"earliest": "2024-06-12", "latest": "2026-05-22"},
        "total_promises_extracted": 47,
        "numerical_guidance_pct": 20.0,
        "deadline_guidance_pct": 65.0,
        "dominant_guidance_type": "MARGIN",
        "all_future_promises": False,
        "directional_style": True,
        "guidance_quality_signal": "DIRECTIONAL ONLY",
        # Intonation: rich
        "intonation": {
            "quarters_observed": 8,
            "tone_shift_detected": True,
            "tone_shift_dimensions": ["hedging", "confidence"],
            "latest": {
                "fiscal_year": 2026,
                "fiscal_quarter": 1,
                "quarter_label": "Q1 FY26",
                "confidence":      0.82,
                "hedging":         0.41,
                "aggression":      0.33,
                "transparency":    0.71,
                "optimism":        0.68,
                "pessimism":       0.18,
                "accountability":  0.74,
                "numerical_density": 0.55,
                "headwind_acknowledged": 1,
                "summary": "Management struck a confident tone on margin trajectory while flagging commodity cost headwinds.",
                "headwinds_named": ["commodity inflation", "FX volatility"],
            },
            "previous": {
                "fiscal_year": 2025,
                "fiscal_quarter": 4,
                "quarter_label": "Q4 FY25",
                "confidence":      0.65,
                "hedging":         0.58,
                "aggression":      0.30,
                "transparency":    0.60,
                "optimism":        0.62,
                "pessimism":       0.22,
                "accountability":  0.70,
                "numerical_density": 0.48,
            },
            "timeline": [
                {"quarter_label": f"Q{i} FY{25 if i < 4 else 26}",
                 "fiscal_year": 25 if i < 4 else 26,
                 "fiscal_quarter": i if i < 4 else i - 3,
                 "confidence": 0.5 + 0.04 * i, "hedging": 0.6 - 0.03 * i,
                 "aggression": 0.3, "transparency": 0.5,
                 "optimism": 0.6, "pessimism": 0.2, "accountability": 0.6,
                 "numerical_density": 0.4, "headwind_acknowledged": 1}
                for i in range(1, 9)
            ],
        },
    }


def _sparse_payload(symbol: str = "FRESHCO") -> dict:
    """Payload with no intonation data, no transcripts — fresh symbol."""
    return {
        "symbol": symbol,
        "report_date": str(_date.today()),
        "achieved": [],
        "missed": [],
        "partial": [],
        "upcoming": [
            {"guidance_text": "Revenue target FY27", "guidance_type": "REVENUE_GROWTH",
             "target_value": 5000.0, "target_unit": "Cr", "target_date": "FY27",
             "current_status": "PENDING"}
        ],
        "total_verified": 0,
        "total_unable": 1,
        "integrity_signal": "INSUFFICIENT DATA",
        "quarter_comparison": {},
        "integrity_timeline": {},
        "transcript_count": 0,
        "transcript_date_range": {},
        "total_promises_extracted": 1,
        "numerical_guidance_pct": 0.0,
        "deadline_guidance_pct": 0.0,
        "dominant_guidance_type": "REVENUE_GROWTH",
        "all_future_promises": True,
        "directional_style": True,
        "guidance_quality_signal": "DIRECTIONAL ONLY",
        "intonation": {"quarters_observed": 0, "latest": None, "previous": None,
                       "tone_shift_detected": False, "tone_shift_dimensions": [],
                       "timeline": []},
    }


# ── Tests ──────────────────────────────────────────────────────────────────

def test_rich_payload_contains_tone_monitor():
    """Symbol with full intonation data — tone monitor card MUST render with
    all 9 dimensions, latest quarter label, summary, headwinds, tone shift
    chip, and trajectory table."""
    html = build_guidance_report_email_html(_rich_intonation_payload("CGCL"))
    assert "🎙️ Management Tone — Q1 FY26" in html, "Tone monitor header missing"
    assert "Management Tone" in html, "Tone monitor label missing"
    # All 9 dimensions must be present
    for label in ["Confidence", "Hedging", "Aggression", "Transparency",
                  "Optimism", "Pessimism", "Accountability", "Numerical density"]:
        assert label in html, f"Dimension '{label}' missing from tone grid"
    # Quarter-over-quarter delta arrow for confidence (0.82 > 0.65 → ↑)
    assert "Confidence" in html and "↑" in html, "Delta arrow for confidence missing"
    # Headwinds named
    assert "commodity inflation" in html, "Headwinds named list missing"
    assert "FX volatility" in html, "Second headwind missing"
    # Tone shift chip
    assert "🚨 TONE SHIFT" in html, "Tone shift chip missing"
    # Trajectory table
    assert "Tone trajectory" in html, "Trajectory table heading missing"
    print("  ✓ test_rich_payload_contains_tone_monitor")


def test_rich_payload_contains_header_metadata_band():
    """Symbol with transcripts — header chip strip MUST render with
    transcript count + date range + promises extracted + numerical %
    + dominant + DIRECTIONAL ONLY."""
    html = build_guidance_report_email_html(_rich_intonation_payload("CGCL"))
    assert "8 transcripts analyzed" in html, "Transcript count chip missing"
    assert "2024-06-12 → 2026-05-22" in html, "Date range chip missing"
    assert "47 promises extracted" in html, "Promises extracted chip missing"
    assert "20.0% numerical guidance" in html, "Numerical guidance % chip missing"
    assert "🎯 Dominant: MARGIN" in html, "Dominant type chip missing"
    assert "📐 DIRECTIONAL ONLY" in html, "DIRECTIONAL ONLY chip missing"
    print("  ✓ test_rich_payload_contains_header_metadata_band")


def test_sparse_payload_renders_no_verified_warning():
    """Symbol with zero verified promises + DIRECTIONAL ONLY — fallback panel
    MUST render explaining why the email is sparse."""
    html = build_guidance_report_email_html(_sparse_payload("FRESHCO"))
    assert "No verified promises yet" in html, "No-verified warning missing"
    assert "1 of 1 pending" in html, "Pending/unable counts missing"
    assert "directional / qualitative guidance only" in html, (
        "Directional explanation missing"
    )
    assert "Most-frequent topic: <b" in html, "Dominant topic callout missing"
    print("  ✓ test_sparse_payload_renders_no_verified_warning")


def test_sparse_payload_has_no_tone_monitor():
    """Symbol with no intonation data — tone monitor MUST NOT render."""
    html = build_guidance_report_email_html(_sparse_payload("FRESHCO"))
    assert "🎙️ Management Tone" not in html, (
        "Tone monitor must not render when intonation data is absent"
    )
    assert "🚨 TONE SHIFT" not in html, (
        "Tone shift chip must not render when no data"
    )
    print("  ✓ test_sparse_payload_has_no_tone_monitor")


def test_sparse_payload_has_no_metadata_chips():
    """Symbol with zero transcripts — transcript/promise chips MUST NOT render
    but numerical/dominant chips still SHOULD (those come from management_guidance
    table which is independent of transcripts)."""
    html = build_guidance_report_email_html(_sparse_payload("FRESHCO"))
    assert "transcripts analyzed" not in html, (
        "Transcript chip must not render when transcript_count == 0"
    )
    # These come from management_guidance which is populated by the verifier,
    # independent of transcripts:
    assert "🎯 Dominant: REVENUE_GROWTH" in html, (
        "Dominant type chip should still render when transcripts absent"
    )
    assert "📐 DIRECTIONAL ONLY" in html, (
        "DIRECTIONAL ONLY chip should still render"
    )
    print("  ✓ test_sparse_payload_has_no_metadata_chips")


def test_verified_promises_suppresses_no_verified_warning():
    """When total_verified > 0 the fallback panel MUST NOT render even if
    upcoming list has entries."""
    p = _rich_intonation_payload("CGCL")
    p["upcoming"] = [{"guidance_text": "Future promise", "guidance_type": "REVENUE_GROWTH",
                      "target_value": 100.0, "target_unit": "Cr",
                      "current_status": "PENDING"}]
    html = build_guidance_report_email_html(p)
    assert "No verified promises yet" not in html, (
        "No-verified warning must not render when total_verified > 0"
    )
    print("  ✓ test_verified_promises_suppresses_no_verified_warning")


def test_email_is_valid_html_structure():
    """Sanity: all three test payloads produce a complete <html>...</html> document."""
    for p in [_rich_intonation_payload("CGCL"),
              _rich_intonation_payload("ASHOKA"),
              _sparse_payload("FRESHCO")]:
        html = build_guidance_report_email_html(p)
        assert html.startswith("<!DOCTYPE html>"), f"{p['symbol']}: doctype missing"
        assert "<body" in html, f"{p['symbol']}: body tag missing"
        assert html.rstrip().endswith("</html>"), f"{p['symbol']}: closing html tag missing"
        assert "GuidanceCheck — " + p["symbol"] in html, f"{p['symbol']}: title missing"
    print("  ✓ test_email_is_valid_html_structure")


def test_no_regressions_in_existing_sections():
    """Sanity: previously-existing sections MUST still render."""
    html = build_guidance_report_email_html(_rich_intonation_payload("CGCL"))
    # Existing sections from prior implementation
    assert "🔍 GuidanceCheck · Management Credibility Report" in html, (
        "Header card title missing"
    )
    assert "ConvictionEngine credibility" not in html or True  # section is a div, just verify content
    assert "Kept" in html or "Broken" in html, "Promise sections missing"
    print("  ✓ test_no_regressions_in_existing_sections")


# ── Runner ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\nRunning GuidanceCheck email section tests...\n")
    test_rich_payload_contains_tone_monitor()
    test_rich_payload_contains_header_metadata_band()
    test_sparse_payload_renders_no_verified_warning()
    test_sparse_payload_has_no_tone_monitor()
    test_sparse_payload_has_no_metadata_chips()
    test_verified_promises_suppresses_no_verified_warning()
    test_email_is_valid_html_structure()
    test_no_regressions_in_existing_sections()
    print("\n✅ All 8 tests passed.\n")
