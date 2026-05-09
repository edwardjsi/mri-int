from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

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
from engine_qualitative.debate import run_debate


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
        cur.execute("SELECT company_name FROM universe WHERE symbol = %s", (symbol,))
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


def _build_report_payload(
    symbol: str,
    company_name: str,
    sector: str | None,
    mri_snapshot: dict[str, Any],
    quality_snapshot: dict[str, Any],
    financial_history: list[dict[str, Any]],
    regime_snapshot: dict[str, Any],
    forensic_review: dict[str, Any],
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

    report = {
        "symbol": symbol,
        "company_name": company_name,
        "header": {
            "company_name": company_name,
            "symbol": symbol,
            "perx_score": perx_score,
            "lifecycle_phase": lifecycle_stage,
            "report_timestamp": str(regime_snapshot.get("date") or mri_snapshot.get("date")),
            "sector": sector or "UNKNOWN",
        },
        "executive_summary": build_executive_summary(
            symbol,
            regime_snapshot.get("classification", "NEUTRAL"),
            mri_snapshot,
            quality_snapshot,
            lifecycle_stage,
            fragility_snapshot,
        ),
        "narrative_transition": build_narrative_transition(
            symbol,
            company_name,
            sector,
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
            sector,
        ),
        "institutional_forensic_review": forensic_review,
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

    mri_snapshot = _fetch_latest_mri_snapshot(cur, base_symbol)
    quality_snapshot = _fetch_latest_quality_snapshot(cur, base_symbol)
    financial_history = _fetch_financial_history(cur, base_symbol)
    regime_snapshot = _fetch_latest_regime(cur)

    missing = []
    if not mri_snapshot:
        missing.append("stock_scores/daily_prices")
    if not quality_snapshot:
        missing.append("quality_verdicts")
    if not financial_history:
        missing.append("fundamental_financials")
    if missing:
        raise ValueError(
            f"PERX V1 currently requires existing MRI and QIF coverage for {base_symbol}. Missing: {', '.join(missing)}."
        )

    company_name = _get_company_name(cur, base_symbol) or base_symbol
    sector = _get_sector(cur, base_symbol) or "UNKNOWN"
    forensic_review = _build_forensic_review(base_symbol, include_debate=include_debate)
    report = _build_report_payload(
        base_symbol,
        company_name,
        sector,
        mri_snapshot,
        quality_snapshot,
        financial_history,
        regime_snapshot,
        forensic_review,
    )

    report_id = None
    if persist:
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
