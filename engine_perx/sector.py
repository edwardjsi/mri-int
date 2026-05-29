from __future__ import annotations
from typing import Any

def safe_float(v):
    if v is None:
        return 0.0
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0

import pandas as pd

def get_sector_context(cur, symbol: str, sector: str) -> dict[str, Any]:
    """Calculate real industry peer ranking and relative strength."""
    if not sector or sector == "UNKNOWN":
        return {"status": "limited", "message": "No sector mapping found for peer comparison."}

    # Fetch peers in the same industry by latest MRI score
    cur.execute(
        """
        SELECT ss.symbol, ss.total_score, sc.company_name
        FROM stock_scores ss
        JOIN stock_sectors sc ON sc.symbol = ss.symbol
        WHERE sc.industry = %s
          AND ss.date = (SELECT MAX(date) FROM stock_scores)
        ORDER BY ss.total_score DESC
        LIMIT 10
        """,
        (sector,)
    )
    peers = cur.fetchall()
    
    # Calculate rank
    peer_list = [dict(p) if isinstance(p, dict) else {"symbol": p[0], "total_score": p[1], "name": p[2]} for p in peers]
    rank = next((i + 1 for i, p in enumerate(peer_list) if p['symbol'] == symbol), None)
    
    # Determine Industry Breadth (Avg score of top 10)
    avg_sector_score = sum(p.get('total_score', 0) for p in peer_list) / len(peer_list) if peer_list else 0
    breadth = "Accumulation" if avg_sector_score >= 70 else "Neutral" if avg_sector_score >= 50 else "Distribution"

    return {
        "status": "active",
        "sector_name": sector,
        "industry_rank": f"{rank}/{len(peer_list)}" if rank else "N/A",
        "industry_breadth": breadth,
        "avg_sector_mri": round(avg_sector_score, 1),
        "top_peers": [p['symbol'] for p in peer_list[:3] if p['symbol'] != symbol]
    }
