#!/usr/bin/env python3
"""CAS Top-20 Manual Review Report (V1.1d release candidate Gate 4).

Per Decision 102 expert feedback: "Literally print rank, symbol, CAS,
reason and ask 'Would I actually want to allocate capital to these?'"

If the top 20 looks wrong, something is wrong — even if every unit test
passes. This is the highest-value manual check.

Outputs:
  - Human-readable table to stdout (default)
  - Markdown to --md <path> for archival in docs/
  - Exit code 0 always (this is informational; eyeball test is manual)

Usage:
    venv/bin/python tools/top20_report.py
    venv/bin/python tools/top20_report.py --as-of 2026-07-07
    venv/bin/python tools/top20_report.py --top 30
    venv/bin/python tools/top20_report.py --md docs/CAS_TOP20_V11D.md
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from engine_core.db import get_connection
from engine_core.capital_allocation import (
    load_config, normalize_row, check_eligibility, compute_market_structure,
    compute_market_score_breakdown, compute_portfolio_allocation_score,
    compute_confidence_stars, render_why_checklist,
)
from engine_core.cas_recommendations import _latest_row_per_symbol, _enrich_row_with_extras


def _build_topn(as_of: date, config: dict, n: int) -> list[dict]:
    """Compute CAS for every symbol, return top N sorted by CAS desc."""
    rows = _latest_row_per_symbol(as_of)
    candidates = []

    for raw_row in rows:
        row = normalize_row(_enrich_row_with_extras(raw_row, config))
        regime = row.get("regime", "BULLISH")

        elig_ok, elig_failed = check_eligibility(row, regime, config)
        if not elig_ok:
            continue
        struct_ok, struct_failed = compute_market_structure(row, config)
        if not struct_ok:
            continue

        sub_scores = {
            "regime": row.get("regime_score", 60),
            "weekly": row.get("weekly_trend_score") or 50,
            "breakout": row.get("breakout_score", 40),
            "overhead_supply": row.get("overhead_supply_score") or 50,
            "rr": 50,
            "rs": row.get("rs_90d", 0) and max(0, min(100, row.get("rs_90d", 0) * 1000)) or 50,
            "volume": row.get("volume_score", 50),
            "sector": 50,
        }
        market_score, _ = compute_market_score_breakdown(sub_scores, config)
        # NOTE: distribution tool runs with NO portfolio state (no winner/concentration).
        # Persisted recommendations add winner_profit_pct and concentration_weight_pct,
        # so live CAS can be higher than what's shown here. This is intentional —
        # the eyeball test should be against the pure scoring signal.
        cas = compute_portfolio_allocation_score(
            market_score, 0.0, 0.0, config,
        )
        stars = compute_confidence_stars(row, sub_scores, {}, config)
        why = render_why_checklist(row, config)

        candidates.append({
            "symbol": row.get("symbol", "?"),
            "cas": float(cas),
            "market_score": float(market_score),
            "stars": int(stars),
            "why": why,
        })

    candidates.sort(key=lambda r: r["cas"], reverse=True)
    return candidates[:n]


def _print_table(rows: list[dict]) -> None:
    print(f"Top {len(rows)} recommendations by CAS")
    print("=" * 100)
    print(f"{'#':>3}  {'Symbol':<14}  {'CAS':>6}  {'MS':>6}  {'Stars':>6}  Reason")
    print("-" * 100)
    for i, r in enumerate(rows, 1):
        reason = " | ".join(r["why"][:3]) if r["why"] else "(no factors)"
        print(f"{i:>3}  {r['symbol']:<14}  {r['cas']:>6.2f}  {r['market_score']:>6.2f}  "
              f"{'★' * r['stars']:<6}  {reason}")
    print()
    print("Eyeball test: 'Would I actually want to allocate capital to these?'")


def _print_markdown(rows: list[dict], as_of: date, path: Path) -> None:
    lines = []
    lines.append(f"# CAS Top-20 — {as_of}")
    lines.append("")
    lines.append("Per Decision 102: manual review gate before V1.1 merge.")
    lines.append("Eyeball test: *Would I actually want to allocate capital to these?*")
    lines.append("")
    lines.append("| # | Symbol | CAS | Market Score | Stars | Top Reasons |")
    lines.append("|---|--------|-----|--------------|-------|-------------|")
    for i, r in enumerate(rows, 1):
        reason = "<br>".join(r["why"][:3]) if r["why"] else "—"
        stars = "★" * r["stars"] + "☆" * (5 - r["stars"])
        lines.append(f"| {i} | {r['symbol']} | {r['cas']:.2f} | {r['market_score']:.2f} | {stars} | {reason} |")
    lines.append("")
    lines.append("## Reviewer notes")
    lines.append("")
    lines.append("(Add your eyeball test observations here.)")
    lines.append("")
    path.write_text("\n".join(lines))
    print(f"Markdown report written to {path}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--as-of", type=date.fromisoformat, default=None)
    p.add_argument("--top", type=int, default=20)
    p.add_argument("--config", default="config/capital_allocation.yaml")
    p.add_argument("--md", type=Path, default=None,
                   help="also write a markdown report to this path")
    args = p.parse_args()

    config = load_config(args.config)
    as_of = args.as_of
    if as_of is None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT MAX(date) AS d FROM daily_prices")
                r = cur.fetchone()
                as_of = r["d"]

    top = _build_topn(as_of, config, args.top)
    if not top:
        print("No eligible stocks found. Cannot produce top-N report.")
        sys.exit(1)

    _print_table(top)
    if args.md:
        _print_markdown(top, as_of, args.md)


if __name__ == "__main__":
    main()
