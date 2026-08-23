from fastapi import APIRouter, Depends, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from engine_core.model_results_repository import ModelResultRepository
from engine_core.db import get_connection
from api.auth import get_current_client

router = APIRouter(prefix="/api/v1/screener", tags=["Screener"])

@router.get("/rrg")
def get_rrg_screener(
    sort: str = Query("rs_ratio"),
    order: str = Query("desc"),
    quadrant: Optional[str] = Query(None),
    client: dict = Depends(get_current_client)
):
    model_repo = ModelResultRepository()
    results = model_repo.latest_for_model_all_symbols("RRG")
    
    company_names = {}
    owned_symbols = set()
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Fetch company names
            cur.execute("SELECT symbol, company_name FROM prde_companies")
            for row in cur.fetchall():
                company_names[row['symbol']] = row['company_name']
                
            # Fetch owned symbols for the client
            cur.execute("SELECT symbol FROM client_portfolio WHERE client_id = %s AND is_open = true", (str(client["id"]),))
            for row in cur.fetchall():
                owned_symbols.add(row['symbol'])
                
            cur.execute("SELECT symbol FROM client_external_holdings WHERE client_id = %s", (str(client["id"]),))
            for row in cur.fetchall():
                owned_symbols.add(row['symbol'])
    except Exception as e:
        print(f"Error fetching RRG metadata: {e}")
    finally:
        if conn:
            conn.close()

    mapped_results = []
    max_date = None
    
    for r in results:
        payload = r.payload or {}
        item_quadrant = payload.get("quadrant", "UNKNOWN")

        # Filter by quadrant early
        if quadrant and quadrant.lower() != "all" and item_quadrant.lower() != quadrant.lower():
            continue
        
        # Track latest date
        if r.evaluation_date:
            if not max_date or r.evaluation_date > max_date:
                max_date = r.evaluation_date
                
        mapped_results.append({
            "symbol": r.symbol,
            "company_name": company_names.get(r.symbol, r.symbol),
            "owned": r.symbol in owned_symbols,
            "rrg": {
                "quadrant": item_quadrant,
                "heading": payload.get("heading"),
                "rs_ratio": payload.get("rs_ratio"),
                "rs_momentum": payload.get("rs_momentum"),
            }
        })
        
    # Apply sorting
    def sort_key(item):
        val = item["rrg"].get(sort)
        # Fallback to symbol for top level fields or if None
        if val is None:
            val = item.get(sort)
        if val is None:
            return float('-inf') if order == 'desc' else float('inf')
        return float(val) if isinstance(val, (int, float)) else str(val)

    mapped_results.sort(key=sort_key, reverse=(order == 'desc'))

    return {
        "last_updated": max_date.isoformat() if max_date else None,
        "total_count": len(mapped_results),
        "results": mapped_results
    }


@router.get("/darvas")
def get_darvas_screener(client: dict = Depends(get_current_client)):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Deterministic scan for Phase 1: Nifty 500, Mcap > 800, Close > 50, High = 252d High
            query = """
            WITH latest_prices AS (
                SELECT DISTINCT ON (symbol)
                    symbol, date, close, high, rolling_high_52w
                FROM daily_prices
                ORDER BY symbol, date DESC
            ),
            latest_mcap AS (
                SELECT DISTINCT ON (symbol)
                    symbol, date, market_cap_cr
                FROM market_cap_history
                ORDER BY symbol, date DESC
            )
            SELECT 
                lp.symbol, 
                COALESCE(c.name, lp.symbol) as company_name, 
                lp.close, 
                lp.high,
                lp.rolling_high_52w,
                lm.market_cap_cr,
                lp.date AS price_date,
                lm.date AS mcap_date
            FROM latest_prices lp
            JOIN nifty500_universe n5 ON lp.symbol = n5.symbol AND n5.constituent_to IS NULL
            LEFT JOIN latest_mcap lm ON lp.symbol = lm.symbol
            LEFT JOIN prde_companies c ON lp.symbol = c.ticker
            WHERE lm.market_cap_cr > 800
              AND lp.close > 50
              AND lp.high >= lp.rolling_high_52w
            """
            cur.execute(query)
            rows = cur.fetchall()
            
            results = []
            for row in rows:
                results.append({
                    "symbol": row['symbol'],
                    "company_name": row['company_name'],
                    "close": float(row['close']) if row['close'] is not None else None,
                    "market_cap_cr": float(row['market_cap_cr']) if row['market_cap_cr'] is not None else None,
                    "price_date": str(row['price_date']),
                    "mcap_date": str(row['mcap_date']),
                    "explanation": [
                        f"✓ Market Cap > ₹800 Cr ({float(row['market_cap_cr']):.0f} Cr)",
                        f"✓ Daily Close > ₹50 (₹{float(row['close']):.2f})",
                        f"✓ Current High = 252-day High (₹{float(row['high']):.2f})"
                    ]
                })
                
            return {
                "scan_name": "Darvas Screener - Phase 1",
                "total_count": len(results),
                "results": results
            }
    except Exception as e:
        print(f"Error running Darvas scan: {e}")
        return {"error": str(e), "results": []}
    finally:
        if conn:
            conn.close()

class SaveScanRequest(BaseModel):
    name: str
    scan_type: str = "DARVAS_52W_HIGH_V1"

@router.post("/save_scan")
def save_scan(req: SaveScanRequest, client: dict = Depends(get_current_client)):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO saved_scans (user_id, name, scan_type)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (client["id"], req.name, req.scan_type))
            scan_id = cur.fetchone()['id']
            conn.commit()
            return {"status": "success", "scan_id": scan_id}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()

@router.get("/chart/{symbol}")
def get_chart(symbol: str):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT date, close, high, low, open 
                FROM daily_prices 
                WHERE symbol = %s 
                ORDER BY date ASC 
                LIMIT 252
            """, (symbol,))
            rows = cur.fetchall()
            results = []
            for row in rows:
                results.append({
                    "date": str(row['date']),
                    "close": float(row['close']),
                    "high": float(row['high']),
                    "low": float(row['low']),
                    "open": float(row['open'])
                })
            return {"symbol": symbol, "data": results}
    except Exception as e:
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()
