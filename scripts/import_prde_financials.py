"""Import PRDE annual financials and ratios from CSV.

Usage:
    python scripts/import_prde_financials.py data/prde_financials.csv
    python scripts/import_prde_financials.py data/prde_financials.csv --dry-run
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("prde_import")


REQUIRED_COLUMNS = {
    "ticker",
    "fiscal_year",
    "revenue",
    "ebitda",
    "pat",
    "roce",
    "capex",
    "employee_cost",
    "total_assets",
}

OPTIONAL_COLUMNS = {
    "name",
    "country",
    "sector",
    "industry",
    "pe",
    "ev_ebitda",
    "pb",
    "debt_equity",
    "source",
}

FINANCIAL_COLUMNS = (
    "revenue",
    "ebitda",
    "pat",
    "roce",
    "capex",
    "employee_cost",
    "total_assets",
)

RATIO_COLUMNS = ("pe", "ev_ebitda", "pb", "debt_equity")


@dataclass
class ImportRow:
    ticker: str
    fiscal_year: int
    company: dict[str, Any]
    financials: dict[str, Any]
    ratios: dict[str, Any]


def normalize_header(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def parse_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "").replace("₹", "").replace("$", "")
    text = re.sub(r"\s+", "", text)
    is_percent = text.endswith("%")
    if is_percent:
        text = text[:-1]
    if text in {"-", "NA", "N/A", "na", "n/a", "null", "None"}:
        return None
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"invalid numeric value: {value!r}") from exc


def parse_year(value: Any) -> int:
    text = str(value or "").strip()
    if not re.fullmatch(r"\d{4}", text):
        raise ValueError(f"invalid fiscal_year: {value!r}")
    return int(text)


def load_csv(path: Path) -> tuple[list[ImportRow], list[str]]:
    warnings: list[str] = []
    rows: list[ImportRow] = []

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header row")

        original_headers = reader.fieldnames
        normalized_headers = [normalize_header(h) for h in original_headers]
        missing = sorted(REQUIRED_COLUMNS - set(normalized_headers))
        if missing:
            raise ValueError(f"missing required columns: {', '.join(missing)}")

        header_map = dict(zip(original_headers, normalized_headers))

        for row_number, raw in enumerate(reader, start=2):
            row = {header_map[k]: v for k, v in raw.items() if k in header_map}
            ticker = str(row.get("ticker") or "").strip().upper()
            if not ticker:
                raise ValueError(f"row {row_number}: ticker is required")

            fiscal_year = parse_year(row.get("fiscal_year"))
            source = str(row.get("source") or path.name).strip()

            company = {
                "ticker": ticker,
                "name": (row.get("name") or "").strip() or None,
                "country": (row.get("country") or "IN").strip().upper() or "IN",
                "sector": (row.get("sector") or "").strip() or None,
                "industry": (row.get("industry") or "").strip() or None,
            }

            financials = {"fiscal_year": fiscal_year, "source": source}
            ratios = {"fiscal_year": fiscal_year, "source": source}

            usable_financial_values = 0
            for column in FINANCIAL_COLUMNS:
                value = parse_decimal(row.get(column))
                financials[column] = value
                if value is not None:
                    usable_financial_values += 1

            for column in RATIO_COLUMNS:
                ratios[column] = parse_decimal(row.get(column))

            if usable_financial_values == 0:
                raise ValueError(f"row {row_number}: no usable financial values")

            if any(ratios[col] is None for col in RATIO_COLUMNS):
                warnings.append(f"row {row_number} {ticker} {fiscal_year}: one or more valuation ratios missing")

            rows.append(
                ImportRow(
                    ticker=ticker,
                    fiscal_year=fiscal_year,
                    company=company,
                    financials=financials,
                    ratios=ratios,
                )
            )

    years_by_ticker: dict[str, set[int]] = defaultdict(set)
    for row in rows:
        years_by_ticker[row.ticker].add(row.fiscal_year)

    for ticker, years in sorted(years_by_ticker.items()):
        if len(years) < 5:
            warnings.append(f"{ticker}: only {len(years)} fiscal years provided; PRDE works best with 5-10 years")

    return rows, warnings


def decimal_default(value: Any) -> str:
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def print_summary(rows: list[ImportRow], warnings: list[str]) -> None:
    by_ticker = Counter(row.ticker for row in rows)
    years = [row.fiscal_year for row in rows]
    summary = {
        "rows": len(rows),
        "companies": len(by_ticker),
        "fiscal_year_min": min(years) if years else None,
        "fiscal_year_max": max(years) if years else None,
        "warnings": len(warnings),
    }
    print(json.dumps(summary, indent=2, default=decimal_default))
    if warnings:
        print("\nWarnings:")
        for warning in warnings[:25]:
            print(f"- {warning}")
        if len(warnings) > 25:
            print(f"- ... {len(warnings) - 25} more warnings")


def upsert_rows(rows: list[ImportRow]) -> None:
    from psycopg2.extras import RealDictCursor

    from api.schema import ensure_prde_tables
    from engine_core.db import get_connection

    conn = get_connection()
    conn.cursor_factory = RealDictCursor
    try:
        with conn.cursor() as cur:
            ensure_prde_tables(cur)

            for row in rows:
                cur.execute(
                    """
                    INSERT INTO public.prde_companies (
                        ticker, name, country, sector, industry, updated_at
                    )
                    VALUES (
                        %(ticker)s, %(name)s, %(country)s, %(sector)s, %(industry)s, NOW()
                    )
                    ON CONFLICT (ticker) DO UPDATE SET
                        name = COALESCE(EXCLUDED.name, public.prde_companies.name),
                        country = COALESCE(EXCLUDED.country, public.prde_companies.country),
                        sector = COALESCE(EXCLUDED.sector, public.prde_companies.sector),
                        industry = COALESCE(EXCLUDED.industry, public.prde_companies.industry),
                        updated_at = NOW()
                    RETURNING id;
                    """,
                    row.company,
                )
                company_id = cur.fetchone()["id"]

                financials = dict(row.financials, company_id=company_id)
                cur.execute(
                    """
                    INSERT INTO public.prde_financials_annual (
                        company_id, fiscal_year, revenue, ebitda, pat, roce, capex,
                        employee_cost, total_assets, source, imported_at
                    )
                    VALUES (
                        %(company_id)s, %(fiscal_year)s, %(revenue)s, %(ebitda)s,
                        %(pat)s, %(roce)s, %(capex)s, %(employee_cost)s,
                        %(total_assets)s, %(source)s, NOW()
                    )
                    ON CONFLICT (company_id, fiscal_year) DO UPDATE SET
                        revenue = EXCLUDED.revenue,
                        ebitda = EXCLUDED.ebitda,
                        pat = EXCLUDED.pat,
                        roce = EXCLUDED.roce,
                        capex = EXCLUDED.capex,
                        employee_cost = EXCLUDED.employee_cost,
                        total_assets = EXCLUDED.total_assets,
                        source = EXCLUDED.source,
                        imported_at = NOW();
                    """,
                    financials,
                )

                ratios = dict(row.ratios, company_id=company_id)
                cur.execute(
                    """
                    INSERT INTO public.prde_ratios_annual (
                        company_id, fiscal_year, pe, ev_ebitda, pb,
                        debt_equity, source, imported_at
                    )
                    VALUES (
                        %(company_id)s, %(fiscal_year)s, %(pe)s, %(ev_ebitda)s,
                        %(pb)s, %(debt_equity)s, %(source)s, NOW()
                    )
                    ON CONFLICT (company_id, fiscal_year) DO UPDATE SET
                        pe = EXCLUDED.pe,
                        ev_ebitda = EXCLUDED.ev_ebitda,
                        pb = EXCLUDED.pb,
                        debt_equity = EXCLUDED.debt_equity,
                        source = EXCLUDED.source,
                        imported_at = NOW();
                    """,
                    ratios,
                )

            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import PRDE annual financials and ratios from CSV")
    parser.add_argument("csv_path", type=Path, help="Path to PRDE financials CSV")
    parser.add_argument("--dry-run", action="store_true", help="Validate and summarize without writing to DB")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if not args.csv_path.exists():
        logger.error("CSV file not found: %s", args.csv_path)
        return 2

    try:
        rows, warnings = load_csv(args.csv_path)
        print_summary(rows, warnings)
        if args.dry_run:
            logger.info("Dry run complete; no database writes performed.")
            return 0
        upsert_rows(rows)
        logger.info("Imported %s PRDE rows across %s companies.", len(rows), len({row.ticker for row in rows}))
        return 0
    except Exception as exc:
        logger.error("Import failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
