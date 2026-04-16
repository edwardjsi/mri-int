#!/usr/bin/env python3
"""Golden-path verification for the live scoring pipeline.

Checks the latest BULL regime day and confirms there are at least 10 stocks
with total_score >= 75 on that date.
"""

from __future__ import annotations

import os
import sys

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
                LIMIT 1
                """
            )
            regime = cur.fetchone()
            if not regime:
                print("NO_BULL_REGIME")
                return 2

            bull_date = regime["date"]
            cur.execute(
                """
                SELECT COUNT(*) AS n
                FROM stock_scores
                WHERE date = %s AND total_score >= 75
                """,
                (bull_date,),
            )
            top_count = cur.fetchone()["n"]

            cur.execute(
                """
                SELECT COUNT(*) AS n
                FROM stock_scores
                WHERE date = %s
                """,
                (bull_date,),
            )
            total_count = cur.fetchone()["n"]

        print(f"BULL_DATE={bull_date}")
        print(f"TOP75={top_count}")
        print(f"TOTAL={total_count}")

        if top_count >= 10:
            print("GOLDEN_PATH_PASS")
            return 0

        print("GOLDEN_PATH_FAIL")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
