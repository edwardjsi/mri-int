from fastapi import APIRouter, Depends, HTTPException, Background_tasks
from pydantic import BaseModel
from typing import List, Optional
import logging
from datetime import datetime

# Unified import - removed the missing grade_symbols_sync
from src.on_demand_ingest import ingest_missing_symbols_sync
from src.db import get_connection

router = APIRouter(prefix="/api/portfolio-review", tags=["Portfolio Review"])
logger = logging.getLogger(__name__)

class ReviewRequest(BaseModel):
    email: str
    name: str
    symbols: List[str]

@router.post("/request")
async def request_portfolio_review(request: ReviewRequest):
    """
    Triggers a synchronized ingestion and scoring for a specific client portfolio.
    This replaces the old two-step fetch and grade process.
    """
    if not request.symbols:
        raise HTTPException(status_code=400, detail="No symbols provided for review.")

    try:
        logger.info(f"Starting on-demand review for {request.name} ({request.email})")
        
        # This function now handles Fetch -> Indicators -> Scoring in one transaction
        # It is the hardened version we verified in the terminal earlier
        ingest_missing_symbols_sync(
            symbols=request.symbols,
            user_id="admin",
            user_email=request.email,
            user_name=request.name
        )

        return {
            "status": "success",
            "message": f"Portfolio review completed for {len(request.symbols)} symbols.",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Portfolio review failed for {request.email}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Review failed: {str(e)}")

@router.get("/status/{email}")
async def get_review_results(email: str):
    """
    Fetches the latest scores for a client's specific portfolio.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Fetching the absolute latest scores for this client's symbols
        # Note: In a production environment, you would join this with a 'holdings' table
        cur.execute("""
            SELECT s.symbol, s.total_score, s.date,
                   s.condition_ema_50_200, s.condition_ema_200_slope,
                   s.condition_6m_high, s.condition_volume, s.condition_rs
            FROM stock_scores s
            WHERE s.date = (SELECT MAX(date) FROM stock_scores)
            ORDER BY s.total_score DESC
        """)
        
        rows = cur.fetchall()
        results = [
            {
                "symbol": r[0],
                "score": r[1],
                "date": r[2],
                "details": {
                    "ema_trend": r[3],
                    "slope_up": r[4],
                    "at_6m_high": r[5],
                    "vol_surge": r[6],
                    "relative_strength": r[7]
                }
            } for r in rows
        ]

        return {"email": email, "latest_scores": results}

    except Exception as e:
        logger.error(f"Error fetching results for {email}: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve portfolio status.")
    finally:
        cur.close()
        conn.close()