"""
api/guidance.py — GuidanceCheck FastAPI Router

Endpoints:
    GET  /api/guidance/{symbol}          — Full guidance dashboard for one stock
    GET  /api/guidance/portfolio          — Guidance check across user's holdings
    GET  /api/guidance/leaderboard        — Top/bottom credibility scores
    POST /api/guidance/scan/{symbol}      — Trigger extraction for a symbol
    POST /api/guidance/thesis             — Save/update investment thesis
    GET  /api/guidance/thesis/{symbol}    — Get thesis for a symbol
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, BackgroundTasks
from api.deps import get_db, get_current_client
from engine_core.db import get_connection
import logging

router = APIRouter(prefix="/api/guidance", tags=["guidance"])
logger = logging.getLogger("api.guidance")


@router.get("/{symbol}")
def get_guidance_dashboard(symbol: str, conn=Depends(get_db)):
    """Single-screen GuidanceCheck dashboard for one company."""
    cur = conn.cursor()

    # Credibility score
    cur.execute(
        "SELECT * FROM management_credibility_scores WHERE symbol=%s",
        (symbol.upper(),),
    )
    score = cur.fetchone()

    # Recent guidance
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
    """
    Manually trigger guidance data priming for a symbol.
    Discovers concall transcripts, extracts guidance via LLM, verifies against financials.
    Runs as a background task — returns immediately.
    """
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
    """
    Prime guidance data for ALL stocks in the system.
    Runs in background — returns immediately with symbol count.
    """
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
            "message": f"Priming {len(all_syms)} stocks in background. This will take several minutes."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

