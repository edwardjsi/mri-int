"""
Portfolio endpoints: open positions, equity curve, performance vs benchmark.
"""
from fastapi import APIRouter, Depends

from api.deps import get_db, get_current_client

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/positions")
def get_open_positions(
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Client's currently open positions with latest prices."""
    cur = conn.cursor()
    cur.execute("""
        SELECT cp.symbol, cp.entry_date, cp.entry_price, cp.quantity, cp.highest_price,
               dp.close AS current_price,
               ROUND(((dp.close - cp.entry_price) / cp.entry_price) * 100, 2) AS pnl_pct
        FROM client_portfolio cp
        LEFT JOIN LATERAL (
            SELECT close FROM daily_prices
            WHERE symbol = cp.symbol
            ORDER BY date DESC LIMIT 1
        ) dp ON true
        WHERE cp.client_id = %s AND cp.is_open = true
        ORDER BY cp.entry_date DESC
    """, (str(client["id"]),))
    positions = cur.fetchall()

    return {
        "count": len(positions),
        "positions": [
            {
                "symbol": p["symbol"],
                "entry_date": str(p["entry_date"]),
                "entry_price": float(p["entry_price"]) if p["entry_price"] else None,
                "quantity": p["quantity"],
                "current_price": float(p["current_price"]) if p["current_price"] else None,
                "pnl_pct": float(p["pnl_pct"]) if p["pnl_pct"] else None,
                "highest_price": float(p["highest_price"]) if p["highest_price"] else None,
            }
            for p in positions
        ],
    }


@router.get("/equity")
def get_equity_curve(
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Client's daily equity curve."""
    cur = conn.cursor()
    cur.execute("""
        SELECT date, equity, cash, open_positions
        FROM client_equity
        WHERE client_id = %s
        ORDER BY date
    """, (str(client["id"]),))
    rows = cur.fetchall()

    return [
        {
            "date": str(r["date"]),
            "equity": float(r["equity"]),
            "cash": float(r["cash"]),
            "open_positions": r["open_positions"],
        }
        for r in rows
    ]


@router.get("/performance")
def get_performance(
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Client equity vs Nifty 50 benchmark comparison."""
    cur = conn.cursor()

    # Client equity
    cur.execute("""
        SELECT date, equity FROM client_equity
        WHERE client_id = %s ORDER BY date
    """, (str(client["id"]),))
    client_eq = cur.fetchall()

    if not client_eq:
        return {"message": "No equity data yet. Execute some signals first."}

    # Nifty benchmark for same period
    start_date = client_eq[0]["date"]
    cur.execute("""
        SELECT date, close FROM index_prices
        WHERE symbol = 'NIFTY50' AND date >= %s
        ORDER BY date
    """, (start_date,))
    nifty = cur.fetchall()

    # Normalize to base 100
    client_base = float(client_eq[0]["equity"])
    nifty_base = float(nifty[0]["close"]) if nifty else 1

    return {
        "client": [
            {"date": str(r["date"]), "value": round(float(r["equity"]) / client_base * 100, 2)}
            for r in client_eq
        ],
        "nifty": [
            {"date": str(r["date"]), "value": round(float(r["close"]) / nifty_base * 100, 2)}
            for r in nifty
        ],
        "initial_capital": client_base,
        "latest_equity": float(client_eq[-1]["equity"]) if client_eq else 0,
    }


@router.get("/daily-summary")
def get_daily_summary(
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Today's portfolio P&L summary."""
    cur = conn.cursor()

    # Get last 2 equity entries to calculate daily change
    cur.execute("""
        SELECT date, equity, cash, open_positions
        FROM client_equity
        WHERE client_id = %s
        ORDER BY date DESC LIMIT 2
    """, (str(client["id"]),))
    rows = cur.fetchall()

    if not rows:
        return {
            "has_data": False,
            "message": "No portfolio data yet. Execute some signals to start tracking.",
        }

    today = rows[0]
    yesterday = rows[1] if len(rows) > 1 else None

    today_equity = float(today["equity"])
    prev_equity = float(yesterday["equity"]) if yesterday else today_equity
    daily_change = today_equity - prev_equity
    daily_pct = (daily_change / prev_equity * 100) if prev_equity else 0

    # Overall return
    cur.execute("SELECT initial_capital FROM clients WHERE id = %s", (str(client["id"]),))
    capital = float(cur.fetchone()["initial_capital"])
    total_return = today_equity - capital
    total_pct = (total_return / capital * 100) if capital else 0

    return {
        "has_data": True,
        "date": str(today["date"]),
        "equity": today_equity,
        "cash": float(today["cash"]),
        "open_positions": today["open_positions"],
        "daily_change": round(daily_change, 2),
        "daily_pct": round(daily_pct, 2),
        "total_return": round(total_return, 2),
        "total_pct": round(total_pct, 2),
        "initial_capital": capital,
    }
