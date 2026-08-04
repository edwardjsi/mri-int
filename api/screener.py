from fastapi import APIRouter, Depends, Query
from typing import Dict, Any, List, Optional
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
        # Filter by quadrant early
        if quadrant and quadrant.lower() != "all" and r.status.lower() != quadrant.lower():
            continue
            
        payload = r.payload or {}
        
        # Track latest date
        if r.evaluation_date:
            if not max_date or r.evaluation_date > max_date:
                max_date = r.evaluation_date
                
        mapped_results.append({
            "symbol": r.symbol,
            "company_name": company_names.get(r.symbol, r.symbol),
            "owned": r.symbol in owned_symbols,
            "rrg": {
                "quadrant": r.status,
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
