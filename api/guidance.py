"""
api/guidance.py — GuidanceCheck FastAPI Router

Endpoints:
    GET  /api/guidance/{symbol}          — Full guidance dashboard for one stock
    GET  /api/guidance/{symbol}/report   — Clean report: trackable promises + verdict
    POST /api/guidance/{symbol}/email    — Send report to user's email
    GET  /api/guidance/portfolio          — Guidance check across user's holdings
    GET  /api/guidance/leaderboard        — Top/bottom credibility scores
    POST /api/guidance/scan/{symbol}      — Trigger extraction for a symbol
    POST /api/guidance/thesis             — Save/update investment thesis
    GET  /api/guidance/thesis/{symbol}    — Get thesis for a symbol
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, BackgroundTasks
from api.deps import get_db, get_current_client
from engine_core.db import get_connection
from datetime import date
import logging

router = APIRouter(prefix="/api/guidance", tags=["guidance"])
logger = logging.getLogger("api.guidance")


def _r(row, i):
    """Safe row access — RealDictCursor dict-like or tuple."""
    if isinstance(row, dict):
        return list(row.values())[i]
    return row[i]


def _fy_label(fy: int | None, fq: int | None) -> str:
    """Format fiscal year + quarter as QxFYy."""
    if fy and fq:
        return f"Q{fq}FY{str(fy)[-2:]}"
    if fy:
        return f"FY{str(fy)[-2:]}"
    return ""


def _build_report_payload(conn, symbol: str) -> dict:
    """
    Build a clean, product-grade guidance report with THREE intelligence layers:
    1. Past Promises Verified — all verified promises with actuals, grouped ACHIEVED/MISSED/PARTIAL
    2. Quarter Comparison — two most recent transcript quarters side-by-side
    3. Integrity Timeline — quarter-by-quarter breakdown of management reliability
    """
    sym = symbol.upper().strip()
    cur = conn.cursor()

    # ── Credibility score ──────────────────────────────────────────────
    cur.execute("SELECT * FROM management_credibility_scores WHERE symbol=%s", (sym,))
    score_row = cur.fetchone()
    credibility = {}
    if score_row:
        credibility = {
            "total_promises": _r(score_row, 1),
            "achieved_count": _r(score_row, 2),
            "missed_count": _r(score_row, 3),
            "accuracy_pct": float(_r(score_row, 4) or 0),
            "avg_variance_pct": float(_r(score_row, 5)) if _r(score_row, 5) else None,
            "trend": _r(score_row, 6),
            # ConvictionEngine (Decision 097) lag fields
            "consecutive_miss_quarters": _r(score_row, 7) or 0,
            "lag_score": float(_r(score_row, 8) or 0),
            "last_verdict_flip": str(_r(score_row, 9)) if _r(score_row, 9) else None,
            "current_verdict": _r(score_row, 10),
            "previous_verdict": _r(score_row, 11),
        }

    # ── Fetch ALL promises with quarter-of-promise and quarter-of-verification ──
    # We join with aae_transcripts to know WHEN the promise was made (transcript date)
    cur.execute(
        """SELECT
             g.guidance_type,
             g.guidance_text,
             g.target_value,
             g.target_unit,
             g.target_date,
             v.status,
             v.actual_value,
             v.variance_pct,
             v.checked_fiscal_year,
             v.checked_fiscal_quarter,
             v.unable_reason,
             t.date,
             EXTRACT(YEAR FROM t.date)::INT as trans_year,
             EXTRACT(QUARTER FROM t.date)::INT as trans_quarter
           FROM management_guidance g
           LEFT JOIN guidance_verification v ON g.id = v.guidance_id
           LEFT JOIN aae_transcripts t ON g.transcript_id = t.id
           WHERE g.symbol = %s
           ORDER BY
             CASE WHEN v.status IN ('ACHIEVED','MISSED','PARTIAL') THEN 0 ELSE 1 END,
             t.date DESC NULLS LAST,
             g.target_date ASC NULLS LAST""",
        (sym,),
    )
    rows = cur.fetchall()

    # Group into categories
    achieved = []  # Verified: target was met
    missed   = []  # Verified: target was NOT met
    partial  = []  # Verified: partially met (within 2pp margin or 25% for revenue)
    upcoming = []  # Has a target_date/quarter in the future OR not yet verified

    for row in rows:
        gtype    = _r(row, 0)
        gtext    = _r(row, 1)
        tval     = _r(row, 2)
        tunit    = _r(row, 3)
        tdate    = _r(row, 4)
        status   = _r(row, 5)
        actual   = _r(row, 6)
        variance = _r(row, 7)
        vfy      = _r(row, 8)   # fiscal year verified
        vfq      = _r(row, 9)   # fiscal quarter verified
        txdate   = _r(row, 10)  # transcript date
        txfy     = _r(row, 11)  # transcript fiscal year
        txfq     = _r(row, 12)  # transcript fiscal quarter

        # Target display string
        target_display = (f"{tval} {tunit or ''}".strip()
                          if tval is not None else
                          (f"by {tdate}" if tdate else ""))

        # Actual result display
        actual_display = ""
        if actual is not None:
            actual_display = f"{float(actual):.1f} {tunit or ''}".strip()
        elif status == "MISSED" and variance is not None:
            actual_display = f"{float(variance):+.1f}% vs target"

        item = {
            "type":         gtype or "OTHER",
            "promise":      gtext,
            "target":       target_display,
            "deadline":     tdate or "",
            "status":       status or "PENDING",
            "actual":       actual_display,
            "variance_pct": float(variance) if variance is not None else None,
            "promised_in":  _fy_label(txfy, txfq) if txfy and txfq else _fy_label(vfy, vfq),
            "verified_in":  _fy_label(vfy, vfq) if vfy and vfq else "",
            "transcript_date": str(txdate) if txdate else "",
            "unable_reason": _r(row, 10),
        }

        if status == "ACHIEVED":
            achieved.append(item)
        elif status == "MISSED":
            missed.append(item)
        elif status == "PARTIAL":
            partial.append(item)
        else:
            upcoming.append(item)

    # ── Summary stats ─────────────────────────────────────────────────
    total     = credibility.get("total_promises", 0)
    accuracy  = credibility.get("accuracy_pct", 0.0)
    trend     = credibility.get("trend", "INSUFFICIENT_DATA")

    # Conviction verdict
    if total < 3:
        verdict = "WATCHING";       verdict_color = "#64748b"; verdict_bg = "#1e293b"
    elif accuracy >= 75:
        verdict = "ADD ZONE" if trend in ("IMPROVING", "STABLE") else "HOLD ZONE"
        verdict_color = "#4ade80"; verdict_bg = "#14532d"
    elif accuracy >= 60:
        verdict = "HOLD ZONE";      verdict_color = "#fbbf24"; verdict_bg = "#451a03"
    elif accuracy >= 40:
        verdict = "REDUCE ZONE";    verdict_color = "#f87171"; verdict_bg = "#7f1d1d"
    else:
        verdict = "THESIS BROKEN";  verdict_color = "#fff";    verdict_bg = "#500"

    circumference = 2 * 3.14159 * 40
    ring_offset   = circumference - (accuracy / 100) * circumference
    ring_color    = ("#4ade80" if accuracy >= 70
                     else "#fbbf24" if accuracy >= 40
                     else "#f87171" if accuracy > 0
                     else "#3b82f6")

    # ── 1. PAST PROMISES VERIFIED ──────────────────────────────────────
    # All verified promises — these are past promises where we have a verdict
    verified_promises = achieved + missed + partial

    # ── 2. QUARTER COMPARISON ──────────────────────────────────────────
    # Get the two most recent transcript quarters
    cur.execute(
        """SELECT DISTINCT
             EXTRACT(YEAR FROM date)::INT as fy,
             EXTRACT(QUARTER FROM date)::INT as fq,
             date
           FROM aae_transcripts
           WHERE symbol = %s
           ORDER BY fy DESC, fq DESC
           LIMIT 2""",
        (sym,),
    )
    trans_quarters = list(cur.fetchall())
    trans_quarters = sorted(trans_quarters, key=lambda r: (_r(r,0) or 0, _r(r,1) or 0))

    quarter_comparison = {"quarters": [], "integrity_by_quarter": {}, "trend": ""}

    if len(trans_quarters) >= 2:
        older_q = trans_quarters[0]  # oldest of the two
        newer_q = trans_quarters[1]  # most recent
        older_fy, older_fq = _r(older_q, 0), _r(older_q, 1)
        newer_fy, newer_fq = _r(newer_q, 0), _r(newer_q, 1)

        # Get promises from each quarter
        def _promises_for_quarter(fy, fq):
            cur.execute(
                """SELECT g.guidance_type, g.guidance_text,
                          g.target_value, g.target_unit, g.target_date,
                          v.status, v.actual_value, v.variance_pct
                   FROM management_guidance g
                   LEFT JOIN guidance_verification v ON g.id = v.guidance_id
                   JOIN aae_transcripts t ON g.transcript_id = t.id
                   WHERE g.symbol = %s
                     AND EXTRACT(YEAR FROM t.date)::INT = %s
                     AND EXTRACT(QUARTER FROM t.date)::INT = %s
                   ORDER BY g.guidance_type, g.guidance_text""",
                (sym, fy, fq),
            )
            rows2 = cur.fetchall()
            items = []
            for r2 in rows2:
                gt2 = _r(r2,0); gt2t = _r(r2,1); tv2 = _r(r2,2)
                tu2 = _r(r2,3); td2 = _r(r2,4); st2 = _r(r2,5)
                av2 = _r(r2,6); vp2 = _r(r2,7)
                tdisp2 = (f"{tv2} {tu2 or ''}".strip() if tv2 is not None
                          else (f"by {td2}" if td2 else ""))
                adisp2 = (f"{float(av2):.1f} {tu2 or ''}".strip() if av2 is not None
                          else (f"{float(vp2):+.1f}% vs target" if vp2 is not None and st2=="MISSED" else ""))
                items.append({"type": gt2 or "OTHER", "promise": gt2t,
                               "target": tdisp2, "status": st2 or "PENDING",
                               "actual": adisp2,
                               "variance_pct": float(vp2) if vp2 is not None else None})
            return items

        older_promises = _promises_for_quarter(older_fy, older_fq)
        newer_promises = _promises_for_quarter(newer_fy, newer_fq)

        # Count verified in older quarter
        older_verified = sum(1 for p in older_promises if p["status"] in ("ACHIEVED","MISSED","PARTIAL"))
        older_achieved = sum(1 for p in older_promises if p["status"] == "ACHIEVED")
        older_missed   = sum(1 for p in older_promises if p["status"] == "MISSED")
        newer_announced = len(newer_promises)

        quarter_comparison = {
            "older_quarter":  _fy_label(older_fy, older_fq),
            "newer_quarter":  _fy_label(newer_fy, newer_fq),
            "older_promises": older_promises,
            "newer_promises": newer_promises,
            "older_summary": {
                "total":       len(older_promises),
                "verified":    older_verified,
                "achieved":    older_achieved,
                "missed":      older_missed,
                "pending":     len(older_promises) - older_verified,
            },
            "newer_summary": {
                "total":      len(newer_promises),
                "announced":  newer_announced,
            },
            # Did newer quarter REPEAT or REVISIT the same topics?
            "repeated_topics": [],  # filled below
            "new_topics":      [],  # filled below
            "integrity_signal": ("IMPROVING" if older_achieved >= older_missed * 2
                                  else "DETERIORATING" if older_missed > older_achieved
                                  else "STABLE"),
        }

        # Find repeated vs new topics (by guidance_type)
        older_types = {p["type"] for p in older_promises}
        newer_types = {p["type"] for p in newer_promises}
        quarter_comparison["repeated_topics"] = list(older_types & newer_types)
        quarter_comparison["new_topics"]      = list(newer_types - older_types)

    # ── 3. INTEGRITY TIMELINE ─────────────────────────────────────────
    # Group verified promises by the QUARTER they were verified in
    # Shows management reliability quarter-by-quarter
    integrity_by_quarter = {}
    for p in (achieved + missed + partial):
        q = p.get("verified_in") or "Unknown"
        if q not in integrity_by_quarter:
            integrity_by_quarter[q] = {"achieved": 0, "missed": 0, "partial": 0, "total": 0}
        s = p["status"].lower()
        integrity_by_quarter[q][s] = integrity_by_quarter[q].get(s, 0) + 1
        integrity_by_quarter[q]["total"] += 1

    # Sort by quarter descending
    sorted_quarters = sorted(integrity_by_quarter.keys(), reverse=True)
    timeline = {q: integrity_by_quarter[q] for q in sorted_quarters}

    # ── Integrity Signal ──────────────────────────────────────────────
    # Count overall broken promises with missed target dates in the past
    broken_with_past_deadline = [
        p for p in missed
        if p.get("deadline") and p.get("status") == "MISSED"
    ]
    total_verified = len(verified_promises)
    integrity_signal = ""
    if total_verified >= 3:
        if accuracy >= 75:
            integrity_signal = "HIGH — management has a strong track record of meeting commitments"
        elif accuracy >= 60:
            integrity_signal = "MODERATE — most commitments met, some gaps to investigate"
        elif accuracy >= 40:
            integrity_signal = "LOW — multiple broken promises; scrutinize forward guidance carefully"
        else:
            integrity_signal = "VERY LOW — majority of commitments missed; management credibility questionable"
    else:
        integrity_signal = "INSUFFICIENT DATA — need at least 3 verified promises to assess integrity"

    # ── Header metadata: transcript coverage + guidance quality signals ──
    cur.execute(
        """SELECT COUNT(*) AS n,
                  MIN(date) AS earliest,
                  MAX(date) AS latest
           FROM aae_transcripts WHERE symbol=%s""",
        (sym,),
    )
    trow = cur.fetchone()
    transcript_count = int(_r(trow, 0) or 0)
    transcript_date_range = {
        "earliest": str(_r(trow, 1)) if _r(trow, 1) else None,
        "latest":   str(_r(trow, 2)) if _r(trow, 2) else None,
    }

    # Numerical guidance quality: % of promises that carry a numeric target AND a deadline.
    # Low score = management gives directional / qualitative guidance only.
    cur.execute(
        """SELECT
              COUNT(*) AS total,
              COUNT(*) FILTER (WHERE target_value IS NOT NULL AND target_unit IS NOT NULL) AS with_numeric,
              COUNT(*) FILTER (WHERE target_date IS NOT NULL AND target_date <> '') AS with_deadline
           FROM management_guidance WHERE symbol=%s""",
        (sym,),
    )
    grow = cur.fetchone()
    g_total = int(_r(grow, 0) or 0)
    g_numeric = int(_r(grow, 1) or 0)
    g_deadline = int(_r(grow, 2) or 0)
    numerical_guidance_pct = round((g_numeric / g_total) * 100, 1) if g_total else 0.0
    deadline_guidance_pct  = round((g_deadline / g_total) * 100, 1) if g_total else 0.0

    # Dominant guidance type (most-frequent bucket — tells you what management talks about most)
    cur.execute(
        """SELECT COALESCE(guidance_type, 'OTHER') AS gtype, COUNT(*) AS n
           FROM management_guidance WHERE symbol=%s
           GROUP BY gtype ORDER BY n DESC LIMIT 1""",
        (sym,),
    )
    drow = cur.fetchone()
    dominant_type = _r(drow, 0) if drow else None

    # All-future flag: every extracted promise is forward-looking AND unverified (no
    # ACHIEVED/MISSED/PARTIAL exists yet). Means the verifier cannot yet score this
    # management team on past promises — only the next 1-2 quarters will change that.
    all_future_promises = (
        total_verified == 0 and (g_total - len(upcoming)) == 0 and g_total > 0
    )

    # ── Intonation: 9-dimension management tone, per quarter + 8-quarter timeline ──
    cur.execute(
        """SELECT fiscal_year, fiscal_quarter, confidence, hedging, aggression,
                  transparency, optimism, pessimism, accountability,
                  numerical_density, headwind_acknowledged, raw
           FROM management_intonation
           WHERE symbol=%s
           ORDER BY fiscal_year DESC, fiscal_quarter DESC
           LIMIT 12""",
        (sym,),
    )
    intonation_rows = cur.fetchall()
    intonation = {
        "quarters_observed": len(intonation_rows),
        "latest": None,
        "previous": None,
        "quarter_over_quarter_delta": None,
        "tone_shift_detected": False,
        "tone_shift_dimensions": [],
        "timeline": [],
    }
    if intonation_rows:
        def _dim(row, idx): return _r(row, idx)
        latest = {
            "fiscal_year": int(_dim(intonation_rows[0], 0)),
            "fiscal_quarter": int(_dim(intonation_rows[0], 1)),
            "quarter_label": _fy_label(int(_dim(intonation_rows[0], 0)),
                                       int(_dim(intonation_rows[0], 1))),
            "confidence":      float(_dim(intonation_rows[0], 2) or 0),
            "hedging":         float(_dim(intonation_rows[0], 3) or 0),
            "aggression":      float(_dim(intonation_rows[0], 4) or 0),
            "transparency":    float(_dim(intonation_rows[0], 5) or 0),
            "optimism":        float(_dim(intonation_rows[0], 6) or 0),
            "pessimism":       float(_dim(intonation_rows[0], 7) or 0),
            "accountability":  float(_dim(intonation_rows[0], 8) or 0),
            "numerical_density": float(_dim(intonation_rows[0], 9) or 0),
            "headwind_acknowledged": int(_dim(intonation_rows[0], 10) or 0),
            "summary": (_dim(intonation_rows[0], 11) or {}).get("one_line_summary", ""),
            "headwinds_named": (_dim(intonation_rows[0], 11) or {}).get("headwinds_named", []),
        }
        intonation["latest"] = latest
        if len(intonation_rows) >= 2:
            prev = intonation_rows[1]
            previous = {
                "fiscal_year": int(_dim(prev, 0)),
                "fiscal_quarter": int(_dim(prev, 1)),
                "quarter_label": _fy_label(int(_dim(prev, 0)), int(_dim(prev, 1))),
                "confidence":      float(_dim(prev, 2) or 0),
                "hedging":         float(_dim(prev, 3) or 0),
                "aggression":      float(_dim(prev, 4) or 0),
                "transparency":    float(_dim(prev, 5) or 0),
                "optimism":        float(_dim(prev, 6) or 0),
                "pessimism":       float(_dim(prev, 7) or 0),
                "accountability":  float(_dim(prev, 8) or 0),
                "numerical_density": float(_dim(prev, 9) or 0),
                "headwind_acknowledged": int(_dim(prev, 10) or 0),
            }
            intonation["previous"] = previous
            # Quarter-over-quarter delta + 1σ tone-shift detection
            shift_dims = []
            for key in ("confidence", "hedging", "aggression", "transparency",
                        "optimism", "pessimism", "accountability", "numerical_density"):
                d = latest[key] - previous[key]
                if abs(d) >= 0.20:  # default 1σ threshold ≈ 0.20 absolute
                    shift_dims.append({"dim": key, "delta": round(d, 3),
                                       "direction": "up" if d > 0 else "down"})
            intonation["quarter_over_quarter_delta"] = {
                "confidence":      round(latest["confidence"] - previous["confidence"], 3),
                "hedging":         round(latest["hedging"] - previous["hedging"], 3),
                "aggression":      round(latest["aggression"] - previous["aggression"], 3),
                "transparency":    round(latest["transparency"] - previous["transparency"], 3),
                "optimism":        round(latest["optimism"] - previous["optimism"], 3),
                "pessimism":       round(latest["pessimism"] - previous["pessimism"], 3),
                "accountability":  round(latest["accountability"] - previous["accountability"], 3),
                "numerical_density": round(latest["numerical_density"] - previous["numerical_density"], 3),
            }
            intonation["tone_shift_detected"] = len(shift_dims) > 0
            intonation["tone_shift_dimensions"] = shift_dims

        # Timeline: reverse-chronological → chronological for chart-friendly order
        for r in reversed(intonation_rows):
            intonation["timeline"].append({
                "quarter_label": _fy_label(int(_dim(r, 0)), int(_dim(r, 1))),
                "fiscal_year": int(_dim(r, 0)),
                "fiscal_quarter": int(_dim(r, 1)),
                "confidence":      float(_dim(r, 2) or 0),
                "hedging":         float(_dim(r, 3) or 0),
                "aggression":      float(_dim(r, 4) or 0),
                "transparency":    float(_dim(r, 5) or 0),
                "optimism":        float(_dim(r, 6) or 0),
                "pessimism":       float(_dim(r, 7) or 0),
                "accountability":  float(_dim(r, 8) or 0),
                "numerical_density": float(_dim(r, 9) or 0),
                "headwind_acknowledged": int(_dim(r, 10) or 0),
            })

    # Management's qualitative style signal — computed from how many promises
    # land in each type. "OTHER" + "REVENUE_GROWTH" with no target = "directional".
    directional_style = (numerical_guidance_pct < 30.0)

    guidance_quality_signal = (
        "DIRECTIONAL ONLY" if directional_style
        else "MIXED" if numerical_guidance_pct < 70.0
        else "NUMERICAL"
    )

    return {
        "symbol": sym,
        "report_date": str(date.today()),

        # Header metadata (transcript coverage + guidance quality signals)
        "transcript_count": transcript_count,
        "transcript_date_range": transcript_date_range,
        "total_promises_extracted": g_total,
        "numerical_guidance_pct": numerical_guidance_pct,
        "deadline_guidance_pct": deadline_guidance_pct,
        "dominant_guidance_type": dominant_type,
        "all_future_promises": all_future_promises,
        "directional_style": directional_style,
        "guidance_quality_signal": guidance_quality_signal,

        # Intonation — 9-dimension management tone (latest + previous + delta + 8q timeline)
        "intonation": intonation,

        # Summary
        "credibility": credibility,
        "verdict": verdict,
        "verdict_color": verdict_color,
        "verdict_bg": verdict_bg,
        "accuracy_pct": accuracy,
        "ring_offset": ring_offset,
        "ring_color": ring_color,
        "ring_circumference": circumference,

        # Counts
        "total_achieved": len(achieved),
        "total_missed":   len(missed),
        "total_partial":  len(partial),
        "total_upcoming": len(upcoming),
        "total_verified": total_verified,
        "total_material": len(achieved) + len(missed) + len(partial) + len(upcoming),
        "total_unable": len([p for p in upcoming if p.get("status") == "UNABLE_TO_VERIFY"]),

        # ── 1. Past Promises Verified ────────────────────────────────
        "achieved": achieved,
        "missed":   missed,
        "partial":  partial,
        "upcoming": upcoming,

        # ── 2. Quarter Comparison ─────────────────────────────────────
        "quarter_comparison": quarter_comparison,

        # ── 3. Integrity Timeline ─────────────────────────────────────
        "integrity_timeline": timeline,
        "integrity_signal": integrity_signal,
    }


@router.get("/{symbol}/report")
def get_guidance_report(symbol: str, conn=Depends(get_db)):
    """
    Clean GuidanceCheck report for a symbol.
    Only trackable promises (numeric target OR deadline).
    Grouped: ACHIEVED / MISSED / PARTIAL / PENDING.
    """
    payload = _build_report_payload(conn, symbol)
    return payload


@router.post("/{symbol}/email")
def send_guidance_report(
    symbol: str,
    background_tasks: BackgroundTasks,
    current_client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """
    Build the GuidanceCheck report and email it to the logged-in user.
    """
    from engine_core.email_service import build_guidance_report_email_html
    from datetime import date

    sym = symbol.upper().strip()
    payload = _build_report_payload(conn, sym)
    client_email = current_client.get("email", "")

    def _send():
        try:
            html = build_guidance_report_email_html(payload)
            from engine_core.email_service import get_ses_client, send_email_custom
            ses = get_ses_client()
            send_email_custom(
                client_email,
                f"GuidanceCheck Report — {sym} ({payload['verdict']})",
                html,
            )
            logger.info(f"GuidanceCheck report emailed for {sym} to {client_email}")
        except Exception as e:
            logger.error(f"Failed to email GuidanceCheck report for {sym}: {e}")

    background_tasks.add_task(_send)
    return {
        "status": "queued",
        "symbol": sym,
        "recipient": client_email,
        "message": "Report is being generated and will arrive in your inbox shortly.",
    }


# ── Original dashboard endpoint (kept for backwards compat) ─────────────

@router.get("/{symbol}")
def get_guidance_dashboard(symbol: str, conn=Depends(get_db)):
    """Single-screen GuidanceCheck dashboard for one company."""
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM management_credibility_scores WHERE symbol=%s",
        (symbol.upper(),),
    )
    score = cur.fetchone()

    cur.execute(
        """SELECT g.id, g.guidance_type, g.guidance_text, g.target_value,
                  g.target_unit, g.target_date, g.confidence,
                  v.status, v.actual_value, v.variance_pct
           FROM management_guidance g
           LEFT JOIN guidance_verification v ON g.id = v.guidance_id
           WHERE g.symbol = %s
           ORDER BY g.extracted_at DESC LIMIT 20""",
        (symbol.upper(),),
    )
    guidance = cur.fetchall()

    return {
        "symbol": symbol.upper(),
        "credibility": score,
        "guidance": guidance,
        "total_promises": score["total_promises"] if score else 0,
    }


@router.get("/portfolio")
def get_portfolio_guidance(conn=Depends(get_db)):
    """GuidanceCheck across all tracked stocks."""
    cur = conn.cursor()
    cur.execute(
        """SELECT * FROM management_credibility_scores
           ORDER BY accuracy_pct ASC"""
    )
    scores = cur.fetchall()
    return {"holdings": scores, "count": len(scores)}


@router.get("/promises-due")
def get_promises_due(conn=Depends(get_db)):
    """Guidance promises with target dates — sorted by nearest deadline."""
    cur = conn.cursor()
    cur.execute(
        """SELECT g.symbol, g.guidance_type, g.guidance_text,
                  g.target_value, g.target_unit, g.target_date,
                  g.confidence, v.status
           FROM management_guidance g
           LEFT JOIN guidance_verification v ON g.id = v.guidance_id
           WHERE g.target_date IS NOT NULL
             AND (v.status IS NULL OR v.status = 'PENDING')
           ORDER BY g.target_date ASC
           LIMIT 50"""
    )
    return cur.fetchall()


@router.get("/leaderboard")
def get_leaderboard(
    worst: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    conn=Depends(get_db),
):
    """Top or bottom credibility scores across all tracked companies."""
    cur = conn.cursor()
    order = "ASC" if worst else "DESC"
    cur.execute(
        f"""SELECT * FROM management_credibility_scores
            WHERE total_promises >= 3
            ORDER BY accuracy_pct {order} LIMIT %s""",
        (limit,),
    )
    return cur.fetchall()


# ── ConvictionEngine (Decision 097) ──────────────────────────────────


@router.get("/conviction")
def get_conviction(
    source: str = Query("all", pattern="^(all|digital_twin|112co|watchlist)$"),
    verdict: str = Query("any", pattern="^(any|ADD ZONE|HOLD ZONE|REDUCE ZONE|THESIS BROKEN|WATCHING)$"),
    limit: int = Query(50, ge=1, le=200),
    conn=Depends(get_db),
):
    """
    ConvictionEngine — unified ranking of management integrity across the
    two lists the user cares about (Digital Twin holdings + 112 Co Universe).

    Default sort: worst credibility first (lowest accuracy_pct, highest lag).
    """
    cur = conn.cursor()

    # Build the symbol universe based on source filter
    where_clauses = ["1=1"]
    params: list = []

    if source in ("all", "digital_twin"):
        # Digital Twin = client_external_holdings (Decision 036/088)
        cur.execute(
            "SELECT DISTINCT UPPER(symbol) AS symbol FROM client_external_holdings"
        )
        dt_syms = {r["symbol"] for r in cur.fetchall()}
    else:
        dt_syms = set()

    if source in ("all", "watchlist"):
        cur.execute(
            "SELECT DISTINCT UPPER(symbol) AS symbol FROM client_watchlist"
        )
        wl_syms = {r["symbol"] for r in cur.fetchall()}
    else:
        wl_syms = set()

    if source in ("all", "112co"):
        cur.execute(
            "SELECT DISTINCT UPPER(symbol) AS symbol FROM universe_112co WHERE is_active=TRUE"
        )
        co_syms = {r["symbol"] for r in cur.fetchall()}
    else:
        co_syms = set()

    universe = sorted(dt_syms | wl_syms | co_syms)
    if not universe:
        return {"source": source, "count": 0, "rows": []}

    # Tag each symbol with its source(s) — a stock can be in multiple lists
    sym_sources: dict[str, list[str]] = {s: [] for s in universe}
    if dt_syms:
        for s in dt_syms:
            sym_sources[s].append("digital_twin")
    if wl_syms:
        for s in wl_syms:
            sym_sources[s].append("watchlist")
    if co_syms:
        for s in co_syms:
            sym_sources[s].append("112co")

    # Fetch credibility rows for these symbols
    cur.execute(
        """SELECT symbol, total_promises, achieved_count, missed_count,
                  accuracy_pct, avg_variance_pct, trend,
                  consecutive_miss_quarters, lag_score, last_verdict_flip,
                  current_verdict, previous_verdict, last_updated
           FROM management_credibility_scores
           WHERE symbol = ANY(%s)""",
        (universe,),
    )
    rows = cur.fetchall()

    out = []
    for r in rows:
        symbol = r["symbol"]
        accuracy = float(r["accuracy_pct"] or 0)
        total = r["total_promises"] or 0
        trend = r["trend"]
        current_verdict = r["current_verdict"]

        # Compute verdict if not already stored (legacy rows may lack it)
        if not current_verdict:
            if total < 3:
                current_verdict = "WATCHING"
            elif accuracy >= 75:
                current_verdict = "ADD ZONE" if trend in ("IMPROVING", "STABLE", "INSUFFICIENT_DATA", None) else "HOLD ZONE"
            elif accuracy >= 60:
                current_verdict = "HOLD ZONE"
            elif accuracy >= 40:
                current_verdict = "REDUCE ZONE"
            else:
                current_verdict = "THESIS BROKEN"

        if verdict != "any" and current_verdict != verdict:
            continue

        out.append({
            "symbol": symbol,
            "sources": sym_sources.get(symbol, []),
            "accuracy_pct": round(accuracy, 2),
            "trend": trend,
            "total_promises": total,
            "achieved_count": r["achieved_count"] or 0,
            "missed_count": r["missed_count"] or 0,
            "avg_variance_pct": float(r["avg_variance_pct"]) if r["avg_variance_pct"] is not None else None,
            "consecutive_miss_quarters": r["consecutive_miss_quarters"] or 0,
            "lag_score": float(r["lag_score"] or 0),
            "current_verdict": current_verdict,
            "previous_verdict": r["previous_verdict"],
            "verdict_flipped": (
                r["previous_verdict"] is not None
                and r["previous_verdict"] != current_verdict
            ),
            "last_verdict_flip": str(r["last_verdict_flip"]) if r["last_verdict_flip"] else None,
            "last_updated": str(r["last_updated"]) if r["last_updated"] else None,
        })

    # Sort: worst credibility first → lowest accuracy, then highest lag
    out.sort(key=lambda x: (x["accuracy_pct"], -x["lag_score"]))
    out = out[:limit]

    # Summary counts for the UI header
    summary = {
        "total": len(out),
        "ADD ZONE": sum(1 for x in out if x["current_verdict"] == "ADD ZONE"),
        "HOLD ZONE": sum(1 for x in out if x["current_verdict"] == "HOLD ZONE"),
        "REDUCE ZONE": sum(1 for x in out if x["current_verdict"] == "REDUCE ZONE"),
        "THESIS BROKEN": sum(1 for x in out if x["current_verdict"] == "THESIS BROKEN"),
        "WATCHING": sum(1 for x in out if x["current_verdict"] == "WATCHING"),
        "lagging_count": sum(1 for x in out if x["consecutive_miss_quarters"] >= 2),
        "flipped_count": sum(1 for x in out if x["verdict_flipped"]),
    }
    return {"source": source, "summary": summary, "rows": out}


@router.post("/scan/{symbol}")
def trigger_guidance_scan(
    symbol: str, background_tasks: BackgroundTasks
):
    """Trigger guidance extraction for a symbol's un-scanned transcripts."""
    from engine_guidance.guidance_extractor import GuidanceExtractor
    from engine_guidance.guidance_verifier import GuidanceVerifier
    from engine_guidance.credibility_scorer import CredibilityScorer

    def _run():
        extractor = GuidanceExtractor(symbol)
        n = extractor.scan_all_transcripts()
        if n > 0:
            verifier = GuidanceVerifier()
            verifier.verify_symbol(symbol)
            scorer = CredibilityScorer()
            scorer.compute_score(symbol)
        logger.info(f"Guidance scan complete: {symbol} ({n} transcripts)")

    background_tasks.add_task(_run)
    return {"status": "queued", "symbol": symbol.upper()}


# ── Thesis Tracking ─────────────────────────────────────────────────────

@router.post("/thesis")
def save_thesis(
    body: dict,
    current_client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Save or update an investment thesis for a stock."""
    symbol = body.get("symbol", "").upper()
    if not symbol:
        raise HTTPException(400, "symbol is required")

    cur = conn.cursor()
    cur.execute(
        """INSERT INTO user_thesis
           (client_id, symbol, thesis_type, key_assumption,
            thesis_breaker, expected_hold, entry_date,
            entry_price, conviction_score, notes)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
           ON CONFLICT (client_id, symbol) DO UPDATE SET
            thesis_type=EXCLUDED.thesis_type,
            key_assumption=EXCLUDED.key_assumption,
            thesis_breaker=EXCLUDED.thesis_breaker,
            expected_hold=EXCLUDED.expected_hold,
            entry_date=EXCLUDED.entry_date,
            entry_price=EXCLUDED.entry_price,
            conviction_score=EXCLUDED.conviction_score,
            notes=EXCLUDED.notes,
            updated_at=NOW()""",
        (
            current_client["id"], symbol,
            body.get("thesis_type"),
            body.get("key_assumption"),
            body.get("thesis_breaker"),
            body.get("expected_hold"),
            body.get("entry_date"),
            body.get("entry_price"),
            body.get("conviction_score", 50),
            body.get("notes"),
        ),
    )
    conn.commit()
    return {"status": "saved", "symbol": symbol}


@router.get("/thesis/{symbol}")
def get_thesis(
    symbol: str,
    current_client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Get investment thesis for a symbol."""
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM user_thesis WHERE client_id=%s AND symbol=%s",
        (current_client["id"], symbol.upper()),
    )
    thesis = cur.fetchone()
    if not thesis:
        raise HTTPException(404, "No thesis found for this symbol")
    return thesis


@router.get("/thesis")
def list_theses(
    current_client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """List all theses for current user."""
    cur = conn.cursor()
    cur.execute(
        """SELECT t.*, s.accuracy_pct, s.trend
           FROM user_thesis t
           LEFT JOIN management_credibility_scores s ON t.symbol = s.symbol
           WHERE t.client_id = %s
           ORDER BY t.updated_at DESC""",
        (current_client["id"],),
    )
    return cur.fetchall()


@router.post("/prime/{symbol}")
def prime_guidance(
    symbol: str,
    background_tasks: BackgroundTasks,
    client=Depends(get_current_client),
):
    """Manually trigger guidance data priming for a symbol."""
    base = symbol.upper().replace(".NS", "").replace(".BO", "").strip()
    try:
        from engine_guidance.guidance_primer import prime_guidance_data
        background_tasks.add_task(prime_guidance_data, base)
        return {"status": "queued", "symbol": base, "message": "Guidance priming started. Check back in 2-3 minutes for results."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/prime-all")
def prime_all_guidance(
    background_tasks: BackgroundTasks,
    client=Depends(get_current_client),
):
    """Prime guidance data for ALL stocks in the system."""
    try:
        from engine_core.db import get_connection
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT UPPER(symbol) AS symbol FROM client_watchlist")
        wl = {row["symbol"] for row in cur.fetchall()}
        cur.execute("SELECT DISTINCT UPPER(symbol) AS symbol FROM client_external_holdings")
        hl = {row["symbol"] for row in cur.fetchall()}
        conn.close()
        all_syms = sorted(wl | hl)

        from engine_guidance.guidance_primer import prime_guidance_data_batch
        background_tasks.add_task(prime_guidance_data_batch, all_syms)

        return {
            "status": "queued",
            "total_symbols": len(all_syms),
            "symbols": all_syms,
            "message": f"Priming {len(all_syms)} stocks in background.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))