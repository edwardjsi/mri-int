#!/usr/bin/env python3
"""Diagnose why the golden-path threshold is not being met."""

from __future__ import annotations

import os
import sys
from collections import Counter

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine_core.config import get_connection_string
from engine_core.db import get_connection


def main() -> int:
    os.environ["DATABASE_URL"] = get_connection_string()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT date, classification
                FROM market_regime
                WHERE classification = 'BULL'
                ORDER BY date DESC
                LIMIT 5
                """
            )
            bull_days = cur.fetchall()
            print("BULL_DAYS")
            for row in bull_days:
                print(f"- {row['date']} {row['classification']}")

            if bull_days:
                bull_date = bull_days[0]["date"]
                cur.execute(
                    """
                    SELECT total_score,
                           condition_ema_50_200,
                           condition_ema_200_slope,
                           condition_6m_high,
                           condition_volume,
                           condition_rs
                    FROM stock_scores
                    WHERE date = %s
                    ORDER BY total_score DESC, symbol
                    """,
                    (bull_date,),
                )
                rows = cur.fetchall()
                scores = [r["total_score"] for r in rows]
                print(f"\nLATEST_BULL_DAY={bull_date}")
                print(f"TOTAL_SYMBOLS={len(rows)}")
                if scores:
                    print(f"MAX_SCORE={max(scores)}")
                    print(f"AVG_SCORE={sum(scores)/len(scores):.2f}")
                    counts = Counter(scores)
                    print("SCORE_DISTRIBUTION")
                    for score in sorted(counts.keys(), reverse=True)[:10]:
                        print(f"- {score}: {counts[score]}")

                condition_names = [
                    "condition_ema_50_200",
                    "condition_ema_200_slope",
                    "condition_6m_high",
                    "condition_volume",
                    "condition_rs",
                ]
                print("\nCONDITION_TRUE_COUNTS")
                for name in condition_names:
                    cur.execute(
                        f"""
                        SELECT COUNT(*) AS n
                        FROM stock_scores
                        WHERE date = %s AND {name} IS TRUE
                        """,
                        (bull_date,),
                    )
                    print(f"- {name}: {cur.fetchone()['n']}")

                print("\nTOP_10_ROWS")
                for row in rows[:10]:
                    flags = [
                        "ema50>200" if row["condition_ema_50_200"] else "ema50<=200",
                        "slope+" if row["condition_ema_200_slope"] else "slope-",
                        "6m_high" if row["condition_6m_high"] else "not_6m_high",
                        "volume" if row["condition_volume"] else "no_volume",
                        "rs+" if row["condition_rs"] else "rs-",
                    ]
                    print(f"- {row['total_score']} :: {' | '.join(flags)}")

            cur.execute(
                """
                SELECT MAX(total_score) AS max_score,
                       COUNT(*) FILTER (WHERE total_score >= 75) AS top75
                FROM stock_scores
                WHERE date = (SELECT MAX(date) FROM stock_scores)
                """
            )
            latest = cur.fetchone()
            print(
                f"\nLATEST_SCORE_DATE_MAX={latest['max_score']} TOP75={latest['top75']}"
            )
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
