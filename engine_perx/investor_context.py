from __future__ import annotations

from typing import Any
import logging

logger = logging.getLogger(__name__)

def safe_float(v) -> float:
    if v is None:
        return 0.0
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def _compute_pe_percentile(current_pe: float, historical_prices: list[dict], financials_by_year: dict) -> float | None:
    """
    Estimate where current P/E sits relative to 5-year history.
    Uses yearly net_profit and close price approximations.
    """
    if current_pe <= 0 or len(historical_prices) < 5:
        return None

    # Build approximate trailing PE for each year in history
    yearly_pes = []
    for row in historical_prices:
        year = row.get("year")
        if year and year in financials_by_year:
            eps = financials_by_year[year]
            if eps and eps > 0:
                yearly_pes.append(safe_float(row.get("close")) / eps)

    if len(yearly_pes) < 3:
        return None

    yearly_pes.sort()
    count_below = sum(1 for p in yearly_pes if p <= current_pe)
    percentile = (count_below / len(yearly_pes)) * 100
    return round(percentile, 1)


def get_valuation_context(cur, base_symbol: str, current_price: float | None = None) -> dict[str, Any]:
    """
    Calculate P/E ratio, sector peer comparison, and historical percentile.
    
    Queries:
      - aae_quarterly_financials for TTM EPS
      - aae_sector_mapping + aae_quarterly_financials for sector median P/E
      - daily_prices for historical close (5-year proxy)
      - fundamental_financials for yearly EPS proxy
    """
    result: dict[str, Any] = {
        "pe_ratio": None,
        "sector_median_pe": None,
        "pe_percentile_vs_history": None,
        "verdict": "Insufficient data for valuation context.",
    }

    # 1. Get TTM EPS from quarterly financials
    cur.execute(
        """
        SELECT eps, year, quarter
        FROM aae_quarterly_financials
        WHERE symbol = %s AND eps IS NOT NULL AND eps > 0
        ORDER BY year DESC, quarter DESC
        LIMIT 4
        """,
        (base_symbol,),
    )
    quarterly_rows = cur.fetchall()
    ttm_eps = None
    if quarterly_rows and len(quarterly_rows) >= 1:
        ttm_eps = sum(safe_float(r.get("eps") if isinstance(r, dict) else r[1]) for r in quarterly_rows)

    # Fallback: try fundamental_financials for yearly EPS
    if not ttm_eps or ttm_eps <= 0:
        cur.execute(
            """
            SELECT year, net_profit, equity
            FROM fundamental_financials
            WHERE symbol = %s AND net_profit IS NOT NULL AND equity IS NOT NULL AND equity > 0
            ORDER BY year DESC
            LIMIT 2
            """,
            (base_symbol,),
        )
        yearly_rows = cur.fetchall()
        if yearly_rows:
            latest = yearly_rows[0]
            net_profit = safe_float(latest.get("net_profit") if isinstance(latest, dict) else latest[1])
            equity = safe_float(latest.get("equity") if isinstance(latest, dict) else latest[2])
            if equity > 0 and net_profit != 0:
                # Approximate: ROE -> EPS proxy using book value per share
                # We use net_profit/equity as a rough earnings power indicator
                ttm_eps = net_profit / equity * 10  # rough scalar

    price = current_price
    if price is None:
        cur.execute(
            "SELECT close FROM daily_prices WHERE symbol = %s ORDER BY date DESC LIMIT 1",
            (base_symbol,),
        )
        row = cur.fetchone()
        if row:
            price = safe_float(row.get("close") if isinstance(row, dict) else row[0])

    if price and ttm_eps and ttm_eps > 0:
        pe = safe_float(price) / safe_float(ttm_eps)
        result["pe_ratio"] = round(pe, 2)

        # 2. Sector median P/E via aae_sector_mapping
        cur.execute(
            "SELECT sector_id FROM aae_sector_mapping WHERE symbol = %s",
            (base_symbol,),
        )
        mapping_row = cur.fetchone()
        if mapping_row:
            sector_id = mapping_row.get("sector_id") if isinstance(mapping_row, dict) else mapping_row[0]
            cur.execute(
                """
                WITH latest_prices AS (
                    SELECT symbol, close
                    FROM daily_prices
                    WHERE date = (SELECT MAX(date) FROM daily_prices)
                ),
                ttm_eps AS (
                    SELECT q.symbol, SUM(q.eps) as total_eps
                    FROM aae_quarterly_financials q
                    WHERE q.eps IS NOT NULL AND q.eps > 0
                    GROUP BY q.symbol
                    HAVING SUM(q.eps) > 0
                )
                SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY (p.close / e.total_eps)) as median_pe
                FROM aae_sector_mapping m
                JOIN latest_prices p ON m.symbol = p.symbol
                JOIN ttm_eps e ON m.symbol = e.symbol
                WHERE m.sector_id = %s
                """,
                (sector_id,),
            )
            median_row = cur.fetchone()
            if median_row:
                median_pe = median_row.get("median_pe") if isinstance(median_row, dict) else median_row[0]
                if median_pe and safe_float(median_pe) > 0:
                    result["sector_median_pe"] = round(safe_float(median_pe), 2)

        # 3. Historical PE percentile (5-year proxy using yearly financials)
        cur.execute(
            """
            SELECT EXTRACT(YEAR FROM date) as year, close
            FROM daily_prices
            WHERE symbol = %s
            ORDER BY date DESC
            LIMIT 1260
            """,
            (base_symbol,),
        )
        hist_rows = cur.fetchall()
        if hist_rows:
            # Build a yearly snapshot from daily data
            yearly_close: dict[int, float] = {}
            for r in hist_rows:
                r_dict = r if isinstance(r, dict) else {"year": None, "close": r[1]}
                yr = r_dict.get("year")
                if yr is None:
                    continue
                yr_val = int(yr) if yr else None
                if yr_val and (yr_val not in yearly_close):
                    yearly_close[yr_val] = safe_float(r_dict.get("close"))

            # Fetch yearly net_profit
            cur.execute(
                """
                SELECT year, net_profit
                FROM fundamental_financials
                WHERE symbol = %s AND net_profit IS NOT NULL
                ORDER BY year DESC
                LIMIT 5
                """,
                (base_symbol,),
            )
            profit_rows = cur.fetchall()
            profits_by_year: dict[int, float] = {}
            for r in profit_rows:
                r_dict = r if isinstance(r, dict) else {"year": r[0], "net_profit": r[1]}
                yr = int(r_dict.get("year", 0)) if r_dict.get("year") else 0
                if yr:
                    profits_by_year[yr] = safe_float(r_dict.get("net_profit"))

            if yearly_close and profits_by_year:
                yearly_pes_list = []
                for yr, close_price in yearly_close.items():
                    np_val = profits_by_year.get(yr)
                    if np_val and np_val > 0:
                        yearly_pes_list.append(safe_float(close_price) / safe_float(np_val))

                if yearly_pes_list:
                    yearly_pes_list.sort()
                    count_below = sum(1 for p in yearly_pes_list if p <= pe)
                    percentile = (count_below / len(yearly_pes_list)) * 100
                    result["pe_percentile_vs_history"] = round(percentile, 1)

        # 4. Build verdict
        verdict_parts = []
        pe_val = result["pe_ratio"]
        median_val = result["sector_median_pe"]
        pct_val = result.get("pe_percentile_vs_history")

        if median_val and pe_val:
            if pe_val < median_val * 0.85:
                verdict_parts.append(f"undervalued vs sector (PE {pe_val}x vs median {median_val}x)")
            elif pe_val > median_val * 1.3:
                verdict_parts.append(f"premium to sector (PE {pe_val}x vs median {median_val}x)")
            else:
                verdict_parts.append(f"in line with sector (PE {pe_val}x vs median {median_val}x)")

        if pct_val is not None:
            if pct_val <= 30:
                verdict_parts.append("near low end of 5-year range")
            elif pct_val >= 80:
                verdict_parts.append("near high end of 5-year range")
            else:
                verdict_parts.append("mid-range vs own history")

        if not verdict_parts:
            if pe_val:
                verdict_parts.append(f"trading at PE {pe_val}x — insufficient historical data for deeper context")

        result["verdict"] = " | ".join(verdict_parts) if verdict_parts else "Limited valuation context available."

    return result


def get_earnings_momentum(cur, base_symbol: str) -> dict[str, Any]:
    """
    Calculate revenue and profit growth trends over last 4 quarters.
    
    Detects acceleration/deceleration patterns.
    """
    result: dict[str, Any] = {
        "revenue_growth_4q_pct": None,
        "profit_growth_4q_pct": None,
        "acceleration": "INSUFFICIENT_DATA",
        "verdict": "Insufficient quarterly data for earnings momentum analysis.",
    }

    cur.execute(
        """
        SELECT year, quarter, revenue, net_profit
        FROM aae_quarterly_financials
        WHERE symbol = %s AND revenue IS NOT NULL
        ORDER BY year DESC, quarter DESC
        LIMIT 5
        """,
        (base_symbol,),
    )
    rows = cur.fetchall()
    if len(rows) < 4:
        # Fallback to yearly data
        cur.execute(
            """
            SELECT year, revenue, net_profit
            FROM fundamental_financials
            WHERE symbol = %s AND revenue IS NOT NULL
            ORDER BY year DESC
            LIMIT 3
            """,
            (base_symbol,),
        )
        yearly_rows = cur.fetchall()
        if len(yearly_rows) >= 2:
            latest_yr = yearly_rows[0]
            prev_yr = yearly_rows[1]
            latest_rev = safe_float(latest_yr.get("revenue") if isinstance(latest_yr, dict) else latest_yr[1])
            prev_rev = safe_float(prev_yr.get("revenue") if isinstance(prev_yr, dict) else prev_yr[1])
            latest_profit = safe_float(latest_yr.get("net_profit") if isinstance(latest_yr, dict) else latest_yr[2]) if len(latest_yr) > 2 else None
            prev_profit = safe_float(prev_yr.get("net_profit") if isinstance(prev_yr, dict) else prev_yr[2]) if len(prev_yr) > 2 else None

            if prev_rev > 0:
                result["revenue_growth_4q_pct"] = round(((latest_rev - prev_rev) / prev_rev) * 100, 1)
            if prev_profit and prev_profit > 0 and latest_profit is not None:
                result["profit_growth_4q_pct"] = round(((latest_profit - prev_profit) / prev_profit) * 100, 1)

            if result["revenue_growth_4q_pct"] is not None:
                result["acceleration"] = "STABLE" if result["revenue_growth_4q_pct"] > 0 else "DECELERATING"
                verdict = f"Revenue growth {result['revenue_growth_4q_pct']:.1f}% YoY (annual). "
                if result["profit_growth_4q_pct"] is not None:
                    verdict += f"Profit growth {result['profit_growth_4q_pct']:.1f}% YoY. "
                result["verdict"] = verdict

        return result

    # Process quarterly data (we have 4+ quarters)
    parsed = []
    for r in rows:
        r_dict = r if isinstance(r, dict) else {"year": r[0], "quarter": r[1], "revenue": r[2], "net_profit": r[3] if len(r) > 3 else None}
        parsed.append({
            "year": int(r_dict.get("year", 0)),
            "quarter": int(r_dict.get("quarter", 0)),
            "revenue": safe_float(r_dict.get("revenue")),
            "net_profit": safe_float(r_dict.get("net_profit")),
        })

    # Use the most recent 4 quarters, ordered chronologically
    parsed.sort(key=lambda x: (x["year"], x["quarter"]))
    last_4 = parsed[-4:]

    if len(last_4) == 4:
        q1, q2, q3, q4 = last_4

        # Revenue acceleration: compare H2 vs H1
        h1_rev = q1["revenue"] + q2["revenue"]
        h2_rev = q3["revenue"] + q4["revenue"]
        if h1_rev > 0:
            rev_growth_h1_h2 = ((h2_rev - h1_rev) / h1_rev) * 100
            result["revenue_growth_4q_pct"] = round(rev_growth_h1_h2, 1)

        # Profit growth
        h1_profit = q1["net_profit"] + q2["net_profit"]
        h2_profit = q3["net_profit"] + q4["net_profit"]
        if h1_profit > 0:
            profit_growth = ((h2_profit - h1_profit) / h1_profit) * 100
            result["profit_growth_4q_pct"] = round(profit_growth, 1)

        # Acceleration detection: are later quarters growing faster?
        qoq_growths = []
        for i in range(1, 4):
            if last_4[i - 1]["revenue"] > 0:
                qoq = ((last_4[i]["revenue"] - last_4[i - 1]["revenue"]) / last_4[i - 1]["revenue"]) * 100
                qoq_growths.append(qoq)

        if len(qoq_growths) >= 2:
            trend = qoq_growths[-1] - qoq_growths[0]
            if trend > 5:
                result["acceleration"] = "ACCELERATING"
            elif trend < -5:
                result["acceleration"] = "DECELERATING"
            else:
                result["acceleration"] = "STABLE"

        # Build verdict
        verdict_parts = []
        if result["revenue_growth_4q_pct"] is not None:
            verdict_parts.append(f"Revenue growth {result['revenue_growth_4q_pct']:.1f}% (H2 vs H1)")
        if result["profit_growth_4q_pct"] is not None:
            verdict_parts.append(f"Profit growth {result['profit_growth_4q_pct']:.1f}%")
        if result["acceleration"] != "INSUFFICIENT_DATA":
            verdict_parts.append(f"Momentum: {result['acceleration']}")

        result["verdict"] = " | ".join(verdict_parts) if verdict_parts else "Earnings momentum data available but inconclusive."

    return result


def get_ownership_signals(cur, base_symbol: str) -> dict[str, Any]:
    """
    Analyze promoter holding trends and governance score from aae_governance_metrics.
    """
    result: dict[str, Any] = {
        "promoter_trend": "UNKNOWN",
        "governance_score": None,
        "pledged_pct": None,
        "verdict": "No ownership data available for this symbol.",
    }

    cur.execute(
        """
        SELECT fiscal_year, fiscal_quarter, promoter_holding_pct, pledged_shares_pct, governance_score
        FROM aae_governance_metrics
        WHERE symbol = %s
        ORDER BY fiscal_year DESC, fiscal_quarter DESC
        LIMIT 4
        """,
        (base_symbol,),
    )
    rows = cur.fetchall()
    if not rows:
        return result

    parsed = []
    for r in rows:
        r_dict = r if isinstance(r, dict) else {
            "fiscal_year": r[0], "fiscal_quarter": r[1],
            "promoter_holding_pct": r[2] if len(r) > 2 else None,
            "pledged_shares_pct": r[3] if len(r) > 3 else None,
            "governance_score": r[4] if len(r) > 4 else None,
        }
        parsed.append({
            "year": int(r_dict.get("fiscal_year", 0)),
            "quarter": int(r_dict.get("fiscal_quarter", 0)),
            "promoter_pct": safe_float(r_dict.get("promoter_holding_pct")),
            "pledged_pct": safe_float(r_dict.get("pledged_shares_pct")),
            "gov_score": safe_float(r_dict.get("governance_score")),
        })

    latest = parsed[0]
    result["governance_score"] = latest["gov_score"] if latest["gov_score"] > 0 else None
    result["pledged_pct"] = latest["pledged_pct"] if latest["pledged_pct"] > 0 else None

    if len(parsed) >= 2:
        prev = parsed[1]
        promoter_diff = latest["promoter_pct"] - prev["promoter_pct"]
        if promoter_diff > 1.0:
            result["promoter_trend"] = "BUYING"
        elif promoter_diff < -1.0:
            result["promoter_trend"] = "SELLING"
        else:
            result["promoter_trend"] = "STABLE"

        verdict_parts = []
        gov = result["governance_score"]
        if gov is not None:
            verdict_parts.append(f"Governance score {gov:.0f}/100")
        if result["promoter_trend"] != "UNKNOWN":
            verdict_parts.append(f"Promoter {result['promoter_trend']}")
        if result["pledged_pct"] and result["pledged_pct"] > 0:
            pledge_warn = " ⚠️ HIGH PLEDGE" if result["pledged_pct"] > 25 else ""
            verdict_parts.append(f"Pledged {result['pledged_pct']:.1f}%{pledge_warn}")

        result["verdict"] = " | ".join(verdict_parts) if verdict_parts else "Ownership data available."
    else:
        if result["governance_score"] is not None:
            result["verdict"] = f"Governance score {result['governance_score']:.0f}/100 — only one data point, trend pending."

    return result


def get_liquidity_profile(cur, base_symbol: str) -> dict[str, Any]:
    """
    Calculate average daily turnover and position-building feasibility.
    """
    result: dict[str, Any] = {
        "avg_daily_turnover_cr": None,
        "days_to_build_50lac_position": None,
        "verdict": "Insufficient liquidity data.",
    }

    # Get average daily traded value (close * volume) over last 20 days
    cur.execute(
        """
        SELECT close, volume
        FROM daily_prices
        WHERE symbol = %s
        ORDER BY date DESC
        LIMIT 20
        """,
        (base_symbol,),
    )
    rows = cur.fetchall()
    if not rows:
        return result

    daily_turnovers = []
    for r in rows:
        r_dict = r if isinstance(r, dict) else {"close": r[0], "volume": r[1]}
        close = safe_float(r_dict.get("close"))
        volume = safe_float(r_dict.get("volume"))
        if close > 0 and volume > 0:
            # Turnover in crores (1 Cr = 10^7)
            daily_turnovers.append((close * volume) / 10_000_000)

    if daily_turnovers:
        avg_turnover = sum(daily_turnovers) / len(daily_turnovers)
        result["avg_daily_turnover_cr"] = round(avg_turnover, 2)

        # How many days to build a ₹50 Lakh position (0.5 Cr) without exceeding 5% of daily volume
        if avg_turnover > 0:
            days = 0.5 / (avg_turnover * 0.05)  # 5% of daily turnover assumption
            result["days_to_build_50lac_position"] = round(days, 2)

        # Verdict
        if avg_turnover >= 50:
            result["verdict"] = f"Highly liquid (~₹{avg_turnover:.0f}Cr daily) — institutional grade."
        elif avg_turnover >= 10:
            result["verdict"] = f"Adequately liquid (~₹{avg_turnover:.0f}Cr daily) — suitable for most positions."
        elif avg_turnover >= 1:
            result["verdict"] = f"Moderate liquidity (~₹{avg_turnover:.1f}Cr daily) — position size carefully."
        else:
            result["verdict"] = f"Thin liquidity (~₹{avg_turnover:.2f}Cr daily) — significant impact on entry/exit."

    return result


def compute_investor_grade(
    valuation: dict[str, Any],
    earnings: dict[str, Any],
    ownership: dict[str, Any],
    liquidity: dict[str, Any],
) -> dict[str, Any]:
    """
    Compute an overall "Investor Grade" (A/B/C) based on the four context pillars.
    
    A = All clear or minor concerns in at most one area
    B = Notable concern in one area, or minor concerns in two
    C = Major red flag in any area, or concerns in three+ areas
    """
    flags: list[str] = []
    warnings: list[str] = []
    critical: list[str] = []

    # Valuation flags
    pe = valuation.get("pe_ratio")
    median = valuation.get("sector_median_pe")
    pct = valuation.get("pe_percentile_vs_history")

    if pe and median:
        if pe > median * 1.5:
            critical.append(f"PE {pe}x is 50%+ above sector median {median}x")
        elif pe > median * 1.3:
            warnings.append(f"PE {pe}x at premium to sector median {median}x")

    if pct is not None:
        if pct >= 90:
            critical.append(f"PE near all-time high vs 5-year history (>{pct:.0f}th percentile)")
        elif pct >= 80:
            warnings.append(f"PE elevated vs 5-year history ({pct:.0f}th percentile)")

    # Earnings flags
    rev_growth = earnings.get("revenue_growth_4q_pct")
    profit_growth = earnings.get("profit_growth_4q_pct")
    accel = earnings.get("acceleration")

    if accel == "DECELERATING":
        warnings.append("Revenue momentum decelerating")
    elif accel == "INSUFFICIENT_DATA":
        warnings.append("Limited earnings history for trend analysis")

    if profit_growth is not None and profit_growth < 0:
        critical.append(f"Profits declining ({profit_growth:.1f}%)")

    # Ownership flags
    promoter_trend = ownership.get("promoter_trend")
    pledged = ownership.get("pledged_pct")

    if promoter_trend == "SELLING":
        warnings.append("Promoters reducing stake")
    if pledged and pledged > 25:
        critical.append(f"High promoter pledge ({pledged:.0f}%)")
    elif pledged and pledged > 15:
        warnings.append(f"Notable promoter pledge ({pledged:.0f}%)")

    # Liquidity flags
    avg_turnover = liquidity.get("avg_daily_turnover_cr")
    if avg_turnover is not None and avg_turnover < 1:
        warnings.append(f"Low liquidity (₹{avg_turnover:.1f}Cr daily)")
    elif avg_turnover is not None and avg_turnover < 0.1:
        critical.append("Very thin liquidity — execution risk")

    # Compute grade
    if critical:
        grade = "C"
    elif len(warnings) >= 2:
        grade = "C"
    elif warnings:
        grade = "B"
    else:
        grade = "A"

    # Build summary
    summary_lines = []
    if grade == "A":
        summary_lines.append("🟢 Investor Grade A — All clear. Valuation reasonable, earnings trending well, and no ownership or liquidity concerns.")
    elif grade == "B":
        summary_lines.append(f"🟡 Investor Grade B — Minor caution. {warnings[0]}{' (' + warnings[1] + ')' if len(warnings) > 1 else ''}.")
    else:
        issues = critical + warnings
        summary_lines.append(f"🔴 Investor Grade C — Thesis needs scrutiny.")
        for issue in issues[:3]:
            summary_lines.append(f"  • {issue}")

    return {
        "grade": grade,
        "flags": flags,
        "warnings": warnings,
        "critical_issues": critical,
        "summary": "\n".join(summary_lines),
    }




def get_peg_ratio(cur, base_symbol: str, current_pe: float | None = None) -> dict[str, Any]:
    """
    Calculate PEG ratio = P/E ÷ EPS growth rate.
    
    Uses trailing 8 quarters of EPS data from aae_quarterly_financials
    to compute trailing 12-month EPS growth.
    """
    result: dict[str, Any] = {
        "peg_ratio": None,
        "eps_growth_pct": None,
        "verdict": "Insufficient EPS history for PEG calculation.",
        "homework": "",
    }

    pe = current_pe
    if pe is None or pe <= 0:
        return result

    # Get trailing 8 quarters of EPS
    cur.execute(
        """
        SELECT eps, year, quarter
        FROM aae_quarterly_financials
        WHERE symbol = %s AND eps IS NOT NULL AND eps > 0
        ORDER BY year DESC, quarter DESC
        LIMIT 8
        """,
        (base_symbol,),
    )
    rows = cur.fetchall()
    if len(rows) < 8:
        return result

    # Split into latest 4 quarters (TTM) and prior 4 quarters
    # rows are already DESC, so first 4 = latest TTM, next 4 = prior TTM
    latest_ttm = sum(safe_float(r.get("eps") if isinstance(r, dict) else r[0]) for r in rows[:4])
    prior_ttm = sum(safe_float(r.get("eps") if isinstance(r, dict) else r[0]) for r in rows[4:8])

    if prior_ttm <= 0:
        return result

    eps_growth_pct = ((latest_ttm - prior_ttm) / prior_ttm) * 100
    result["eps_growth_pct"] = round(eps_growth_pct, 1)

    if eps_growth_pct > 0:
        peg = pe / (eps_growth_pct / 100)  # divide by growth rate in decimal
        result["peg_ratio"] = round(peg, 2)

        if peg < 1.0:
            result["verdict"] = f"PEG {peg:.2f}x — undervalued relative to growth (PEG < 1.0). Favorable rerating setup."
            result["homework"] = "Confirm EPS growth sustainability. Check if growth is from one-time items or recurring operations."
        elif peg < 2.0:
            result["verdict"] = f"PEG {peg:.2f}x — reasonable valuation for growth (PEG 1-2x). Rerating possible if growth accelerates."
            result["homework"] = "Watch for EPS growth acceleration in next 2 quarters — even 5% CAGR improvement could shift PEG below 1x."
        else:
            result["verdict"] = f"PEG {peg:.2f}x — premium growth valuation. Full rerating depends on growth sustaining above current trajectory."
            result["homework"] = "The current PE already prices in growth. Rerating requires GROWTH ACCELERATION, not just sustained growth."
    else:
        result["verdict"] = f"EPS declining ({eps_growth_pct:.1f}%) — PEG is undefined. Rerating thesis requires earnings turnaround first."
        result["homework"] = "What is causing the earnings decline? Is it cyclical, one-time, or structural? Look for margin stabilization before expecting rerating."

    return result


def get_ev_ebitda(cur, base_symbol: str) -> dict[str, Any]:
    """
    Calculate Enterprise Value / EBITDA proxy from fundamental_financials.
    
    Dynamically detects available columns to handle schema variations.
    Falls back gracefully when columns are missing.
    """
    result: dict[str, Any] = {
        "ev_ebitda": None,
        "market_cap_cr": None,
        "net_debt_ebitda": None,
        "verdict": "EV/EBITDA unavailable — required columns not found in fundamental_financials.",
        "homework": "",
    }

    # First, detect what columns are available in fundamental_financials
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'fundamental_financials'
          AND column_name IN ('market_cap', 'total_debt', 'cash_equivalents', 'ebitda')
        """,
    )
    available_cols = [row[0] if isinstance(row, (list, tuple)) else row.get("column_name", "") for row in cur.fetchall()]
    available_set = set(available_cols)

    if not available_set:
        return result

    # Build query dynamically based on available columns
    select_cols = ["year"]
    if "market_cap" in available_set:
        select_cols.append("market_cap")
    if "total_debt" in available_set:
        select_cols.append("total_debt")
    if "cash_equivalents" in available_set:
        select_cols.append("cash_equivalents")
    if "ebitda" in available_set:
        select_cols.append("ebitda")

    query = f"""
        SELECT {', '.join(select_cols)}
        FROM fundamental_financials
        WHERE symbol = %s
        ORDER BY year DESC
        LIMIT 1
    """
    cur.execute(query, (base_symbol,))
    row = cur.fetchone()
    if not row:
        return result

    rdict = dict(row) if isinstance(row, dict) else {col: row[i] for i, col in enumerate(select_cols)}

    market_cap = safe_float(rdict.get("market_cap"))
    total_debt = safe_float(rdict.get("total_debt"))
    cash_eq = safe_float(rdict.get("cash_equivalents"))
    ebitda = safe_float(rdict.get("ebitda"))

    # Market cap in crores (if raw value is in lakhs or raw)
    if market_cap and market_cap > 0:
        # Assume raw value might be in actual rupees — convert to crores
        if market_cap > 1_000_000_000_000:  # > 1000 Cr already? No, adjust
            market_cap_cr = round(market_cap / 10_000_000, 2)
        else:
            market_cap_cr = round(market_cap, 2)
        result["market_cap_cr"] = market_cap_cr

        if ebitda and ebitda > 0:
            # Enterprise Value = Market Cap + Total Debt - Cash
            if total_debt > 0 and cash_eq >= 0:
                ev = market_cap_cr + (total_debt / 10_000_000) - (cash_eq / 10_000_000)
            else:
                ev = market_cap_cr
                if total_debt > 0:
                    ev += total_debt / 10_000_000

            ebitda_cr = ebitda / 10_000_000 if ebitda > 100_000_000 else ebitda
            ev_ebitda_ratio = ev / ebitda_cr if ebitda_cr > 0 else None
            result["ev_ebitda"] = round(ev_ebitda_ratio, 2) if ev_ebitda_ratio else None

            # Net Debt / EBITDA
            if total_debt > 0 and cash_eq >= 0:
                net_debt_cr = (total_debt - cash_eq) / 10_000_000
                result["net_debt_ebitda"] = round(net_debt_cr / ebitda_cr, 2) if ebitda_cr > 0 else None

    # Build verdict
    ev_val = result.get("ev_ebitda")
    nd_val = result.get("net_debt_ebitda")
    verdict_parts = []

    if ev_val:
        if ev_val < 10:
            verdict_parts.append(f"EV/EBITDA {ev_val:.1f}x — reasonable (typically <12x for mid-caps)")
        elif ev_val < 20:
            verdict_parts.append(f"EV/EBITDA {ev_val:.1f}x — elevated but plausible for growth names")
        else:
            verdict_parts.append(f"EV/EBITDA {ev_val:.1f}x — premium valuation, common in high-growth sectors")

    if nd_val is not None:
        if nd_val < 0:
            verdict_parts.append("Net cash position — clean balance sheet")
        elif nd_val < 1.5:
            verdict_parts.append(f"Net debt/EBITDA {nd_val:.1f}x — low leverage")
        elif nd_val < 3:
            verdict_parts.append(f"Net debt/EBITDA {nd_val:.2f}x — moderate leverage")
        else:
            verdict_parts.append(f"Net debt/EBITDA {nd_val:.2f}x — elevated leverage, monitor")

    if verdict_parts:
        result["verdict"] = " | ".join(verdict_parts)
        result["homework"] = "EV/EBITDA is a sector-dependent metric. Compare with direct peers (not just market) for rerating potential."
    else:
        result["verdict"] = "EV/EBITDA data found but insufficient for analysis."

    return result


def get_institutional_flow(cur, base_symbol: str) -> dict[str, Any]:
    """
    Analyze FII/DII holding percentage changes from aae_governance_metrics.
    
    Tracks quarterly institutional ownership shifts to detect smart money flow.
    """
    result: dict[str, Any] = {
        "fii_holding_pct": None,
        "dii_holding_pct": None,
        "fii_change_qoq": None,
        "dii_change_qoq": None,
        "fii_trend": "UNKNOWN",
        "dii_trend": "UNKNOWN",
        "verdict": "",
        "homework": "",
    }

    cur.execute(
        """
        SELECT fiscal_year, fiscal_quarter, fii_holding_pct, dii_holding_pct
        FROM aae_governance_metrics
        WHERE symbol = %s
          AND (fii_holding_pct IS NOT NULL OR dii_holding_pct IS NOT NULL)
        ORDER BY fiscal_year DESC, fiscal_quarter DESC
        LIMIT 4
        """,
        (base_symbol,),
    )
    rows = cur.fetchall()
    if len(rows) < 2:
        result["verdict"] = "Insufficient institutional holding data for trend analysis."
        return result

    parsed = []
    for r in rows:
        r_dict = r if isinstance(r, dict) else {
            "fiscal_year": r[0], "fiscal_quarter": r[1],
            "fii": r[2] if len(r) > 2 else None,
            "dii": r[3] if len(r) > 3 else None,
        }
        parsed.append({
            "year": int(r_dict.get("fiscal_year", 0)),
            "quarter": int(r_dict.get("fiscal_quarter", 0)),
            "fii": safe_float(r_dict.get("fii")),
            "dii": safe_float(r_dict.get("dii")),
        })

    latest = parsed[0]
    prev = parsed[1]

    # Latest holdings
    if latest["fii"] > 0:
        result["fii_holding_pct"] = latest["fii"]
    if latest["dii"] > 0:
        result["dii_holding_pct"] = latest["dii"]

    # QoQ changes
    if latest["fii"] > 0 and prev["fii"] > 0:
        change = latest["fii"] - prev["fii"]
        result["fii_change_qoq"] = round(change, 2)
        result["fii_trend"] = "ADDING" if change > 0.5 else ("REDUCING" if change < -0.5 else "STABLE")

    if latest["dii"] > 0 and prev["dii"] > 0:
        change = latest["dii"] - prev["dii"]
        result["dii_change_qoq"] = round(change, 2)
        result["dii_trend"] = "ADDING" if change > 0.5 else ("REDUCING" if change < -0.5 else "STABLE")

    # Build verdict
    verdict_parts = []
    homework_parts = []

    if result["fii_trend"] == "ADDING":
        verdict_parts.append(f"FIIs adding (+{result['fii_change_qoq']:.1f}% QoQ)")
        homework_parts.append("FIIs are accumulating — confirm via latest shareholding pattern on BSE/NSE")
    elif result["fii_trend"] == "REDUCING":
        verdict_parts.append(f"FIIs reducing ({result['fii_change_qoq']:+.1f}% QoQ)")
        homework_parts.append("FIIs reducing — check if this is sector-wide or stock-specific")

    if result["dii_trend"] == "ADDING":
        verdict_parts.append(f"DIIs adding (+{result['dii_change_qoq']:.1f}% QoQ)")
        homework_parts.append("Domestic institutions are stepping in — bullish local conviction")
    elif result["dii_trend"] == "REDUCING":
        verdict_parts.append(f"DIIs reducing ({result['dii_change_qoq']:+.1f}% QoQ)")

    if result["fii_trend"] == "REDUCING" and result["dii_trend"] != "ADDING":
        verdict_parts.append("⚠️ FIIs exiting without DII buying — potential headwind")
        homework_parts.append("Critical: No domestic buyers absorbing FII exit. This creates downward price pressure.")

    result["verdict"] = " | ".join(verdict_parts) if verdict_parts else "Institutional holding data available but no clear trend."
    result["homework"] = " | ".join(homework_parts)

    return result


def get_rerating_analogs(cur, current_perx_score: float, current_lifecycle: str,
                         exclude_symbol: str | None = None) -> dict[str, Any]:
    """
    Find historical peers at same lifecycle stage and similar PERX score.
    
    Returns top 5 most recent analogs from perx_reports archive.
    """
    result: dict[str, Any] = {
        "analogs": [],
        "verdict": "No historical analogs found for this lifecycle/score combination.",
        "homework": "Build a personal watchlist of stocks that have successfully re-rated through this lifecycle stage.",
    }

    score_lower = current_perx_score - 15
    score_upper = current_perx_score + 15

    # Exact match: same lifecycle, similar score
    params: list[Any] = [current_lifecycle, score_lower, score_upper]
    exclude_clause = ""
    if exclude_symbol:
        exclude_clause = " AND symbol != %s"
        params.append(exclude_symbol)

    cur.execute(
        f"""
        SELECT symbol, perx_score, lifecycle_stage, created_at, summary
        FROM perx_reports
        WHERE lifecycle_stage = %s
          AND perx_score BETWEEN %s AND %s
          {exclude_clause}
        ORDER BY created_at DESC
        LIMIT 5
        """,
        params,
    )
    rows = cur.fetchall()

    if rows:
        analogs = []
        for r in rows:
            r_dict = r if isinstance(r, dict) else {
                "symbol": r[0], "perx_score": r[1], "lifecycle_stage": r[2],
                "created_at": r[3], "summary": r[4] if len(r) > 4 else None,
            }
            analogs.append({
                "symbol": r_dict.get("symbol"),
                "perx_score": safe_float(r_dict.get("perx_score")),
                "lifecycle_stage": r_dict.get("lifecycle_stage"),
                "date": str(r_dict.get("created_at", ""))[:10],
                "summary": r_dict.get("summary", "")[:120] if r_dict.get("summary") else "",
            })
        result["analogs"] = analogs
        result["verdict"] = f"Found {len(analogs)} historical analogs in same lifecycle stage ({current_lifecycle}) with similar PERX score (±15 pts)."
        result["homework"] = "Review each analog's score trajectory since the report date. Did PERX scores rise or fall from this lifecycle stage?"
        return result

    # Broader match: same lifecycle, any score
    params_broader = [current_lifecycle]
    exclude_clause_b = ""
    if exclude_symbol:
        exclude_clause_b = " AND symbol != %s"
        params_broader.append(exclude_symbol)

    cur.execute(
        f"""
        SELECT symbol, perx_score, lifecycle_stage, created_at, summary
        FROM perx_reports
        WHERE lifecycle_stage = %s
          {exclude_clause_b}
        ORDER BY created_at DESC
        LIMIT 5
        """,
        params_broader,
    )
    broader_rows = cur.fetchall()

    if broader_rows:
        analogs = []
        for r in broader_rows:
            r_dict = r if isinstance(r, dict) else {
                "symbol": r[0], "perx_score": r[1], "lifecycle_stage": r[2],
                "created_at": r[3], "summary": r[4] if len(r) > 4 else None,
            }
            analogs.append({
                "symbol": r_dict.get("symbol"),
                "perx_score": safe_float(r_dict.get("perx_score")),
                "lifecycle_stage": r_dict.get("lifecycle_stage"),
                "date": str(r_dict.get("created_at", ""))[:10],
                "summary": r_dict.get("summary", "")[:120] if r_dict.get("summary") else "",
            })
        result["analogs"] = analogs
        result["verdict"] = f"No exact score match (±15 pts). Showing {len(analogs)} broader analogs in same lifecycle stage ({current_lifecycle})."
        result["homework"] = "The score range is wide — focus on analogs from the same QUARTILE (within 25 pts of current score)."

    return result


def get_all_investor_context(cur, base_symbol: str, current_price: float | None = None,
                              current_perx_score: float | None = None,
                              current_lifecycle: str | None = None) -> dict[str, Any]:
    """
    Master function that runs all context engines and returns a unified investor context block.
    """
    valuation = get_valuation_context(cur, base_symbol, current_price)
    earnings = get_earnings_momentum(cur, base_symbol)
    ownership = get_ownership_signals(cur, base_symbol)
    liquidity = get_liquidity_profile(cur, base_symbol)
    grade = compute_investor_grade(valuation, earnings, ownership, liquidity)

    # PEG ratio (uses current PE from valuation)
    try:
        peg = get_peg_ratio(cur, base_symbol, current_pe=valuation.get("pe_ratio"))
    except Exception as e:
        cur.connection.rollback()
        logger.warning(f"PEG ratio failed for {base_symbol}: {e}")
        peg = {"peg_ratio": None, "eps_growth_pct": None, "verdict": "PEG unavailable.", "homework": ""}

    # EV/EBITDA (proxy — depends on fundamental_financials columns)
    try:
        ev_ebitda = get_ev_ebitda(cur, base_symbol)
    except Exception as e:
        cur.connection.rollback()
        logger.warning(f"EV/EBITDA failed for {base_symbol}: {e}")
        ev_ebitda = {"ev_ebitda": None, "market_cap_cr": None, "net_debt_ebitda": None, "verdict": "EV/EBITDA unavailable.", "homework": ""}

    # Institutional flow (FII/DII changes)
    try:
        inst_flow = get_institutional_flow(cur, base_symbol)
    except Exception as e:
        cur.connection.rollback()
        logger.warning(f"Institutional flow failed for {base_symbol}: {e}")
        inst_flow = {"fii_holding_pct": None, "dii_holding_pct": None, "fii_change_qoq": None, "dii_change_qoq": None, "verdict": "", "homework": ""}

    # Historical analogs from perx_reports archive
    try:
        analogs = {}
        if current_perx_score is not None and current_lifecycle:
            analogs = get_rerating_analogs(cur, current_perx_score, current_lifecycle, base_symbol)
        else:
            analogs = {
                "analogs": [],
                "verdict": "PERX score or lifecycle not provided for analog matching.",
                "homework": "Run a PERX scan first to enable historical analog matching."
            }
    except Exception as e:
        cur.connection.rollback()
        logger.warning(f"Analogs failed for {base_symbol}: {e}")
        analogs = {"analogs": [], "verdict": "Analogs unavailable.", "homework": ""}

    # Build pre-mortem risk section
    pre_mortem_risks = []
    if valuation.get("pe_percentile_vs_history") and valuation["pe_percentile_vs_history"] >= 80:
        pre_mortem_risks.append("Limited margin of safety at current valuation — any earnings miss could trigger multiple contraction.")
    if earnings.get("acceleration") == "DECELERATING":
        pre_mortem_risks.append("Growth engine losing steam — if this continues 2 more quarters, the rerating thesis weakens materially.")
    if ownership.get("promoter_trend") == "SELLING":
        pre_mortem_risks.append("Management selling into strength — fundamental misalignment with public shareholders.")
    if ownership.get("pledged_pct") and ownership["pledged_pct"] > 25:
        pre_mortem_risks.append("High promoter pledge — margin call risk if price declines.")
    if liquidity.get("avg_daily_turnover_cr") is not None and liquidity["avg_daily_turnover_cr"] < 1:
        pre_mortem_risks.append("Low liquidity may cause slippage on entry/exit beyond modeled levels.")
    if inst_flow.get("fii_trend") == "REDUCING" and inst_flow.get("dii_trend") != "ADDING":
        pre_mortem_risks.append("Foreign institutions reducing exposure — potential headwind for rerating momentum.")
    if peg.get("peg_ratio") and peg["peg_ratio"] > 3:
        pre_mortem_risks.append(f"PEG ratio at {peg['peg_ratio']:.1f}x — growth is not keeping pace with valuation.")
    if ev_ebitda.get("net_debt_ebitda") and ev_ebitda["net_debt_ebitda"] > 3:
        pre_mortem_risks.append("Elevated net debt/EBITDA — balance sheet could constrain future rerating.")
    if not pre_mortem_risks:
        pre_mortem_risks.append("No deterministic pre-mortem flags from current data — key risk remains execution durability.")

    # Catalyst questions — what the user should watch for rerating to materialize
    catalyst_questions = []
    pe_val = valuation.get("pe_ratio")
    if pe_val and valuation.get("pe_percentile_vs_history") and valuation["pe_percentile_vs_history"] >= 80:
        catalyst_questions.append(f"At P/E {pe_val}x (top of 5-year range), the rerating case rests on earnings compounding. Are net profits growing faster than the P/E multiple being paid?")
    if earnings.get("acceleration") == "DECELERATING":
        catalyst_questions.append("Revenue/profit decelerating. What would reverse this? New client wins? Margin expansion? Price hikes passing through?")
    elif earnings.get("acceleration") == "STABLE" and earnings.get("revenue_growth_4q_pct") and earnings["revenue_growth_4q_pct"] > 0:
        catalyst_questions.append(f"Revenue growing at {earnings['revenue_growth_4q_pct']:.0f}% YoY. Can this sustain another 4 quarters? Check order book or management guidance.")
    if ownership.get("promoter_trend") == "BUYING":
        catalyst_questions.append("Promoters are buying — strong insider signal. Confirm this is open market purchase (not ESOP or rights issue).")
    if inst_flow.get("fii_trend") == "ADDING":
        catalyst_questions.append(f"FIIs added {inst_flow['fii_change_qoq']:.1f}% — institutional confidence signal. Confirm via latest shareholding pattern filing.")
    if ev_ebitda.get("ev_ebitda") and ev_ebitda["ev_ebitda"] < 12:
        catalyst_questions.append(f"EV/EBITDA {ev_ebitda['ev_ebitda']:.1f}x leaves room for rerating IF EBITDA compounds. Can you identify 3 drivers of EBITDA growth for next 12 months?")
    if ownership.get("governance_score") and ownership["governance_score"] < 40:
        catalyst_questions.append(f"Governance score {ownership['governance_score']:.0f}/100 is low. Review: related party transactions, auditor qualifications, or promoter litigation.")
    if not catalyst_questions:
        catalyst_questions.append("No specific catalyst flags from current data. Key question remains: what needs to happen in the next 4 quarters for institutional perception to shift from current lifecycle ({}?) to the next stage?".format(current_lifecycle or "unknown"))

    # ---------------------------------------------------------------
    # PRDE Financial Fingerprint Score (from Milestone 0/1)
    # ---------------------------------------------------------------
    prde_block = {}
    try:
        cur.execute(
            """
            SELECT s.master_score, s.components, s.risk_penalty, s.mri_overlay
            FROM public.prde_final_scores s
            JOIN public.prde_companies c ON c.id = s.company_id
            WHERE c.ticker = %s
            ORDER BY s.created_at DESC
            LIMIT 1
            """,
            (base_symbol,),
        )
        prde_row = cur.fetchone()
        if prde_row:
            prde_block = {
                "master_score": float(prde_row["master_score"]) if prde_row["master_score"] is not None else None,
                "components": prde_row.get("components") if isinstance(prde_row.get("components"), dict) else {},
                "risk_penalty": float(prde_row["risk_penalty"]) if prde_row["risk_penalty"] is not None else 0.0,
                "mri_overlay": float(prde_row["mri_overlay"]) if prde_row["mri_overlay"] is not None else 0.0,
            }
    except Exception as e:
        cur.connection.rollback()
        logger.warning(f"PRDE score not available for {base_symbol}: {e}")
        prde_block = {"master_score": None, "components": {}, "risk_penalty": 0.0, "mri_overlay": 0.0}

    return {
        "valuation": valuation,
        "earnings_momentum": earnings,
        "ownership": ownership,
        "liquidity": liquidity,
        "peg_ratio": peg,
        "ev_ebitda": ev_ebitda,
        "institutional_flow": inst_flow,
        "historical_analogs": analogs,
        "investor_grade": grade,
        "prde_score": prde_block,
        "pre_mortem": {
            "risks": pre_mortem_risks,
        },
        "catalyst_questions": catalyst_questions,
        "homework_note": "The questions above are what an analyst would investigate next — use them to build conviction if answers are favorable, or as a checklist to disqualify if red flags surface.",
    }
