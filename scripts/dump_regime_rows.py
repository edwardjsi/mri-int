#!/usr/bin/env python3
"""Dump raw regime rows and classification counts."""

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
                SELECT classification, COUNT(*) AS n
                FROM market_regime
                GROUP BY classification
                ORDER BY n DESC, classification
                """
            )
            print("CLASSIFICATION_COUNTS")
            for row in cur.fetchall():
                print(f"- {row['classification']!r}: {row['n']}")

            cur.execute(
                """
                SELECT date, classification
                FROM market_regime
                ORDER BY date
                LIMIT 10
                """
            )
            print("HEAD_ROWS")
            for row in cur.fetchall():
                print(f"- {row['date']} {row['classification']!r}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
