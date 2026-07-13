#!/usr/bin/env python3
"""CAS Distribution Sanity Check (V1.1d release candidate Gate 3).

Per Decision 102 expert feedback: golden cases alone aren't enough.
Before merging V1.1, verify the FULL distribution of CAS outputs across
the universe. Look for obvious anomalies that golden cases won't catch:

  - 90% of stocks scoring above 80 (distribution collapsed at the top)
  - Everyone getting 5 stars (confidence saturation)
  - overhead_supply_score collapsing toward zero (bug in scoring)
  - weekly_trend_score clustered at 0 or 100 (broken component)
  - eligible universe too narrow (<5%) or too wide (>80%)

Outputs:
  - JSON to --json <path> for CI / archival
  - Human-readable report to stdout (default)
  - Exit code 0 on PASS, 1 on FAIL (use --no-strict to never fail)

Usage:
    venv/bin/python tools/distribution_sanity_check.py
    venv/bin/python tools/distribution_sanity_check.py --as-of 2026-07-07
    venv/bin/python tools/distribution_sanity_check.py --json out.json
    venv/bin/python tools/distribution_sanity_check.py --no-strict  # never exit 1
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from datetime import date
from pathlib import Path

# Ensure repo root is on sys.path so we can import engine_core
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import logging
logging.basicConfig(level=logging.ERROR)  # suppress noisy eligibility WARNINGs
logging.getLogger("engine_core.capital_allocation").setLevel(logging.ERROR)

from engine_core.db import get_connection
from engine_core.capital_allocation import load_config, normalize_row, check_eligibility, compute_market_structure
from engine_core.cas_recommendations import _latest_row_per_symbol, _enrich_row_with_extras
from engine_core.capital_allocation import (
    compute_market_score_breakdown,
    compute_portfolio_allocation_score,
    compute_confidence_stars,
)


# ----------------------------------------------------------------------------
# Anomaly thresholds (tunable; align with expert "obvious red flags")
# ----------------------------------------------------------------------------

ANOMALY_RULES = {
    # If >80% of stocks have CAS >= 80, the engine is too generous
    "cas_pct_above_80_max": 0.80,
    # If <2% of stocks have CAS >= 80, the engine is too strict
    "cas_pct_above_80_min": 0.02,
    # If >40% get 5 stars, confidence is saturated
    "five_star_pct_max": 0.40,
    # If >60% get 1 star, the model is too pessimistic (or data too thin)
    "one_star_pct_max": 0.60,
    # If eligible universe <5%, the engine is too restrictive
    "eligible_pct_min": 0.05,
    # If eligible universe >80%, the gates are too loose
    "eligible_pct_max": 0.80,
    # If overhead_supply_score collapses (95th percentile <5), something is wrong
    "overhead_p95_min": 5.0,
    # If weekly_trend_score median is below 20, scoring is biased pessimistic
    "weekly_median_min": 20.0,
}


def _percentile(values: list[float], pct: float) -> float:
    """Compute the pct-th percentile (0-100) of values. Returns 0 if empty."""
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return s[f]
    return s[f] + (s[c] - s[f]) * (k - f)


def analyze(as_of: date, config: dict) -> dict:
    """Run the engine on every symbol for the given date and collect distribution.

    Returns:
        {
          "as_of": "YYYY-MM-DD",
          "n_symbols": int,
          "n_eligible": int,
          "eligible_pct": float,
          "cas": {"mean", "median", "p5", "p25", "p75", "p95", "pct_above_60", "pct_above_80"},
          "weekly_trend_score": {"mean", "median", "p5", "p95"},
          "overhead_supply_score": {"mean", "median", "p5", "p95"},
          "confidence_stars": {"1": count, "2": count, ..., "5": count, "five_star_pct"},
          "anomalies": [{"rule": str, "value": float, "threshold": float, "severity": "warn"|"fail"}],
          "passed": bool,
        }
    """
    rows = _latest_row_per_symbol(as_of)
    if not rows:
        return {"as_of": as_of.isoformat(), "n_symbols": 0, "error": "no rows"}

    # Per-symbol computed values
    cas_values: list[float] = []
    weekly_values: list[float] = []
    overhead_values: list[float] = []
    stars_distribution: Counter = Counter()
    n_eligible = 0

    for raw_row in rows:
        row = normalize_row(_enrich_row_with_extras(raw_row, config))
        regime = row.get("regime", "BULLISH")

        # Weekly trend is always computable (it's a sub-score)
        weekly_trend = row.get("weekly_trend_score")
        if weekly_trend is not None:
            weekly_values.append(float(weekly_trend))
        overhead = row.get("overhead_supply_score")
        if overhead is not None:
            overhead_values.append(float(overhead))

        elig_ok, _ = check_eligibility(row, regime, config)
        if not elig_ok:
            # Even ineligible rows get a sub-score snapshot for diagnostic.
            # But CAS is only computed for eligible+structure-passed.
            continue

        struct_ok, _ = compute_market_structure(row, config)
        if not struct_ok:
            continue

        n_eligible += 1

        # Compute full CAS
        sub_scores = {
            "regime": row.get("regime_score", 60),
            "weekly": row.get("weekly_trend_score") or 50,
            "breakout": row.get("breakout_score", 40),
            "overhead_supply": row.get("overhead_supply_score") or 50,
            "rr": 50,  # not used
            "rs": row.get("rs_90d", 0) and max(0, min(100, row.get("rs_90d", 0) * 1000)) or 50,
            "volume": row.get("volume_score", 50),
            "sector": 50,  # proxy
        }
        market_score, _ = compute_market_score_breakdown(sub_scores, config)
        cas = compute_portfolio_allocation_score(
            market_score, row.get("winner_profit_pct") or 0,
            row.get("concentration_weight_pct") or 0, config,
        )
        stars = compute_confidence_stars(row, sub_scores, {}, config)
        cas_values.append(float(cas))
        stars_distribution[int(stars)] += 1

    n_symbols = len(rows)
    eligible_pct = n_eligible / n_symbols if n_symbols else 0.0

    cas_stats = {
        "n": len(cas_values),
        "mean": round(statistics.mean(cas_values), 2) if cas_values else 0,
        "median": round(_percentile(cas_values, 50), 2),
        "p5": round(_percentile(cas_values, 5), 2),
        "p25": round(_percentile(cas_values, 25), 2),
        "p75": round(_percentile(cas_values, 75), 2),
        "p95": round(_percentile(cas_values, 95), 2),
        "pct_above_60": round(sum(1 for c in cas_values if c >= 60) / max(len(cas_values), 1), 3),
        "pct_above_80": round(sum(1 for c in cas_values if c >= 80) / max(len(cas_values), 1), 3),
    }

    weekly_stats = {
        "n": len(weekly_values),
        "mean": round(statistics.mean(weekly_values), 2) if weekly_values else 0,
        "median": round(_percentile(weekly_values, 50), 2),
        "p5": round(_percentile(weekly_values, 5), 2),
        "p95": round(_percentile(weekly_values, 95), 2),
    }

    overhead_stats = {
        "n": len(overhead_values),
        "mean": round(statistics.mean(overhead_values), 2) if overhead_values else 0,
        "median": round(_percentile(overhead_values, 50), 2),
        "p5": round(_percentile(overhead_values, 5), 2),
        "p95": round(_percentile(overhead_values, 95), 2),
    }

    five_star_pct = stars_distribution[5] / max(sum(stars_distribution.values()), 1)
    one_star_pct = stars_distribution[1] / max(sum(stars_distribution.values()), 1)

    stars_dict = {str(k): v for k, v in sorted(stars_distribution.items())}
    # Pad missing stars
    for k in ["1", "2", "3", "4", "5"]:
        stars_dict.setdefault(k, 0)
    stars_dict["five_star_pct"] = round(five_star_pct, 3)
    stars_dict["one_star_pct"] = round(one_star_pct, 3)

    # Anomaly detection
    anomalies = []
    if cas_stats["pct_above_80"] > ANOMALY_RULES["cas_pct_above_80_max"]:
        anomalies.append({
            "rule": "cas_pct_above_80_max",
            "value": cas_stats["pct_above_80"],
            "threshold": ANOMALY_RULES["cas_pct_above_80_max"],
            "severity": "fail",
            "message": f"{cas_stats['pct_above_80']*100:.1f}% of stocks have CAS >= 80 (max allowed: {ANOMALY_RULES['cas_pct_above_80_max']*100:.0f}%). Engine too generous.",
        })
    if cas_stats["pct_above_80"] < ANOMALY_RULES["cas_pct_above_80_min"]:
        anomalies.append({
            "rule": "cas_pct_above_80_min",
            "value": cas_stats["pct_above_80"],
            "threshold": ANOMALY_RULES["cas_pct_above_80_min"],
            "severity": "warn",
            "message": f"Only {cas_stats['pct_above_80']*100:.1f}% of stocks have CAS >= 80 (min expected: {ANOMALY_RULES['cas_pct_above_80_min']*100:.0f}%). Engine very strict.",
        })
    if five_star_pct > ANOMALY_RULES["five_star_pct_max"]:
        anomalies.append({
            "rule": "five_star_pct_max",
            "value": five_star_pct,
            "threshold": ANOMALY_RULES["five_star_pct_max"],
            "severity": "fail",
            "message": f"{five_star_pct*100:.1f}% of eligible stocks get 5 stars (max: {ANOMALY_RULES['five_star_pct_max']*100:.0f}%). Confidence saturation.",
        })
    if one_star_pct > ANOMALY_RULES["one_star_pct_max"]:
        anomalies.append({
            "rule": "one_star_pct_max",
            "value": one_star_pct,
            "threshold": ANOMALY_RULES["one_star_pct_max"],
            "severity": "warn",
            "message": f"{one_star_pct*100:.1f}% of eligible stocks get 1 star (max: {ANOMALY_RULES['one_star_pct_max']*100:.0f}%). Model too pessimistic.",
        })
    if eligible_pct > ANOMALY_RULES["eligible_pct_max"]:
        anomalies.append({
            "rule": "eligible_pct_max",
            "value": eligible_pct,
            "threshold": ANOMALY_RULES["eligible_pct_max"],
            "severity": "warn",
            "message": f"{eligible_pct*100:.1f}% of universe is eligible (max: {ANOMALY_RULES['eligible_pct_max']*100:.0f}%). Gates too loose.",
        })
    if eligible_pct < ANOMALY_RULES["eligible_pct_min"]:
        anomalies.append({
            "rule": "eligible_pct_min",
            "value": eligible_pct,
            "threshold": ANOMALY_RULES["eligible_pct_min"],
            "severity": "warn",
            "message": f"Only {eligible_pct*100:.1f}% of universe is eligible (min: {ANOMALY_RULES['eligible_pct_min']*100:.0f}%). Gates too strict.",
        })
    if overhead_stats["p95"] < ANOMALY_RULES["overhead_p95_min"]:
        anomalies.append({
            "rule": "overhead_p95_min",
            "value": overhead_stats["p95"],
            "threshold": ANOMALY_RULES["overhead_p95_min"],
            "severity": "warn",
            "message": f"overhead_supply_score p95={overhead_stats['p95']} (min expected: {ANOMALY_RULES['overhead_p95_min']}). Possible collapse.",
        })
    if weekly_stats["median"] < ANOMALY_RULES["weekly_median_min"]:
        anomalies.append({
            "rule": "weekly_median_min",
            "value": weekly_stats["median"],
            "threshold": ANOMALY_RULES["weekly_median_min"],
            "severity": "warn",
            "message": f"weekly_trend_score median={weekly_stats['median']} (min expected: {ANOMALY_RULES['weekly_median_min']}). Biased pessimistic.",
        })

    passed = not any(a["severity"] == "fail" for a in anomalies)

    return {
        "as_of": as_of.isoformat(),
        "n_symbols": n_symbols,
        "n_eligible": n_eligible,
        "eligible_pct": round(eligible_pct, 3),
        "cas": cas_stats,
        "weekly_trend_score": weekly_stats,
        "overhead_supply_score": overhead_stats,
        "confidence_stars": stars_dict,
        "anomalies": anomalies,
        "passed": passed,
    }


def _print_human(report: dict) -> None:
    print(f"CAS Distribution Sanity Check")
    print(f"{'=' * 60}")
    print(f"As of:               {report['as_of']}")
    print(f"Total symbols:       {report['n_symbols']}")
    print(f"Eligible:            {report['n_eligible']} ({report['eligible_pct']*100:.1f}%)")
    print()

    cas = report["cas"]
    print(f"Capital Allocation Score (n={cas['n']}):")
    print(f"  mean={cas['mean']}, median={cas['median']}, p95={cas['p95']}")
    print(f"  pct >= 60: {cas['pct_above_60']*100:.1f}%,  pct >= 80: {cas['pct_above_80']*100:.1f}%")
    print()

    w = report["weekly_trend_score"]
    print(f"Weekly Trend Score (n={w['n']}):")
    print(f"  mean={w['mean']}, median={w['median']}, p5={w['p5']}, p95={w['p95']}")
    print()

    o = report["overhead_supply_score"]
    print(f"Overhead Supply Score (n={o['n']}):")
    print(f"  mean={o['mean']}, median={o['median']}, p5={o['p5']}, p95={o['p95']}")
    print()

    s = report["confidence_stars"]
    print(f"Confidence Stars distribution:")
    for k in ["5", "4", "3", "2", "1"]:
        n = s.get(k, 0)
        bar = "█" * int(n / max(report["n_eligible"], 1) * 50)
        print(f"  ★{k[0]:>1} ({k}): {n:>4}  {bar}")
    print(f"  5-star pct: {s['five_star_pct']*100:.1f}%,  1-star pct: {s['one_star_pct']*100:.1f}%")
    print()

    print(f"Anomalies: {len(report['anomalies'])}")
    if report["anomalies"]:
        for a in report["anomalies"]:
            print(f"  [{a['severity'].upper():>4}] {a['message']}")
    else:
        print("  (none)")

    print()
    print("RESULT:", "PASS ✅" if report["passed"] else "FAIL ❌")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--as-of", type=date.fromisoformat, default=None,
                   help="date to analyze (defaults to latest trading date)")
    p.add_argument("--config", default="config/capital_allocation.yaml",
                   help="path to CAS config YAML")
    p.add_argument("--json", type=Path, default=None,
                   help="write JSON report to this path")
    p.add_argument("--no-strict", action="store_true",
                   help="never exit with non-zero (still print report)")
    args = p.parse_args()

    config = load_config(args.config)
    as_of = args.as_of
    if as_of is None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT MAX(date) AS d FROM daily_prices")
                r = cur.fetchone()
                as_of = r["d"]

    report = analyze(as_of, config)

    _print_human(report)
    if args.json:
        args.json.write_text(json.dumps(report, indent=2, default=str))
        print(f"\nJSON written to {args.json}")

    if not args.no_strict and not report["passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
