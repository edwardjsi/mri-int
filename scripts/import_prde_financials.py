#!/usr/bin/env python3
"""Import PRDE financial data from CSV into PostgreSQL.

Idempotent: re-running the same CSV produces zero new rows.
Upserts companies, financials, and ratios.

Usage:
    python scripts/import_prde_financials.py data/prde_financials_seed.csv --dry-run
    python scripts/import_prde_financials.py data/prde_financials_seed.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

from engine_core.db import get_connection
from api.schema import ensure_prde_tables

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("import_prde")

REQUIRED_COLUMNS = [
    "ticker", "name", "sector", "industry", "fiscal_year",
    "revenue", "ebitda", "pat", "roce", "capex", "employee_cost", "total_assets",
    "pe", "ev_ebitda", "pb", "debt_equity",
]


def parse_numeric(val: str | None) -> float | None:
    if val is None or val.strip() == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def validate_csv(path: Path) -> tuple[list[dict], list[str]]:
    """Read and validate the CSV. Returns (rows, errors)."""
    errors: list[str] = []

    if not path.exists():
        return [], [f"File not found: {path}"]

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []

        missing_cols = [c for c in REQUIRED_COLUMNS if c not in headers]
        if missing_cols:
            errors.append(f"Missing columns: {missing_cols}")

        rows = []
        for i, row in enumerate(reader, start=2):  # line 2 = first data row
            ticker = row.get("ticker", "").strip().upper()
            fiscal_year = row.get("fiscal_year", "").strip()

            if not ticker:
                errors.append(f"Line {i}: missing ticker")
                continue

            try:
                fy = int(fiscal_year)
            except (ValueError, TypeError):
                errors.append(f"Line {i}: invalid fiscal_year '{fiscal_year}'")
                continue

            rows.append({
                "ticker": ticker,
                "name": row.get("name", "").strip(),
                "sector": row.get("sector", "").strip(),
                "industry": row.get("industry", "").strip(),
                "fiscal_year": fy,
                "revenue": parse_numeric(row.get("revenue")),
                "ebitda": parse_numeric(row.get("ebitda")),
                "pat": parse_numeric(row.get("pat")),
                "roce": parse_numeric(row.get("roce")),
                "capex": parse_numeric(row.get("capex")),
                "employee_cost": parse_numeric(row.get("employee_cost")),
                "total_assets": parse_numeric(row.get("total_assets")),
                "pe": parse_numeric(row.get("pe")),
                "ev_ebitda": parse_numeric(row.get("ev_ebitda")),
                "pb": parse_numeric(row.get("pb")),
                "debt_equity": parse_numeric(row.get("debt_equity")),
            })

    return rows, errors


def import_data(rows: list[dict], dry_run: bool = False) -> dict:
    """Import rows into PRDE tables. Returns summary stats."""
    conn = get_connection()
    stats = {
        "companies_inserted": 0,
        "companies_skipped": 0,
        "financials_inserted": 0,
        "financials_skipped": 0,
        "ratios_inserted": 0,
        "ratios_skipped": 0,
    }

    try:
        with conn.cursor() as cur:
            ensure_prde_tables(cur)

            # Deduplicate by ticker
            tickers = sorted(set(r["ticker"] for r in rows))

            # Phase 1: Upsert companies
            for ticker in tickers:
                co_rows = [r for r in rows if r["ticker"] == ticker]
                first = co_rows[0]

                cur.execute(
                    """
                    INSERT INTO public.prde_companies (ticker, name, sector, industry)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (ticker) DO UPDATE SET
                        name     = EXCLUDED.name,
                        sector   = EXCLUDED.sector,
                        industry = EXCLUDED.industry
                    RETURNING id, (xmax = 0) AS is_insert
                    """,
                    (ticker, first["name"], first["sector"], first["industry"]),
                )
                result = cur.fetchone()
                company_id = result["id"]
                is_insert = result["is_insert"]

                if is_insert:
                    stats["companies_inserted"] += 1
                else:
                    stats["companies_skipped"] += 1

                # Phase 2: Upsert financials
                for row in co_rows:
                    cur.execute(
                        """
                        INSERT INTO public.prde_financials_annual
                            (company_id, fiscal_year, revenue, ebitda, pat, roce,
                             capex, employee_cost, total_assets)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (company_id, fiscal_year) DO UPDATE SET
                            revenue       = EXCLUDED.revenue,
                            ebitda        = EXCLUDED.ebitda,
                            pat           = EXCLUDED.pat,
                            roce          = EXCLUDED.roce,
                            capex         = EXCLUDED.capex,
                            employee_cost = EXCLUDED.employee_cost,
                            total_assets  = EXCLUDED.total_assets
                        RETURNING id, (xmax = 0) AS is_insert
                        """,
                        (
                            company_id, row["fiscal_year"],
                            row["revenue"], row["ebitda"], row["pat"], row["roce"],
                            row["capex"], row["employee_cost"], row["total_assets"],
                        ),
                    )
                    fin_result = cur.fetchone()
                    if fin_result["is_insert"]:
                        stats["financials_inserted"] += 1
                    else:
                        stats["financials_skipped"] += 1

                    # Phase 3: Upsert ratios
                    if any(row.get(k) is not None for k in ("pe", "ev_ebitda", "pb", "debt_equity")):
                        cur.execute(
                            """
                            INSERT INTO public.prde_ratios_annual
                                (company_id, fiscal_year, pe, ev_ebitda, pb, debt_equity)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (company_id, fiscal_year) DO UPDATE SET
                                pe         = EXCLUDED.pe,
                                ev_ebitda  = EXCLUDED.ev_ebitda,
                                pb         = EXCLUDED.pb,
                                debt_equity = EXCLUDED.debt_equity
                            RETURNING id, (xmax = 0) AS is_insert
                            """,
                            (
                                company_id, row["fiscal_year"],
                                row["pe"], row["ev_ebitda"],
                                row["pb"], row["debt_equity"],
                            ),
                        )
                        rat_result = cur.fetchone()
                        if rat_result["is_insert"]:
                            stats["ratios_inserted"] += 1
                        else:
                            stats["ratios_skipped"] += 1

            if dry_run:
                conn.rollback()
                logger.info("DRY RUN — all changes rolled back")
            else:
                conn.commit()
                logger.info("Import committed")

        return stats

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import PRDE financial seed CSV")
    parser.add_argument("csv_path", help="Path to the CSV file")
    parser.add_argument("--dry-run", action="store_true", help="Validate and simulate without committing")
    args = parser.parse_args(argv or sys.argv[1:])

    csv_path = Path(args.csv_path)

    print(f"Reading {csv_path}...")
    rows, errors = validate_csv(csv_path)

    if errors:
        print(f"\n❌ Validation errors ({len(errors)}):")
        for err in errors:
            print(f"  • {err}")
        return 1

    print(f"✓ CSV valid: {len(rows)} rows across {len(set(r['ticker'] for r in rows))} companies")

    if args.dry_run:
        print("\n🔍 DRY RUN — validating without writing to database\n")

    stats = import_data(rows, dry_run=args.dry_run)

    total_inserted = stats["companies_inserted"] + stats["financials_inserted"] + stats["ratios_inserted"]
    total_skipped  = stats["companies_skipped"] + stats["financials_skipped"] + stats["ratios_skipped"]

    if args.dry_run:
        print("Would insert:")
    else:
        print("\nImport complete:")

    print(f"  Companies:    {stats['companies_inserted']} new, {stats['companies_skipped']} already present")
    print(f"  Financials:   {stats['financials_inserted']} new, {stats['financials_skipped']} already present")
    print(f"  Ratios:       {stats['ratios_inserted']} new, {stats['ratios_skipped']} already present")
    print(f"  ─────────────────────────────────────────")
    print(f"  Total:        {total_inserted} new, {total_skipped} skipped (idempotent)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
