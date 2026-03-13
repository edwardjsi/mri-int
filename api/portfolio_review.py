"""
Portfolio Review API — endpoints for portfolio risk analysis.

POST /api/portfolio-review/analyze  — full portfolio risk analysis
GET  /api/portfolio-review/quick/{symbol}  — single stock MRI check
POST /api/portfolio-review/upload-csv  — import broker holdings for analysis
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional
import pandas as pd
import io
import uuid

from psycopg2.extras import RealDictCursor
from api.deps import get_db, get_current_client
from api.schema import ensure_client_external_holdings_table
from src.portfolio_review_engine import analyze_portfolio, analyze_single_stock
from src.on_demand_ingest import ingest_missing_symbols_sync, grade_symbols_sync
from src.yahoo_quotes import fetch_quotes

router = APIRouter(prefix="/api/portfolio-review", tags=["portfolio-review"])

def _pricing_note(quotes_error: str | None) -> str:
    if quotes_error:
        return (
            "Prices shown are the latest end-of-day close from our database (typically yesterday). "
            f"Live Yahoo quotes were unavailable: {quotes_error}"
        )
    return "Prices shown use live Yahoo quotes when available; otherwise we show the latest end-of-day close (typically yesterday)."


def _attach_quotes(result: dict, quotes_by_symbol: dict, quotes_error: str | None) -> dict:
    # Attach a top-level note and per-holding quote fields for the UI.
    result["pricing_note"] = _pricing_note(quotes_error)
    result["pricing_live_available"] = bool(quotes_by_symbol) and not bool(quotes_error)

    holdings = result.get("holdings") or []
    for h in holdings:
        sym = str(h.get("symbol", "")).upper().strip()
        q = quotes_by_symbol.get(sym)
        if q:
            h["live_price"] = q.price
            h["live_ticker"] = q.source_ticker
            h["live_fetched_at_unix"] = q.fetched_at_unix
        else:
            h["live_price"] = None
            h["live_ticker"] = None
            h["live_fetched_at_unix"] = None
    return result


def _get_external_holdings_count(conn, client_id: str) -> int:
    # Note: our DB connections are created with RealDictCursor by default (see api/deps.py),
    # so fetchone() returns dict-like rows. Avoid numeric indexing (KeyError: 0).
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        ensure_client_external_holdings_table(conn)
        cur.execute(
            "SELECT COUNT(*) AS holdings_count FROM client_external_holdings WHERE client_id = %s",
            (client_id,),
        )
        row = cur.fetchone()
        return int(row["holdings_count"]) if row and row.get("holdings_count") is not None else 0
    finally:
        cur.close()


def _get_ungraded_symbols_count(conn, client_id: str) -> int | None:
    """
    Count how many persisted external-holding symbols have no entry in stock_scores at all.
    If stock_scores doesn't exist yet, return None (unknown).
    """
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        ensure_client_external_holdings_table(conn)
        cur.execute(
            """
            SELECT COUNT(*) AS ungraded_count
            FROM client_external_holdings h
            LEFT JOIN (SELECT DISTINCT symbol FROM stock_scores) s
              ON s.symbol = h.symbol
            WHERE h.client_id = %s
              AND s.symbol IS NULL
            """,
            (client_id,),
        )
        row = cur.fetchone()
        return int(row["ungraded_count"]) if row and row.get("ungraded_count") is not None else 0
    except Exception:
        return None
    finally:
        cur.close()


@router.get("/holdings-status")
def holdings_status(
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Return storage readiness + persisted holdings count for the authenticated client."""
    client_id = str(client["id"])
    try:
        count = _get_external_holdings_count(conn, client_id)
        ungraded = _get_ungraded_symbols_count(conn, client_id)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute("SELECT current_database() AS db")
            row = cur.fetchone()
            db = row.get("db") if row else None
        finally:
            cur.close()
        return {
            "storage_ready": True,
            "client_id": client_id,
            "holdings_count": count,
            "ungraded_symbols_count": ungraded,
            "database": db,
        }
    except Exception as e:
        conn.rollback()
        return {"storage_ready": False, "client_id": client_id, "error": str(e)}


class HoldingInput(BaseModel):
    symbol: str
    quantity: float = Field(default=0.0, ge=0, description="Number of shares held")
    avg_cost: Optional[float] = Field(default=None, ge=0, description="Average purchase price")


class PortfolioSaveInput(BaseModel):
    symbol: str
    quantity: float = Field(ge=0)
    avg_cost: float = Field(ge=0)


class PortfolioInput(BaseModel):
    holdings: List[HoldingInput] = Field(min_length=1, max_length=100)


@router.post("/analyze")
def analyze(
    body: PortfolioInput,
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """
    Full portfolio risk analysis.
    Submit holdings → get per-stock MRI score breakdown + aggregate risk level.
    """
    holdings = [h.model_dump() for h in body.holdings]
    result = analyze_portfolio(holdings, conn=conn)
    quotes_by_symbol, quotes_error = fetch_quotes([h.get("symbol") for h in holdings])
    result = _attach_quotes(result, quotes_by_symbol, quotes_error)
    return result


@router.post("/upload-csv")
async def upload_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """
    Upload a CSV file (e.g., Zerodha holdings) for portfolio risk audit.

    Behavior:
    - Returns immediate analysis for all rows.
    - Persists uploaded holdings into `client_external_holdings` (Digital Twin layer)
      so they always display later with delete controls.
    - If some symbols are missing from MRI universe, kicks off async ingestion.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    try:
        digital_twin_saved = False
        digital_twin_error: str | None = None

        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))

        portfolio = []
        orig_cols = list(df.columns)
        cols = [str(c).strip().lower() for c in orig_cols]

        sym_col = None
        qty_col = None
        cost_col = None

        for i, c in enumerate(cols):
            if not sym_col and c in ('symbol', 'ticker', 'instrument'):
                sym_col = orig_cols[i]
            if not qty_col and c in ('quantity', 'qty', 'shares', 'qty.'):
                qty_col = orig_cols[i]
            if not cost_col and c in ('avg_cost', 'cost', 'price', 'buy_price', 'avg. cost'):
                cost_col = orig_cols[i]

        if not sym_col:
            raise HTTPException(status_code=400, detail="CSV must contain a 'symbol' or 'instrument' column.")

        for _, row in df.iterrows():
            if pd.isna(row[sym_col]):
                continue
            portfolio.append({
                "symbol": str(row[sym_col]).strip(),
                "quantity": float(row[qty_col]) if qty_col and pd.notna(row[qty_col]) else 0.0,
                "avg_cost": float(row[cost_col]) if cost_col and pd.notna(row[cost_col]) else 0.0,
            })

        result = analyze_portfolio(portfolio, conn=conn)
        quotes_by_symbol, quotes_error = fetch_quotes([h.get("symbol") for h in portfolio])
        result = _attach_quotes(result, quotes_by_symbol, quotes_error)

        # Automatic local persistence for authenticated users:
        # Save ALL holdings from CSV (even if score is unknown)
        holdings_to_save = [
            {
                "symbol": h["symbol"],
                "quantity": h["quantity"],
                "avg_cost": h["avg_cost"],
            }
            for h in result.get("holdings", [])
        ]

        if holdings_to_save:
            print(f"DEBUG: Auto-saving {len(holdings_to_save)} holdings for {client['email']}")
            cur = conn.cursor(cursor_factory=RealDictCursor)
            try:
                ensure_client_external_holdings_table(conn)
                for h in holdings_to_save:
                    cur.execute(
                        """
                        INSERT INTO client_external_holdings (id, client_id, symbol, quantity, avg_cost, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (client_id, symbol) DO UPDATE
                        SET quantity = EXCLUDED.quantity,
                            avg_cost = EXCLUDED.avg_cost,
                            updated_at = NOW()
                        """,
                        (str(uuid.uuid4()), str(client["id"]), str(h["symbol"]).upper().strip(), h["quantity"], h["avg_cost"]),
                    )
                conn.commit()
                digital_twin_saved = True
                result["digital_twin_row_count"] = _get_external_holdings_count(conn, str(client["id"]))
            except Exception as e:
                print(f"DEBUG: Auto-save failed during upload: {e}")
                conn.rollback()
                digital_twin_error = str(e)
            finally:
                cur.close()

        missing = result.get("missing_symbols", [])
        if missing:
            background_tasks.add_task(
                ingest_missing_symbols_sync,
                missing,
                portfolio,
                str(client["id"]),
                client["email"],
                client["name"],
            )
            result["async_processing"] = True
        else:
            result["async_processing"] = False

        result["digital_twin_saved"] = digital_twin_saved
        result["digital_twin_error"] = digital_twin_error

        return result

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")


@router.get("/holdings")
def get_holdings(
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Retrieve saved external holdings with MRI analysis."""
    client_id = str(client["id"])
    print(f"DEBUG: Fetching holdings for client_id: {client_id}")

    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        ensure_client_external_holdings_table(conn)
        cur.execute(
            """
            SELECT symbol, quantity, avg_cost
            FROM client_external_holdings
            WHERE client_id = %s
            ORDER BY symbol
            """,
            (client_id,),
        )
        rows = cur.fetchall()
    except Exception as e:
        conn.rollback()
        return {
            "regime": None,
            "risk_level": "LOW",
            "risk_score": 0,
            "holdings_count": 0,
            "holdings": [],
            "missing_symbols": [],
            "summary": f"Holdings storage is not available yet: {str(e)}",
            "storage_ready": False,
        }
    finally:
        cur.close()

    print(f"DEBUG: Found {len(rows)} rows for client_id: {client_id}")

    if not rows:
        return {
            "regime": None,
            "risk_level": "LOW",
            "risk_score": 0,
            "holdings_count": 0,
            "holdings": [],
            "missing_symbols": [],
            "summary": "No saved holdings yet.",
            "storage_ready": True,
        }

    holdings = [dict(r) for r in rows]
    quotes_by_symbol, quotes_error = fetch_quotes([h.get("symbol") for h in holdings])
    try:
        result = analyze_portfolio(holdings, conn=conn)
        result["storage_ready"] = True
        return _attach_quotes(result, quotes_by_symbol, quotes_error)
    except Exception as e:
        # If analysis fails (e.g., missing score/regime tables on a fresh DB),
        # still return the persisted holdings so the "Digital Twin" remains usable.
        conn.rollback()
        safe_holdings = []
        total_value = 0.0
        for h in holdings:
            symbol = str(h.get("symbol", "")).upper().strip()
            quantity = float(h.get("quantity", 0) or 0)
            avg_cost = float(h.get("avg_cost", 0) or 0)
            total_value += quantity * avg_cost
            safe_holdings.append(
                {
                    "symbol": symbol,
                    "quantity": quantity,
                    "avg_cost": avg_cost,
                    "current_price": None,
                    "pnl_pct": None,
                    "weight_pct": None,
                    "score": None,
                    "conditions": None,
                    "below_200ema": None,
                    "ema_50": None,
                    "ema_200": None,
                    "rs_90d": None,
                    "alignment": "UNKNOWN",
                    "risk_factor": None,
                    "risk_contribution_pct": 0.0,
                }
            )

        fallback = {
            "regime": None,
            "regime_date": None,
            "risk_level": "LOW",
            "risk_level_description": "Analysis temporarily unavailable.",
            "risk_score": 0.0,
            "risk_score_pct": "0%",
            "total_portfolio_value": float(round(total_value, 2)),
            "holdings_count": len(safe_holdings),
            "holdings": safe_holdings,
            "missing_symbols": [],
            "summary": f"Saved holdings loaded, but MRI analysis is unavailable right now: {str(e)}",
            "storage_ready": True,
            "analysis_error": str(e),
        }
        return _attach_quotes(fallback, quotes_by_symbol, quotes_error)


@router.post("/holdings/regrade")
def regrade_holdings(
    background_tasks: BackgroundTasks,
    send_email: bool = False,
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """
    Kick off a targeted regrade of the client's persisted holdings.
    Useful if the portfolio was persisted but scores/indicators were not computed yet.
    """
    client_id = str(client["id"])
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        ensure_client_external_holdings_table(conn)
        cur.execute(
            """
            SELECT symbol, quantity, avg_cost
            FROM client_external_holdings
            WHERE client_id = %s
            ORDER BY symbol
            """,
            (client_id,),
        )
        rows = cur.fetchall()
    finally:
        cur.close()

    holdings = [dict(r) for r in (rows or [])]
    symbols = [str(h.get("symbol", "")).upper().strip() for h in holdings if h.get("symbol")]
    if not symbols:
        return {"status": "noop", "message": "No saved holdings to regrade."}

    # Optionally email an updated report (best effort; requires SES configured).
    background_tasks.add_task(
        grade_symbols_sync,
        symbols,
        holdings,
        client.get("email"),
        client.get("name"),
        bool(send_email),
    )
    return {"status": "started", "symbols_count": len(symbols), "email_queued": bool(send_email)}


@router.post("/holdings/regrade-sync")
def regrade_holdings_sync(
    send_email: bool = False,
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """
    Synchronous regrade: runs indicator+score computation and returns the refreshed analysis.
    Use this when background tasks are unreliable in the hosting environment.
    """
    client_id = str(client["id"])
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        ensure_client_external_holdings_table(conn)
        cur.execute(
            """
            SELECT symbol, quantity, avg_cost
            FROM client_external_holdings
            WHERE client_id = %s
            ORDER BY symbol
            """,
            (client_id,),
        )
        rows = cur.fetchall()
    finally:
        cur.close()

    holdings = [dict(r) for r in (rows or [])]
    symbols = [str(h.get("symbol", "")).upper().strip() for h in holdings if h.get("symbol")]
    if not symbols:
        return {"status": "noop", "message": "No saved holdings to regrade.", "storage_ready": True, "holdings": []}

    # Run grading inline, then re-analyze and return.
    grade_symbols_sync(symbols, holdings, client.get("email"), client.get("name"), bool(send_email))

    quotes_by_symbol, quotes_error = fetch_quotes([h.get("symbol") for h in holdings])
    result = analyze_portfolio(holdings, conn=conn)
    result["storage_ready"] = True
    return _attach_quotes(result, quotes_by_symbol, quotes_error)


@router.post("/save-bulk")
def save_holdings_bulk(
    body: List[PortfolioSaveInput],
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Bulk save or update holdings in the persistent Digital Twin layer."""
    client_id = str(client["id"])
    print(f"DEBUG: Bulk saving {len(body)} holdings for client_id: {client_id}")

    cur = conn.cursor()
    try:
        ensure_client_external_holdings_table(conn)
        for holding in body:
            cur.execute(
                """
                INSERT INTO client_external_holdings (id, client_id, symbol, quantity, avg_cost, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (client_id, symbol) DO UPDATE
                SET quantity = EXCLUDED.quantity,
                    avg_cost = EXCLUDED.avg_cost,
                    updated_at = NOW()
                """,
                (str(uuid.uuid4()), client_id, holding.symbol.upper().strip(), holding.quantity, holding.avg_cost),
            )

        conn.commit()
        print(f"DEBUG: Successfully bulk saved {len(body)} symbols")
        persisted = _get_external_holdings_count(conn, client_id)
        return {"status": "success", "count": len(body), "persisted_holdings_count": persisted}
    except Exception as e:
        print(f"DEBUG: Bulk save error: {e}")
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()


@router.post("/save")
def save_holding(
    body: PortfolioSaveInput,
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Save or update a single holding."""
    client_id = str(client["id"])
    print(f"DEBUG: Saving holding {body.symbol} for client_id: {client_id}")

    cur = conn.cursor()
    try:
        ensure_client_external_holdings_table(conn)
        cur.execute(
            """
            INSERT INTO client_external_holdings (id, client_id, symbol, quantity, avg_cost, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            ON CONFLICT (client_id, symbol) DO UPDATE
            SET quantity = EXCLUDED.quantity,
                avg_cost = EXCLUDED.avg_cost,
                updated_at = NOW()
            """,
            (str(uuid.uuid4()), client_id, body.symbol.upper().strip(), body.quantity, body.avg_cost),
        )
        conn.commit()
        print(f"DEBUG: Successfully saved {body.symbol}")
        persisted = _get_external_holdings_count(conn, client_id)
        return {"status": "success", "message": f"Saved {body.symbol}", "persisted_holdings_count": persisted}
    except Exception as e:
        print(f"DEBUG: Error saving {body.symbol}: {e}")
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()


@router.delete("/holdings/{symbol}")
def delete_holding(
    symbol: str,
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Remove a holding from the persistent layer."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        ensure_client_external_holdings_table(conn)
        cur.execute(
            """
            DELETE FROM client_external_holdings
            WHERE client_id = %s AND symbol = %s
            """,
            (str(client["id"]), symbol.upper().strip()),
        )
        conn.commit()
        persisted = _get_external_holdings_count(conn, str(client["id"]))
        return {"status": "success", "message": f"Deleted {symbol}", "persisted_holdings_count": persisted}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()


@router.delete("/holdings")
def delete_all_holdings(
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Remove all persisted external holdings for the authenticated client."""
    client_id = str(client["id"])
    cur = conn.cursor()
    try:
        ensure_client_external_holdings_table(conn)
        cur.execute(
            "DELETE FROM client_external_holdings WHERE client_id = %s",
            (client_id,),
        )
        deleted = int(cur.rowcount or 0)
        conn.commit()
        persisted = _get_external_holdings_count(conn, client_id)
        return {"status": "success", "deleted": deleted, "persisted_holdings_count": persisted}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()


@router.post("/holdings/delete-all")
def delete_all_holdings_post(
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """
    Delete-all alternative to support environments that block/strip DELETE.
    Frontend should prefer this endpoint.
    """
    return delete_all_holdings(client=client, conn=conn)


@router.get("/quick/{symbol}")
def quick_check(
    symbol: str,
    client=Depends(get_current_client),
    conn=Depends(get_db),
):
    """Quick single-stock MRI analysis: score, regime alignment, EMA position."""
    result = analyze_single_stock(symbol, conn=conn)
    if not result.get("found", True):
        raise HTTPException(status_code=404, detail=result.get("message", "Symbol not found"))
    return result
