from fastapi import APIRouter, Depends, HTTPException
from api.auth import get_current_client
from engine_fundamental.aae_orchestrator import AAEOrchestrator
import logging

router = APIRouter(prefix="/api/aae", tags=["AAE V3"])
logger = logging.getLogger(__name__)

@router.get("/scan/{symbol}")
async def get_aae_scan(symbol: str, client=Depends(get_current_client)):
    """
    Trigger a full AAE V3 institutional scan for a symbol.
    """
    try:
        orchestrator = AAEOrchestrator(symbol)
        result = orchestrator.run_full_scan()
        return result
    except Exception as e:
        logger.error(f"AAE Scan failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/top-candidates")
async def get_aae_top_candidates(client=Depends(get_current_client)):
    """
    Fetch top AAE V3 candidates from the pre-computed snapshot.
    """
    from engine_core.db import fetch_df
    try:
        query = """
            SELECT symbol, master_score, sector, valuation_status, 
                   ownership_status, reasons
            FROM aae_results_snapshot
            ORDER BY master_score DESC
            LIMIT 20
        """
        df = fetch_df(query)
        if df is None or df.empty:
            return []
        return df.to_dict(orient='records')
    except Exception as e:
        logger.error(f"Failed to fetch AAE top candidates: {e}")
        return []
