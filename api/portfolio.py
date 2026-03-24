from datetime import date
from fastapi import APIRouter, Depends
from psycopg2.extras import RealDictCursor
from api.deps import get_db, get_current_client
from api.schema import ensure_client_external_holdings_table
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
    cur.execute(
        """
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
        """,
        (client_id,),
    )
    core_rows = cur.fetchall()

    # 2. Fetch External Positions (Digital Twin)
    external_rows = []
    try:
        ensure_client_external_holdings_table(conn)
        cur.execute(
            """
            SELECT symbol, quantity, avg_cost
            FROM client_external_holdings
            WHERE client_id = %s
            """,
            (client_id,),
        )
        external_rows = cur.fetchall()
    except Exception:
        conn.rollback()

    positions = []

    # Process Core
    is_dict = not core_rows or isinstance(core_rows[0], dict)
    for p in core_rows:
        positions.append(
            {
                "source": "Core",
                "symbol": p["symbol"] if is_dict else p[0],
                "entry_date": str(p["entry_date"] if is_dict else p[1]),
                "entry_price": float(p["entry_price"] if is_dict else p[2]) if (p["entry_price"] if is_dict else p[2]) else None,
                "quantity": p["quantity"] if is_dict else p[3],
                "current_price": float(p["current_price"] if is_dict else p[5]) if (p["current_price"] if is_dict else p[5]) else None,
                "pnl_pct": float(p["pnl_pct"] if is_dict else p[6]) if (p["pnl_pct"] if is_dict else p[6]) else None,
            }
        )

    # Process External via Review Engine for valuation
    if external_rows:
        is_dict_ext = isinstance(external_rows[0], dict)
        external_holdings = []
        for r in external_rows:
            if is_dict_ext:
                external_holdings.append(dict(r))
            else:
                external_holdings.append({
                    "symbol": r[0],
                    "quantity": r[1],
                    "avg_cost": r[2]
                })

        try:
            analysis = analyze_portfolio(external_holdings, conn=conn)
            for h in analysis.get("holdings", []):
                positions.append(
                    {
                        "source": "External",
                        "symbol": h["symbol"],
                        "entry_date": "N/A",
                        "entry_price": float(h["avg_cost"]) if h.get("avg_cost") else None,
                        "quantity": h["quantity"],
                        "current_price": float(h["current_price"]) if h.get("current_price") else None,
                        "pnl_pct": float(h["pnl_pct"]) if h.get("pnl_pct") is not None else None,
                    }
                )
        except Exception:
            # If analysis tables are missing (fresh DB) or scoring isn't ready yet, still show holdings.
            conn.rollback()
            syms = [str(h.get("symbol", "")).upper().strip() for h in external_holdings if h.get("symbol")]
            prices_by_symbol = {}
            if syms:
                cur.execute(
                    """
                    SELECT DISTINCT ON (dp.symbol) dp.symbol, dp.close
                    FROM daily_prices dp
                    WHERE dp.symbol = ANY(%s)
                    ORDER BY dp.symbol, dp.date DESC
                    """,
                    (syms,),
                )
                prices_rows = cur.fetchall()
                is_dict_pr = not prices_rows or isinstance(prices_rows[0], dict)
                prices_by_symbol = {
                    (r["symbol"] if is_dict_pr else r[0]): (r["close"] if is_dict_pr else r[1]) 
                    for r in prices_rows 
                    if (r["symbol"] if is_dict_pr else r[0])
                }

            for h in external_holdings:
                sym = str(h.get("symbol", "")).upper().strip()
                qty = float(h.get("quantity", 0) or 0)
                avg_cost = float(h.get("avg_cost", 0) or 0)
                current = prices_by_symbol.get(sym)
                current_price = float(current) if current is not None else None
                pnl_pct = None
                if current_price is not None and avg_cost > 0:
                    pnl_pct = round(((current_price - avg_cost) / avg_cost) * 100, 2)

                positions.append(
                    {
                        "source": "External",
                        "symbol": sym,
                        "entry_date": "N/A",
                        "entry_price": avg_cost if avg_cost > 0 else None,
                        "quantity": qty,
                        "current_price": current_price,
                        "pnl_pct": pnl_pct,
                    }
                )

    return {"count": len(positions), "positions": positions}


@router.get("/equity")
def get_equity_curve(
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Client's daily equity curve."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        SELECT date, equity, cash, open_positions
        FROM client_equity
        WHERE client_id = %s
        ORDER BY date
        """,
        (str(client["id"]),),
    )
    rows = cur.fetchall()
    cur.close()

    is_dict = not rows or isinstance(rows[0], dict)

    return [
        {
            "date": str(r["date"] if is_dict else r[0]),
            "equity": float(r["equity"] if is_dict else r[1]),
            "cash": float(r["cash"] if is_dict else r[2]),
            "open_positions": r["open_positions"] if is_dict else r[3],
        }
        for r in rows
    ]


@router.get("/performance")
def get_performance(
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Client equity vs Nifty 50 benchmark comparison."""
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Client equity
    cur.execute(
        """
        SELECT date, equity FROM client_equity
        WHERE client_id = %s ORDER BY date
        """,
        (str(client["id"]),),
    )
    client_eq = cur.fetchall()

    if not client_eq:
        cur.close()
        return {"message": "No equity data yet. Execute some signals first."}

    is_dict_ce = isinstance(client_eq[0], dict)

    # Nifty benchmark for same period
    start_date = client_eq[0]["date"] if is_dict_ce else client_eq[0][0]
    cur.execute(
        """
        SELECT date, close FROM index_prices
        WHERE symbol = 'NIFTY50' AND date >= %s
        ORDER BY date
        """,
        (start_date,),
    )
    nifty = cur.fetchall()
    cur.close()

    # Normalize to base 100
    client_base = float(client_eq[0]["equity"] if is_dict_ce else client_eq[0][1])
    
    is_dict_nf = not nifty or isinstance(nifty[0], dict)
    nifty_base = float(nifty[0]["close"] if is_dict_nf else nifty[0][1]) if nifty else 1

    return {
        "client": [
            {"date": str(r["date"] if is_dict_ce else r[0]), "value": round(float(r["equity"] if is_dict_ce else r[1]) / client_base * 100, 2)}
            for r in client_eq
        ],
        "nifty": [
            {"date": str(r["date"] if is_dict_nf else r[0]), "value": round(float(r["close"] if is_dict_nf else r[1]) / nifty_base * 100, 2)}
            for r in nifty
        ],
        "initial_capital": client_base,
        "latest_equity": float(client_eq[-1]["equity"] if is_dict_ce else client_eq[-1][1]) if client_eq else 0,
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
    cur.execute(
        """
        SELECT date, equity, cash, open_positions
        FROM client_equity
        WHERE client_id = %s
        ORDER BY date DESC LIMIT 2
        """,
        (client_id,),
    )
    core_rows = cur.fetchall()
    is_dict_core = not core_rows or isinstance(core_rows[0], dict)

    # 2. Fetch External Data
    external_rows = []
    try:
        ensure_client_external_holdings_table(conn)
        cur.execute(
            """
            SELECT symbol, quantity, avg_cost
            FROM client_external_holdings
            WHERE client_id = %s
            """,
            (client_id,),
        )
        external_rows = cur.fetchall()
    except Exception:
        conn.rollback()

    cur.close()

    ext_market_value = 0
    ext_cost_basis = 0
    ext_count = 0

    if external_rows:
        is_dict_ext = isinstance(external_rows[0], dict)
        ext_holdings = []
        for r in external_rows:
            if is_dict_ext:
                ext_holdings.append(dict(r))
            else:
                ext_holdings.append({
                    "symbol": r[0],
                    "quantity": r[1],
                    "avg_cost": r[2]
                })

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

    today_equity = float(core_today["equity"] if is_dict_core else core_today[1]) if core_today else initial_cap
    today_cash = float(core_today["cash"] if is_dict_core else core_today[2]) if core_today else initial_cap

    # Combined Metrics
    total_wealth = today_equity + float(ext_market_value)

    # Crude approx for daily change:
    if core_yesterday:
        prev_equity = float(core_yesterday["equity"] if is_dict_core else core_yesterday[1]) + float(ext_market_value)
    else:
        prev_equity = today_equity + float(ext_market_value)

    total_invested = initial_cap + float(ext_cost_basis)
    total_return = total_wealth - total_invested
    total_pct = (total_return / total_invested * 100) if total_invested else 0.0

    return {
        "has_data": True,
        "date": str(core_today["date"] if is_dict_core else core_today[0]) if core_today else str(date.today()),
        "equity": float(round(total_wealth, 2)),
        "cash": float(round(today_cash, 2)),
        "open_positions": int(
            ((core_today["open_positions"] if is_dict_core else core_today[3]) if core_today and (core_today["open_positions"] if is_dict_core else core_today[3]) is not None else 0)
            + ext_count
        ),
        "daily_change": float(round(total_wealth - prev_equity, 2)),
        "daily_pct": float(round(((total_wealth - prev_equity) / prev_equity * 100), 2)) if prev_equity else 0.0,
        "total_return": float(round(total_return, 2)),
        "total_pct": float(round(total_pct, 2)),
        "initial_capital": float(initial_cap),
        "external_cost": float(round(ext_cost_basis, 2)),
        "total_invested": float(round(total_invested, 2)),
    }
