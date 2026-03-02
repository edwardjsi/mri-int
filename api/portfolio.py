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
