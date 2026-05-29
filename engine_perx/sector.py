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


def get_peer_fundamental_comparison(cur, symbol: str, sector: str) -> dict[str, Any]:
    """
    MOSI Step 9: Peer fundamental comparison — Revenue CAGR, OPM, ROCE vs peers.

    Queries fundamental_financials for all stocks in the same sector,
    computes 3-year Revenue CAGR, latest OPM (EBITDA/Revenue), and ROCE (Net Profit/Equity),
    then positions the target stock as Outperforming / In-line / Underperforming.
    """
    if not sector or sector == "UNKNOWN":
        return {"verdict": "No sector mapping — peer comparison unavailable."}

    # Find peers in the same sector
    cur.execute(
        "SELECT DISTINCT symbol FROM stock_sectors WHERE industry = %s",
        (sector,),
    )
    peer_symbols = [row[0] if isinstance(row, tuple) else row["symbol"] for row in cur.fetchall()]
    if symbol not in peer_symbols:
        peer_symbols.append(symbol)

    if len(peer_symbols) < 2:
        return {"verdict": f"Only {symbol} found in sector '{sector}' — no peers to compare."}

    # Fetch latest fundamental data for all peers
    peers_data: list[dict] = []
    for psym in peer_symbols:
        cur.execute(
            """SELECT year, revenue, ebitda, net_profit, equity
               FROM fundamental_financials
               WHERE symbol = %s AND revenue IS NOT NULL
               ORDER BY year DESC""",
            (psym,),
        )
        rows = cur.fetchall()
        if not rows:
            continue

        parsed = []
        for r in rows:
            if isinstance(r, tuple):
                parsed.append({
                    "year": r[0], "revenue": safe_float(r[1]),
                    "ebitda": safe_float(r[2]), "net_profit": safe_float(r[3]),
                    "equity": safe_float(r[4]),
                })
            else:
                parsed.append({
                    "year": r["year"], "revenue": safe_float(r.get("revenue")),
                    "ebitda": safe_float(r.get("ebitda")), "net_profit": safe_float(r.get("net_profit")),
                    "equity": safe_float(r.get("equity")),
                })

        if not parsed:
            continue

        latest = parsed[0]

        # Revenue CAGR: compare latest year revenue vs 3 years ago
        rev_cagr = None
        if len(parsed) >= 4:
            oldest_rev = parsed[min(3, len(parsed) - 1)]["revenue"]
            if oldest_rev and oldest_rev > 0:
                years = min(3, len(parsed) - 1)
                rev_cagr = round(((latest["revenue"] / oldest_rev) ** (1 / years) - 1) * 100, 1)
        elif len(parsed) >= 2:
            oldest_rev = parsed[-1]["revenue"]
            if oldest_rev and oldest_rev > 0:
                years = len(parsed) - 1
                rev_cagr = round(((latest["revenue"] / oldest_rev) ** (1 / years) - 1) * 100, 1)

        # OPM = EBITDA / Revenue
        opm = round((latest["ebitda"] / latest["revenue"]) * 100, 1) if latest["revenue"] and latest["revenue"] > 0 else None

        # ROCE proxy = Net Profit / Equity
        roce = round((latest["net_profit"] / latest["equity"]) * 100, 1) if latest["equity"] and latest["equity"] > 0 else None

        peers_data.append({
            "symbol": psym,
            "revenue_cagr": rev_cagr,
            "opm": opm,
            "roce": roce,
            "latest_year": latest["year"],
        })

    if not peers_data:
        return {"verdict": "No fundamental data available for peers in this sector."}

    # Position the target stock
    target = next((p for p in peers_data if p["symbol"] == symbol), None)
    if not target:
        return {"verdict": f"{symbol} has no fundamental data — cannot compare.", "peers": peers_data}

    comparisons = {}
    for metric, key in [("Revenue CAGR", "revenue_cagr"), ("OPM", "opm"), ("ROCE", "roce")]:
        values = [(p[key], p["symbol"]) for p in peers_data if p[key] is not None]
        if not values or target[key] is None:
            continue
        values.sort(key=lambda x: x[0], reverse=True)
        median_idx = len(values) // 2
        median_val = values[median_idx][0]

        if target[key] >= median_val * 1.15:
            pos = "Outperforming"
        elif target[key] <= median_val * 0.85:
            pos = "Underperforming"
        else:
            pos = "In-line"

        comparisons[metric] = {
            "target": target[key],
            "sector_median": round(median_val, 1),
            "position": pos,
        }

    return {
        "verdict": f"Compared {symbol} against {len(peers_data)} sector peers.",
        "comparisons": comparisons,
        "peers": peers_data,
    }
