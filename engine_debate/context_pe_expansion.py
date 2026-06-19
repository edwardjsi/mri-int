"""
engine_debate.context_pe_expansion — Build the deterministic context payload
that feeds the Expansion Lens bear/bull debate.

Reuses engine_perx.pe_signals.build_pe_expansion_report() to assemble the
report, then trims and reshapes for the LLM context. The LLM does NOT see
the verbatim quotes, status grids, or per-promise details — only the
summary-level state. (If the LLM needs to ground a specific claim, the user
can read those in the actual report above the debate modal.)

Output shape:
{
  "symbol": "POLYCAB",
  "header": {company_name, sector, pe_score, rank, total, bucket,
             generated_at_ist},
  "bottom_line": {summary, action, highlights: [{signal, status, status_label}]},
  "top_drivers": [label, ...],
  "category_breakdown_summary": {
    strong: [...], weak: [...], missing: [...]
  },
  "cross_check": [{dimension, pe_view, indep_view, fin_view, price_view,
                   alignment}, ...],
  "independent_check": {master_score, sector, reasons, updated_at} | null,
  "financial_quality": {score, category, agents: {7 fields}, flags} | null,
  "price_action": {total_score, breakout_state, conditions: {7 booleans},
                   as_of} | null,
  "credibility": <same shape as GuidanceCheck credibility block>,
  "coverage": {n_promises_total, n_quote_verified, n_transcripts, n_quarter_span}
}
"""
from __future__ import annotations

import logging
from typing import Any

from engine_core.db import get_connection

logger = logging.getLogger("engine_debate.context_pe_expansion")


def build_pe_expansion_context(symbol: str) -> dict:
    """Assemble the deterministic context payload for the Expansion Lens debate.

    Calls engine_perx.pe_signals.build_pe_expansion_report() and reshapes
    the result into a focused LLM-friendly context. No LLM calls.
    """
    sym = symbol.upper().strip()
    try:
        report = _call_build_pe_expansion_report(sym)
    except Exception as e:
        logger.exception(f"build_pe_expansion_report({sym}) failed: {e}")
        return _empty_context(sym, error=str(e))

    if not report or "header" not in report:
        return _empty_context(sym, error="No PE Expansion report available")

    # ── Header summary ───────────────────────────────────────────────
    h = report["header"]
    header = {
        "company_name": h.get("company_name"),
        "sector": h.get("sector"),
        "pe_score": h.get("pe_score"),
        "rank": h.get("rank"),
        "total": h.get("total"),
        "bucket": h.get("bucket"),
        "generated_at_ist": h.get("generated_at_ist"),
    }

    # ── Bottom line ──────────────────────────────────────────────────
    bottom_line = report.get("bottom_line") or {
        "summary": None,
        "action": "no_data",
        "highlights": [],
    }

    # ── Category breakdown summary ──────────────────────────────────
    cb_summary = _summarize_categories(report.get("category_breakdown") or [])

    # ── Cross-check ─────────────────────────────────────────────────
    cross_check = report.get("cross_check") or []

    # ── 3 other engines (Independent / Financial Quality / Price Action) ─
    indep = report.get("independent_check")
    fq = report.get("financial_quality")
    pa = report.get("price_action")
    cred = report.get("credibility")

    return {
        "symbol": sym,
        "header": header,
        "bottom_line": bottom_line,
        "top_drivers": report.get("top_drivers") or [],
        "category_breakdown_summary": cb_summary,
        "cross_check": cross_check,
        "independent_check": indep,
        "financial_quality": fq,
        "price_action": pa,
        "credibility": cred,
        "coverage": report.get("coverage") or {},
    }


def _call_build_pe_expansion_report(sym: str) -> dict[str, Any]:
    """Call into engine_perx to assemble the report.

    Done as a separate function so we can patch it in tests, and so the
    import path is explicit (helps when tracing circular dep issues).
    """
    from engine_perx.pe_signals import build_pe_expansion_report
    return build_pe_expansion_report(sym)


def _summarize_categories(breakdown: list[dict]) -> dict:
    """Bucket the 12 categories into strong/weak/missing for the LLM.

    Avoids dumping all 12 rows into the prompt — the LLM only needs
    which categories are firing and which are silent.
    """
    strong, weak, missing = [], [], []
    for row in breakdown:
        label = row.get("label")
        if not label:
            continue
        if row.get("missing"):
            missing.append(label)
        else:
            strength = row.get("signal_strength", 0) or 0
            if strength >= 4:
                strong.append(f"{label} (strength {strength}/5)")
            elif strength <= 2:
                weak.append(f"{label} (strength {strength}/5)")
            else:
                # Middle tier — surface but don't bin
                pass
    return {
        "strong_categories": strong,
        "weak_categories": weak,
        "missing_categories": missing,
        "n_total": len(breakdown),
        "n_strong": len(strong),
        "n_weak": len(weak),
        "n_missing": len(missing),
    }


def _empty_context(sym: str, error: str) -> dict:
    return {
        "symbol": sym,
        "header": None,
        "bottom_line": None,
        "top_drivers": [],
        "category_breakdown_summary": {"strong_categories": [], "weak_categories": [], "missing_categories": []},
        "cross_check": [],
        "independent_check": None,
        "financial_quality": None,
        "price_action": None,
        "credibility": None,
        "coverage": {},
        "error": error,
    }
