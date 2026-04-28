from fastapi import APIRouter, Depends, HTTPException, Query
from engine_core.db import get_db
import logging

# Lazy imports to prevent startup crash if engine modules are unavailable
try:
    from engine_fundamental.pipeline import run_quality_pipeline
    from engine_fundamental.collector import fetch_and_store_financials
    _engines_available = True
except Exception as _e:
    _engines_available = False
    import logging as _log
    _log.getLogger(__name__).warning(f"engine_fundamental not available: {_e}")


router = APIRouter(prefix="/fundamental", tags=["fundamental"])
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
