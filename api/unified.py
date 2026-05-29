"""
Unified Analysis API — single endpoint composing PERX + AAE + GuidanceCheck + MOSI.

POST /api/unified/scan/{symbol}
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
import logging

from api.deps import get_current_client, get_db
from engine_core.unified_analysis import UnifiedAnalyzer

router = APIRouter(prefix="/api/unified", tags=["Unified Scan"])
logger = logging.getLogger(__name__)


@router.post("/scan/{symbol}")
def scan_unified(
    symbol: str,
    background_tasks: BackgroundTasks,
    include_email: bool = Query(False, description="Email the unified report to the client"),
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """
    Run a unified institutional scan: PERX + AAE + GuidanceCheck + MOSI gaps.

    Returns a single merged report payload. Error isolation: if one engine
    fails, the others still produce results. Warnings are returned in
    the `_warnings` field.
    """
    try:
        analyzer = UnifiedAnalyzer(symbol)
        result = analyzer.run()
        
        # Auto-prime guidance data in background if not already present
        if result.get("guidance", {}).get("total_promises", -1) == 0:
            try:
                from engine_guidance.guidance_primer import prime_guidance_data
                background_tasks.add_task(prime_guidance_data, symbol)
            except Exception:
                pass
        
        # Optional email delivery
        if include_email:
            client_email = client.get("email")
            if client_email:
                try:
                    from engine_core.email_service import send_unified_report_email
                    background_tasks.add_task(
                        send_unified_report_email,
                        client_email,
                        client.get("name", "Investor"),
                        result,
                    )
                except Exception as e:
                    logger.warning(f"Could not queue unified email: {e}")

        return result

    except Exception as e:
        logger.error(f"Unified scan failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Unified scan failed: {str(e)}")
