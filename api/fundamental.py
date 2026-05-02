from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from api.deps import get_db, get_current_client
from engine_fundamental.pipeline import run_quality_pipeline
from engine_fundamental.collector import fetch_and_store_financials
from engine_qualitative.debate import run_debate, format_debate_email_html
from engine_core.email_service import send_email_custom
import logging

router = APIRouter(prefix="/api/fundamental", tags=["fundamental"])
logger = logging.getLogger(__name__)

@router.get("/verdict/{symbol}")
def get_quality_verdict(symbol: str, conn=Depends(get_db)):
    """Retrieve or trigger the Quality Investor verdict for a stock."""
    cur = conn.cursor()
    cur.execute("SELECT * FROM quality_verdicts WHERE symbol = %s", (symbol.upper(),))
    row = cur.fetchone()
    
    if not row:
        # If not found, try to run it on the fly
        try:
            # Check if we have financials first
            cur.execute("SELECT COUNT(*) FROM fundamental_financials WHERE symbol = %s", (symbol.upper(),))
            count = cur.fetchone()[0]
            if count == 0:
                fetch_and_store_financials(symbol.upper())
            
            verdict = run_quality_pipeline(symbol.upper())
            if not verdict:
                raise HTTPException(status_code=404, detail="Could not generate verdict for this symbol.")
            return verdict
        except Exception as e:
            logger.error(f"Failed to generate verdict for {symbol}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
            
    return row

@router.get("/top-quality")
def get_top_quality_stocks(limit: int = 10, conn=Depends(get_db)):
    """Get the highest-scoring quality stocks."""
    cur = conn.cursor()
    cur.execute("""
        SELECT symbol, score, category, flags, updated_at
        FROM quality_verdicts
        WHERE category IN ('HIGH_QUALITY', 'EARLY_COMPOUNDER')
        ORDER BY score DESC
        LIMIT %s
    """, (limit,))
    return cur.fetchall()

@router.post("/recompute/{symbol}")
def trigger_recompute(symbol: str):
    """Manually trigger a fresh financial fetch and quality recompute."""
    fetch_and_store_financials(symbol.upper())
    return run_quality_pipeline(symbol.upper())

@router.get("/improvers")
def get_top_improvers(limit: int = 20, conn=Depends(get_db)):
    """Get stocks with the highest positive score change (trajectory)."""
    cur = conn.cursor()
    cur.execute("""
        SELECT symbol, score, prev_score, score_change, velocity, category
        FROM quality_verdicts
        WHERE score_change IS NOT NULL
        ORDER BY score_change DESC
        LIMIT %s
    """, (limit,))
    return cur.fetchall()

@router.get("/alerts")
def get_trajectory_alerts(conn=Depends(get_db)):
    """Get active trajectory alerts for explosive improvers."""
    from scripts.quality_alerts import check_quality_alerts
    return check_quality_alerts()

@router.post("/debate/{symbol}")
def trigger_debate(symbol: str, background_tasks: BackgroundTasks, client=Depends(get_current_client), conn=Depends(get_db)):
    """
    Run GPT debate analysis for a symbol and email results to the client.
    Only works for symbols already in quality_verdicts (must pass QIF screen first).
    """
    symbol = symbol.upper().replace(".NS", "").replace(".BO", "")
    
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM quality_verdicts WHERE symbol = %s", (symbol,))
    verdict = cur.fetchone()

    if not verdict:
        raise HTTPException(status_code=404, detail=f"{symbol} not found in quality verdicts. Run QIF pipeline first.")

    def get_val(item, key, index):
        if isinstance(item, dict): return item.get(key)
        if isinstance(item, (list, tuple)):
            return item[index] if len(item) > index else None
        return None

    client_email = get_val(client, 'email', 1)
    logger.info(f"Debate triggered for {symbol} by {client_email}")

    def _run_and_email():
        try:
            logger.info(f"Starting background debate analysis for {symbol}...")
            analysis = run_debate(symbol)
            if "error" not in analysis:
                logger.info(f"Debate analysis complete for {symbol}. Sending email to {client_email}...")
                html = format_debate_email_html(analysis)
                success = send_email_custom(
                    recipient_email=client_email,
                    subject=f"MRI Forensic Debate: {symbol}",
                    html_body=html
                )
                if success:
                    logger.info(f"Debate email successfully sent for {symbol}")
                else:
                    logger.error(f"Failed to send debate email for {symbol} to {client_email}. Check SES credentials and verified identities.")
            else:
                error_msg = analysis.get('error')
                logger.error(f"Debate analysis failed for {symbol}: {error_msg}")
                send_email_custom(
                    recipient_email=client_email,
                    subject=f"MRI Debate Failed: {symbol}",
                    html_body=f"<p>Debate analysis could not be generated for {symbol}.</p><p>Error: <b>{error_msg}</b></p><p>Please ensure OPENAI_API_KEY is set in the production environment.</p>"
                )
        except Exception as e:
            logger.exception(f"CRITICAL ERROR in debate background task for {symbol}: {e}")

    background_tasks.add_task(_run_and_email)
    return {"status": "debate_started", "symbol": symbol, "message": f"Analysis running for {symbol}. Results will be emailed to {client_email or 'your address'} shortly."}
