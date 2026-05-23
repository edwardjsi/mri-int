from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from engine_perx.analogs import get_historical_analogs
from engine_perx.report_builder import (
    build_engine_outputs,
    build_executive_summary,
    build_final_verdict,
    build_narrative_transition,
)
from engine_perx.scoring import (
    classify_lifecycle_stage,
    compute_fragility_snapshot,
    compute_perx_score,
    compute_stee_setup_score,
    compute_trajectory_support,
    narrative_intensity_label,
)
from engine_perx.investor_context import get_all_investor_context


class PerxScanError(Exception):
    """Structured error for PERX scan failures with actionable details."""

    def __init__(self, message: str, error_type: str = "UNKNOWN",
                 data_source: str | None = None, action: str | None = None):
        self.message = message
        self.error_type = error_type
        self.data_source = data_source
        self.action = action
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {
            "error": self.error_type,
            "detail": self.message,
            "data_source": self.data_source,
            "action": self.action,
        }
from engine_perx.sector import get_sector_context
from engine_qualitative.debate import run_debate


def _collect_data_warnings(report: dict, symbol: str) -> list[dict]:
    '''Collect data quality warnings from the report's investor context.'''
    warnings = []
    ic = report.get("investor_context", {})
    if not ic:
        return warnings

    checks = [
        ("peg_ratio", "PEG Ratio", "Not enough quarterly EPS data (needs 8 quarters)"),
        ("ev_ebitda", "EV/EBITDA", "Missing fundamental data columns for Enterprise Value"),
        ("institutional_flow", "Institutional Flow", "FII/DII data not available from current data sources"),
        ("historical_analogs", "Historical Analogs", "No archived PERX reports at similar lifecycle stage"),
        ("cashflow_health", "Cash Flow Health", "Operating cash flow or free cash flow not available for this symbol"),
    ]

    for key, label, reason in checks:
        module = ic.get(key, {})
        if not isinstance(module, dict):
            continue
        verdict = module.get("verdict", "")
        if not verdict:
            continue
        lower = verdict.lower()
        if any(w in lower for w in ["unavailable", "no ", "insufficient", "not available"]):
            warnings.append({
                "module": label,
                "key": key,
                "detail": verdict[:150],
                "action": reason,
            })

    return warnings


def normalize_symbol(symbol: str) -> str:
    return symbol.replace(".NS", "").replace(".BO", "").upper().strip()


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _get_company_name(cur, symbol: str) -> str | None:
    try:
        cur.execute("SELECT company_name FROM stock_sectors WHERE symbol = %s", (symbol,))
        row = cur.fetchone()
        if row:
            return row["company_name"] if isinstance(row, dict) else row[0]
    except Exception:
        return None
    return None


def _get_sector(cur, symbol: str) -> str | None:
    try:
        cur.execute("SELECT industry FROM stock_sectors WHERE symbol = %s", (symbol,))
        row = cur.fetchone()
        if row:
            return row["industry"] if isinstance(row, dict) else row[0]
    except Exception:
        return None
    return None


def _fetch_latest_mri_snapshot(cur, symbol: str) -> dict[str, Any] | None:
    cur.execute(
        """
        SELECT ss.date, ss.symbol, ss.total_score,
               ss.condition_ema_50_200, ss.condition_ema_200_slope,
               ss.condition_6m_high, ss.condition_volume, ss.condition_rs,
               ss.condition_breakout_10d, ss.condition_price_quality,
               dp.close, dp.volume, dp.avg_volume_20d, dp.rs_90d,
               dp.ema_50, dp.ema_200, dp.high_10d, dp.high, dp.low
        FROM stock_scores ss
        JOIN daily_prices dp
          ON dp.symbol = ss.symbol
         AND dp.date = ss.date
        WHERE ss.symbol = %s
        ORDER BY ss.date DESC
        LIMIT 1
        """,
        (symbol,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def _fetch_latest_quality_snapshot(cur, symbol: str) -> dict[str, Any] | None:
    cur.execute("SELECT * FROM quality_verdicts WHERE symbol = %s", (symbol,))
    row = cur.fetchone()
    return dict(row) if row else None


def _fetch_financial_history(cur, symbol: str) -> list[dict[str, Any]]:
    cur.execute(
        """
        SELECT year, revenue, ebitda, net_profit, total_assets,
               capital_employed, receivables, inventory, debt, equity
        FROM fundamental_financials
        WHERE symbol = %s
        ORDER BY year ASC
        """,
        (symbol,),
    )
    return [dict(row) for row in cur.fetchall()]


def _fetch_latest_regime(cur) -> dict[str, Any]:
    cur.execute("SELECT date, classification, ema_50, ema_200 FROM market_regime ORDER BY date DESC LIMIT 1")
    row = cur.fetchone()
    return dict(row) if row else {"classification": "NEUTRAL", "date": None, "ema_50": None, "ema_200": None}


def _build_forensic_review(symbol: str, include_debate: bool) -> dict[str, Any]:
    if not include_debate:
        return {
            "unavailable": True,
            "status": "available_on_demand",
            "message": "Institutional Forensic Review is available through the existing Debate flow and can be included on demand.",
        }

    review = run_debate(symbol)
    if review.get("error"):
        return {
            "unavailable": True,
            "status": "generation_failed",
            "message": review["error"],
        }
    return review


def _fetch_previous_report(cur, symbol: str, client_id: str | None) -> dict[str, Any] | None:
    """Fetch the most recent prior report for this symbol/client to provide context."""
    if not client_id:
        return None
    cur.execute(
        """
        SELECT report_json, perx_score, created_at
        FROM perx_reports
        WHERE symbol = %s AND client_id = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (symbol, client_id),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def _build_report_payload(
    symbol: str,
    company_name: str,
    sector_intelligence: dict[str, Any],
    mri_snapshot: dict[str, Any],
    quality_snapshot: dict[str, Any],
    financial_history: list[dict[str, Any]],
    regime_snapshot: dict[str, Any],
    forensic_review: dict[str, Any],
    previous_report: dict[str, Any] | None = None,
    investor_context: dict[str, Any] | None = None,
    cur=None,
    current_price: float | None = None,
) -> dict[str, Any]:
    stee_score = compute_stee_setup_score(mri_snapshot)
    trajectory_support = compute_trajectory_support(quality_snapshot)
    fragility_snapshot = compute_fragility_snapshot(quality_snapshot, financial_history, mri_snapshot)
    perx_score = compute_perx_score(
        mri_snapshot,
        quality_snapshot,
        stee_score,
        trajectory_support,
        fragility_snapshot,
        forensic_review=forensic_review,
    )
    lifecycle_stage = classify_lifecycle_stage(perx_score, mri_snapshot, quality_snapshot, fragility_snapshot)
    narrative_intensity = narrative_intensity_label(perx_score)
    analogs = get_historical_analogs(perx_score, lifecycle_stage)

    # Compute investor context inside where perx_score and lifecycle_stage are known
    if investor_context is None and cur is not None:
        investor_context = get_all_investor_context(
            cur, symbol, current_price=current_price,
            current_perx_score=perx_score, current_lifecycle=lifecycle_stage,
        )

    # Contextual evaluation against prior report
    prior_context = "No previous institutional evaluation found in your archive."
    if previous_report:
        prev_score = float(previous_report.get("perx_score") or 0)
        prev_date = previous_report.get("created_at")
        diff = perx_score - prev_score
        direction = "improved" if diff > 0 else "softened" if diff < 0 else "remained stable"
        prior_context = f"Baseline established on {prev_date}: PERX score has {direction} by {abs(diff):.1f} points."

    report = {
        "symbol": symbol,
        "company_name": company_name,
        "header": {
            "company_name": company_name,
            "symbol": symbol,
            "perx_score": perx_score,
            "lifecycle_phase": lifecycle_stage,
            "report_timestamp": str(regime_snapshot.get("date") or mri_snapshot.get("date")),
            "sector": sector_intelligence.get("sector_name") or "UNKNOWN",
            "prior_baseline": prior_context
        },
        "executive_summary": build_executive_summary(
            symbol,
            regime_snapshot.get("classification", "NEUTRAL"),
            mri_snapshot,
            quality_snapshot,
            lifecycle_stage,
            fragility_snapshot,
            investor_context=investor_context,
        ),
        "narrative_transition": build_narrative_transition(
            symbol,
            company_name,
            sector_intelligence.get("sector_name"),
            quality_snapshot,
            mri_snapshot,
            lifecycle_stage,
        ),
        "engine_outputs": build_engine_outputs(
            mri_snapshot,
            quality_snapshot,
            regime_snapshot,
            stee_score,
            fragility_snapshot,
            perx_score,
            narrative_intensity,
            sector_intelligence,
            analogs,
            investor_context=investor_context,
        ),
        "institutional_forensic_review": forensic_review,
        "investor_context": investor_context,
        "lifecycle": {
            "stage": lifecycle_stage,
            "narrative_intensity": narrative_intensity,
        },
        "final_institutional_verdict": build_final_verdict(
            company_name,
            symbol,
            lifecycle_stage,
            perx_score,
            fragility_snapshot,
            quality_snapshot,
            mri_snapshot,
        ),
    }
    return _json_safe(report)


def generate_perx_report(
    symbol: str,
    conn,
    client_id: str | None = None,
    include_debate: bool = False,
    persist: bool = True,
) -> dict[str, Any]:
    base_symbol = normalize_symbol(symbol)
    cur = conn.cursor()

    # 1. Fetch current evidence
    mri_snapshot = _fetch_latest_mri_snapshot(cur, base_symbol)
    quality_snapshot = _fetch_latest_quality_snapshot(cur, base_symbol)
    financial_history = _fetch_financial_history(cur, base_symbol)
    regime_snapshot = _fetch_latest_regime(cur)
    
    # 2. Fetch previous report for context
    previous_report = _fetch_previous_report(cur, base_symbol, client_id)

    if not mri_snapshot:
        raise ValueError(
            f"PERX requires MRI price/indicator data for {base_symbol}. "
            "Please ensure the symbol is in the tracked universe and today's data has been ingested."
        )

    if not quality_snapshot or not financial_history:
        try:
            from engine_fundamental.collector import fetch_and_store_financials
            from engine_fundamental.pipeline import run_quality_pipeline
            yf_sym = f"{base_symbol}.NS" if not base_symbol.endswith((".NS", ".BO")) else base_symbol
            fetch_and_store_financials(yf_sym)
            run_quality_pipeline(base_symbol)
            quality_snapshot = _fetch_latest_quality_snapshot(cur, base_symbol)
            financial_history = _fetch_financial_history(cur, base_symbol)
        except Exception:
            pass

    company_name = _get_company_name(cur, base_symbol) or base_symbol
    sector = _get_sector(cur, base_symbol) or "UNKNOWN"
    
    # Calculate Sector Intelligence (V3)
    sector_intelligence = get_sector_context(cur, base_symbol, sector)
    
    # Calculate Investor Context & build report
    current_price = mri_snapshot.get("close") if mri_snapshot else None
    forensic_review = _build_forensic_review(base_symbol, include_debate=include_debate)
    report = _build_report_payload(
        base_symbol,
        company_name,
        sector_intelligence,
        mri_snapshot,
        quality_snapshot or {},
        financial_history,
        regime_snapshot,
        forensic_review,
        previous_report=previous_report,
        cur=cur,
        current_price=current_price,
    )

    # If report generation succeeded but investor context has data gaps,
    # attach a warnings block to the report
    report["_data_warnings"] = _collect_data_warnings(report, base_symbol)

    report_id = None
    if persist:
        try:
            summary = report["executive_summary"]
            cur.execute(
                """
                INSERT INTO perx_reports (
                    client_id, symbol, company_name, perx_score, lifecycle_stage,
                    report_json, summary, include_debate
                )
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                RETURNING id
                """,
                (
                    client_id,
                    base_symbol,
                    company_name,
                    report["header"]["perx_score"],
                    report["header"]["lifecycle_phase"],
                    json.dumps(report),
                    summary,
                    include_debate,
                ),
            )
            report_id = cur.fetchone()["id"]
            cur.execute(
                """
                INSERT INTO perx_scores (
                    symbol, latest_report_id, perx_score, lifecycle_stage,
                    narrative_intensity, fragility_level
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol) DO UPDATE SET
                    latest_report_id = EXCLUDED.latest_report_id,
                    perx_score = EXCLUDED.perx_score,
                    lifecycle_stage = EXCLUDED.lifecycle_stage,
                    narrative_intensity = EXCLUDED.narrative_intensity,
                    fragility_level = EXCLUDED.fragility_level,
                    generated_at = NOW()
                """,
                (
                    base_symbol,
                    report_id,
                    report["header"]["perx_score"],
                    report["header"]["lifecycle_phase"],
                    report["lifecycle"]["narrative_intensity"],
                    report["engine_outputs"]["fragility"]["level"],
                ),
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise PerxScanError(
                message=f"Failed to persist PERX report to database: {e}",
                error_type="DB_ERROR",
                action="This is likely a transient database issue. Try the scan again."
            )

    return {
        "report_id": report_id,
        "report": report,
    }


def fetch_perx_report(report_id: str, conn, client_id: str) -> dict[str, Any] | None:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, symbol, company_name, perx_score, lifecycle_stage,
               report_json, summary, include_debate, created_at
        FROM perx_reports
        WHERE id = %s AND client_id = %s
        """,
        (report_id, client_id),
    )
    row = cur.fetchone()
    if not row:
        return None
    report = dict(row)
    return report


def list_perx_reports_for_client(conn, client_id: str, limit: int = 10) -> list[dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, symbol, company_name, perx_score, lifecycle_stage,
               summary, include_debate, created_at
        FROM perx_reports
        WHERE client_id = %s
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (client_id, limit),
    )
    rows = cur.fetchall()
    return [dict(row) for row in rows]


def get_perx_score_history(conn, symbol: str, limit: int = 30) -> list[dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, symbol, perx_score, lifecycle_stage, created_at
        FROM perx_reports
        WHERE symbol = %s
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (normalize_symbol(symbol), limit),
    )
    rows = cur.fetchall()
    return [dict(row) for row in rows]


def list_perx_archive_for_client(
    conn,
    client_id: str,
    symbol: str | None = None,
    lifecycle_stage: str | None = None,
    min_score: float | None = None,
    max_score: float | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    cur = conn.cursor()
    conditions = ["client_id = %s"]
    params: list[Any] = [client_id]

    if symbol:
        conditions.append("symbol ILIKE %s")
        params.append(f"%{symbol.upper()}%")
    if lifecycle_stage:
        conditions.append("lifecycle_stage = %s")
        params.append(lifecycle_stage)
    if min_score is not None:
        conditions.append("perx_score >= %s")
        params.append(min_score)
    if max_score is not None:
        conditions.append("perx_score <= %s")
        params.append(max_score)
    if from_date:
        conditions.append("created_at >= %s")
        params.append(from_date)
    if to_date:
        conditions.append("created_at <= %s")
        params.append(to_date)

    where_clause = " AND ".join(conditions)

    cur.execute(f"SELECT COUNT(*) FROM perx_reports WHERE {where_clause}", params)
    row_count = cur.fetchone()
    total = row_count['count'] if isinstance(row_count, dict) else row_count[0]

    cur.execute(
        f"""
        SELECT id, symbol, company_name, perx_score, lifecycle_stage,
               summary, include_debate, created_at
        FROM perx_reports
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """,
        params + [limit, offset],
    )
    rows = cur.fetchall()
    return [dict(row) for row in rows], int(total)


def generate_perx_comparison(conn, symbol_a: str, symbol_b: str, client_id: str, include_debate: bool = False) -> dict[str, Any]:
    report_a = generate_perx_report(
        normalize_symbol(symbol_a), conn, client_id=client_id,
        include_debate=include_debate, persist=True,
    )
    report_b = generate_perx_report(
        normalize_symbol(symbol_b), conn, client_id=client_id,
        include_debate=include_debate, persist=True,
    )
    left = report_a["report"]
    right = report_b["report"]

    winner: dict[str, str] = {}
    differentials: list[str] = []

    score_a = float(left.get("header", {}).get("perx_score") or 0)
    score_b = float(right.get("header", {}).get("perx_score") or 0)
    winner["perx_score"] = "left" if score_a >= score_b else "right"

    mri_a = float(left.get("engine_outputs", {}).get("mri", {}).get("total_score") or 0)
    mri_b = float(right.get("engine_outputs", {}).get("mri", {}).get("total_score") or 0)
    winner["mri"] = "left" if mri_a >= mri_b else "right"

    qif_a = float(left.get("engine_outputs", {}).get("qif", {}).get("score") or 0)
    qif_b = float(right.get("engine_outputs", {}).get("qif", {}).get("score") or 0)
    winner["qif"] = "left" if qif_a >= qif_b else "right"

    frag_a = left.get("engine_outputs", {}).get("fragility", {}).get("level")
    frag_b = right.get("engine_outputs", {}).get("fragility", {}).get("level")
    frag_order = {"LOW": 0, "MODERATE": 1, "HIGH": 2}
    winner["fragility"] = "left" if (frag_order.get(frag_a, 0) <= frag_order.get(frag_b, 0)) else "right"

    lifecycle_rank = {"Accumulation": 0, "Early Rerating": 1, "Institutional Expansion": 2, "Euphoria": 3, "Distribution": 4}
    rank_a = lifecycle_rank.get(left.get("lifecycle", {}).get("stage"), 0)
    rank_b = lifecycle_rank.get(right.get("lifecycle", {}).get("stage"), 0)
    winner["lifecycle"] = "left" if rank_a >= rank_b else "right"

    if qif_a != qif_b:
        differentials.append(f"QIF: {'left' if qif_a > qif_b else 'right'} leads by {abs(qif_a - qif_b):.0f} points")
    if mri_a != mri_b:
        differentials.append(f"MRI: {'left' if mri_a > mri_b else 'right'} leads by {abs(mri_a - mri_b):.0f} points")
    if frag_a != frag_b:
        differentials.append(f"Fragility: {frag_a} vs {frag_b}")
    score_delta = round(score_a - score_b, 1)
    differentials.append(f"PERX delta: {score_delta:+.1f}")

    return {
        "report_id_a": report_a["report_id"],
        "report_id_b": report_b["report_id"],
        "left": left,
        "right": right,
        "comparison": {
            "winner": winner,
            "score_delta": score_delta,
            "key_differentials": differentials,
        },
    }
