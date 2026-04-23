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
    cur.close()
    
    if not row:
        return {"regime": "UNKNOWN", "date": None}
    
    # Tuple-safe access
    is_dict = isinstance(row, dict)
    res = {
        "regime": row["classification"] if is_dict else row[1],
        "date": str(row["date"] if is_dict else row[0]),
        "sma_200": float(row["sma_200"] if is_dict else row[2]) if (row["sma_200"] if is_dict else row[2]) else None,
        "sma_200_slope": float(row["sma_200_slope_20"] if is_dict else row[3]) if (row["sma_200_slope_20"] if is_dict else row[3]) else None,
    }
    return res


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
               ca.action_taken, ca.actual_price, ca.quantity,
               ss.condition_ema_50_200, ss.condition_ema_200_slope,
               ss.condition_6m_high, ss.condition_volume, ss.condition_rs
        FROM client_signals cs
        LEFT JOIN client_actions ca ON ca.signal_id = cs.id
        LEFT JOIN LATERAL (
            SELECT condition_ema_50_200, condition_ema_200_slope,
                   condition_6m_high, condition_volume, condition_rs
            FROM stock_scores
            WHERE symbol = cs.symbol AND date = cs.date
            LIMIT 1
        ) ss ON true
        WHERE cs.client_id = %s
          AND cs.date = (SELECT MAX(date) FROM client_signals WHERE client_id = %s)
        ORDER BY cs.action, cs.score DESC
    """, (str(client["id"]), str(client["id"])))
    signals = cur.fetchall()
    cur.close()

    is_dict = not signals or isinstance(signals[0], dict)
    
    return {
        "date": str(signals[0]["date"] if is_dict else signals[0][1]) if signals else str(date.today()),
        "signals": [
            {
                "id": str(s["id"] if is_dict else s[0]),
                "symbol": s["symbol"] if is_dict else s[2],
                "action": s["action"] if is_dict else s[3],
                "recommended_price": float(s["recommended_price"] if is_dict else s[4]) if (s["recommended_price"] if is_dict else s[4]) else None,
                "score": s["score"] if is_dict else s[5],
                "regime": s["regime"] if is_dict else s[6],
                "reason": s["reason"] if is_dict else s[7],
                "client_action": s["action_taken"] if is_dict else s[8],
                "actual_price": float(s["actual_price"] if is_dict else s[9]) if (s["actual_price"] if is_dict else s[9]) else None,
                "quantity": s["quantity"] if is_dict else s[10],
                "conditions": {
                    "ema_50_above_200": bool(s["condition_ema_50_200"] if is_dict else s[11]),
                    "ema_200_slope_positive": bool(s["condition_ema_200_slope"] if is_dict else s[12]),
                    "at_6m_high": bool(s["condition_6m_high"] if is_dict else s[13]),
                    "volume_surge": bool(s["condition_volume"] if is_dict else s[14]),
                    "relative_strength": bool(s["condition_rs"] if is_dict else s[15]),
                } if (s["condition_ema_50_200"] if is_dict else s[11]) is not None else None
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
               cs.score, cs.regime, cs.reason,
               ss.condition_ema_50_200, ss.condition_ema_200_slope,
               ss.condition_6m_high, ss.condition_volume, ss.condition_rs
        FROM client_signals cs
        LEFT JOIN client_actions ca ON ca.signal_id = cs.id
        LEFT JOIN LATERAL (
            SELECT condition_ema_50_200, condition_ema_200_slope,
                   condition_6m_high, condition_volume, condition_rs
            FROM stock_scores
            WHERE symbol = cs.symbol AND date = cs.date
            LIMIT 1
        ) ss ON true
        WHERE cs.client_id = %s
          AND ca.id IS NULL
        ORDER BY cs.date DESC, cs.action, cs.score DESC
    """, (str(client["id"]),))
    signals = cur.fetchall()
    cur.close()

    is_dict = not signals or isinstance(signals[0], dict)

    return [
        {
            "id": str(s["id"] if is_dict else s[0]),
            "date": str(s["date"] if is_dict else s[1]),
            "symbol": s["symbol"] if is_dict else s[2],
            "action": s["action"] if is_dict else s[3],
            "recommended_price": float(s["recommended_price"] if is_dict else s[4]) if (s["recommended_price"] if is_dict else s[4]) else None,
            "score": s["score"] if is_dict else s[5],
            "regime": s["regime"] if is_dict else s[6],
            "reason": s["reason"] if is_dict else s[7],
            "conditions": {
                "ema_50_above_200": bool(s["condition_ema_50_200"] if is_dict else s[8]),
                "ema_200_slope_positive": bool(s["condition_ema_200_slope"] if is_dict else s[9]),
                "at_6m_high": bool(s["condition_6m_high"] if is_dict else s[10]),
                "volume_surge": bool(s["condition_volume"] if is_dict else s[11]),
                "relative_strength": bool(s["condition_rs"] if is_dict else s[12]),
            } if (s["condition_ema_50_200"] if is_dict else s[8]) is not None else None
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
               ca.action_taken, ca.actual_price, ca.quantity,
               ss.condition_ema_50_200, ss.condition_ema_200_slope,
               ss.condition_6m_high, ss.condition_volume, ss.condition_rs
        FROM client_signals cs
        LEFT JOIN client_actions ca ON ca.signal_id = cs.id
        LEFT JOIN LATERAL (
            SELECT condition_ema_50_200, condition_ema_200_slope,
                   condition_6m_high, condition_volume, condition_rs
            FROM stock_scores
            WHERE symbol = cs.symbol AND date = cs.date
            LIMIT 1
        ) ss ON true
        WHERE cs.client_id = %s
          AND cs.date >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY cs.date DESC, cs.action, cs.symbol
    """, (str(client["id"]), days))
    signals = cur.fetchall()
    cur.close()

    is_dict = not signals or isinstance(signals[0], dict)

    return [
        {
            "id": str(s["id"] if is_dict else s[0]),
            "date": str(s["date"] if is_dict else s[1]),
            "symbol": s["symbol"] if is_dict else s[2],
            "action": s["action"] if is_dict else s[3],
            "recommended_price": float(s["recommended_price"] if is_dict else s[4]) if (s["recommended_price"] if is_dict else s[4]) else None,
            "score": s["score"] if is_dict else s[5],
            "regime": s["regime"] if is_dict else s[6],
            "reason": s["reason"] if is_dict else s[7],
            "client_action": s["action_taken"] if is_dict else s[8],
            "actual_price": float(s["actual_price"] if is_dict else s[9]) if (s["actual_price"] if is_dict else s[9]) else None,
            "quantity": s["quantity"] if is_dict else s[10],
            "conditions": {
                "ema_50_above_200": bool(s["condition_ema_50_200"] if is_dict else s[11]),
                "ema_200_slope_positive": bool(s["condition_ema_200_slope"] if is_dict else s[12]),
                "at_6m_high": bool(s["condition_6m_high"] if is_dict else s[13]),
                "volume_surge": bool(s["condition_volume"] if is_dict else s[14]),
                "relative_strength": bool(s["condition_rs"] if is_dict else s[15]),
            } if (s["condition_ema_50_200"] if is_dict else s[11]) is not None else None
        }
        for s in signals
    ]


@router.get("/screener")
def get_screener(
    conn=Depends(get_db),
    min_score: int = Query(default=75, ge=0, le=100),
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
    cur.close()

    is_dict = not stocks or isinstance(stocks[0], dict)

    return {
        "date": str(stocks[0]["date"] if is_dict else stocks[0][2]) if stocks else None,
        "count": len(stocks),
        "stocks": [
            {
                "symbol": s["symbol"] if is_dict else s[0],
                "score": s["total_score"] if is_dict else s[1],
                "close": float(s["close"] if is_dict else s[8]) if (s["close"] if is_dict else s[8]) else None,
                "volume": int(s["volume"] if is_dict else s[9]) if (s["volume"] if is_dict else s[9]) else None,
                "conditions": {
                    "ema_50_200": s["condition_ema_50_200"] if is_dict else s[3],
                    "ema_200_slope": s["condition_ema_200_slope"] if is_dict else s[4],
                    "6m_high": s["condition_6m_high"] if is_dict else s[5],
                    "volume": s["condition_volume"] if is_dict else s[6],
                    "relative_strength": s["condition_rs"] if is_dict else s[7],
                },
            }
            for s in stocks
        ],
    }
