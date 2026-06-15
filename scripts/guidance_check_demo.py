#!/usr/bin/env python3
"""
GuidanceCheck Demo — Management Promise Tracker

One job: show what management promised, what actually happened,
and how reliable they are over time.

Usage:
    python3 scripts/guidance_check_demo.py                  # run on 10 quality stocks
    python3 scripts/guidance_check_demo.py --symbols TCS RELIANCE HDFCBANK INFY
    python3 scripts/guidance_check_demo.py --top-credible 10
    python3 scripts/guidance_check_demo.py --worst-offenders 10
    python3 scripts/guidance_check_demo.py --watchlist      # use user's watchlist from DB

Output: structured markdown table + conviction meter per company.
"""

import argparse
import sys
from engine_core.db import get_connection, fetch_df
from engine_guidance.credibility_scorer import CredibilityScorer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _r(row, i):
    """Safe row access — works with RealDictCursor (dict-like) or tuple."""
    if isinstance(row, dict):
        return list(row.values())[i]
    return row[i]


def _ru(row, key):
    """Safe dict/tuple key access."""
    if isinstance(row, dict):
        return row.get(key)
    return row[key] if isinstance(row, (list, tuple)) else None


def _fetch_promises(symbol: str) -> list:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT g.id, g.guidance_type, g.guidance_text,
                      g.target_value, g.target_unit, g.target_date,
                      v.status, v.actual_value, v.variance_pct,
                      v.checked_fiscal_year, v.checked_fiscal_quarter
               FROM management_guidance g
               LEFT JOIN guidance_verification v ON g.id = v.guidance_id
               WHERE g.symbol = %s
               ORDER BY g.id""",
            (symbol.upper(),),
        )
        rows = cur.fetchall()
        result = []
        for row in rows:
            result.append({
                "id": _r(row, 0),
                "guidance_type": _r(row, 1),
                "guidance_text": _r(row, 2),
                "target_value": _r(row, 3),
                "target_unit": _r(row, 4),
                "target_date": _r(row, 5),
                "status": _r(row, 6),
                "actual_value": _r(row, 7),
                "variance_pct": _r(row, 8),
                "checked_fiscal_year": _r(row, 9),
                "checked_fiscal_quarter": _r(row, 10),
            })
        return result
    finally:
        conn.close()


def _fetch_credibility(symbol: str) -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM management_credibility_scores WHERE symbol = %s",
            (symbol.upper(),),
        )
        row = cur.fetchone()
        if not row:
            return {}
        return {
            "symbol": _r(row, 0),
            "total_promises": _r(row, 1),
            "achieved_count": _r(row, 2),
            "missed_count": _r(row, 3),
            "accuracy_pct": _r(row, 4),
            "avg_variance_pct": _r(row, 5),
            "trend": _r(row, 6),
        }
    finally:
        conn.close()


def _fetch_watchlist_symbols(limit: int = 20) -> list:
    """Fetch top watchlist symbols by MRI score."""
    df = fetch_df(
        """SELECT DISTINCT w.symbol
           FROM client_watchlist w
           JOIN LATERAL (
               SELECT total_score FROM stock_scores s
               WHERE s.symbol = w.symbol
               ORDER BY s.total_score DESC NULLS LAST
               LIMIT 1
           ) sc ON true
           ORDER BY sc.total_score DESC
           LIMIT %s""",
        params=(limit,),
    )
    if df.empty:
        return []
    return df["symbol"].str.upper().tolist()


def _conviction_label(accuracy_pct: float, trend: str, total: int) -> str:
    """Map accuracy + trend to conviction action."""
    if total < 3:
        return "🔵 Watching"
    if accuracy_pct >= 75 and trend in ("IMPROVING", "STABLE"):
        return "🟢 Add Zone"
    if accuracy_pct >= 60:
        return "🟡 Hold Zone"
    if accuracy_pct >= 40:
        return "🟠 Reduce Zone"
    return "🔴 Thesis Broken"


def _status_icon(status: str) -> str:
    return {
        "ACHIEVED": "✅",
        "MISSED": "❌",
        "PARTIAL": "⚠️",
        "PENDING": "⏳",
    }.get(status, "⚡")


def _trend_arrow(trend: str) -> str:
    return {
        "IMPROVING": "↑",
        "STABLE": "→",
        "DETERIORATING": "↓",
        "INSUFFICIENT_DATA": "?",
    }.get(trend, "?")


# ---------------------------------------------------------------------------
# Per-company report
# ---------------------------------------------------------------------------

def report_company(symbol: str) -> str:
    promises = _fetch_promises(symbol)
    cred = _fetch_credibility(symbol)

    total = cred.get("total_promises", 0)
    achieved = cred.get("achieved_count", 0)
    missed = cred.get("missed_count", 0)
    accuracy = cred.get("accuracy_pct", 0.0)
    trend = cred.get("trend", "INSUFFICIENT_DATA")
    avg_var = cred.get("avg_variance_pct")

    lines = []
    divider = "─" * 72

    # Header
    accuracy_str = f"{accuracy:.0f}%" if accuracy else "N/A"
    conviction = _conviction_label(accuracy, trend, total)
    trend_str = f"{_trend_arrow(trend)} {trend}"

    lines.append(f"\n{'=' * 72}")
    lines.append(f"  {symbol.upper()}  |  Accuracy: {accuracy_str}  |  Trend: {trend_str}  |  {conviction}")
    lines.append(f"{'=' * 72}")

    if not promises:
        lines.append(f"\n  No promises tracked yet for {symbol}.")
        lines.append("  Run guidance extraction pipeline first: `python3 -m engine_guidance.guidance_primer`")
        return "\n".join(lines)

    # Credibility summary bar
    if total > 0:
        bar_len = 30
        achieved_pct = accuracy / 100
        filled = int(bar_len * achieved_pct)
        bar = "█" * filled + "░" * (bar_len - filled)
        lines.append(f"\n  [{bar}] {accuracy:.1f}% accuracy ({achieved}✅ / {missed}❌ / {total} total)")
        if avg_var:
            lines.append(f"  Avg miss when broken: {avg_var:.1f}%")
    else:
        lines.append(f"\n  No verified promises yet — {len(promises)} unverified.")

    # Promise table
    lines.append(f"\n  {'Promise':<50} {'Target':>10}  Status")
    lines.append(f"  {'-'*50}  {'-'*10}  {'-'*10}")

    for p in promises:
        text = (p["guidance_text"] or "")[:50]
        target = ""
        if p["target_value"] is not None:
            unit = p["target_unit"] or ""
            target = f"{p['target_value']} {unit}".strip()
        status = p["status"] or "PENDING"

        if status == "PENDING" and p["target_date"]:
            target = f"{target} (by {p['target_date']})"

        icon = _status_icon(status)
        if status == "ACHIEVED" and p["actual_value"] is not None:
            target = f"{target} → {p['actual_value']}"
        elif status == "MISSED" and p["actual_value"] is not None:
            target = f"{target} → {p['actual_value']} ({p['variance_pct']:.0f}%)"

        lines.append(f"  {text:<50} {target:>10}  {icon} {status}")

    lines.append(f"\n  {divider}\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="GuidanceCheck Demo — Management Promise Tracker")
    parser.add_argument("--symbols", "-s", nargs="+", help="Specific symbols to analyze")
    parser.add_argument("--top-credible", type=int, metavar="N", help="Show top N most credible companies")
    parser.add_argument("--worst-offenders", type=int, metavar="N", help="Show bottom N (least credible)")
    parser.add_argument("--watchlist", action="store_true", help="Use symbols from user's watchlist")
    parser.add_argument("--limit", type=int, default=20, help="Max symbols when using --watchlist (default: 20)")
    args = parser.parse_args()

    # Default: use watchlist or fall back to hardcoded quality set
    if args.symbols:
        symbols = [s.upper().strip().replace(".NS", "").replace(".BO", "") for s in args.symbols]
    elif args.top_credible:
        scorer = CredibilityScorer()
        rows = scorer.get_leaderboard(args.top_credible, worst=False)
        symbols = [_r(r, 0) for r in rows]
    elif args.worst_offenders:
        scorer = CredibilityScorer()
        rows = scorer.get_leaderboard(args.worst_offenders, worst=True)
        symbols = [_r(r, 0) for r in rows]
    elif args.watchlist:
        symbols = _fetch_watchlist_symbols(args.limit)
    else:
        # Hardcoded quality starter set — high-coverage, well-tracked names
        symbols = [
            "TCS", "INFY", "RELIANCE", "HDFCBANK", "HUL",
            "ITC", "SBIN", "BHARTIARTL", "LT", "KOTAKBANK",
        ]

    if not symbols:
        print("No symbols found. Use --symbols, --watchlist, or add stocks to watchlist first.")
        sys.exit(1)

    print(f"\n{'#' * 72}")
    print("  GuidanceCheck Demo — Management Promise Tracker")
    print(f"  Companies: {', '.join(symbols)}")
    print(f"{'#' * 72}")

    for symbol in symbols:
        if symbol in (None, ""):
            continue
        try:
            output = report_company(symbol)
            print(output)
        except Exception as e:
            print(f"\n  ERROR processing {symbol}: {e}\n")

    # Footer
    print(f"\n{'#' * 72}")
    print("  Legend:")
    print("    ✅ ACHIEVED  ❌ MISSED  ⚠️ PARTIAL  ⏳ PENDING")
    print("    Add Zone     | Hold Zone  | Reduce Zone  | Thesis Broken")
    print("    ↑ IMPROVING  → STABLE    ↓ DETERIORATING")
    print(f"{'#' * 72}\n")


if __name__ == "__main__":
    main()