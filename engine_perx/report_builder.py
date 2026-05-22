from __future__ import annotations


def _pass_fail(value: bool | None, positive: str, negative: str) -> str:
    return positive if value else negative


def build_executive_summary(
    symbol: str,
    regime: str,
    mri_snapshot: dict,
    quality_snapshot: dict,
    lifecycle_stage: str,
    fragility_snapshot: dict,
    investor_context: dict | None = None,
) -> str:
    parts = [
        f"{symbol} is currently classified in the {lifecycle_stage} phase.",
        f"MRI technical leadership is at {int(float(mri_snapshot.get('total_score') or 0))}/100 in a {regime} market backdrop.",
        f"QIF business quality stands at {int(float(quality_snapshot.get('score') or 0))}/100 with category {quality_snapshot.get('category', 'UNKNOWN')}.",
        f"Current fragility is {fragility_snapshot.get('level', 'UNKNOWN').lower()}, which shapes how durable the rerating case appears from current evidence.",
    ]

    # Append investor context to summary if available
    if investor_context:
        inv_grade = investor_context.get("investor_grade", {})
        grade = inv_grade.get("grade", "")
        if grade:
            parts.append(f"Investor Grade: {grade}.")

        valuation = investor_context.get("valuation", {})
        pe_val = valuation.get("pe_ratio")
        if pe_val:
            parts.append(f"Trading at P/E {pe_val}x.")

        earnings = investor_context.get("earnings_momentum", {})
        accel = earnings.get("acceleration", "")
        if accel in ("ACCELERATING", "DECELERATING"):
            parts.append(f"Earnings momentum {accel.lower()}.")

    return " ".join(parts)


def build_narrative_transition(
    symbol: str,
    company_name: str,
    sector: str | None,
    quality_snapshot: dict,
    mri_snapshot: dict,
    lifecycle_stage: str,
) -> dict:
    category = quality_snapshot.get("category") or "WATCHLIST"
    previous = "ordinary cyclical operator"
    emerging = "institutionally watched rerating candidate"

    if category == "HIGH_QUALITY":
        previous = "good business without broad market sponsorship"
        emerging = "institutionally accumulating quality compounder"
    elif category == "EARLY_COMPOUNDER":
        previous = "improving operator still earning credibility"
        emerging = "early quality rerating candidate"
    elif category == "WATCHLIST":
        previous = "fundamentally mixed operator"
        emerging = "selectively improving business under review"

    if float(mri_snapshot.get("total_score") or 0) >= 80:
        emerging = f"{emerging} with active market confirmation"

    sector_fragment = f" in {sector}" if sector and sector != "UNKNOWN" else ""
    explanation = (
        f"{company_name} ({symbol}) appears to be moving from a market view of "
        f"'{previous}' toward '{emerging}'. The shift matters because improving business quality, "
        f"technical leadership, and {lifecycle_stage.lower()} behaviour can invite more serious institutional attention"
        f"{sector_fragment} if execution remains durable."
    )

    return {
        "previous_market_perception": previous,
        "emerging_market_perception": emerging,
        "why_this_matters": explanation,
    }


def build_engine_outputs(
    mri_snapshot: dict,
    quality_snapshot: dict,
    regime_snapshot: dict,
    stee_score: float,
    fragility_snapshot: dict,
    perx_score: float,
    narrative_intensity: str,
    sector_intelligence: dict,
    analogs: list[str],
    investor_context: dict | None = None,
) -> dict:
    avg_volume = float(mri_snapshot.get("avg_volume_20d") or 0)
    volume = float(mri_snapshot.get("volume") or 0)
    volume_multiple = round(volume / avg_volume, 2) if avg_volume > 0 else None

    return {
        "mri": {
            "total_score": mri_snapshot.get("total_score"),
            "relative_strength": _pass_fail(mri_snapshot.get("condition_rs"), "Strong", "Weak"),
            "volume_expansion": "Confirmed" if mri_snapshot.get("condition_volume") else "Not Confirmed",
            "ema_alignment": "Bullish" if mri_snapshot.get("condition_ema_50_200") else "Mixed",
            "breakout_structure": "Active" if mri_snapshot.get("condition_breakout_10d") else "Inactive",
            "price_quality": "Strong" if mri_snapshot.get("condition_price_quality") else "Average",
            "volume_multiple_20d": volume_multiple,
        },
        "stee": {
            "setup_quality_score": stee_score,
            "compression": "Present" if mri_snapshot.get("condition_price_quality") else "Not Clear",
            "leadership_structure": "Confirmed" if mri_snapshot.get("condition_rs") and mri_snapshot.get("condition_ema_50_200") else "Not Confirmed",
            "breakout_ready": bool(mri_snapshot.get("condition_breakout_10d")),
        },
        "qif": {
            "score": quality_snapshot.get("score"),
            "category": quality_snapshot.get("category"),
            "revenue_growth": quality_snapshot.get("revenue_score"),
            "ebitda_margins": quality_snapshot.get("margin_score"),
            "roce": quality_snapshot.get("roce_score"),
            "debt": quality_snapshot.get("leverage_score"),
            "trajectory_change": quality_snapshot.get("score_change"),
            "velocity": quality_snapshot.get("velocity"),
        },
        "sector": sector_intelligence,
        "perx": {
            "score": perx_score,
            "narrative_intensity": narrative_intensity,
            "institutional_suitability": "Strong" if perx_score >= 75 else "Developing" if perx_score >= 60 else "Early",
            "market_regime": regime_snapshot.get("classification"),
        },
        "investor": investor_context,
        "fragility": fragility_snapshot,
        "analogs": analogs,
    }


def build_final_verdict(
    company_name: str,
    symbol: str,
    lifecycle_stage: str,
    perx_score: float,
    fragility_snapshot: dict,
    quality_snapshot: dict,
    mri_snapshot: dict,
) -> str:
    return (
        f"{company_name} ({symbol}) currently reads as a {lifecycle_stage.lower()} candidate with a PERX score of {perx_score}/100. "
        f"Business quality is {quality_snapshot.get('category', 'under review')}, while market confirmation sits at "
        f"{int(float(mri_snapshot.get('total_score') or 0))}/100. The key constraint remains fragility at "
        f"{fragility_snapshot.get('level', 'UNKNOWN').lower()} from present deterministic evidence. "
        "This is institutional intelligence, not a trading call, and the thesis still depends on execution durability."
    )
