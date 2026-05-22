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
        pe = price / ttm_eps
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
            SELECT year, close
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
                        yearly_pes_list.append(close_price / np_val)

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


def get_all_investor_context(cur, base_symbol: str, current_price: float | None = None) -> dict[str, Any]:
    """
    Master function that runs all four context engines and returns a unified investor context block.
    """
    valuation = get_valuation_context(cur, base_symbol, current_price)
    earnings = get_earnings_momentum(cur, base_symbol)
    ownership = get_ownership_signals(cur, base_symbol)
    liquidity = get_liquidity_profile(cur, base_symbol)
    grade = compute_investor_grade(valuation, earnings, ownership, liquidity)

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
    if not pre_mortem_risks:
        pre_mortem_risks.append("No deterministic pre-mortem flags from current data — key risk remains execution durability.")

    return {
        "valuation": valuation,
        "earnings_momentum": earnings,
        "ownership": ownership,
        "liquidity": liquidity,
        "investor_grade": grade,
        "pre_mortem": {
            "risks": pre_mortem_risks,
        },
    }
