"""
Signal endpoints: today's signals, signal history, current regime.
"""
from fastapi import APIRouter, Depends, Query
from datetime import date

from api.deps import get_db, get_current_client

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("/regime")
def get_current_regime(conn=Depends(get_db)):
    """Current market regime (latest date in market_regime)."""
    cur = conn.cursor()
    cur.execute("""
        SELECT date, classification, sma_200, sma_200_slope_20
        FROM market_regime
        ORDER BY date DESC LIMIT 1
    """)
    row = cur.fetchone()
    if not row:
        return {"regime": "UNKNOWN", "date": None}
    return {
        "regime": row["classification"],
        "date": str(row["date"]),
        "sma_200": float(row["sma_200"]) if row["sma_200"] else None,
        "sma_200_slope": float(row["sma_200_slope_20"]) if row["sma_200_slope_20"] else None,
    }


@router.get("/today")
def get_todays_signals(
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Today's BUY/SELL signals for the logged-in client."""
    cur = conn.cursor()
    cur.execute("""
        SELECT cs.id, cs.date, cs.symbol, cs.action, cs.recommended_price,
               cs.score, cs.regime, cs.reason,
               ca.action_taken, ca.actual_price, ca.quantity
        FROM client_signals cs
        LEFT JOIN client_actions ca ON ca.signal_id = cs.id
        WHERE cs.client_id = %s
          AND cs.date = (SELECT MAX(date) FROM client_signals WHERE client_id = %s)
        ORDER BY cs.action, cs.score DESC
    """, (str(client["id"]), str(client["id"])))
    signals = cur.fetchall()

    return {
        "date": str(signals[0]["date"]) if signals else str(date.today()),
        "signals": [
            {
                "id": str(s["id"]),
                "symbol": s["symbol"],
                "action": s["action"],
                "recommended_price": float(s["recommended_price"]) if s["recommended_price"] else None,
                "score": s["score"],
                "regime": s["regime"],
                "reason": s["reason"],
                "client_action": s["action_taken"],
                "actual_price": float(s["actual_price"]) if s["actual_price"] else None,
                "quantity": s["quantity"],
            }
            for s in signals
        ],
    }


@router.get("/pending")
def get_pending_signals(
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """All signals the client hasn't acted on yet (from any date)."""
    cur = conn.cursor()
    cur.execute("""
        SELECT cs.id, cs.date, cs.symbol, cs.action, cs.recommended_price,
               cs.score, cs.regime, cs.reason
        FROM client_signals cs
        LEFT JOIN client_actions ca ON ca.signal_id = cs.id
        WHERE cs.client_id = %s
          AND ca.id IS NULL
        ORDER BY cs.date DESC, cs.action, cs.score DESC
    """, (str(client["id"]),))
    signals = cur.fetchall()

    return [
        {
            "id": str(s["id"]),
            "date": str(s["date"]),
            "symbol": s["symbol"],
            "action": s["action"],
            "recommended_price": float(s["recommended_price"]) if s["recommended_price"] else None,
            "score": s["score"],
            "regime": s["regime"],
            "reason": s["reason"],
        }
        for s in signals
    ]


@router.get("/history")
def get_signal_history(
    client=Depends(get_current_client),
    conn=Depends(get_db),
    days: int = Query(default=30, le=365),
):
    """Signal history for the past N days."""
    cur = conn.cursor()
    cur.execute("""
        SELECT cs.id, cs.date, cs.symbol, cs.action, cs.recommended_price,
               cs.score, cs.regime, cs.reason,
               ca.action_taken, ca.actual_price, ca.quantity
        FROM client_signals cs
        LEFT JOIN client_actions ca ON ca.signal_id = cs.id
        WHERE cs.client_id = %s
          AND cs.date >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY cs.date DESC, cs.action, cs.symbol
    """, (str(client["id"]), days))
    signals = cur.fetchall()

    return [
        {
            "id": str(s["id"]),
            "date": str(s["date"]),
            "symbol": s["symbol"],
            "action": s["action"],
            "recommended_price": float(s["recommended_price"]) if s["recommended_price"] else None,
            "score": s["score"],
            "regime": s["regime"],
            "reason": s["reason"],
            "client_action": s["action_taken"],
            "actual_price": float(s["actual_price"]) if s["actual_price"] else None,
            "quantity": s["quantity"],
        }
        for s in signals
    ]


@router.get("/screener")
def get_screener(
    conn=Depends(get_db),
    min_score: int = Query(default=4, ge=0, le=5),
):
    """Latest stock scores, filterable by minimum score."""
    cur = conn.cursor()
    cur.execute("""
        SELECT ss.symbol, ss.total_score, ss.date,
               ss.condition_ema_50_200, ss.condition_ema_200_slope,
               ss.condition_6m_high, ss.condition_volume, ss.condition_rs,
               dp.close, dp.volume
        FROM stock_scores ss
        JOIN daily_prices dp ON dp.symbol = ss.symbol AND dp.date = ss.date
        WHERE ss.date = (SELECT MAX(date) FROM stock_scores)
          AND ss.total_score >= %s
        ORDER BY ss.total_score DESC, ss.symbol
    """, (min_score,))
    stocks = cur.fetchall()

    return {
        "date": str(stocks[0]["date"]) if stocks else None,
        "count": len(stocks),
        "stocks": [
            {
                "symbol": s["symbol"],
                "score": s["total_score"],
                "close": float(s["close"]) if s["close"] else None,
                "volume": int(s["volume"]) if s["volume"] else None,
                "conditions": {
                    "ema_50_200": s["condition_ema_50_200"],
                    "ema_200_slope": s["condition_ema_200_slope"],
                    "6m_high": s["condition_6m_high"],
                    "volume": s["condition_volume"],
                    "relative_strength": s["condition_rs"],
                },
            }
            for s in stocks
        ],
    }
