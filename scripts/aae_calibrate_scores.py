#!/usr/bin/env python3
"""AAE Score Calibration and Backtest Framework.

Analyzes historical re-rating cases, compares score changes against
subsequent returns, and produces threshold calibration reports.

Usage:
    python scripts/aae_calibrate_scores.py --report
    python scripts/aae_calibrate_scores.py --seed-cases
    python scripts/aae_calibrate_scores.py --analyze --min-cases 5
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, timedelta
from typing import Any

from engine_core.db import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("aae_calibrate")

# Known Indian re-rating stories (publicly documented cases)
# These serve as seed data for calibration
SEED_CASES: list[dict[str, Any]] = [
    {
        "symbol": "TRENT",
        "case_type": "SUCCESS",
        "entry_date": "2020-03-31",
        "exit_date": "2024-03-31",
        "pre_score": 75.0,
        "post_return_pct": 1200.0,
        "time_to_rerate_months": 12,
        "notes": "Department store → fashion powerhouse repositioning. Revenue 5x in 4 years. Westside expansion + Zudio scaling. Market re-rated from retail PE to consumption compounder PE.",
    },
    {
        "symbol": "VARUNBEVERAGES",
        "case_type": "SUCCESS",
        "entry_date": "2020-03-31",
        "exit_date": "2024-03-31",
        "pre_score": 70.0,
        "post_return_pct": 800.0,
        "time_to_rerate_months": 18,
        "notes": "Pepsi bottler → multi-product FMCG distribution platform. International expansion (Africa). Margin improvement via backward integration (own preforms).",
    },
    {
        "symbol": "DIXON",
        "case_type": "SUCCESS",
        "entry_date": "2020-03-31",
        "exit_date": "2024-03-31",
        "pre_score": 80.0,
        "post_return_pct": 1500.0,
        "time_to_rerate_months": 8,
        "notes": "EMS manufacturing pivot. PLI scheme beneficiary. Mobile manufacturing scale-up. Revenue growth 50%+ CAGR. Market re-rated from contract manufacturer to tech platform.",
    },
    {
        "symbol": "POLYCAB",
        "case_type": "SUCCESS",
        "entry_date": "2020-03-31",
        "exit_date": "2024-03-31",
        "pre_score": 65.0,
        "post_return_pct": 600.0,
        "time_to_rerate_months": 15,
        "notes": "Wire & cable → FMEG platform. Housing + infra capex cycle beneficiary. Distribution moat strengthening.",
    },
    {
        "symbol": "TITAN",
        "case_type": "SUCCESS",
        "entry_date": "2020-03-31",
        "exit_date": "2024-03-31",
        "pre_score": 72.0,
        "post_return_pct": 350.0,
        "time_to_rerate_months": 10,
        "notes": "Jewelry → lifestyle platform. Tanishq brand moat. Store expansion. Market share gains from unorganized sector.",
    },
    # False positives — stocks that screened well but didn't deliver
    {
        "symbol": "YESBANK",
        "case_type": "FALSE_POSITIVE",
        "entry_date": "2018-03-31",
        "exit_date": "2020-03-31",
        "pre_score": 65.0,
        "post_return_pct": -90.0,
        "time_to_rerate_months": None,
        "notes": "Governance implosion. High NPA divergence. Management credibility collapse. Governance kill switch would have caught this.",
    },
    {
        "symbol": "DHFL",
        "case_type": "FALSE_POSITIVE",
        "entry_date": "2018-03-31",
        "exit_date": "2019-09-30",
        "pre_score": 60.0,
        "post_return_pct": -95.0,
        "time_to_rerate_months": None,
        "notes": "NBFC liquidity crisis. ALM mismatch. Related-party lending. Governance red flags were visible in retrospect.",
    },
    {
        "symbol": "VODAFONEIDEA",
        "case_type": "FALSE_POSITIVE",
        "entry_date": "2019-03-31",
        "exit_date": "2021-03-31",
        "pre_score": 55.0,
        "post_return_pct": -70.0,
        "time_to_rerate_months": None,
        "notes": "AGR liability shock. Balance sheet destroyed by regulatory overhang. Macro/policy risk not priced in.",
    },
]


def seed_case_library() -> int:
    """Insert seed calibration cases into the case library."""
    conn = get_connection()
    inserted = 0
    try:
        with conn.cursor() as cur:
            for case in SEED_CASES:
                cur.execute(
                    """
                    INSERT INTO public.aae_case_library
                        (symbol, case_type, entry_date, exit_date, pre_score,
                         post_return_pct, time_to_rerate_months, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        case["symbol"], case["case_type"],
                        case["entry_date"], case["exit_date"],
                        case["pre_score"], case["post_return_pct"],
                        case["time_to_rerate_months"], case["notes"],
                    ),
                )
                if cur.rowcount > 0:
                    inserted += 1
            conn.commit()
    finally:
        conn.close()

    logger.info(f"Seeded {inserted} cases into aae_case_library")
    return inserted


def analyze_cases(min_cases: int = 5) -> dict:
    """Analyze calibration cases and produce threshold recommendations."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Success cases
            cur.execute(
                """
                SELECT pre_score, post_return_pct, time_to_rerate_months, symbol, notes
                FROM public.aae_case_library
                WHERE case_type = 'SUCCESS'
                ORDER BY pre_score DESC
                """
            )
            successes = [dict(row) for row in cur.fetchall()]

            # False positive cases
            cur.execute(
                """
                SELECT pre_score, post_return_pct, symbol, notes
                FROM public.aae_case_library
                WHERE case_type = 'FALSE_POSITIVE'
                ORDER BY pre_score DESC
                """
            )
            false_positives = [dict(row) for row in cur.fetchall()]

    finally:
        conn.close()

    if len(successes) + len(false_positives) < min_cases:
        return {"error": f"Need at least {min_cases} cases, found {len(successes) + len(false_positives)}. Run --seed-cases first."}

    # Compute statistics
    success_scores = [c["pre_score"] for c in successes]
    fp_scores = [c["pre_score"] for c in false_positives]

    avg_success_score = sum(success_scores) / len(success_scores) if success_scores else 0
    avg_fp_score = sum(fp_scores) / len(fp_scores) if fp_scores else 0

    success_returns = [c["post_return_pct"] for c in successes]
    avg_return = sum(success_returns) / len(success_returns) if success_returns else 0

    re_rate_times = [c["time_to_rerate_months"] for c in successes if c["time_to_rerate_months"]]
    avg_rerate_time = sum(re_rate_times) / len(re_rate_times) if re_rate_times else 0

    # Threshold recommendations
    # If false positives cluster at a score level, raise the threshold
    # If successes cluster above a score level, that's the minimum
    max_fp_score = max(fp_scores) if fp_scores else 50
    min_success_score = min(success_scores) if success_scores else 50

    # Conservative threshold: just above the highest false positive
    conservative_threshold = max_fp_score + 5
    # Aggressive threshold: include most successes
    aggressive_threshold = max(min_success_score, conservative_threshold - 10)

    recommendations = {
        "high_conviction_threshold": round(aggressive_threshold, 1),
        "watch_threshold": round(aggressive_threshold - 10, 1),
        "avg_rerate_time_months": round(avg_rerate_time, 1),
        "expected_upside_pct": round(avg_return, 0),
    }

    return {
        "cases_analyzed": len(successes) + len(false_positives),
        "successes": len(successes),
        "false_positives": len(false_positives),
        "avg_success_score": round(avg_success_score, 1),
        "avg_fp_score": round(avg_fp_score, 1),
        "success_score_range": f"{min_success_score:.0f}–{max(success_scores):.0f}",
        "fp_score_range": f"{min(fp_scores):.0f}–{max_fp_score:.0f}" if fp_scores else "N/A",
        "avg_return_pct": round(avg_return, 0),
        "avg_time_to_rerate_months": round(avg_rerate_time, 1),
        "threshold_recommendations": recommendations,
        "success_cases": [{"symbol": s["symbol"], "score": s["pre_score"], "return": s["post_return_pct"]} for s in successes],
        "false_positive_cases": [{"symbol": f["symbol"], "score": f["pre_score"], "return": f["post_return_pct"]} for f in false_positives],
    }


def export_analyst_feedback(output_path: str | None = None) -> list[dict]:
    """Export analyst feedback for calibration analysis."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT symbol, action, justification, profile_version, created_at
                FROM public.aae_analyst_feedback
                ORDER BY created_at DESC
                """
            )
            rows = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

    if output_path:
        with open(output_path, "w") as f:
            json.dump(rows, f, indent=2, default=str)
        logger.info(f"Exported {len(rows)} feedback entries to {output_path}")

    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AAE Score Calibration Framework")
    parser.add_argument("--seed-cases", action="store_true", help="Seed historical calibration cases")
    parser.add_argument("--analyze", action="store_true", help="Analyze cases and produce threshold recommendations")
    parser.add_argument("--report", action="store_true", help="Full calibration report")
    parser.add_argument("--min-cases", type=int, default=5, help="Minimum cases required for analysis")
    parser.add_argument("--export-feedback", help="Export analyst feedback to JSON file")
    args = parser.parse_args(argv or sys.argv[1:])

    if args.seed_cases or args.report:
        count = seed_case_library()
        print(f"✓ Seeded {count} calibration cases")

    if args.export_feedback:
        rows = export_analyst_feedback(args.export_feedback)
        print(f"✓ Exported {len(rows)} feedback entries")

    if args.analyze or args.report:
        result = analyze_cases(min_cases=args.min_cases)

        if "error" in result:
            print(f"⚠ {result['error']}")
            return 1

        print(f"\n{'='*60}")
        print("AAE SCORE CALIBRATION REPORT")
        print(f"{'='*60}")
        print(f"Cases analyzed:    {result['cases_analyzed']} ({result['successes']} successes, {result['false_positives']} false positives)")
        print(f"Avg success score: {result['avg_success_score']:.1f}")
        print(f"Avg FP score:      {result['avg_fp_score']:.1f}")
        print(f"Success range:     {result['success_score_range']}")
        print(f"FP range:          {result['fp_score_range']}")
        print(f"Avg return:        {result['avg_return_pct']:.0f}%")
        print(f"Avg time to re-rate: {result['avg_time_to_rerate_months']:.1f} months")
        print(f"\n{'─'*40}")
        print("THRESHOLD RECOMMENDATIONS")
        print(f"{'─'*40}")
        recs = result["threshold_recommendations"]
        print(f"High conviction (80+):  ≥ {recs['high_conviction_threshold']:.0f}")
        print(f"Watch list:             ≥ {recs['watch_threshold']:.0f}")
        print(f"Expected re-rate horizon: {recs['avg_rerate_time_months']:.0f} months")
        print(f"Historical upside:        {recs['expected_upside_pct']:.0f}%")

        print(f"\n{'─'*40}")
        print("SUCCESS CASES")
        print(f"{'─'*40}")
        for c in result["success_cases"]:
            print(f"  {c['symbol']:<12} Score: {c['score']:.0f}  Return: {c['return']:.0f}%")

        print(f"\n{'─'*40}")
        print("FALSE POSITIVE CASES")
        print(f"{'─'*40}")
        for c in result["false_positive_cases"]:
            print(f"  {c['symbol']:<12} Score: {c['score']:.0f}  Return: {c['return']:.0f}%")

    return 0


if __name__ == "__main__":
    sys.exit(main())
