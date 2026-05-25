from api.deps import get_db
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from api.auth import get_current_client
from engine_core.aae_re_rating_orchestrator import ReRatingOrchestrator
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


def _persist_rerating_profile(profile: dict, conn):
    """
    Persist a Re-Rating Candidate Profile to:
      1. aae_re_rating_profiles — versioned master record
      2. aae_results_snapshot   — legacy snapshot cache (for top-candidates backward compat)
    """
    if profile.get("status") == "REJECTED":
        return

    symbol = profile["symbol"]
    cur = conn.cursor()
    try:
        # 1. Upsert re-rating profile (versioned)
        cur.execute(
            """
            INSERT INTO public.aae_re_rating_profiles (symbol, profile, thesis_version, thesis_hash)
            VALUES (%s, %s, 1, %s)
            ON CONFLICT (symbol) DO UPDATE SET
                profile         = EXCLUDED.profile,
                thesis_version  = public.aae_re_rating_profiles.thesis_version + 1,
                thesis_hash     = EXCLUDED.thesis_hash,
                updated_at      = NOW()
            RETURNING thesis_version
            """,
            (symbol, psycopg2.extras.Json(profile), profile.get("thesis", {}).get("summary", "")[:32]),
        )
        version = cur.fetchone()["thesis_version"]

        # 2. Upsert legacy snapshot cache
        scores = profile.get("financial_fingerprint", {})
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
            profile.get("rerating_probability_score"),
            profile.get("macro_alignment", {}).get("sector"),
            scores.get("valuation_status"),
            scores.get("ownership_status"),
            json.dumps([r for r in profile.get("thesis", {}).get("reasons", [])]),
        ))

        conn.commit()
        logger.info(f"Persisted Re-Rating Profile for {symbol} (v{version})")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to persist Re-Rating Profile for {symbol}: {e}")
    finally:
        cur.close()


@router.get("/scan/{symbol}")
async def get_aae_scan(symbol: str, client=Depends(get_current_client), conn=Depends(get_db)):
    """
    Build a full Re-Rating Candidate Profile for a symbol.
    Result is persisted to aae_re_rating_profiles + aae_results_snapshot.
    """
    try:
        orchestrator = ReRatingOrchestrator(symbol)
        profile = orchestrator.build_profile()
        _persist_rerating_profile(profile, conn)
        return profile
    except Exception as e:
        logger.error(f"AAE scan failed for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/top-candidates")
async def get_aae_top_candidates(client=Depends(get_current_client)):
    """
    Fetch top AAE candidates ranked by re-rating probability score.
    Uses the aae_re_rating_profiles cache (populated by every scan).
    """
    from engine_core.db import fetch_df
    try:
        # Fetch re-rating profiles and extract in Python for reliable casting
        query = "SELECT symbol, profile FROM aae_re_rating_profiles ORDER BY symbol"
        df = fetch_df(query)
        if df is not None and not df.empty:
            candidates = []
            for _, r in df.iterrows():
                p = r["profile"]
                if isinstance(p, str):
                    import json as _json
                    p = _json.loads(p)
                candidates.append({
                    "symbol": r["symbol"],
                    "master_score": p.get("rerating_probability_score"),
                    "sector": p.get("macro_alignment", {}).get("sector"),
                    "thesis_summary": p.get("thesis", {}).get("summary"),
                    "risk_level": p.get("risk_level"),
                    "macro_outlook": p.get("macro_alignment", {}).get("outlook"),
                })
            return sorted(candidates, key=lambda x: x["master_score"] or 0, reverse=True)[:20]
    except Exception as e:
        logger.warning(f"Re-rating profile query failed: {e}")

        # Fallback: legacy snapshot
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
    Build a Re-Rating Profile and email the detailed forensic report.
    """
    try:
        orchestrator = ReRatingOrchestrator(symbol)
        profile = orchestrator.build_profile()

        # Persist the profile
        _persist_rerating_profile(profile, conn)

        # Extract legacy scan result for email (builder expects AAEOrchestrator output format)
        legacy_result = profile.get("legacy_forensic", profile)
        legacy_result["symbol"] = symbol.upper()

        # Send email in background
        background_tasks.add_task(send_aae_report_email, client["email"], client.get("name", "Investor"), legacy_result)

        return {"status": "SUCCESS", "message": f"Re-Rating Profile for {symbol} queued for email to {client['email']}."}
    except Exception as e:
        logger.error(f"Failed to email AAE report for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

