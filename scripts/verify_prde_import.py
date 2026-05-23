#!/usr/bin/env python3
"""Verify PRDE import completeness and data quality.

Checks row counts, null coverage, year spans, and company counts.

Usage:
    python scripts/verify_prde_import.py
    python scripts/verify_prde_import.py --min-companies 10 --min-years 5
"""

from __future__ import annotations

import argparse
import logging
import sys

from engine_core.db import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("verify_prde")


def run_checks(min_companies: int = 10, min_years: int = 5) -> tuple[bool, list[str]]:
    """Run all verification checks. Returns (passed, messages)."""
    from engine_core.db import get_connection
    import psycopg2.extras
    conn = get_connection()
    messages: list[str] = []
    all_passed = True

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # 1. Table existence
            tables = [
                "prde_companies",
                "prde_financials_annual",
                "prde_ratios_annual",
                "prde_feature_snapshots",
            ]
            for table in tables:
                cur.execute(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s) AS exists_flag",
                    (table,),
                )
                exists = cur.fetchone()["exists_flag"]
                if exists:
                    messages.append(f"✓ Table public.{table} exists")
                else:
                    messages.append(f"✗ Table public.{table} MISSING")
                    all_passed = False

            # 2. Company count
            cur.execute("SELECT COUNT(*) AS cnt FROM public.prde_companies WHERE is_active = TRUE")
            company_count = cur.fetchone()["cnt"]
            if company_count >= min_companies:
                messages.append(f"✓ Companies: {company_count} active (min {min_companies})")
            else:
                messages.append(f"✗ Companies: {company_count} active (need {min_companies}+)")
                all_passed = False

            # 3. Financial years per company
            cur.execute("""
                SELECT p.ticker, COUNT(f.id) AS years,
                       MIN(f.fiscal_year) AS first_year, MAX(f.fiscal_year) AS last_year
                FROM public.prde_companies p
                LEFT JOIN public.prde_financials_annual f ON f.company_id = p.id
                WHERE p.is_active = TRUE
                GROUP BY p.ticker, p.id
                ORDER BY p.ticker
            """)
            company_years = cur.fetchall()

            low_year_companies = []
            for row in company_years:
                ticker = row["ticker"]
                years = row["years"]
                first = row["first_year"]
                last = row["last_year"]
                if years < min_years:
                    low_year_companies.append(f"{ticker} ({years} years: {first}–{last})")

            if low_year_companies:
                messages.append(f"✗ Companies with < {min_years} years: {', '.join(low_year_companies)}")
                all_passed = False
            else:
                messages.append(f"✓ All {company_count} companies have ≥ {min_years} years of data")

            # 4. Total financial rows
            cur.execute("SELECT COUNT(*) AS cnt FROM public.prde_financials_annual")
            fin_count = cur.fetchone()["cnt"]
            messages.append(f"✓ Financial rows: {fin_count}")

            # 5. Total ratio rows
            cur.execute("SELECT COUNT(*) AS cnt FROM public.prde_ratios_annual")
            rat_count = cur.fetchone()["cnt"]
            messages.append(f"✓ Ratio rows: {rat_count}")

            # 6. Null coverage in critical fields
            critical_fields = [
                ("revenue", "prde_financials_annual"),
                ("ebitda", "prde_financials_annual"),
                ("pat", "prde_financials_annual"),
                ("total_assets", "prde_financials_annual"),
            ]
            for field, table in critical_fields:
                cur.execute(f'SELECT COUNT(*) AS cnt FROM public.{table} WHERE {field} IS NULL')
                null_count = cur.fetchone()["cnt"]
                if null_count > 0:
                    pct = round(null_count / max(fin_count, 1) * 100, 1)
                    messages.append(f"⚠ {field}: {null_count} NULL values ({pct}% of {fin_count} rows)")
                else:
                    messages.append(f"✓ {field}: 0 NULL values")

            # 7. Duplicate check (should not exist due to UNIQUE constraint)
            cur.execute("""
                SELECT company_id, fiscal_year, COUNT(*) AS cnt
                FROM public.prde_financials_annual
                GROUP BY company_id, fiscal_year
                HAVING COUNT(*) > 1
            """)
            dupes = cur.fetchall()
            if dupes:
                messages.append(f"✗ Duplicate financial rows found: {len(dupes)}")
                all_passed = False
            else:
                messages.append("✓ No duplicate financial rows")

            # 8. Year span summary
            cur.execute("""
                SELECT MIN(fiscal_year) AS min_year, MAX(fiscal_year) AS max_year FROM public.prde_financials_annual
            """)
            row = cur.fetchone()
            messages.append(f"✓ Year span: {row['min_year']} – {row['max_year']}")

            # 9. Per-company detail
            messages.append("")
            messages.append(f"{'Ticker':<12} {'Years':>6}  {'First':>6}  {'Last':>6}  {'Revenue (latest)':>18}  {'EBITDA (latest)':>18}")
            messages.append("-" * 85)
            for row in company_years:
                ticker = row["ticker"]
                years = row["years"]
                first = row["first_year"]
                last = row["last_year"]
                cur.execute("""
                    SELECT revenue, ebitda FROM public.prde_financials_annual f
                    JOIN public.prde_companies c ON c.id = f.company_id
                    WHERE c.ticker = %s
                    ORDER BY f.fiscal_year DESC LIMIT 1
                """, (ticker,))
                latest = cur.fetchone()
                rev_str = f"{latest['revenue']:,.0f}" if latest and latest["revenue"] else "N/A"
                ebitda_str = f"{latest['ebitda']:,.0f}" if latest and latest["ebitda"] else "N/A"
                messages.append(f"{ticker:<12} {years:>6}  {first:>6}  {last:>6}  {rev_str:>18}  {ebitda_str:>18}")

    except Exception as e:
        messages.append(f"✗ Check failed: {e}")
        all_passed = False
    finally:
        conn.close()

    return all_passed, messages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify PRDE import data quality")
    parser.add_argument("--min-companies", type=int, default=10, help="Minimum active companies required")
    parser.add_argument("--min-years", type=int, default=5, help="Minimum fiscal years per company")
    args = parser.parse_args(argv or sys.argv[1:])

    passed, messages = run_checks(min_companies=args.min_companies, min_years=args.min_years)

    for msg in messages:
        print(msg)

    if passed:
        print("\n✅ All PRDE verification checks passed.")
        return 0
    else:
        print("\n❌ Some verification checks failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
