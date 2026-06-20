"""
Quality Investor Agents — Rule-based fundamental analysts.
Each agent evaluates a specific aspect of business quality.

Phase D1 (Data Richness Sprint, docs/INITIATIVE_DATA_RICHNESS_2026-06-19.md):
Each agent now returns a `detail` dict alongside score/reason/confidence.
The detail contains per-year metrics so the bear/bull debate and Expansion
Lens cross-check can argue from full trajectory instead of a single summary
score + flag.

Backward-compatible: existing callers (api/fundamental.py, engine_perx/,
engine_core/orchestrator.py, scripts/pipeline_cloud.sh) only read
score/reason/confidence. The new `detail` key is additive.
"""

from decimal import Decimal
import math


# ─── Safe arithmetic helpers ──────────────────────────────────────────────

def safe_float(v):
    if v is None:
        return 0.0
    try:
        if isinstance(v, Decimal) and v.is_nan():
            return 0.0
        fv = float(v)
        if math.isnan(fv):
            return 0.0
        return fv
    except Exception:
        return 0.0


def safe_div(num, den):
    fnum = safe_float(num)
    fden = safe_float(den)
    if fden == 0:
        return 0.0
    return fnum / fden


def get_growth(curr, prev):
    fcurr = safe_float(curr)
    fprev = safe_float(prev)
    if fprev == 0:
        return 0.0
    return (fcurr - fprev) / fprev


def get_trend(values):
    valid_values = []
    for v in values:
        if v is None:
            continue
        if isinstance(v, Decimal) and v.is_nan():
            continue
        try:
            fv = float(v)
            if math.isnan(fv):
                continue
            valid_values.append(fv)
        except Exception:
            continue

    if len(valid_values) < 2:
        return "neutral"
    if valid_values[-1] > valid_values[0]:
        return "up"
    if valid_values[-1] < valid_values[0]:
        return "down"
    return "flat"


# ─── Per-year detail helpers (Phase D1) ──────────────────────────────────

def _years_observed(financials):
    """Sorted list of years (ints) actually present in financials."""
    return sorted({int(f["year"]) for f in financials if f.get("year") is not None})


def _row_for_year(financials, year):
    """Return the financials row matching the given year, or None."""
    for f in financials:
        if f.get("year") is not None and int(f["year"]) == year:
            return f
    return None


def _previous_row(financials, year):
    """Return the financials row for the year before `year`, or None."""
    for f in financials:
        fy = f.get("year")
        if fy is not None and int(fy) == year - 1:
            return f
    return None


def _yoy_pct(curr, prev):
    """Year-over-year growth as a percentage (0.12 → 12.0)."""
    return get_growth(curr, prev) * 100.0


def _bps_delta(curr, prev):
    """Delta in basis points (e.g. OPM delta from 11.6% to 8.2% = -340 bps)."""
    return round((safe_float(curr) - safe_float(prev)) * 10000.0, 1)


def _rolling_avg(values, window):
    """Average of the last `window` values, skipping None/zero."""
    valid = [safe_float(v) for v in values if v is not None]
    if not valid:
        return 0.0
    return sum(valid[-window:]) / min(len(valid), window)


# ─── 1. REVENUE QUALITY AGENT ─────────────────────────────────────────────

def revenue_quality_agent(financials):
    if len(financials) < 2:
        return {"score": 0, "reason": "Insufficient history", "confidence": 0,
                "detail": {"per_year": []}}

    revs = [safe_float(f["revenue"]) for f in financials]
    latest_growth = get_growth(revs[-1], revs[-2])
    margin_trend = get_trend([safe_div(f["ebitda"], f["revenue"]) for f in financials])

    if latest_growth > 0.12 and margin_trend != "down":
        score, base_reason = 10, f"Strong growth ({latest_growth:.1%}) with healthy margins."
    elif latest_growth > 0.08:
        score, base_reason = 7, f"Moderate growth ({latest_growth:.1%})."
    else:
        score, base_reason = 3, "Weak or stagnant revenue growth."

    # Per-year detail
    per_year = []
    for f in financials:
        y = f.get("year")
        if y is None:
            continue
        y = int(y)
        prev = _previous_row(financials, y)
        growth_yoy = _yoy_pct(f.get("revenue"), prev.get("revenue")) if prev else 0.0
        # 3-year average revenue growth requires >=3 prior years; we approximate
        # by using available prior history (window bounded by what's present).
        prior_growths = []
        all_years = _years_observed(financials)
        if y in all_years:
            idx = all_years.index(y)
            for j in range(max(0, idx - 3), idx):
                prev_y = all_years[j]
                prev_row = _row_for_year(financials, prev_y)
                prev_prev_row = _previous_row(financials, prev_y)
                if prev_row is not None and prev_prev_row is not None:
                    prior_growths.append(_yoy_pct(prev_row.get("revenue"), prev_prev_row.get("revenue")))
        growth_3y_avg = sum(prior_growths) / len(prior_growths) if prior_growths else growth_yoy
        per_year.append({
            "year": y,
            "growth_yoy_pct": round(growth_yoy, 2),
            "growth_3y_avg_pct": round(growth_3y_avg, 2),
            "trend": "up" if growth_yoy > 5 else ("down" if growth_yoy < -5 else "flat"),
        })

    return {
        "score": score,
        "reason": base_reason,
        "confidence": 0.8,
        "detail": {"per_year": per_year, "metric": "revenue_growth"},
    }


# ─── 2. MARGIN QUALITY AGENT ──────────────────────────────────────────────

def margin_quality_agent(financials):
    margins = [safe_div(f["ebitda"], f["revenue"]) for f in financials]
    m_trend = get_trend(margins)

    if m_trend == "up":
        score, base_reason = 10, "Expansion driven by pricing power or product mix."
    elif m_trend == "flat":
        score, base_reason = 7, "Stable margins indicating competitive positioning."
    else:
        score, base_reason = 2, "Declining margins — potential cost pressures or loss of moat."

    per_year = []
    all_years = _years_observed(financials)
    for y in all_years:
        row = _row_for_year(financials, y)
        if row is None:
            continue
        opm = safe_div(row.get("ebitda"), row.get("revenue")) * 100.0
        # 3-year rolling avg of OPM up to (and including) year y
        idx = all_years.index(y)
        prior_opms = []
        for j in range(max(0, idx - 2), idx + 1):
            r = _row_for_year(financials, all_years[j])
            if r is not None:
                prior_opms.append(safe_div(r.get("ebitda"), r.get("revenue")) * 100.0)
        opm_3y_avg = sum(prior_opms) / len(prior_opms) if prior_opms else opm
        # YoY compression (negative = expansion)
        prev_y = all_years[idx - 1] if idx > 0 else None
        prev_row = _row_for_year(financials, prev_y) if prev_y is not None else None
        prev_opm = safe_div(prev_row.get("ebitda"), prev_row.get("revenue")) * 100.0 if prev_row is not None else opm
        compression = round((opm - prev_opm) * 100.0, 1)  # percentage points * 100 = bps
        per_year.append({
            "year": y,
            "opm_pct": round(opm, 2),
            "opm_3y_avg_pct": round(opm_3y_avg, 2),
            "compression_bps_yoy": compression,
        })

    return {
        "score": score,
        "reason": base_reason,
        "confidence": 0.9,
        "detail": {"per_year": per_year, "metric": "margin"},
    }


# ─── 3. OPERATING LEVERAGE AGENT ──────────────────────────────────────────

def operating_leverage_agent(financials):
    if len(financials) < 2:
        return {"score": 5, "reason": "N/A", "confidence": 0,
                "detail": {"per_year": []}}

    f_curr = financials[-1]
    f_prev = financials[-2]
    rev_growth = get_growth(f_curr["revenue"], f_prev["revenue"])
    ebitda_growth = get_growth(f_curr["ebitda"], f_prev["ebitda"])

    if ebitda_growth > 0 and rev_growth > 0 and ebitda_growth >= (1.5 * rev_growth):
        score = 10
        reason = f"Significant operating leverage: EBITDA growing {ebitda_growth/rev_growth:.1f}x faster than sales."
    elif ebitda_growth > rev_growth:
        score = 7
        reason = "Positive operating leverage detected."
    else:
        score = 3
        reason = "Profits lagging revenue growth — inefficient scaling."

    per_year = []
    all_years = _years_observed(financials)
    for y in all_years:
        row = _row_for_year(financials, y)
        prev_row = _previous_row(financials, y)
        if row is None or prev_row is None:
            ratio = 0.0
        else:
            rev_g = get_growth(row.get("revenue"), prev_row.get("revenue"))
            ebitda_g = get_growth(row.get("ebitda"), prev_row.get("ebitda"))
            ratio = (ebitda_g / rev_g) if rev_g != 0 else 0.0
        per_year.append({
            "year": y,
            "ebitda_to_revenue_growth_ratio": round(ratio, 2),
        })

    return {
        "score": score,
        "reason": reason,
        "confidence": 0.7,
        "detail": {"per_year": per_year, "metric": "operating_leverage"},
    }


# ─── 4. WORKING CAPITAL AGENT ─────────────────────────────────────────────

def working_capital_agent(financials):
    if len(financials) < 2:
        return {"score": 5, "reason": "N/A", "confidence": 0,
                "detail": {"per_year": []}}

    f_curr = financials[-1]
    f_prev = financials[-2]
    rev_growth = get_growth(f_curr["revenue"], f_prev["revenue"])
    rec_growth = get_growth(f_curr["receivables"], f_prev["receivables"])

    if rec_growth > rev_growth + 0.05:
        score = 2
        reason = f"Red Flag: Receivables (+{rec_growth:.1%}) outstripping sales (+{rev_growth:.1%})."
    else:
        score = 8
        reason = "Healthy working capital cycle."

    per_year = []
    all_years = _years_observed(financials)
    for y in all_years:
        row = _row_for_year(financials, y)
        prev_row = _previous_row(financials, y)
        if row is None or prev_row is None:
            rec_g = 0.0
            rev_g = 0.0
        else:
            rec_g = _yoy_pct(row.get("receivables"), prev_row.get("receivables"))
            rev_g = _yoy_pct(row.get("revenue"), prev_row.get("revenue"))
        per_year.append({
            "year": y,
            "receivable_growth_yoy_pct": round(rec_g, 2),
            "receivable_vs_revenue_growth_pct": round(rec_g - rev_g, 2),
        })

    return {
        "score": score,
        "reason": reason,
        "confidence": 0.85,
        "detail": {"per_year": per_year, "metric": "working_capital"},
    }


# ─── 5. CAPITAL EFFICIENCY AGENT (ROCE vs WACC) ──────────────────────────

def capital_efficiency_agent(financials, wacc=0.12):
    if not financials:
        return {"score": 0, "reason": "No financial history", "confidence": 0,
                "detail": {"per_year": [], "wacc_pct": wacc * 100.0}}

    latest = financials[-1]
    roce = safe_div(latest["ebitda"], latest["capital_employed"])
    if roce > wacc + 0.05:
        score = 10
        reason = f"High value creation: ROCE ({roce:.1%}) significantly above WACC ({wacc:.1%})."
    elif roce > wacc:
        score = 7
        reason = f"Value creation: ROCE ({roce:.1%}) covers cost of capital."
    else:
        score = 0
        reason = f"Value Destruction: ROCE ({roce:.1%}) below WACC ({wacc:.1%})."

    per_year = []
    all_years = _years_observed(financials)
    wacc_pct = wacc * 100.0
    for y in all_years:
        row = _row_for_year(financials, y)
        if row is None:
            continue
        r = safe_div(row.get("ebitda"), row.get("capital_employed")) * 100.0
        per_year.append({
            "year": y,
            "roce_pct": round(r, 2),
            "wacc_pct": round(wacc_pct, 2),
            "gap_pct": round(r - wacc_pct, 2),
        })

    return {
        "score": score,
        "reason": reason,
        "confidence": 1.0,
        "detail": {"per_year": per_year, "metric": "capital_efficiency", "wacc_pct": wacc_pct},
    }


# ─── 6. BUSINESS EVOLUTION AGENT ──────────────────────────────────────────

def business_evolution_agent(financials):
    asset_growth = get_trend([f["total_assets"] for f in financials])
    margin_stability = get_trend([safe_div(f["ebitda"], f["revenue"]) for f in financials])

    if asset_growth == "up" and margin_stability != "down":
        score = 8
        reason = "Signs of structural expansion and capacity building."
    else:
        score = 5
        reason = "Steady state business evolution."

    per_year = []
    all_years = _years_observed(financials)
    margins_pct = []
    for y in all_years:
        row = _row_for_year(financials, y)
        if row is None:
            continue
        opm = safe_div(row.get("ebitda"), row.get("revenue")) * 100.0
        margins_pct.append(opm)
        prev_row = _previous_row(financials, y)
        asset_g = _yoy_pct(row.get("total_assets"), prev_row.get("total_assets")) if prev_row else 0.0
        # Margin change vs 3 years prior (or earliest available)
        idx = all_years.index(y)
        if idx >= 3:
            earlier_row = _row_for_year(financials, all_years[idx - 3])
            if earlier_row is not None:
                earlier_opm = safe_div(earlier_row.get("ebitda"), earlier_row.get("revenue")) * 100.0
                margin_3y_bps = round((opm - earlier_opm) * 100.0, 1)
            else:
                margin_3y_bps = 0.0
        else:
            margin_3y_bps = 0.0
        per_year.append({
            "year": y,
            "asset_growth_yoy_pct": round(asset_g, 2),
            "margin_change_3y_bps": margin_3y_bps,
        })

    return {
        "score": score,
        "reason": reason,
        "confidence": 0.5,
        "detail": {"per_year": per_year, "metric": "business_evolution"},
    }


# ─── 7. FINANCIAL TRANSLATION AGENT ───────────────────────────────────────

def financial_translation_agent(financials):
    if len(financials) < 2:
        return {"score": 5, "reason": "N/A", "confidence": 0,
                "detail": {"per_year": []}}

    curr = financials[-1]
    prev = financials[-2]
    ebitda = safe_float(curr["ebitda"])
    rec_curr = safe_float(curr["receivables"])
    rec_prev = safe_float(prev["receivables"])
    net_profit = safe_float(curr["net_profit"])

    cash_gen_proxy = ebitda - (rec_curr - rec_prev)
    conversion_ratio = safe_div(cash_gen_proxy, net_profit)

    if conversion_ratio > 0.8:
        score = 10
        reason = f"High earnings quality: Cash conversion ratio {conversion_ratio:.1f}x."
    elif conversion_ratio > 0.5:
        score = 7
        reason = "Acceptable earnings quality."
    else:
        score = 2
        reason = f"Poor translation: Earnings not reflecting in cash (Ratio: {conversion_ratio:.1f}x)."

    per_year = []
    all_years = _years_observed(financials)
    for y in all_years:
        row = _row_for_year(financials, y)
        prev_row = _previous_row(financials, y)
        if row is None or prev_row is None:
            ratio = 0.0
        else:
            eb = safe_float(row.get("ebitda"))
            rc = safe_float(row.get("receivables"))
            rp = safe_float(prev_row.get("receivables"))
            np_ = safe_float(row.get("net_profit"))
            proxy = eb - (rc - rp)
            ratio = safe_div(proxy, np_)
        per_year.append({
            "year": y,
            "cash_conversion_ratio": round(ratio, 2),
        })

    return {
        "score": score,
        "reason": reason,
        "confidence": 0.8,
        "detail": {"per_year": per_year, "metric": "financial_translation"},
    }
