"""Verify PRDE fundamentals import health.

Usage:
    python scripts/verify_prde_import.py
    python scripts/verify_prde_import.py --min-companies 10 --min-years 5
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("prde_verify")


def fetch_one(cur, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    cur.execute(query, params)
    return dict(cur.fetchone() or {})


def fetch_all(cur, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    cur.execute(query, params)
    return [dict(row) for row in cur.fetchall()]


def verify(min_companies: int, min_years: int) -> tuple[int, dict[str, Any]]:
    from api.schema import ensure_prde_tables
    from engine_core.db import get_connection

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            ensure_prde_tables(cur)
            conn.commit()

            counts = fetch_one(
                cur,
                """
                SELECT
                    (SELECT COUNT(*) FROM public.prde_companies) AS companies,
                    (SELECT COUNT(*) FROM public.prde_financials_annual) AS financial_rows,
                    (SELECT COUNT(*) FROM public.prde_ratios_annual) AS ratio_rows
                """,
            )

            duplicate_financials = fetch_one(
                cur,
                """
                SELECT COUNT(*) AS count
                FROM (
                    SELECT company_id, fiscal_year
                    FROM public.prde_financials_annual
                    GROUP BY company_id, fiscal_year
                    HAVING COUNT(*) > 1
                ) dupes
                """,
            )["count"]

            duplicate_ratios = fetch_one(
                cur,
                """
                SELECT COUNT(*) AS count
                FROM (
                    SELECT company_id, fiscal_year
                    FROM public.prde_ratios_annual
                    GROUP BY company_id, fiscal_year
                    HAVING COUNT(*) > 1
                ) dupes
                """,
            )["count"]

            short_histories = fetch_all(
                cur,
                """
                SELECT c.ticker, COUNT(f.id) AS years
                FROM public.prde_companies c
                LEFT JOIN public.prde_financials_annual f ON f.company_id = c.id
                GROUP BY c.ticker
                HAVING COUNT(f.id) < %s
                ORDER BY years ASC, c.ticker ASC
                LIMIT 25
                """,
                (min_years,),
            )

            missing_required = fetch_one(
                cur,
                """
                SELECT COUNT(*) AS count
                FROM public.prde_financials_annual
                WHERE revenue IS NULL
                   OR ebitda IS NULL
                   OR pat IS NULL
                   OR roce IS NULL
                   OR capex IS NULL
                   OR employee_cost IS NULL
                   OR total_assets IS NULL
                """,
            )["count"]

            latest_imports = fetch_all(
                cur,
                """
                SELECT c.ticker, COUNT(f.id) AS years, MIN(f.fiscal_year) AS first_year,
                       MAX(f.fiscal_year) AS last_year, MAX(f.imported_at) AS latest_imported_at
                FROM public.prde_companies c
                JOIN public.prde_financials_annual f ON f.company_id = c.id
                GROUP BY c.ticker
                ORDER BY latest_imported_at DESC, c.ticker ASC
                LIMIT 20
                """,
            )

        failures: list[str] = []
        if int(counts["companies"]) < min_companies:
            failures.append(f"companies below threshold: {counts['companies']} < {min_companies}")
        if int(duplicate_financials) > 0:
            failures.append(f"duplicate financial company/year groups: {duplicate_financials}")
        if int(duplicate_ratios) > 0:
            failures.append(f"duplicate ratio company/year groups: {duplicate_ratios}")
        if int(missing_required) > 0:
            failures.append(f"financial rows with missing required values: {missing_required}")
        if short_histories:
            failures.append(f"{len(short_histories)} companies have fewer than {min_years} fiscal years")

        report = {
            "status": "FAIL" if failures else "PASS",
            "counts": counts,
            "duplicate_financial_groups": duplicate_financials,
            "duplicate_ratio_groups": duplicate_ratios,
            "missing_required_financial_rows": missing_required,
            "short_histories": short_histories,
            "latest_imports": latest_imports,
            "failures": failures,
        }
        return (1 if failures else 0), report
    finally:
        conn.close()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify PRDE fundamentals import health")
    parser.add_argument("--min-companies", type=int, default=10, help="Minimum expected companies")
    parser.add_argument("--min-years", type=int, default=5, help="Minimum expected fiscal years per company")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        exit_code, report = verify(args.min_companies, args.min_years)
    except Exception as exc:
        logger.error("PRDE import verification failed: %s", exc)
        return 2

    print(json.dumps(report, indent=2, default=str))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
