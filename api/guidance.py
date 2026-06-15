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


def _build_report_payload(conn, symbol: str) -> dict:
    """
    Build a clean, product-grade guidance report.
    Only shows promises with a numeric target or a defined deadline.
    Groups into ACHIEVED / MISSED / PARTIAL / PENDING.
    """
    sym = symbol.upper().strip()
    cur = conn.cursor()

    # Credibility score
    cur.execute(
        "SELECT * FROM management_credibility_scores WHERE symbol=%s",
        (sym,),
    )
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
        }

    # Fetch all promises with verification
    cur.execute(
        """SELECT g.guidance_type, g.guidance_text,
                  g.target_value, g.target_unit, g.target_date,
                  v.status, v.actual_value, v.variance_pct,
                  v.checked_fiscal_year, v.checked_fiscal_quarter
           FROM management_guidance g
           LEFT JOIN guidance_verification v ON g.id = v.guidance_id
           WHERE g.symbol = %s
           ORDER BY
             CASE WHEN v.status IN ('ACHIEVED','MISSED','PARTIAL') THEN 0 ELSE 1 END,
             g.target_date ASC NULLS LAST,
             g.extracted_at DESC""",
        (sym,),
    )
    rows = cur.fetchall()

    achieved = []
    missed = []
    partial = []
    pending = []

    for row in rows:
        gtype   = _r(row, 0)
        gtext   = _r(row, 1)
        tval    = _r(row, 2)
        tunit   = _r(row, 3)
        tdate   = _r(row, 4)
        status  = _r(row, 5)
        actual  = _r(row, 6)
        variance = _r(row, 7)
        fyear   = _r(row, 8)
        fquarter = _r(row, 9)

        # Build display target string
        target_display = ""
        if tval is not None:
            target_display = f"{tval} {tunit or ''}".strip()
        elif tdate:
            target_display = f"by {tdate}"

        # Format actual result
        actual_display = ""
        if actual is not None:
            actual_display = f"{actual} {tunit or ''}".strip()
        elif status == "MISSED" and variance is not None:
            actual_display = f"{variance:+.1f}% vs target"

        item = {
            "type": gtype or "OTHER",
            "promise": gtext,
            "target": target_display,
            "deadline": tdate or "",
            "status": status or "PENDING",
            "actual": actual_display,
            "variance_pct": float(variance) if variance is not None else None,
            "verified_period": f"Q{fquarter}FY{str(fyear)[-2:]}" if fyear and fquarter else "",
        }

        if status == "ACHIEVED":
            achieved.append(item)
        elif status == "MISSED":
            missed.append(item)
        elif status == "PARTIAL":
            partial.append(item)
        else:
            pending.append(item)

    # Summary stats
    total = credibility.get("total_promises", 0)
    accuracy = credibility.get("accuracy_pct", 0.0)
    trend = credibility.get("trend", "INSUFFICIENT_DATA")

    # Conviction verdict
    if total < 3:
        verdict = "WATCHING"
        verdict_color = "#64748b"
        verdict_bg = "#1e293b"
    elif accuracy >= 75:
        verdict = "ADD ZONE" if trend in ("IMPROVING", "STABLE") else "HOLD ZONE"
        verdict_color = "#4ade80"
        verdict_bg = "#14532d"
    elif accuracy >= 60:
        verdict = "HOLD ZONE"
        verdict_color = "#fbbf24"
        verdict_bg = "#451a03"
    elif accuracy >= 40:
        verdict = "REDUCE ZONE"
        verdict_color = "#f87171"
        verdict_bg = "#7f1d1d"
    else:
        verdict = "THESIS BROKEN"
        verdict_color = "#fff"
        verdict_bg = "#500"

    # Accuracy ring
    circumference = 2 * 3.14159 * 40  # r=40
    ring_offset = circumference - (accuracy / 100) * circumference
    ring_color = "#4ade80" if accuracy >= 70 else "#fbbf24" if accuracy >= 40 else "#f87171" if accuracy > 0 else "#3b82f6"

    return {
        "symbol": sym,
        "report_date": str(date.today()),
        "credibility": credibility,
        "verdict": verdict,
        "verdict_color": verdict_color,
        "verdict_bg": verdict_bg,
        "accuracy_pct": accuracy,
        "ring_offset": ring_offset,
        "ring_color": ring_color,
        "ring_circumference": circumference,
        "achieved": achieved,
        "missed": missed,
        "partial": partial,
        "pending": pending,
        "total_achieved": len(achieved),
        "total_missed": len(missed),
        "total_partial": len(partial),
        "total_pending": len(pending),
        "total_material": len(achieved) + len(missed) + len(partial) + len(pending),
        "total_verified": len(achieved) + len(missed) + len(partial),
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