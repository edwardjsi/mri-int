"""
Unified Analysis API — single endpoint composing PERX + AAE + GuidanceCheck + MOSI.

POST /api/unified/scan/{symbol}

Restricted to stocks in the user's Watchlist or Digital Twin (Portfolio).
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

    Restricted to stocks in the user's Watchlist or Digital Twin.
    Error isolation: if one engine fails, the others still produce results.
    """
    base_symbol = symbol.upper().replace(".NS", "").replace(".BO", "").strip()
    client_id = client["id"]

    # ── Validate: symbol must be in Watchlist or Portfolio ──────────
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM watchlist WHERE client_id = %s AND symbol = %s",
            (client_id, base_symbol),
        )
        in_watchlist = cur.fetchone() is not None

        cur.execute(
            "SELECT 1 FROM holdings WHERE client_id = %s AND symbol = %s",
            (client_id, base_symbol),
        )
        in_holdings = cur.fetchone() is not None

        if not in_watchlist and not in_holdings:
            raise HTTPException(
                status_code=403,
                detail=f"{base_symbol} is not in your Watchlist or Portfolio. Add it first before running a Unified Scan."
            )

    try:
        analyzer = UnifiedAnalyzer(base_symbol)
        result = analyzer.run()

        # Auto-prime guidance data in background if not already present
        if result.get("guidance", {}).get("total_promises", -1) == 0:
            try:
                from engine_guidance.guidance_primer import prime_guidance_data
                background_tasks.add_task(prime_guidance_data, base_symbol)
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

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Unified scan failed for {base_symbol}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Unified scan failed: {str(e)}")
