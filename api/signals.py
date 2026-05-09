"""
Signal endpoints: today's signals, signal history, current regime.
"""
from fastapi import APIRouter, Depends, Query
from datetime import date

from api.deps import get_db, get_current_client

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("/shadow")
def get_shadow_signals(conn=Depends(get_db)):
    """Top 10 stocks regardless of regime, specifically for swing trade audit."""
    cur = conn.cursor()
    try:
        # Fetching top 20 to find breakout candidates in the lead group
        cur.execute("""
            SELECT s.symbol, s.total_score, s.date,
                   s.condition_ema_50_200, s.condition_ema_200_slope,
                   s.condition_6m_high, s.condition_volume, s.condition_rs,
                   s.condition_breakout_10d, s.condition_price_quality,
                   dp.close
            FROM public.stock_scores s
            LEFT JOIN public.daily_prices dp
              ON dp.symbol = s.symbol AND dp.date = s.date
            WHERE s.date = (SELECT MAX(date) FROM public.stock_scores)
            ORDER BY s.total_score DESC, (s.condition_6m_high AND s.condition_volume) DESC, s.symbol ASC
            LIMIT 10
        """)
        rows = cur.fetchall()
        is_dict = not rows or isinstance(rows[0], dict)
        
        stocks = []
        for r in rows:
            if is_dict:
                sym, score, dt = r['symbol'], r['total_score'], r['date']
                c_ema, c_slope, c_high, c_vol, c_rs = r['condition_ema_50_200'], r['condition_ema_200_slope'], r['condition_6m_high'], r['condition_volume'], r['condition_rs']
                c_breakout, c_quality, close = r['condition_breakout_10d'], r['condition_price_quality'], r['close']
            else:
                sym, score, dt, c_ema, c_slope, c_high, c_vol, c_rs, c_breakout, c_quality, close = r
            
            # Explicitly force breakout detection
            is_breakout = bool(c_high and c_vol)
            
            stocks.append({
                "symbol": sym,
                "total_score": int(score) if score is not None else 0,
                "condition_ema_50_200": bool(c_ema),
                "condition_ema_200_slope": bool(c_slope),
                "condition_6m_high": bool(c_high),
                "condition_volume": bool(c_vol),
                "condition_rs": bool(c_rs),
                "condition_breakout_10d": bool(c_breakout),
                "condition_price_quality": bool(c_quality),
                "close": float(close) if close is not None else None,
                "is_breakout": is_breakout
            })
            
        latest_date = rows[0]["date"] if is_dict and rows else (rows[0][2] if rows else None)
        return {"date": str(latest_date) if latest_date else None, "stocks": stocks}
    except Exception as e:
        import logging
        logging.getLogger("mri_api").error(f"SHADOW_API_ERROR: {e}")
        return {"error": str(e), "stocks": []}
    finally:
        cur.close()

@router.get("/regime")
def get_current_regime(conn=Depends(get_db)):
    """Current market regime (latest date in market_regime)."""
    cur = conn.cursor()
    cur.execute("""
        SELECT date, classification, ema_50, ema_200
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
        "ema_50": float(row["ema_50"] if is_dict else row[2]) if (row["ema_50"] if is_dict else row[2]) else None,
        "ema_200": float(row["ema_200"] if is_dict else row[3]) if (row["ema_200"] if is_dict else row[3]) else None,
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
               ss.condition_6m_high, ss.condition_volume, ss.condition_rs,
               ss.condition_breakout_10d, ss.condition_price_quality
        FROM client_signals cs
        LEFT JOIN client_actions ca ON ca.signal_id = cs.id
        LEFT JOIN LATERAL (
            SELECT condition_ema_50_200, condition_ema_200_slope,
                   condition_6m_high, condition_volume, condition_rs,
                   condition_breakout_10d, condition_price_quality
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
                    "breakout_10d": bool(s["condition_breakout_10d"] if is_dict else s[16]),
                    "price_quality": bool(s["condition_price_quality"] if is_dict else s[17]),
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
               ss.condition_6m_high, ss.condition_volume, ss.condition_rs,
               ss.condition_breakout_10d, ss.condition_price_quality
        FROM client_signals cs
        LEFT JOIN client_actions ca ON ca.signal_id = cs.id
        LEFT JOIN LATERAL (
            SELECT condition_ema_50_200, condition_ema_200_slope,
                   condition_6m_high, condition_volume, condition_rs,
                   condition_breakout_10d, condition_price_quality
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
                "breakout_10d": bool(s["condition_breakout_10d"] if is_dict else s[13]),
                "price_quality": bool(s["condition_price_quality"] if is_dict else s[14]),
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
               ss.condition_6m_high, ss.condition_volume, ss.condition_rs,
               ss.condition_breakout_10d, ss.condition_price_quality
        FROM client_signals cs
        LEFT JOIN client_actions ca ON ca.signal_id = cs.id
        LEFT JOIN LATERAL (
            SELECT condition_ema_50_200, condition_ema_200_slope,
                   condition_6m_high, condition_volume, condition_rs,
                   condition_breakout_10d, condition_price_quality
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
                "breakout_10d": bool(s["condition_breakout_10d"] if is_dict else s[16]),
                "price_quality": bool(s["condition_price_quality"] if is_dict else s[17]),
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
               ss.condition_breakout_10d, ss.condition_price_quality,
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
                    "breakout_10d": s["condition_breakout_10d"] if is_dict else s[8],
                    "price_quality": s["condition_price_quality"] if is_dict else s[9],
                },
            }
            for s in stocks
        ],
    }
