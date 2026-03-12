from datetime import date
from fastapi import APIRouter, Depends
from psycopg2.extras import RealDictCursor
from api.deps import get_db, get_current_client
from src.portfolio_review_engine import analyze_portfolio

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/positions")
def get_open_positions(
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Client's currently open positions (Core + External)."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    client_id = str(client["id"])
    
    # 1. Fetch Core Positions (from MRI signals)
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
    """, (client_id,))
    core_rows = cur.fetchall()
    
    # 2. Fetch External Positions (Digital Twin)
    cur.execute("""
        SELECT symbol, quantity, avg_cost
        FROM client_external_holdings
        WHERE client_id = %s
    """, (client_id,))
    external_rows = cur.fetchall()
    
    positions = []
    
    # Process Core
    for p in core_rows:
        positions.append({
            "source": "Core",
            "symbol": p["symbol"],
            "entry_date": str(p["entry_date"]),
            "entry_price": float(p["entry_price"]) if p["entry_price"] else None,
            "quantity": p["quantity"],
            "current_price": float(p["current_price"]) if p["current_price"] else None,
            "pnl_pct": float(p["pnl_pct"]) if p["pnl_pct"] else None,
        })
        
    # Process External via Review Engine for valuation
    if external_rows:
        external_holdings = [dict(r) for r in external_rows]
        analysis = analyze_portfolio(external_holdings, conn=conn)
        for h in analysis.get("holdings", []):
            positions.append({
                "source": "External",
                "symbol": h["symbol"],
                "entry_date": "N/A",
                "entry_price": float(h["avg_cost"]) if h["avg_cost"] else None,
                "quantity": h["quantity"],
                "current_price": float(h["current_price"]) if h["current_price"] else None,
                "pnl_pct": float(h["pnl_pct"]) if h.get("pnl_pct") is not None else None,
            })

    return {
        "count": len(positions),
        "positions": positions
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
    """Today's unified portfolio P&L summary."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    client_id = str(client["id"])

    # 1. Fetch Core Data
    cur.execute("""
        SELECT date, equity, cash, open_positions
        FROM client_equity
        WHERE client_id = %s
        ORDER BY date DESC LIMIT 2
    """, (client_id,))
    core_rows = cur.fetchall()

    # 2. Fetch External Data
    cur.execute("""
        SELECT symbol, quantity, avg_cost
        FROM client_external_holdings
        WHERE client_id = %s
    """, (client_id,))
    external_rows = cur.fetchall()
    
    ext_market_value = 0
    ext_cost_basis = 0
    ext_count = 0
    
    if external_rows:
        ext_holdings = [dict(r) for r in external_rows]
        analysis = analyze_portfolio(ext_holdings, conn=conn)
        ext_market_value = analysis.get("total_portfolio_value", 0)
        ext_cost_basis = sum(h["quantity"] * h["avg_cost"] for h in ext_holdings)
        ext_count = len(ext_holdings)

    if not core_rows and not external_rows:
        return {
            "has_data": False,
            "message": "No portfolio data yet. Execute signals or upload a CSV.",
        }

    # Base values (if no core rows, we start from initial capital)
    core_today = core_rows[0] if core_rows else None
    core_yesterday = core_rows[1] if len(core_rows) > 1 else None
    
    initial_cap = float(client["initial_capital"])
    
    # Combined Metrics
    total_equity = (float(core_today["equity"]) if core_today else initial_cap) + ext_market_value
    prev_equity = (float(core_yesterday["equity"]) if core_yesterday else (float(core_today["equity"]) if core_today else initial_cap)) + ext_market_value # Crude approx for daily change
    
    total_invested = initial_cap + ext_cost_basis
    total_return = total_equity - total_invested
    total_pct = (total_return / total_invested * 100) if total_invested else 0

    return {
        "has_data": True,
        "date": str(core_today["date"]) if core_today else str(date.today()),
        "equity": round(total_equity, 2),
        "cash": float(core_today["cash"]) if core_today else initial_cap,
        "open_positions": (core_today["open_positions"] if core_today else 0) + ext_count,
        "daily_change": round(total_equity - prev_equity, 2),
        "daily_pct": round(((total_equity - prev_equity)/prev_equity*100), 2) if prev_equity else 0,
        "total_return": round(total_return, 2),
        "total_pct": round(total_pct, 2),
        "initial_capital": initial_cap,
        "external_cost": round(ext_cost_basis, 2),
        "total_invested": round(total_invested, 2)
    }
