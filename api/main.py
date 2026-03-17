from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import date
import logging
from src.db import get_connection

router = APIRouter(prefix="/api/signals", tags=["Signals"])
logger = logging.getLogger(__name__)

@router.get("/latest-date")
async def get_latest_available_date():
    """Returns the most recent date present in the scoring table."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT MAX(date) FROM stock_scores")
        row = cur.fetchone()
        return {"latest_date": row[0] if row else None}
    except Exception as e:
        logger.error(f"Error fetching latest date: {e}")
        return {"latest_date": None}
    finally:
        cur.close()
        conn.close()

@router.get("/")
async def get_market_signals(
    target_date: Optional[date] = None,
    regime_only: bool = False
):
    """
    Fetches MRI signals and Market Regime.
    If target_date is not provided, it automatically finds the ABSOLUTE LATEST data.
    """
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # 1. Determine the date to show
        if not target_date:
            cur.execute("SELECT MAX(date) FROM stock_scores")
            res = cur.fetchone()
            if not res or not res[0]:
                return {"date": None, "regime": "UNKNOWN", "signals": []}
            effective_date = res[0]
        else:
            effective_date = target_date

        # 2. Fetch Market Regime for that date
        cur.execute("""
            SELECT classification, sma_200, sma_200_slope_20 
            FROM market_regime 
            WHERE date = %s
        """, (effective_date,))
        regime_row = cur.fetchone()
        
        regime_data = {
            "classification": regime_row[0] if regime_row else "NEUTRAL",
            "sma_200": float(regime_row[1]) if regime_row and regime_row[1] else 0,
            "slope": float(regime_row[2]) if regime_row and regime_row[2] else 0
        }

        if regime_only:
            return {"date": effective_date, "regime": regime_data, "signals": []}

        # 3. Fetch all Stock Signals for that date
        cur.execute("""
            SELECT 
                symbol, total_score, condition_ema_50_200, 
                condition_ema_200_slope, condition_6m_high, 
                condition_volume, condition_rs
            FROM stock_scores 
            WHERE date = %s
            ORDER BY total_score DESC, symbol ASC
        """, (effective_date,))
        
        rows = cur.fetchall()
        signals = [
            {
                "symbol": r[0],
                "score": r[1],
                "details": {
                    "ema_trend": r[2],
                    "slope_up": r[3],
                    "at_6m_high": r[4],
                    "vol_surge": r[5],
                    "relative_strength": r[6]
                }
            } for r in rows
        ]

        return {
            "date": effective_date,
            "regime": regime_data,
            "signals": signals
        }

    except Exception as e:
        logger.error(f"Failed to fetch signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()