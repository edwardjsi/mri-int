"""
V2 PERX endpoint — returns structured data_warnings and EngineResult wrapper.

V1 is unchanged for backward compatibility.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks

from api.deps import get_current_client, get_db
from engine_perx.orchestrator import generate_perx_report, PerxScanError

router = APIRouter(prefix="/perx", tags=["perx-v2"])


@router.post("/scan/{symbol}")
def scan_symbol_v2(
    symbol: str,
    background_tasks: BackgroundTasks,
    include_debate: bool = Query(False, description="Include AI forensic review."),
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """V2: PERX scan with structured data_warnings and metadata about what data was available."""
    try:
        result = generate_perx_report(
            symbol=symbol,
            conn=conn,
            client_id=str(client["id"]),
            include_debate=include_debate,
            persist=True,
        )

        data_warnings = result["report"].get("_data_warnings", [])

        # Build a summary of what engines ran vs what was unavailable
        ic = result["report"].get("investor_context", {})
        module_status = {}
        for key in ["peg_ratio", "ev_ebitda", "institutional_flow", "historical_analogs",
                     "valuation", "earnings_momentum", "ownership", "liquidity"]:
            mod = ic.get(key, {})
            if not isinstance(mod, dict):
                module_status[key] = "UNAVAILABLE"
            else:
                verdict = mod.get("verdict", "")
                if not verdict or "unavailable" in verdict.lower() or "no " in verdict.lower()[:50] or "insufficient" in verdict.lower()[:50]:
                    module_status[key] = "UNAVAILABLE"
                else:
                    module_status[key] = "OK"

        return {
            "v": 2,
            "status": "ok",
            "report_id": result["report_id"],
            "report": result["report"],
            "data_warnings": data_warnings,
            "module_status": module_status,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "v": 2,
                "error": "DATA_MISSING",
                "detail": str(exc),
                "action": "Check that the symbol is valid and has market data available.",
            },
        )
    except Exception as exc:
        err = getattr(exc, "to_dict", None)
        if err:
            error_payload = err()
        else:
            error_payload = {
                "error": "PERX_SCAN_FAILED",
                "detail": str(exc),
                "action": "Unexpected error. Please try again or contact support.",
            }
        error_payload["v"] = 2
        raise HTTPException(status_code=500, detail=error_payload)


@router.get("/report/{report_id}")
def get_report_v2(
    report_id: str,
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """V2: Fetch a stored PERX report."""
    from engine_perx.orchestrator import fetch_perx_report

    row = fetch_perx_report(report_id, conn, str(client["id"]))
    if not row:
        raise HTTPException(status_code=404, detail={"v": 2, "error": "NOT_FOUND", "detail": "PERX report not found"})

    # Add module status summary
    report_payload = row.get("report_json")
    data_warnings = []
    module_status = {}
    if isinstance(report_payload, dict):
        ic = report_payload.get("investor_context", {})
        for key in ["peg_ratio", "ev_ebitda", "institutional_flow", "historical_analogs",
                     "valuation", "earnings_momentum", "ownership", "liquidity"]:
            mod = ic.get(key, {})
            if not isinstance(mod, dict):
                module_status[key] = "UNAVAILABLE"
            else:
                verdict = mod.get("verdict", "")
                if not verdict or any(w in verdict.lower()[:60] for w in ["unavailable", "no ", "insufficient"]):
                    module_status[key] = "UNAVAILABLE"
                else:
                    module_status[key] = "OK"
        data_warnings = report_payload.get("_data_warnings", [])

    return {
        "v": 2,
        "report": row,
        "data_warnings": data_warnings,
        "module_status": module_status,
    }
