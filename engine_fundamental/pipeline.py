import logging
import math
import json
from datetime import datetime
from engine_core.db import get_connection
from engine_fundamental.agents import (
    revenue_quality_agent, margin_quality_agent, operating_leverage_agent,
    working_capital_agent, capital_efficiency_agent, business_evolution_agent,
    financial_translation_agent
)
from engine_qualitative.collector import build_qil_input
from engine_qualitative.extractor import extract_signals
from engine_qualitative.scorer import score_signals
from engine_qualitative.cross_check import cross_check
from engine_fundamental.trajectory import compute_score_velocity, detect_score_trend

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_financial_history(symbol):
    """Fetch financial history as RealDictRow list, ordered ascending by year."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT year, revenue, ebitda, net_profit, total_assets,
                   capital_employed, receivables, inventory, debt, equity
            FROM fundamental_financials
            WHERE symbol = %s
            ORDER BY year ASC
        """, (symbol,))
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_qil_sources_for_ticker(symbol):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT concall_url, annual_report_url FROM qil_sources WHERE symbol = %s", (symbol,))
        row = cur.fetchone()
        if not row:
            return []

        def get_val(item, key, index):
            if isinstance(item, dict):
                return item.get(key)
            if isinstance(item, (list, tuple)):
                return item[index] if len(item) > index else None
            return None

        sources = []
        concall_url = get_val(row, "concall_url", 0)
        annual_url = get_val(row, "annual_report_url", 1)
        if concall_url:
            sources.append({"url": concall_url, "type": "concall", "date": datetime.now().strftime("%Y-%m")})
        if annual_url:
            sources.append({"url": annual_url, "type": "annual_report", "date": datetime.now().strftime("%Y-%m")})
        return sources
    finally:
        conn.close()


# ─── Phase D1: per-year detail aggregation ────────────────────────────────

def _sanitize_for_json(obj):
    """Recursively replace NaN/Inf floats with 0.0 so JSON serialization
    succeeds (Postgres JSONB rejects NaN)."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else 0.0
    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_json(v) for v in obj]
    return obj


def _build_agent_details_json(agents_results, financials):
    """
    Merge the 7 agents' per-year detail dicts into a single `by_year[]` array,
    plus a pre-computed `trajectory` summary.

    agents_results: dict mapping agent_key -> {"score", "reason", "confidence", "detail"}
                    (where detail contains "per_year": [...]).
    financials: ordered list of financial dicts (ascending by year).

    Returns a JSONB-serializable dict with shape:
      {
        "by_year": [
          {"year": 2026, "scores": {...}, "metrics": {...}},
          ...
        ],
        "trajectory": {
          "score_trend": "improving|stable|declining",
          "score_change_yoy": float,
          "roce_change_yoy_bps": float,
          "margin_compression_bps_yoy": float,
          "revenue_cagr_3y_pct": float,
          "years_observed": int
        }
      }

    If financials is empty or no per-year detail exists, returns {"by_year": [], "trajectory": {}}.
    """
    if not financials:
        return {"by_year": [], "trajectory": {}}

    # Collect all years present across agents
    years_set = set()
    for f in financials:
        y = f.get("year")
        if y is not None:
            years_set.add(int(y))
    years = sorted(years_set)

    # Index per-year detail by year for each agent
    detail_by_agent_year = {}
    for agent_key, res in agents_results.items():
        d = res.get("detail", {}) if isinstance(res, dict) else {}
        per_year = d.get("per_year", []) if isinstance(d, dict) else []
        for entry in per_year:
            y = entry.get("year")
            if y is not None:
                detail_by_agent_year[(agent_key, int(y))] = entry

    # Build merged by_year[] with scores + metrics
    by_year = []
    for y in years:
        # Per-year score (the agent's overall score; trajectory uses these per-year? No,
        # scores are current-state. We just snapshot each year's metric details.)
        scores_snapshot = {}
        metrics_snapshot = {}
        for agent_key, res in agents_results.items():
            entry = detail_by_agent_year.get((agent_key, y))
            if entry:
                # Strip 'year' from the entry; merge remainder into metrics_snapshot
                metrics = {k: v for k, v in entry.items() if k != "year"}
                metrics_snapshot[agent_key] = metrics
        by_year.append({
            "year": y,
            "scores": scores_snapshot,
            "metrics": metrics_snapshot,
        })

    # Trajectory summary — computed from the latest two years of available data
    trajectory = _compute_trajectory_summary(agents_results, financials, years)

    sanitized = _sanitize_for_json({"by_year": by_year, "trajectory": trajectory})
    return sanitized


def _compute_trajectory_summary(agents_results, financials, years):
    """
    Compute a trajectory summary: trend classification, YoY deltas, 3-yr CAGR.
    Operates on the final-score trajectory (computed from quality_verdicts_history
    upstream) plus per-year agent metrics.
    """
    if not years:
        return {}

    n = len(years)
    latest_y = years[-1]
    prior_y = years[-2] if n >= 2 else None

    # Find the most recent per-year ROCE and OPM entries
    def latest_metric(agent_key, metric_name):
        d = (agents_results.get(agent_key) or {}).get("detail", {})
        per_year = d.get("per_year", []) if isinstance(d, dict) else []
        for entry in reversed(per_year):
            if entry.get(metric_name) is not None:
                return entry.get(metric_name)
        return None

    def prior_year_metric(agent_key, metric_name, target_year):
        d = (agents_results.get(agent_key) or {}).get("detail", {})
        per_year = d.get("per_year", []) if isinstance(d, dict) else []
        for entry in per_year:
            if entry.get("year") == target_year and entry.get(metric_name) is not None:
                return entry.get(metric_name)
        return None

    # YoY changes
    roce_now = latest_metric("capital_efficiency", "roce_pct")
    roce_prior = prior_year_metric("capital_efficiency", "roce_pct", prior_y) if prior_y else None
    roce_change_yoy_bps = round((roce_now - roce_prior) * 100.0, 1) if (roce_now is not None and roce_prior is not None) else 0.0

    opm_now = latest_metric("margin", "opm_pct")
    opm_prior = prior_year_metric("margin", "opm_pct", prior_y) if prior_y else None
    margin_compression_bps_yoy = round((opm_now - opm_prior) * 100.0, 1) if (opm_now is not None and opm_prior is not None) else 0.0

    # Revenue 3-year CAGR: needs >=4 years of revenue data
    revenue_cagr_3y_pct = 0.0
    if n >= 4:
        rev_now = None
        rev_3y_prior = None
        for f in financials:
            if f.get("year") is not None and int(f["year"]) == latest_y:
                rev_now = float(f.get("revenue") or 0)
            if f.get("year") is not None and int(f["year"]) == years[-4]:
                rev_3y_prior = float(f.get("revenue") or 0)
        # Guard against NaN/Inf/zero in either operand — NaN serializes to
        # invalid JSONB in Postgres, so sanitize upstream.
        def _is_finite_number(v):
            try:
                f = float(v)
                return math.isfinite(f) and f > 0
            except (TypeError, ValueError):
                return False
        if _is_finite_number(rev_now) and _is_finite_number(rev_3y_prior):
            years_diff = latest_y - years[-4]
            if years_diff > 0:
                try:
                    cagr = ((rev_now / rev_3y_prior) ** (1.0 / years_diff) - 1.0) * 100.0
                    if math.isfinite(cagr):
                        revenue_cagr_3y_pct = round(cagr, 2)
                except (ValueError, OverflowError, ZeroDivisionError):
                    pass

    # Score trend classification — based on roce + margin direction
    score_trend = "stable"
    if roce_change_yoy_bps < -100 or margin_compression_bps_yoy < -100:
        score_trend = "declining"
    elif roce_change_yoy_bps > 100 or margin_compression_bps_yoy > 100:
        score_trend = "improving"

    return {
        "score_trend": score_trend,
        "score_change_yoy": 0.0,  # populated by caller using final_score vs prev_score
        "roce_change_yoy_bps": roce_change_yoy_bps,
        "margin_compression_bps_yoy": margin_compression_bps_yoy,
        "revenue_cagr_3y_pct": revenue_cagr_3y_pct,
        "years_observed": n,
    }


# ─── Main pipeline entry point ────────────────────────────────────────────

def run_quality_pipeline(symbol):
    base_sym = symbol.replace(".NS", "").replace(".BO", "").upper()
    history = get_financial_history(base_sym)
    if not history:
        logger.error(f"No financial history for {base_sym}. Run collector first.")
        return None

    # Execute all agents
    results = {
        "revenue_growth": revenue_quality_agent(history),
        "margin_quality": margin_quality_agent(history),
        "operating_leverage": operating_leverage_agent(history),
        "working_capital": working_capital_agent(history),
        "capital_efficiency": capital_efficiency_agent(history),
        "business_evolution": business_evolution_agent(history),
        "financial_translation": financial_translation_agent(history),
    }

    # Weights and scoring
    weights = {
        "capital_efficiency": 0.25,
        "revenue_growth": 0.20,
        "margin_quality": 0.15,
        "operating_leverage": 0.10,
        "working_capital": 0.15,
        "financial_translation": 0.10,
        "business_evolution": 0.05,
    }

    base_score = sum(results[k]["score"] * weights[k] for k in weights) * 10

    flags = []
    penalty = 0
    reject = False

    # Critical rejection rule: ROCE < WACC
    if results["capital_efficiency"]["score"] < 3:
        penalty += 20
        reject = True
        flags.append("🚨 VALUE DESTRUCTION: ROCE < WACC")

    # QIL ADJUSTMENT
    qil_score = 0
    qil_flags = []
    qil_adjustment = 0

    if not reject:
        try:
            sources = get_qil_sources_for_ticker(base_sym)
            if sources:
                docs = build_qil_input(base_sym, sources)
                signals = extract_signals(docs)
                qil_score, s_flags = score_signals(signals)
                qil_adjustment = (qil_score - 5) * 0.6
                agent_map = {
                    "margin_quality": results["margin_quality"]["score"],
                    "working_capital": results["working_capital"]["score"],
                }
                cross_penalty, c_flags = cross_check(qil_score, agent_map)
                penalty += cross_penalty
                qil_flags = s_flags + c_flags
        except Exception as e:
            print(f"QIL Engine failed for {base_sym}: {e}")

    final_score = max(0, min(100, base_score + qil_adjustment - penalty))

    # Overall categorization
    if reject:
        category = "REJECT"
    elif final_score >= 80:
        category = "HIGH_QUALITY"
    elif final_score >= 70:
        category = "EARLY_COMPOUNDER"
    elif final_score >= 60:
        category = "WATCHLIST"
    else:
        category = "REJECT"

    # Trajectory Integration
    prev_score = None
    score_change = 0
    velocity = 0

    conn = get_connection()
    try:
        cur = conn.cursor()

        # Get last known score from history
        cur.execute("SELECT score FROM quality_verdicts WHERE symbol = %s", (base_sym,))
        row = cur.fetchone()
        if row:
            prev_score = float(row["score"])
            score_change = final_score - prev_score

        # Get score history for velocity
        cur.execute(
            "SELECT score FROM quality_verdicts_history WHERE symbol = %s ORDER BY recorded_at DESC LIMIT 5",
            (base_sym,),
        )
        history_rows = cur.fetchall()
        score_history = [float(r["score"]) for r in reversed(history_rows)]
        score_history.append(final_score)

        velocity = compute_score_velocity(score_history)
        trend = detect_score_trend(score_history)

        # Phase D1: Build per-year agent_details JSONB
        agent_details = _build_agent_details_json(results, history)
        if agent_details.get("trajectory"):
            agent_details["trajectory"]["score_change_yoy"] = round(score_change, 2)

        # Persistence
        cur.execute(
            """
            INSERT INTO quality_verdicts (
                symbol, score, category, reasoning, flags,
                prev_score, score_change, velocity,
                revenue_score, margin_score, leverage_score, wc_score, roce_score, evolution_score,
                qil_score, qil_flags, agent_details
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol) DO UPDATE SET
                prev_score = EXCLUDED.prev_score,
                score_change = EXCLUDED.score_change,
                velocity = EXCLUDED.velocity,
                score = EXCLUDED.score,
                category = EXCLUDED.category,
                reasoning = EXCLUDED.reasoning,
                flags = EXCLUDED.flags,
                revenue_score = EXCLUDED.revenue_score,
                margin_score = EXCLUDED.margin_score,
                leverage_score = EXCLUDED.leverage_score,
                wc_score = EXCLUDED.wc_score,
                roce_score = EXCLUDED.roce_score,
                evolution_score = EXCLUDED.evolution_score,
                qil_score = EXCLUDED.qil_score,
                qil_flags = EXCLUDED.qil_flags,
                agent_details = EXCLUDED.agent_details,
                updated_at = NOW()
        """,
            (
                base_sym, final_score, category, f"Quality Analysis for {base_sym}. Fundamental strength score: {base_score:.1f}",
                flags,
                prev_score, score_change, velocity,
                results["revenue_growth"]["score"], results["margin_quality"]["score"],
                results["operating_leverage"]["score"], results["working_capital"]["score"],
                results["capital_efficiency"]["score"], results["business_evolution"]["score"],
                qil_score, qil_flags,
                json.dumps(agent_details),
            ),
        )

        # Record in history
        cur.execute(
            "INSERT INTO quality_verdicts_history (symbol, score) VALUES (%s, %s)",
            (base_sym, final_score),
        )

        conn.commit()
    finally:
        conn.close()

    logger.info(
        f"Quality Verdict for {base_sym}: {category} ({final_score:.1f}/100) | "
        f"Change: {score_change:+.1f} | Velocity: {velocity:.1f} | Trend: {trend} | "
        f"agent_details: {len(agent_details.get('by_year', []))} years, "
        f"trajectory trend: {agent_details.get('trajectory', {}).get('score_trend', 'n/a')}"
    )

    return {
        "symbol": base_sym,
        "score": final_score,
        "category": category,
        "flags": flags,
        "agents": results,
        "agent_details": agent_details,
    }


if __name__ == "__main__":
    run_quality_pipeline("RELIANCE.NS")
