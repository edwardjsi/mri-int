"""PRDE Deterministic Scoring Engine.

Converts PRDE feature snapshots into transparent, inspectable numeric scores
using the Master Investor Checklist. No AI/LLM — purely deterministic math.

Score Components:
  Operating Leverage (20%)   — EBITDA growth vs revenue growth
  Capital Efficiency (20%)   — ROCE trend and level vs WACC
  Margin Quality (20%)       — EBITDA margin expansion + stability
  Growth Quality (15%)       — Revenue/EBITDA/PAT CAGR consistency
  Cash Conversion (10%)      — FCF generation proxy
  Balance Sheet Health (10%) — Debt reduction, leverage stability
  Valuation Gap (5%)         — Current PE vs historical band
  Risk Penalty               — Red flags from governance, strain, earnings quality
  MRI Overlay                — Momentum confirmation from existing MRI scores

Usage:
    python engine_core/prde_scoring_engine.py --limit 20 --dry-run
    python engine_core/prde_scoring_engine.py --symbol RELIANCE
    python engine_core/prde_scoring_engine.py --limit 50
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import sys
from datetime import date
from typing import Any
from uuid import uuid4

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("prde_scoring")

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def safe_get(d: dict, *keys, default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


# ---------------------------------------------------------------------------
# Score component functions — each returns (score 0-100, reason string)
# ---------------------------------------------------------------------------


def score_operating_leverage(features: dict) -> tuple[float, str]:
    """Operating leverage: EBITDA grows faster than revenue => fixed-cost efficiency."""
    ebitda_yoy = safe_get(features, "ebitda_yoy_mean")
    revenue_yoy = safe_get(features, "revenue_yoy_mean")

    if ebitda_yoy is None or revenue_yoy is None:
        return 50.0, "insufficient data for operating leverage"

    spread = ebitda_yoy - revenue_yoy

    if spread > 0.10:
        return 90.0, f"strong positive operating leverage (EBITDA growth {ebitda_yoy:.1%} >> revenue {revenue_yoy:.1%})"
    elif spread > 0.05:
        return 75.0, f"positive operating leverage (EBITDA {ebitda_yoy:.1%} > revenue {revenue_yoy:.1%})"
    elif spread > 0.0:
        return 60.0, f"mild operating leverage (EBITDA {ebitda_yoy:.1%} ~ revenue {revenue_yoy:.1%})"
    elif spread > -0.05:
        return 40.0, f"negative operating leverage (EBITDA {ebitda_yoy:.1%} < revenue {revenue_yoy:.1%})"
    else:
        return 20.0, f"significant negative operating leverage (EBITDA {ebitda_yoy:.1%} << revenue {revenue_yoy:.1%})"


def score_capital_efficiency(features: dict) -> tuple[float, str]:
    """Capital efficiency: ROCE level and trend."""
    roce_latest = safe_get(features, "roce", "latest")
    roce_trend = safe_get(features, "roce", "trend_slope")

    if roce_latest is None:
        return 50.0, "ROCE data unavailable"

    # Base score from ROCE level (vs 15% WACC proxy for India)
    if roce_latest > 0.25:
        base = 90.0
        level_desc = f"exceptional ROCE {roce_latest:.1%}"
    elif roce_latest > 0.20:
        base = 80.0
        level_desc = f"strong ROCE {roce_latest:.1%}"
    elif roce_latest > 0.15:
        base = 65.0
        level_desc = f"adequate ROCE {roce_latest:.1%}"
    elif roce_latest > 0.10:
        base = 45.0
        level_desc = f"below-threshold ROCE {roce_latest:.1%}"
    else:
        base = 25.0
        level_desc = f"poor ROCE {roce_latest:.1%}"

    # Trend modifier
    if roce_trend is not None:
        if roce_trend > 0.02:
            base = min(base + 15, 100)
            trend_desc = "improving"
        elif roce_trend > 0.0:
            base = min(base + 5, 100)
            trend_desc = "stable-positive"
        elif roce_trend > -0.02:
            trend_desc = "flat"
        else:
            base = max(base - 15, 0)
            trend_desc = "deteriorating"
    else:
        trend_desc = "unknown trend"

    return clamp(base), f"{level_desc}, trend {trend_desc}"


def score_margin_quality(features: dict) -> tuple[float, str]:
    """Margin quality: EBITDA margin level, trend, and stability."""
    margin_latest = safe_get(features, "ebitda_margin", "latest")
    margin_trend = safe_get(features, "ebitda_margin", "trend_slope")
    margin_stability = safe_get(features, "ebitda_margin", "stability")

    if margin_latest is None:
        return 50.0, "margin data unavailable"

    # Level
    if margin_latest > 0.30:
        base = 90.0
        level_desc = f"high margin {margin_latest:.1%}"
    elif margin_latest > 0.20:
        base = 70.0
        level_desc = f"healthy margin {margin_latest:.1%}"
    elif margin_latest > 0.10:
        base = 50.0
        level_desc = f"moderate margin {margin_latest:.1%}"
    else:
        base = 30.0
        level_desc = f"thin margin {margin_latest:.1%}"

    # Trend
    if margin_trend is not None:
        if margin_trend > 0.02:
            base = min(base + 10, 100)
            trend_desc = "expanding"
        elif margin_trend < -0.02:
            base = max(base - 15, 0)
            trend_desc = "contracting"
        else:
            trend_desc = "stable"
    else:
        trend_desc = "unknown"

    # Stability bonus/penalty
    if margin_stability is not None:
        if margin_stability < 0.03:
            base = min(base + 5, 100)
            stability_desc = "very stable"
        elif margin_stability < 0.06:
            stability_desc = "stable"
        else:
            base = max(base - 10, 0)
            stability_desc = "volatile"
    else:
        stability_desc = "unknown"

    return clamp(base), f"{level_desc}, {trend_desc}, {stability_desc}"


def score_growth_quality(features: dict) -> tuple[float, str]:
    """Growth quality: CAGR consistency across revenue, EBITDA, PAT."""
    rev_cagr = safe_get(features, "revenue_cagr_3y")
    ebitda_cagr = safe_get(features, "ebitda_cagr_3y")
    pat_cagr = safe_get(features, "pat_cagr_3y")

    cagrs = [v for v in (rev_cagr, ebitda_cagr, pat_cagr) if v is not None]

    if len(cagrs) < 2:
        return 50.0, f"insufficient CAGR data ({len(cagrs)}/3 available)"

    mean_cagr = sum(cagrs) / len(cagrs)

    if mean_cagr > 0.20:
        base = 90.0
        growth_desc = "exceptional"
    elif mean_cagr > 0.15:
        base = 75.0
        growth_desc = "strong"
    elif mean_cagr > 0.10:
        base = 60.0
        growth_desc = "healthy"
    elif mean_cagr > 0.05:
        base = 45.0
        growth_desc = "moderate"
    elif mean_cagr > 0:
        base = 30.0
        growth_desc = "low"
    else:
        base = 15.0
        growth_desc = "negative"

    # Consistency: penalize if PAT CAGR << revenue CAGR (quality erosion)
    if rev_cagr is not None and pat_cagr is not None:
        spread = rev_cagr - pat_cagr
        if spread > 0.10:
            base = max(base - 20, 0)
            consistency = "PAT significantly lagging revenue"
        elif spread > 0.05:
            base = max(base - 10, 0)
            consistency = "PAT lagging revenue"
        elif pat_cagr > rev_cagr:
            base = min(base + 5, 100)
            consistency = "PAT growing faster than revenue"
        else:
            consistency = "aligned"
    else:
        consistency = "unknown"

    return clamp(base), f"{growth_desc} growth (mean CAGR {mean_cagr:.1%}), {consistency}"


def score_cash_conversion(features: dict) -> tuple[float, str]:
    """Cash conversion proxy: capex intensity and asset turnover as FCF quality signals."""
    capex_intensity = safe_get(features, "capex_intensity", "latest")
    asset_turnover = safe_get(features, "asset_turnover", "latest")

    if capex_intensity is None and asset_turnover is None:
        return 50.0, "no cash conversion proxy data"

    score = 50.0
    reasons = []

    if capex_intensity is not None:
        if capex_intensity < 0.05:
            score += 25
            reasons.append(f"low capex intensity {capex_intensity:.1%} (asset-light)")
        elif capex_intensity < 0.10:
            score += 10
            reasons.append(f"moderate capex {capex_intensity:.1%}")
        elif capex_intensity > 0.25:
            score -= 20
            reasons.append(f"high capex intensity {capex_intensity:.1%} (cash-hungry)")

    if asset_turnover is not None:
        if asset_turnover > 1.5:
            score += 20
            reasons.append(f"high asset turnover {asset_turnover:.1f}x")
        elif asset_turnover > 0.8:
            score += 5
            reasons.append(f"adequate asset turnover {asset_turnover:.1f}x")
        elif asset_turnover < 0.3:
            score -= 15
            reasons.append(f"low asset turnover {asset_turnover:.1f}x (capital-intensive)")

    return clamp(score), "; ".join(reasons) if reasons else "neutral cash conversion signals"


def score_balance_sheet_health(features: dict) -> tuple[float, str]:
    """Balance sheet health: debt/equity level and trend."""
    de_latest = safe_get(features, "debt_equity", "latest")
    de_trend = safe_get(features, "debt_equity", "trend_slope")

    if de_latest is None:
        return 50.0, "debt/equity data unavailable"

    if de_latest < 0.2:
        base = 90.0
        level_desc = f"near-zero debt (D/E {de_latest:.2f})"
    elif de_latest < 0.5:
        base = 75.0
        level_desc = f"low leverage (D/E {de_latest:.2f})"
    elif de_latest < 1.0:
        base = 55.0
        level_desc = f"moderate leverage (D/E {de_latest:.2f})"
    elif de_latest < 2.0:
        base = 35.0
        level_desc = f"high leverage (D/E {de_latest:.2f})"
    else:
        base = 15.0
        level_desc = f"very high leverage (D/E {de_latest:.2f})"

    if de_trend is not None:
        if de_trend < -0.10:
            base = min(base + 15, 100)
            trend_desc = "rapidly deleveraging"
        elif de_trend < -0.02:
            base = min(base + 5, 100)
            trend_desc = "deleveraging"
        elif de_trend > 0.10:
            base = max(base - 15, 0)
            trend_desc = "rapidly releveraging"
        elif de_trend > 0.02:
            base = max(base - 5, 0)
            trend_desc = "releveraging"
        else:
            trend_desc = "stable"
    else:
        trend_desc = "unknown trend"

    return clamp(base), f"{level_desc}, {trend_desc}"


def score_valuation_gap(features: dict) -> tuple[float, str]:
    """Valuation gap: current PE vs historical band."""
    pe_latest = safe_get(features, "pe", "latest")
    pe_mean = safe_get(features, "pe", "mean")
    pe_min = safe_get(features, "pe", "min")
    pe_max = safe_get(features, "pe", "max")

    if pe_latest is None or pe_mean is None:
        return 50.0, "valuation data unavailable"

    # Percentile within historical range
    if pe_max is not None and pe_min is not None and pe_max > pe_min:
        percentile = (pe_latest - pe_min) / (pe_max - pe_min)
    else:
        percentile = 0.5

    if percentile < 0.2:
        return 90.0, f"PE {pe_latest:.1f} near historical lows ({percentile:.0%} percentile)"
    elif percentile < 0.4:
        return 70.0, f"PE {pe_latest:.1f} below historical median ({percentile:.0%} percentile)"
    elif percentile < 0.6:
        return 50.0, f"PE {pe_latest:.1f} near historical median ({percentile:.0%} percentile)"
    elif percentile < 0.8:
        return 30.0, f"PE {pe_latest:.1f} above median ({percentile:.0%} percentile)"
    else:
        return 10.0, f"PE {pe_latest:.1f} near historical highs ({percentile:.0%} percentile) — expensive"


def score_risk_penalty(features: dict) -> tuple[float, list[str]]:
    """Risk penalty from red flags. Returns (penalty_points, flags)."""
    penalty = 0.0
    flags = []

    # High debt + deteriorating
    de_latest = safe_get(features, "debt_equity", "latest")
    de_trend = safe_get(features, "debt_equity", "trend_slope")
    if de_latest is not None and de_latest > 1.5:
        penalty += 10
        flags.append(f"high debt/equity ({de_latest:.1f})")
    if de_trend is not None and de_trend > 0.10:
        penalty += 5
        flags.append("rapidly increasing leverage")

    # Declining margins
    margin_trend = safe_get(features, "ebitda_margin", "trend_slope")
    if margin_trend is not None and margin_trend < -0.03:
        penalty += 10
        flags.append("significant margin compression")

    # Negative PAT CAGR
    pat_cagr = safe_get(features, "pat_cagr_3y")
    if pat_cagr is not None and pat_cagr < 0:
        penalty += 8
        flags.append(f"negative PAT CAGR ({pat_cagr:.1%})")

    # Extreme capex intensity
    capex_intensity = safe_get(features, "capex_intensity", "latest")
    if capex_intensity is not None and capex_intensity > 0.30:
        penalty += 5
        flags.append(f"very high capex intensity ({capex_intensity:.1%})")

    return penalty, flags


# ---------------------------------------------------------------------------
# Master scoring function
# ---------------------------------------------------------------------------


def compute_master_score(features: dict, mri_score: float | None = None) -> dict[str, Any]:
    """Compute the Master Investor Checklist score from PRDE features.

    Returns a dict with total_score, component breakdown, and reasons.
    """
    components = {
        "operating_leverage":  {"weight": 0.20, "score": 50.0, "reason": ""},
        "capital_efficiency":  {"weight": 0.20, "score": 50.0, "reason": ""},
        "margin_quality":      {"weight": 0.20, "score": 50.0, "reason": ""},
        "growth_quality":      {"weight": 0.15, "score": 50.0, "reason": ""},
        "cash_conversion":     {"weight": 0.10, "score": 50.0, "reason": ""},
        "balance_sheet":       {"weight": 0.10, "score": 50.0, "reason": ""},
        "valuation_gap":       {"weight": 0.05, "score": 50.0, "reason": ""},
    }

    # Score each component
    components["operating_leverage"]["score"], components["operating_leverage"]["reason"] = score_operating_leverage(features)
    components["capital_efficiency"]["score"], components["capital_efficiency"]["reason"] = score_capital_efficiency(features)
    components["margin_quality"]["score"], components["margin_quality"]["reason"] = score_margin_quality(features)
    components["growth_quality"]["score"], components["growth_quality"]["reason"] = score_growth_quality(features)
    components["cash_conversion"]["score"], components["cash_conversion"]["reason"] = score_cash_conversion(features)
    components["balance_sheet"]["score"], components["balance_sheet"]["reason"] = score_balance_sheet_health(features)
    components["valuation_gap"]["score"], components["valuation_gap"]["reason"] = score_valuation_gap(features)

    # Weighted total
    weighted_total = sum(c["score"] * c["weight"] for c in components.values())

    # Risk penalty
    penalty, risk_flags = score_risk_penalty(features)
    weighted_total -= penalty

    # MRI overlay (0-5 point boost for strong momentum)
    mri_boost = 0.0
    if mri_score is not None:
        if mri_score >= 80:
            mri_boost = 5.0
        elif mri_score >= 60:
            mri_boost = 2.0
        weighted_total += mri_boost

    master_score = clamp(weighted_total)

    return {
        "master_score": round(master_score, 1),
        "components": {k: {"score": round(v["score"], 1), "weight": v["weight"], "reason": v["reason"]}
                       for k, v in components.items()},
        "risk_penalty": round(penalty, 1),
        "risk_flags": risk_flags,
        "mri_overlay_boost": round(mri_boost, 1),
    }


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------


def ensure_scoring_tables(cur) -> None:
    """Create prde_final_scores table if not exists."""
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS public.prde_final_scores (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id      INT          NOT NULL REFERENCES public.prde_companies(id) ON DELETE CASCADE,
            run_id          UUID         NOT NULL,
            master_score    NUMERIC(5,2) NOT NULL,
            components      JSONB        NOT NULL,
            risk_penalty    NUMERIC(5,2) DEFAULT 0,
            mri_overlay     NUMERIC(5,2) DEFAULT 0,
            feature_hash    VARCHAR(64),
            created_at      TIMESTAMPTZ  DEFAULT NOW()
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prde_scores_company ON public.prde_final_scores(company_id, created_at DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prde_scores_run ON public.prde_final_scores(run_id);")


def fetch_latest_snapshots(cur, symbol: str | None = None, limit: int | None = None) -> list[dict]:
    """Fetch latest feature snapshot per company, with optional MRI score."""
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
        SELECT c.id AS company_id, c.ticker, c.name, c.sector,
               s.features, s.feature_hash, s.created_at AS snapshot_at,
               ss.total_score AS mri_score
        FROM public.prde_companies c
        JOIN LATERAL (
            SELECT features, feature_hash, created_at
            FROM public.prde_feature_snapshots
            WHERE company_id = c.id
            ORDER BY created_at DESC
            LIMIT 1
        ) s ON TRUE
        LEFT JOIN LATERAL (
            SELECT total_score
            FROM public.stock_scores
            WHERE symbol = c.ticker
            ORDER BY date DESC
            LIMIT 1
        ) ss ON TRUE
        {where}
        ORDER BY c.ticker ASC
        {limit_clause}
        """,
        tuple(params),
    )
    return [dict(row) for row in cur.fetchall()]


def persist_score(cur, company_id: int, run_id: str, feature_hash: str | None,
                  scoring_result: dict) -> str:
    from psycopg2.extras import Json

    cur.execute(
        """
        INSERT INTO public.prde_final_scores
            (company_id, run_id, master_score, components, risk_penalty,
             mri_overlay, feature_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            company_id, run_id,
            scoring_result["master_score"],
            Json(scoring_result["components"]),
            scoring_result["risk_penalty"],
            scoring_result["mri_overlay_boost"],
            feature_hash,
        ),
    )
    return str(cur.fetchone()["id"])


def run_scoring(
    *,
    symbol: str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run the PRDE scoring engine across the universe."""
    from api.schema import ensure_prde_tables
    from engine_core.db import get_connection

    conn = get_connection()
    run_id = str(uuid4())
    scored: list[dict] = []
    skipped: list[dict] = []

    try:
        with conn.cursor() as cur:
            ensure_prde_tables(cur)
            ensure_scoring_tables(cur)

            snapshots = fetch_latest_snapshots(cur, symbol, limit)

            for snap in snapshots:
                features = snap["features"]
                if isinstance(features, str):
                    features = json.loads(features)

                mri_score = snap.get("mri_score")
                if mri_score is not None:
                    mri_score = float(mri_score)

                result = compute_master_score(features, mri_score)

                score_id = None
                if not dry_run:
                    score_id = persist_score(
                        cur, snap["company_id"], run_id,
                        snap.get("feature_hash"), result,
                    )

                scored.append({
                    "ticker": snap["ticker"],
                    "name": snap["name"],
                    "sector": snap["sector"],
                    "score_id": score_id,
                    "master_score": result["master_score"],
                    "risk_penalty": result["risk_penalty"],
                    "mri_boost": result["mri_overlay_boost"],
                })

            if dry_run:
                conn.rollback()
            else:
                conn.commit()

        return {
            "run_id": run_id,
            "dry_run": dry_run,
            "snapshots_found": len(snapshots),
            "scored": sorted(scored, key=lambda x: x["master_score"], reverse=True),
            "skipped": skipped,
        }

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PRDE Deterministic Scoring Engine")
    parser.add_argument("--symbol", help="Score a single ticker")
    parser.add_argument("--limit", type=int, help="Maximum companies to score")
    parser.add_argument("--dry-run", action="store_true", help="Compute scores without persisting")
    args = parser.parse_args(argv or sys.argv[1:])

    try:
        result = run_scoring(symbol=args.symbol, limit=args.limit, dry_run=args.dry_run)
    except Exception as exc:
        logger.error("PRDE scoring failed: %s", exc)
        return 1

    print(f"Run ID: {result['run_id']}")
    print(f"Snapshots found: {result['snapshots_found']}")
    print(f"Scored: {len(result['scored'])}")

    if result["scored"]:
        print(f"\n{'Rank':>4}  {'Ticker':<12} {'Master':>7}  {'Risk':>6}  {'MRI':>5}  {'Name'}")
        print("-" * 70)
        for rank, s in enumerate(result["scored"], 1):
            print(f"{rank:>4}  {s['ticker']:<12} {s['master_score']:>7.1f}  {s['risk_penalty']:>6.1f}  {s['mri_boost']:>5.1f}  {s['name'][:30]}")

    if not result["scored"]:
        logger.warning("No companies scored. Run Milestone 0 first to generate feature snapshots.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
