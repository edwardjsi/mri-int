#!/usr/bin/env python3
"""Fetch annual financials from yfinance for Indian blue-chip companies.

Outputs a CSV seed file for PRDE import with columns:
  ticker, name, sector, industry, fiscal_year,
  revenue, ebitda, pat, roce, capex, employee_cost, total_assets,
  pe, ev_ebitda, pb, debt_equity

Usage:
    python scripts/fetch_prde_seed_data.py --companies 15 --output data/prde_financials_seed.csv
    python scripts/fetch_prde_seed_data.py --tickers RELIANCE,TCS,HDFCBANK --output data/my_seed.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

import yfinance as yf

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("fetch_prde_seed")

# Top Indian blue-chips with sector classification
DEFAULT_UNIVERSE: list[dict[str, str]] = [
    {"ticker": "TCS.NS",        "name": "Tata Consultancy Services", "sector": "IT",          "industry": "IT Services"},
    {"ticker": "INFY.NS",       "name": "Infosys",                   "sector": "IT",          "industry": "IT Services"},
    {"ticker": "WIPRO.NS",      "name": "Wipro",                     "sector": "IT",          "industry": "IT Services"},
    {"ticker": "HCLTECH.NS",    "name": "HCL Technologies",          "sector": "IT",          "industry": "IT Services"},
    {"ticker": "HDFCBANK.NS",   "name": "HDFC Bank",                 "sector": "BANKS",       "industry": "Private Bank"},
    {"ticker": "ICICIBANK.NS",  "name": "ICICI Bank",                "sector": "BANKS",       "industry": "Private Bank"},
    {"ticker": "SBIN.NS",       "name": "State Bank of India",       "sector": "BANKS",       "industry": "Public Bank"},
    {"ticker": "BAJFINANCE.NS", "name": "Bajaj Finance",             "sector": "NBFC",        "industry": "NBFC"},
    {"ticker": "RELIANCE.NS",   "name": "Reliance Industries",       "sector": "CONGLOMERATE","industry": "Diversified"},
    {"ticker": "HINDUNILVR.NS", "name": "Hindustan Unilever",        "sector": "CONSUMER",    "industry": "FMCG"},
    {"ticker": "NESTLEIND.NS",  "name": "Nestle India",              "sector": "CONSUMER",    "industry": "FMCG"},
    {"ticker": "MARUTI.NS",     "name": "Maruti Suzuki",             "sector": "AUTO",        "industry": "Passenger Vehicles"},
    {"ticker": "TATAMOTORS.NS", "name": "Tata Motors",               "sector": "AUTO",        "industry": "Auto Manufacturer"},
    {"ticker": "SUNPHARMA.NS",  "name": "Sun Pharmaceutical",        "sector": "PHARMA",      "industry": "Pharmaceuticals"},
    {"ticker": "DIVISLAB.NS",   "name": "Divi's Laboratories",       "sector": "PHARMA",      "industry": "Pharmaceuticals"},
    {"ticker": "HINDZINC.NS",   "name": "Hindustan Zinc",            "sector": "METALS",      "industry": "Non-Ferrous Metals"},
    {"ticker": "JSWSTEEL.NS",   "name": "JSW Steel",                 "sector": "METALS",      "industry": "Steel"},
    {"ticker": "ULTRACEMCO.NS", "name": "UltraTech Cement",          "sector": "CEMENT",      "industry": "Cement"},
    {"ticker": "POWERGRID.NS",  "name": "Power Grid Corporation",    "sector": "POWER",       "industry": "Power Transmission"},
    {"ticker": "NTPC.NS",       "name": "NTPC",                      "sector": "POWER",       "industry": "Power Generation"},
]


def safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        if f != f:
            return None
        return f
    except (TypeError, ValueError):
        return None


def fetch_company_financials(ticker: str, name: str, sector: str, industry: str, min_years: int = 5) -> list[dict]:
    logger.info(f"Fetching {ticker} ({name})...")
    stock = yf.Ticker(ticker)

    try:
        income = stock.financials
    except Exception as e:
        logger.warning(f"  {ticker}: income statement fetch failed: {e}")
        return []

    if income is None or income.empty:
        logger.warning(f"  {ticker}: no income statement data")
        return []

    try:
        balance = stock.balance_sheet
    except Exception:
        balance = None

    try:
        cashflow = stock.cashflow
    except Exception:
        cashflow = None

    try:
        info = stock.info
    except Exception:
        info = {}

    def get_row(df, row_names: list[str], fiscal_year) -> float | None:
        if df is None or df.empty:
            return None
        for rn in row_names:
            if rn in df.index:
                val = df.loc[rn, fiscal_year] if fiscal_year in df.columns else None
                if val is not None:
                    return safe_float(val)
        return None

    years = [col for col in income.columns if isinstance(col, (int, float)) or str(col).isdigit()]
    years = sorted([int(y) for y in years if str(y).isdigit()])

    if len(years) < min_years:
        logger.warning(f"  {ticker}: only {len(years)} years available, need {min_years}")

    rows = []
    for fy in years:
        revenue = get_row(income, ["Total Revenue", "Revenue", "TotalRevenue"], fy)
        ebitda  = get_row(income, ["EBITDA", "Ebitda", "Normalized EBITDA"], fy)
        pat     = get_row(income, ["Net Income", "NetIncome", "Net Income Common Stockholders"], fy)
        ebit    = get_row(income, ["EBIT", "Ebit", "Operating Income", "OperatingIncome"], fy)

        if ebitda is None and ebit is not None:
            da = get_row(income, ["Reconciled Depreciation", "Depreciation & Amortization", "DepreciationAndAmortization"], fy)
            if da is not None:
                ebitda = ebit + da

        capex         = get_row(cashflow, ["Capital Expenditure", "CapitalExpenditure", "Capital Expenditures"], fy)
        total_assets  = get_row(balance, ["Total Assets", "TotalAssets"], fy)
        curr_liab     = get_row(balance, ["Current Liabilities", "CurrentLiabilities"], fy)

        roce = None
        if ebit is not None and total_assets is not None and curr_liab is not None:
            capital_employed = total_assets - curr_liab
            if capital_employed > 0:
                roce = round(ebit / capital_employed, 6)

        employee_cost = get_row(income, ["Salaries And Wages", "Employee benefit expenses", "EmployeeBenefitsExpense"], fy)

        pe         = safe_float(info.get("trailingPE") or info.get("forwardPE"))
        ev_ebitda  = safe_float(info.get("enterpriseToEbitda"))
        pb         = safe_float(info.get("priceToBook"))
        debt_equity = safe_float(info.get("debtToEquity"))

        rows.append({
            "ticker":        ticker.replace(".NS", "").replace(".BO", ""),
            "name":          name,
            "sector":        sector,
            "industry":      industry,
            "fiscal_year":   fy,
            "revenue":       revenue,
            "ebitda":        ebitda,
            "pat":           pat,
            "roce":          roce,
            "capex":         capex,
            "employee_cost": employee_cost,
            "total_assets":  total_assets,
            "pe":            pe,
            "ev_ebitda":     ev_ebitda,
            "pb":            pb,
            "debt_equity":   debt_equity,
        })

    logger.info(f"  {ticker}: {len(rows)} years ({years[0]}–{years[-1]})")
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch PRDE seed financial data from yfinance")
    parser.add_argument("--tickers", help="Comma-separated tickers (e.g. RELIANCE,TCS)")
    parser.add_argument("--companies", type=int, default=15, help="Number of companies from default universe")
    parser.add_argument("--output", default="data/prde_financials_seed.csv", help="Output CSV path")
    parser.add_argument("--min-years", type=int, default=5, help="Minimum fiscal years required")
    args = parser.parse_args(argv or sys.argv[1:])

    if args.tickers:
        custom_tickers = [t.strip() + (".NS" if not (".NS" in t or ".BO" in t) else "") for t in args.tickers.split(",")]
        universe = [{"ticker": t, "name": t, "sector": "UNKNOWN", "industry": "UNKNOWN"} for t in custom_tickers]
    else:
        universe = DEFAULT_UNIVERSE[:args.companies]

    all_rows = []
    for company in universe:
        rows = fetch_company_financials(
            company["ticker"], company["name"],
            company["sector"], company["industry"],
            min_years=args.min_years,
        )
        all_rows.extend(rows)

    if not all_rows:
        logger.error("No data fetched for any company.")
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "ticker", "name", "sector", "industry", "fiscal_year",
        "revenue", "ebitda", "pat", "roce", "capex", "employee_cost", "total_assets",
        "pe", "ev_ebitda", "pb", "debt_equity",
    ]

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    companies_found = len(set(r["ticker"] for r in all_rows))
    logger.info(f"Wrote {len(all_rows)} rows for {companies_found} companies to {output_path}")

    print(f"\n{'Ticker':<12} {'Company':<28} {'Years':>6}  {'Rev Range':>24}")
    print("-" * 75)
    for ticker in sorted(set(r["ticker"] for r in all_rows)):
        co_rows = [r for r in all_rows if r["ticker"] == ticker]
        years_span = f"{min(r['fiscal_year'] for r in co_rows)}–{max(r['fiscal_year'] for r in co_rows)}"
        revs = [r["revenue"] for r in co_rows if r["revenue"] is not None]
        rev_range = f"{min(revs):,.0f} – {max(revs):,.0f}" if revs else "N/A"
        name = co_rows[0]["name"][:28]
        print(f"{ticker:<12} {name:<28} {years_span:>6}  {rev_range:>24}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
