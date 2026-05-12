from api.deps import get_db
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from api.auth import get_current_client
from engine_fundamental.aae_orchestrator import AAEOrchestrator
from engine_core.email_service import send_aae_report_email
import json
import logging
import psycopg2.extras

router = APIRouter(prefix="/api/aae", tags=["AAE V3"])
logger = logging.getLogger(__name__)

@router.get("/sectors/heatmap")
def get_sector_heatmap(conn=Depends(get_db)):
    """Fetch live sector relative strength and trends."""
    query = """
        SELECT i.sector_name, i.nse_ticker, h.ema_50, h.ema_200, h.relative_strength_90d
        FROM aae_sector_indices i
        JOIN aae_sector_history h ON i.sector_id = h.sector_id
        WHERE h.date = (SELECT MAX(date) FROM aae_sector_history)
        ORDER BY h.relative_strength_90d DESC NULLS LAST
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(query)
        rows = cur.fetchall()
        return rows
    except Exception as e:
        logger.error(f"Sector heatmap error: {e}")
        return []
    finally:
        cur.close()


def _persist_scan(result: dict, scan_source: str, conn):
    """
    Persist every AAE scan to:
      1. aae_scan_history   — append-only timeline (never overwritten)
      2. aae_results_snapshot — latest-state cache (upserted)
    """
    if result.get("status") == "REJECTED":
        return  # Don't persist kill-switch rejections

    symbol = result["symbol"]
    cur = conn.cursor()
    try:
        # 1. Append to history (immutable log)
        cur.execute("""
            INSERT INTO public.aae_scan_history (
                symbol, master_score, sector, market_confirmation,
                debate_conviction, risk_summary, reasons, scan_source
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            symbol,
            result.get("master_score"),
            result.get("sector"),
            result.get("market_confirmation"),
            result.get("debate_conviction"),
            result.get("risk_summary"),
            json.dumps(result.get("reasons", [])),
            scan_source,
        ))

        # 2. Upsert latest snapshot
        cur.execute("""
            INSERT INTO public.aae_results_snapshot (
                symbol, master_score, sector, valuation_status,
                ownership_status, reasons
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol) DO UPDATE SET
                master_score = EXCLUDED.master_score,
                sector = EXCLUDED.sector,
                valuation_status = EXCLUDED.valuation_status,
                ownership_status = EXCLUDED.ownership_status,
                reasons = EXCLUDED.reasons,
                updated_at = NOW()
        """, (
            symbol,
            result.get("master_score"),
            result.get("sector"),
            result.get("valuation_status"),
            result.get("ownership_status"),
            json.dumps(result.get("reasons", [])),
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to persist AAE scan for {symbol}: {e}")
    finally:
        cur.close()


@router.get("/scan/{symbol}")
async def get_aae_scan(symbol: str, client=Depends(get_current_client), conn=Depends(get_db)):
    """
    Trigger a full AAE V3 institutional scan for a symbol.
    Result is persisted to aae_scan_history + aae_results_snapshot.
    """
    try:
        orchestrator = AAEOrchestrator(symbol)
        result = orchestrator.run_full_scan()
        _persist_scan(result, "MANUAL", conn)
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


@router.get("/history/{symbol}")
async def get_aae_history(symbol: str, client=Depends(get_current_client)):
    """
    Fetch the full AAE scan history for a symbol — score trajectory over time.
    """
    from engine_core.db import fetch_df
    try:
        query = """
            SELECT master_score, sector, market_confirmation,
                   debate_conviction, risk_summary, reasons,
                   scan_source, scanned_at
            FROM aae_scan_history
            WHERE symbol = %s
            ORDER BY scanned_at DESC
            LIMIT 50
        """
        df = fetch_df(query, (symbol.upper(),))
        if df is None or df.empty:
            return []
        records = df.to_dict(orient='records')
        for r in records:
            if r.get('scanned_at'):
                r['scanned_at'] = str(r['scanned_at'])
        return records
    except Exception as e:
        logger.error(f"Failed to fetch AAE history for {symbol}: {e}")
        return []


@router.post("/email/{symbol}")
async def email_aae_report(
    symbol: str, 
    background_tasks: BackgroundTasks,
    client=Depends(get_current_client), 
    conn=Depends(get_db)
):
    """
    Trigger a full AAE V3 scan and email the detailed forensic report to the client.
    """
    try:
        orchestrator = AAEOrchestrator(symbol)
        result = orchestrator.run_full_scan()
        
        # Persist the scan
        _persist_scan(result, "EMAIL_REQUEST", conn)
        
        # Send email in background
        background_tasks.add_task(send_aae_report_email, client["email"], client.get("name", "Investor"), result)
        
        return {"status": "SUCCESS", "message": f"Forensic report for {symbol} has been queued for email to {client['email']}."}
    except Exception as e:
        logger.error(f"Failed to email AAE report for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

