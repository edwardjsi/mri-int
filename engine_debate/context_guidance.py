"""
engine_debate.context_guidance — Build the deterministic context payload
that feeds the GuidanceCheck bear/bull debate.

Decoupled from api/guidance.py:_build_report_payload — same DB tables,
same fields, but a focused shape: only what the LLM needs to argue
from. No UI-specific fields, no per-promise items (those would explode
the prompt size; we aggregate instead).

Output shape (what the LLM sees):
{
  "symbol": "POLYCAB",
  "credibility": {
    accuracy_pct, total_promises, achieved_count, missed_count,
    partial_count, trend, consecutive_miss_quarters, lag_score,
    current_verdict, previous_verdict, last_verdict_flip, summary
  },
  "intonation": {
    latest_quarter, latest: {9 dims}, previous: {9 dims},
    quarter_over_quarter_delta: {9 dims}, tone_shift_detected,
    tone_shift_dimensions: [...], timeline: [{q, ...9 dims}],
    quarters_observed
  },
  "verifier_summary": {
    n_achieved, n_missed, n_partial, n_pending, n_unable_to_verify,
    unable_reasons: {reason: count, ...}
  },
  "guidance_quality_signal": "DIRECTIONAL ONLY" | "MIXED" | "NUMERICAL",
  "total_material_promises": <int>
}
"""
from __future__ import annotations

import logging
from typing import Any

from engine_core.db import get_connection

logger = logging.getLogger("engine_debate.context_guidance")


def build_guidance_context(symbol: str) -> dict:
    """Assemble the deterministic context payload for the GuidanceCheck debate.

    Pure SQL — no LLM calls. The hash of this dict IS the cache key, so
    any underlying data change will produce a different hash → cache miss
    → fresh debate.
    """
    sym = symbol.upper().strip()
    conn = get_connection()
    try:
        cur = conn.cursor()

        # ── Credibility row ─────────────────────────────────────────────
        cur.execute(
            """SELECT total_promises, achieved_count, missed_count,
                      accuracy_pct, avg_variance_pct, trend,
                      consecutive_miss_quarters, lag_score, last_verdict_flip,
                      current_verdict, previous_verdict
               FROM management_credibility_scores
               WHERE symbol = %s""",
            (sym,),
        )
        cred_row = cur.fetchone()
        credibility = _credibility_block(cred_row)

        # ── Intonation trajectory (latest + previous + delta + timeline) ─
        cur.execute(
            """SELECT fiscal_year, fiscal_quarter,
                      confidence, hedging, aggression, transparency,
                      optimism, pessimism, accountability,
                      numerical_density, headwind_acknowledged,
                      raw, extracted_at
               FROM management_intonation
               WHERE symbol = %s
               ORDER BY fiscal_year DESC, fiscal_quarter DESC
               LIMIT 8""",
            (sym,),
        )
        intonation_rows = cur.fetchall()
        intonation = _intonation_block(intonation_rows)

        # ── Verifier summary (status counts + unable reasons breakdown) ─
        cur.execute(
            """SELECT v.status, v.unable_reason, COUNT(*) as n
               FROM guidance_verification v
               JOIN management_guidance g ON g.id = v.guidance_id
               WHERE g.symbol = %s
               GROUP BY v.status, v.unable_reason""",
            (sym,),
        )
        verifier_summary = _verifier_summary(cur, sym)

        # ── Guidance quality signal (DIRECTIONAL ONLY / MIXED / NUMERICAL) ─
        cur.execute(
            """SELECT
                 COUNT(*) FILTER (WHERE target_value IS NOT NULL) AS n_with_target,
                 COUNT(*) AS n_total
               FROM management_guidance
               WHERE symbol = %s""",
            (sym,),
        )
        qq_row = cur.fetchone()

        def _qgv(r, key):
            if isinstance(r, dict):
                return r.get(key)
            # Tuple fallback
            keys = ["n_with_target", "n_total"]
            return r[keys.index(key)]

        n_with_target = _qgv(qq_row, "n_with_target") or 0
        n_total = _qgv(qq_row, "n_total") or 0
        numerical_pct = (100.0 * n_with_target / n_total) if n_total else 0.0
        if numerical_pct < 30.0:
            quality_signal = "DIRECTIONAL ONLY"
        elif numerical_pct < 70.0:
            quality_signal = "MIXED"
        else:
            quality_signal = "NUMERICAL"

        return {
            "symbol": sym,
            "credibility": credibility,
            "intonation": intonation,
            "verifier_summary": verifier_summary,
            "guidance_quality_signal": quality_signal,
            "total_material_promises": n_total,
        }
    finally:
        conn.close()


# ── Helpers ──────────────────────────────────────────────────────────────


def _credibility_block(row) -> dict:
    if not row:
        return {
            "has_data": False,
            "note": "No credibility row yet — not enough verified promises to score. "
                    "Bear case will rely on tone + verifier data only; bull case has "
                    "limited evidence to cite.",
        }

    def _r(i):
        if isinstance(row, dict):
            keys = ["total_promises", "achieved_count", "missed_count",
                    "accuracy_pct", "avg_variance_pct", "trend",
                    "consecutive_miss_quarters", "lag_score", "last_verdict_flip",
                    "current_verdict", "previous_verdict"]
            return row.get(keys[i])
        return row[i]

    total = _r(0) or 0
    achieved = _r(1) or 0
    missed = _r(2) or 0
    partial = max(0, total - achieved - missed)

    return {
        "has_data": True,
        "accuracy_pct": float(_r(3) or 0),
        "total_promises": total,
        "achieved_count": achieved,
        "missed_count": missed,
        "partial_count": partial,
        "avg_variance_pct": float(_r(4)) if _r(4) is not None else None,
        "trend": _r(5),
        "consecutive_miss_quarters": _r(6) or 0,
        "lag_score": float(_r(7) or 0),
        "last_verdict_flip": str(_r(8)) if _r(8) else None,
        "current_verdict": _r(9),
        "previous_verdict": _r(10),
    }


def _intonation_block(rows) -> dict:
    if not rows:
        return {
            "has_data": False,
            "note": "No intonation data — bear/bull cannot use tone as evidence.",
            "quarters_observed": 0,
        }

    dims = ["confidence", "hedging", "aggression", "transparency",
            "optimism", "pessimism", "accountability",
            "numerical_density", "headwind_acknowledged"]

    def _row_to_dict(r, is_latest=True):
        def _gv(i):
            if isinstance(r, dict):
                keys = ["fiscal_year", "fiscal_quarter"] + dims + ["raw", "extracted_at"]
                return r.get(keys[i])
            return r[i]
        out = {
            "fiscal_year": _gv(0),
            "fiscal_quarter": _gv(1),
            "quarter_label": f"Q{_gv(1)}FY{str(_gv(0))[-2:]}" if _gv(0) and _gv(1) else None,
        }
        for i, dim in enumerate(dims):
            v = _gv(i + 2)
            out[dim] = float(v) if v is not None else None
        return out

    latest = _row_to_dict(rows[0])
    previous = _row_to_dict(rows[1]) if len(rows) > 1 else None

    # Quarter-over-quarter delta (positive = increasing)
    delta = None
    if previous:
        delta = {}
        for dim in dims:
            l = latest.get(dim)
            p = previous.get(dim)
            if l is not None and p is not None:
                d = l - p
                delta[dim] = round(d, 2)
            else:
                delta[dim] = None

    # Tone shift detection: any dimension moves > 1σ between consecutive quarters
    # Or simpler heuristic: any dimension moves > 15 absolute points
    tone_shift_detected = False
    tone_shift_dimensions = []
    if delta:
        for dim in dims:
            d = delta.get(dim)
            if d is not None and abs(d) >= 15:
                tone_shift_detected = True
                tone_shift_dimensions.append({
                    "dim": dim,
                    "delta": d,
                    "direction": "up" if d > 0 else "down",
                })

    timeline = [_row_to_dict(r) for r in rows]  # already DESC

    return {
        "has_data": True,
        "latest_quarter": latest.get("quarter_label"),
        "latest": {k: latest.get(k) for k in dims},
        "previous": ({k: previous.get(k) for k in dims} if previous else None),
        "quarter_over_quarter_delta": delta,
        "tone_shift_detected": tone_shift_detected,
        "tone_shift_dimensions": tone_shift_dimensions,
        "timeline": [{k: row.get(k) for k in dims + ["quarter_label"]} for row in timeline],
        "quarters_observed": len(rows),
    }


def _verifier_summary(cur, sym: str) -> dict:
    """Aggregate status counts + unable_reason breakdown for the symbol."""
    cur.execute(
        """SELECT v.status, COALESCE(v.unable_reason, '') AS reason, COUNT(*) AS n
           FROM guidance_verification v
           JOIN management_guidance g ON g.id = v.guidance_id
           WHERE g.symbol = %s
           GROUP BY v.status, v.unable_reason""",
        (sym,),
    )
    rows = cur.fetchall()

    by_status = {}
    unable_reasons = {}
    for r in rows:
        def _gv(i):
            if isinstance(r, dict):
                return list(r.values())[i]
            return r[i]
        status = _gv(0) or "PENDING"
        reason = _gv(1) or ""
        n = _gv(2) or 0
        by_status[status] = by_status.get(status, 0) + n
        if status == "UNABLE_TO_VERIFY" and reason:
            unable_reasons[reason] = unable_reasons.get(reason, 0) + n

    return {
        "by_status": by_status,
        "unable_reasons": unable_reasons,
        "n_achieved": by_status.get("ACHIEVED", 0),
        "n_missed": by_status.get("MISSED", 0),
        "n_partial": by_status.get("PARTIAL", 0),
        "n_pending": by_status.get("PENDING", 0),
        "n_unable_to_verify": by_status.get("UNABLE_TO_VERIFY", 0),
    }
