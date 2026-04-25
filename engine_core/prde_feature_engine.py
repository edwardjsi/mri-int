"""PRDE deterministic feature engineering.

Builds reproducible feature snapshots from imported annual financials and ratios.

Usage:
    python engine_core/prde_feature_engine.py --dry-run --limit 20
    python engine_core/prde_feature_engine.py --limit 20
    python engine_core/prde_feature_engine.py --symbol TCS --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import sys
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("prde_feature_engine")


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def round_or_none(value: float | None, digits: int = 4) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return round(value, digits)


def ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def cagr(first: float | None, last: float | None, periods: int) -> float | None:
    if first is None or last is None or first <= 0 or last <= 0 or periods <= 0:
        return None
    return (last / first) ** (1 / periods) - 1


def yoy_growth(values: list[float | None]) -> list[float | None]:
    growth: list[float | None] = []
    for prev, current in zip(values, values[1:]):
        growth.append(ratio((current - prev) if current is not None and prev is not None else None, prev))
    return growth


def average(values: list[float | None]) -> float | None:
    clean = [v for v in values if v is not None and math.isfinite(v)]
    if not clean:
        return None
    return sum(clean) / len(clean)


def stddev(values: list[float | None]) -> float | None:
    clean = [v for v in values if v is not None and math.isfinite(v)]
    if len(clean) < 2:
        return None
    mean = sum(clean) / len(clean)
    variance = sum((v - mean) ** 2 for v in clean) / (len(clean) - 1)
    return math.sqrt(variance)


def slope(xs: list[int], ys: list[float | None]) -> float | None:
    pairs = [(x, y) for x, y in zip(xs, ys) if y is not None and math.isfinite(y)]
    if len(pairs) < 2:
        return None
    x_values = [p[0] for p in pairs]
    y_values = [p[1] for p in pairs]
    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(y_values) / len(y_values)
    denominator = sum((x - x_mean) ** 2 for x in x_values)
    if denominator == 0:
        return None
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    return numerator / denominator


def canonical_hash(features: dict[str, Any]) -> str:
    payload = json.dumps(features, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fetch_companies(cur, symbol: str | None, limit: int | None) -> list[dict[str, Any]]:
    params: list[Any] = []
    where = "WHERE c.is_active = TRUE"
    if symbol:
        where += " AND c.ticker = %s"
        params.append(symbol.upper().strip())

    limit_clause = ""
    if limit is not None:
        limit_clause = " LIMIT %s"
        params.append(limit)

    cur.execute(
        f"""
        SELECT c.id, c.ticker, c.name, c.country, c.sector, c.industry,
               COUNT(f.id) AS financial_years
        FROM public.prde_companies c
        LEFT JOIN public.prde_financials_annual f ON f.company_id = c.id
        {where}
        GROUP BY c.id, c.ticker, c.name, c.country, c.sector, c.industry
        ORDER BY c.ticker ASC
        {limit_clause}
        """,
        tuple(params),
    )
    return [dict(row) for row in cur.fetchall()]


def fetch_company_history(cur, company_id: int) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT f.fiscal_year, f.revenue, f.ebitda, f.pat, f.roce, f.capex,
               f.employee_cost, f.total_assets, r.pe, r.ev_ebitda, r.pb,
               r.debt_equity
        FROM public.prde_financials_annual f
        LEFT JOIN public.prde_ratios_annual r
          ON r.company_id = f.company_id
         AND r.fiscal_year = f.fiscal_year
        WHERE f.company_id = %s
        ORDER BY f.fiscal_year ASC
        """,
        (company_id,),
    )
    return [dict(row) for row in cur.fetchall()]


def build_features(company: dict[str, Any], history: list[dict[str, Any]], min_years: int) -> tuple[dict[str, Any] | None, str | None]:
    if len(history) < min_years:
        return None, f"insufficient history: {len(history)} years < {min_years}"

    years = [int(row["fiscal_year"]) for row in history]
    year_span = years[-1] - years[0]
    if year_span <= 0:
        return None, "invalid fiscal year span"

    revenue = [to_float(row["revenue"]) for row in history]
    ebitda = [to_float(row["ebitda"]) for row in history]
    pat = [to_float(row["pat"]) for row in history]
    roce = [to_float(row["roce"]) for row in history]
    capex = [to_float(row["capex"]) for row in history]
    employee_cost = [to_float(row["employee_cost"]) for row in history]
    total_assets = [to_float(row["total_assets"]) for row in history]
    pe = [to_float(row["pe"]) for row in history]
    ev_ebitda = [to_float(row["ev_ebitda"]) for row in history]
    pb = [to_float(row["pb"]) for row in history]
    debt_equity = [to_float(row["debt_equity"]) for row in history]

    ebitda_margin = [ratio(e, r) for e, r in zip(ebitda, revenue)]
    pat_margin = [ratio(p, r) for p, r in zip(pat, revenue)]
    asset_turnover = [ratio(r, a) for r, a in zip(revenue, total_assets)]
    capex_intensity = [ratio(c, r) for c, r in zip(capex, revenue)]
    employee_cost_pct = [ratio(e, r) for e, r in zip(employee_cost, revenue)]

    revenue_yoy = yoy_growth(revenue)
    ebitda_yoy = yoy_growth(ebitda)
    pat_yoy = yoy_growth(pat)

    recent_period = min(3, year_span)
    recent_start_idx = max(0, len(history) - recent_period - 1)
    recent_year_span = years[-1] - years[recent_start_idx]

    revenue_cagr = cagr(revenue[0], revenue[-1], year_span)
    ebitda_cagr = cagr(ebitda[0], ebitda[-1], year_span)
    pat_cagr = cagr(pat[0], pat[-1], year_span)
    recent_revenue_cagr = cagr(revenue[recent_start_idx], revenue[-1], recent_year_span)
    recent_ebitda_cagr = cagr(ebitda[recent_start_idx], ebitda[-1], recent_year_span)
    recent_pat_cagr = cagr(pat[recent_start_idx], pat[-1], recent_year_span)

    latest = history[-1]
    features = {
        "company": {
            "id": company["id"],
            "ticker": company["ticker"],
            "name": company.get("name"),
            "country": company.get("country"),
            "sector": company.get("sector"),
            "industry": company.get("industry"),
        },
        "period": {
            "first_year": years[0],
            "last_year": years[-1],
            "year_span": year_span,
            "years_available": len(history),
        },
        "growth": {
            "revenue_cagr": round_or_none(revenue_cagr),
            "ebitda_cagr": round_or_none(ebitda_cagr),
            "pat_cagr": round_or_none(pat_cagr),
            "recent_revenue_cagr": round_or_none(recent_revenue_cagr),
            "recent_ebitda_cagr": round_or_none(recent_ebitda_cagr),
            "recent_pat_cagr": round_or_none(recent_pat_cagr),
            "revenue_growth_acceleration": round_or_none((recent_revenue_cagr - revenue_cagr) if recent_revenue_cagr is not None and revenue_cagr is not None else None),
            "ebitda_vs_revenue_cagr_spread": round_or_none((ebitda_cagr - revenue_cagr) if ebitda_cagr is not None and revenue_cagr is not None else None),
            "pat_vs_revenue_cagr_spread": round_or_none((pat_cagr - revenue_cagr) if pat_cagr is not None and revenue_cagr is not None else None),
            "revenue_yoy_avg": round_or_none(average(revenue_yoy)),
            "revenue_yoy_volatility": round_or_none(stddev(revenue_yoy)),
            "ebitda_yoy_avg": round_or_none(average(ebitda_yoy)),
            "pat_yoy_avg": round_or_none(average(pat_yoy)),
        },
        "margins": {
            "ebitda_margin_first": round_or_none(ebitda_margin[0]),
            "ebitda_margin_latest": round_or_none(ebitda_margin[-1]),
            "ebitda_margin_change": round_or_none((ebitda_margin[-1] - ebitda_margin[0]) if ebitda_margin[-1] is not None and ebitda_margin[0] is not None else None),
            "ebitda_margin_slope": round_or_none(slope(years, ebitda_margin)),
            "pat_margin_first": round_or_none(pat_margin[0]),
            "pat_margin_latest": round_or_none(pat_margin[-1]),
            "pat_margin_change": round_or_none((pat_margin[-1] - pat_margin[0]) if pat_margin[-1] is not None and pat_margin[0] is not None else None),
            "pat_margin_slope": round_or_none(slope(years, pat_margin)),
        },
        "quality": {
            "roce_first": round_or_none(roce[0]),
            "roce_latest": round_or_none(roce[-1]),
            "roce_change": round_or_none((roce[-1] - roce[0]) if roce[-1] is not None and roce[0] is not None else None),
            "roce_slope": round_or_none(slope(years, roce)),
            "asset_turnover_first": round_or_none(asset_turnover[0]),
            "asset_turnover_latest": round_or_none(asset_turnover[-1]),
            "asset_turnover_change": round_or_none((asset_turnover[-1] - asset_turnover[0]) if asset_turnover[-1] is not None and asset_turnover[0] is not None else None),
            "asset_turnover_slope": round_or_none(slope(years, asset_turnover)),
        },
        "operating_leverage": {
            "employee_cost_pct_first": round_or_none(employee_cost_pct[0]),
            "employee_cost_pct_latest": round_or_none(employee_cost_pct[-1]),
            "employee_cost_pct_change": round_or_none((employee_cost_pct[-1] - employee_cost_pct[0]) if employee_cost_pct[-1] is not None and employee_cost_pct[0] is not None else None),
            "employee_cost_pct_slope": round_or_none(slope(years, employee_cost_pct)),
            "capex_intensity_first": round_or_none(capex_intensity[0]),
            "capex_intensity_latest": round_or_none(capex_intensity[-1]),
            "capex_intensity_change": round_or_none((capex_intensity[-1] - capex_intensity[0]) if capex_intensity[-1] is not None and capex_intensity[0] is not None else None),
            "capex_intensity_slope": round_or_none(slope(years, capex_intensity)),
        },
        "valuation": {
            "pe_latest": round_or_none(pe[-1]),
            "ev_ebitda_latest": round_or_none(ev_ebitda[-1]),
            "pb_latest": round_or_none(pb[-1]),
            "pe_slope": round_or_none(slope(years, pe)),
            "ev_ebitda_slope": round_or_none(slope(years, ev_ebitda)),
        },
        "risk": {
            "debt_equity_latest": round_or_none(debt_equity[-1]),
            "debt_equity_slope": round_or_none(slope(years, debt_equity)),
            "revenue_volatility": round_or_none(stddev(revenue_yoy)),
            "earnings_volatility": round_or_none(stddev(pat_yoy)),
        },
        "series": [
            {
                "fiscal_year": int(row["fiscal_year"]),
                "revenue": round_or_none(to_float(row["revenue"])),
                "ebitda": round_or_none(to_float(row["ebitda"])),
                "pat": round_or_none(to_float(row["pat"])),
                "roce": round_or_none(to_float(row["roce"])),
                "ebitda_margin": round_or_none(ebitda_margin[idx]),
                "pat_margin": round_or_none(pat_margin[idx]),
                "asset_turnover": round_or_none(asset_turnover[idx]),
                "capex_intensity": round_or_none(capex_intensity[idx]),
                "employee_cost_pct": round_or_none(employee_cost_pct[idx]),
                "pe": round_or_none(pe[idx]),
                "ev_ebitda": round_or_none(ev_ebitda[idx]),
                "debt_equity": round_or_none(debt_equity[idx]),
            }
            for idx, row in enumerate(history)
        ],
        "generated_at": str(date.today()),
    }

    features["feature_hash"] = canonical_hash(features)
    return features, None


def persist_feature_snapshot(cur, company_id: int, run_id: str, features: dict[str, Any]) -> str:
    from psycopg2.extras import Json

    cur.execute(
        """
        INSERT INTO public.prde_feature_snapshots (
            company_id, run_id, feature_hash, features, created_at
        )
        VALUES (%s, %s, %s, %s, NOW())
        ON CONFLICT (company_id, feature_hash) DO UPDATE SET
            features = EXCLUDED.features
        RETURNING id
        """,
        (company_id, run_id, features["feature_hash"], Json(features)),
    )
    return str(cur.fetchone()["id"])


def generate_feature_snapshots(
    *,
    symbol: str | None = None,
    limit: int | None = None,
    min_years: int = 5,
    dry_run: bool = False,
) -> dict[str, Any]:
    from api.schema import ensure_prde_tables
    from engine_core.db import get_connection

    conn = get_connection()
    run_id = str(uuid4())
    generated: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []

    try:
        with conn.cursor() as cur:
            ensure_prde_tables(cur)
            companies = fetch_companies(cur, symbol, limit)
            for company in companies:
                history = fetch_company_history(cur, company["id"])
                features, skip_reason = build_features(company, history, min_years)
                if skip_reason:
                    skipped.append({"ticker": company["ticker"], "reason": skip_reason})
                    continue

                snapshot_id = None
                if not dry_run and features is not None:
                    snapshot_id = persist_feature_snapshot(cur, company["id"], run_id, features)

                generated.append(
                    {
                        "ticker": company["ticker"],
                        "snapshot_id": snapshot_id,
                        "feature_hash": features["feature_hash"] if features else None,
                        "years_available": features["period"]["years_available"] if features else 0,
                    }
                )

            if dry_run:
                conn.rollback()
            else:
                conn.commit()

        return {
            "run_id": run_id,
            "dry_run": dry_run,
            "companies_seen": len(companies),
            "generated": generated,
            "skipped": skipped,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate PRDE deterministic feature snapshots")
    parser.add_argument("--symbol", help="Generate features for one ticker")
    parser.add_argument("--limit", type=int, help="Maximum companies to process")
    parser.add_argument("--min-years", type=int, default=5, help="Minimum annual rows required per company")
    parser.add_argument("--dry-run", action="store_true", help="Compute features without writing snapshots")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        result = generate_feature_snapshots(
            symbol=args.symbol,
            limit=args.limit,
            min_years=args.min_years,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        logger.error("PRDE feature generation failed: %s", exc)
        return 1

    print(json.dumps(result, indent=2, default=str))
    if not result["generated"]:
        logger.warning("No PRDE feature snapshots generated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
