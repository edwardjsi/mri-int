"""
CAS Recommendations API (Decision 103 — V2 Pyramiding Discipline Gates).

Endpoints:
  GET /api/cas/recommendations
      Returns recent CAS recommendations from cas_recommendations table.
      Optionally filtered by ?symbol=X, ?days=N (default 30), ?limit=N (default 50).
      Each row surfaces the V2 4-state decision layer + per-row gate breakdown
      from factor_snapshot JSONB (final_state, gates, gate_score_pct,
      resistance_source, config_snapshot). V1.1d rows (no V2 keys in snapshot)
      return None for the V2 fields — graceful backward compat.

  GET /api/cas/add-eligibility  (P4d — added in next sub-task)
      Per-symbol gate evaluation for the P5 AddStatusChip hover popover.

Created in P4c. Register this router in api/main.py.
"""
from fastapi import APIRouter, Depends, Query
from api.deps import get_db
import psycopg2.extras
import logging
from typing import Any, Optional
from datetime import datetime, timezone

# Decision 103 P4d — engine wiring
from engine_core.cas_recommendations import evaluate_add_gates
from engine_core.cas_decision_layer import compute_layered_state
from engine_core.capital_allocation import load_config as _load_cas_yaml
# Reuse the radar's MOSI Lite enrichment (decision_score + mri_technical_score)
from api.breakout_status import _enrich_with_mosi_lite

router = APIRouter(prefix="/api/cas", tags=["CAS Recommendations"])
log = logging.getLogger(__name__)

# Module-level config cache — load once, reuse per-request. If YAML changes
# at runtime, the API process must be restarted for new thresholds to apply
# (matches the indicator_engine pattern).
_CAS_CONFIG_CACHE: dict[str, Any] = {}


def _get_cas_config() -> dict[str, Any]:
    """Load and cache config/capital_allocation.yaml. Returns the full dict;
    callers should pull .get('add_gate', {}) for the V2 gate thresholds."""
    if "config" not in _CAS_CONFIG_CACHE:
        _CAS_CONFIG_CACHE["config"] = _load_cas_yaml("config/capital_allocation.yaml")
    return _CAS_CONFIG_CACHE["config"]


def _expand_factor_snapshot(row: dict) -> dict:
    """
    Hoist the V2 decision-layer fields out of factor_snapshot JSONB to the
    top level of the response so the P5 frontend can read them directly.

    factor_snapshot (V2 shape) keys we extract:
      - final_state:        'OBSERVE' | 'APPROACHING_ADD' | 'READY_FOR_ADD' | 'ADD_SECOND_TRANCHE'
      - gates:              dict with keys {passed, total, blocked}
      - gate_score_pct:     float (0–100)
      - resistance_source:  'PRIOR_52W_HIGH' | 'ALL_TIME_HIGH'
      - config_snapshot:    dict with version + threshold values

    V1.1d rows have a factor_snapshot without these keys — they return None
    so the UI can show "—" rather than crashing.
    """
    snap = row.get("factor_snapshot") or {}
    # V1.1d rows: factor_snapshot is a flat dict of factor scores.
    # V2 rows: factor_snapshot has the V2 nested keys.
    # We tolerate both — missing V2 keys => None.
    out = dict(row)  # shallow copy; preserves all base columns
    out["final_state"] = snap.get("final_state")
    gates = snap.get("gates")
    if isinstance(gates, dict):
        out["gates"] = {
            "passed": gates.get("passed"),
            "total": gates.get("total"),
            "blocked": gates.get("blocked", []),
        }
    else:
        out["gates"] = None
    out["gate_score_pct"] = snap.get("gate_score_pct")
    out["resistance_source"] = snap.get("resistance_source")
    out["config_snapshot"] = snap.get("config_snapshot")
    # Keep the raw factor_snapshot too — useful for the frontend hover popover
    # that wants the full sub-score breakdown (weekly, breakout, volume, etc.).
    return out


@router.get("/recommendations")
def list_cas_recommendations(
    symbol: Optional[str] = Query(None, description="Filter to a single symbol"),
    days: int = Query(30, ge=1, le=365, description="Look-back window in days"),
    limit: int = Query(50, ge=1, le=500, description="Max rows to return"),
    conn=Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Return recent CAS recommendations with V2 decision-layer fields expanded.

    Filters:
      - symbol: optional exact match
      - days:   only recs with recommendation_date >= today - days (default 30)
      - limit:  hard cap on rows (default 50, max 500)

    Response shape (per row):
      {
        recommendation_id, recommendation_date, symbol, regime,
        market_score, cas, confidence_stars, action,
        price_at_recommendation, cas_version, config_hash,
        created_at,
        # V2 fields (None for V1.1d rows):
        final_state, gates, gate_score_pct,
        resistance_source, config_snapshot,
        factor_snapshot   # raw JSONB (full sub-score breakdown)
      }
    """
    where_clauses = ["recommendation_date >= CURRENT_DATE - (%(days)s || ' days')::interval"]
    params: dict[str, Any] = {"days": int(days), "limit": int(limit)}
    if symbol:
        where_clauses.append("symbol = %(symbol)s")
        params["symbol"] = symbol.upper()

    where_sql = " AND ".join(where_clauses)
    query = f"""
        SELECT
            recommendation_id,
            recommendation_date,
            symbol,
            regime,
            market_score,
            cas,
            confidence_stars,
            action,
            price_at_recommendation,
            factor_snapshot,
            cas_version,
            config_hash,
            commit_sha,
            engine_signature,
            created_at
        FROM cas_recommendations
        WHERE {where_sql}
        ORDER BY recommendation_date DESC, symbol ASC
        LIMIT %(limit)s
    """

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(query, params)
        rows = cur.fetchall()
        return [_expand_factor_snapshot(dict(r)) for r in rows]
    except Exception as e:
        log.error(f"CAS recommendations error: {e}")
        return []
    finally:
        cur.close()


@router.get("/add-eligibility")
def get_add_eligibility(
    symbol: str = Query(..., description="Stock symbol (e.g. WELCORP)"),
    client_id: str = Query(..., description="Client UUID from client_portfolio.client_id"),
    conn=Depends(get_db),
) -> dict[str, Any]:
    """
    Decision 103 V2 — per-(symbol, client) ADD_SECOND_TRANCHE gate evaluation.

    Powers the P5 AddStatusChip hover popover. Returns the full 4-state result
    (OBSERVE / APPROACHING_ADD / READY_FOR_ADD / ADD_SECOND_TRANCHE) plus the
    per-gate breakdown so the UI can show "5/6 gates passed" and which gate
    is blocking.

    Reads:
      - daily_prices (latest row): breakout_state, breakout_age, V2 cols
        (weekly_close_above_resistance, breakout_day_volume_ratio,
        volume_confirmed_breakout, resistance_source)
      - cas_recommendations (latest for symbol): confidence_stars
      - client_portfolio: has_existing_position for (client_id, symbol)
      - config/capital_allocation.yaml: V2 gate thresholds + version

    Computes (via MOSI Lite enrichment, same path as /api/breakout/radar):
      - decision_score, mri_technical_score

    Response shape:
      {
        symbol, client_id, has_existing_position,
        evaluated_at,
        gate_inputs: { decision_score, mri_technical_score,
                       weekly_close_above_resistance, breakout_day_volume_ratio,
                       breakout_age, confidence_stars, resistance_source },
        gate_result: { passed, total, blocked, score_pct },
        final_state: 'OBSERVE' | 'APPROACHING_ADD' | 'READY_FOR_ADD' | 'ADD_SECOND_TRANCHE',
        config_snapshot: { version, decision_score_min, mri_technical_min,
                           breakout_age_max, breakout_volume_ratio,
                           confidence_stars_min },
        error?: str   # when symbol has no CAS recommendation yet
      }
    """
    symbol_u = symbol.upper().strip()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # 1. Latest daily_prices row for the symbol (V2 cols + breakout state)
        cur.execute(
            """
            SELECT date, close, breakout_state, breakout_age,
                   prior_52w_high, all_time_high_before_current_week,
                   resistance_source, weekly_close_above_resistance,
                   breakout_day_volume_ratio, volume_confirmed_breakout,
                   breakout_date_for_volume
            FROM daily_prices
            WHERE symbol = %(symbol)s
            ORDER BY date DESC
            LIMIT 1
            """,
            {"symbol": symbol_u},
        )
        dp_row = cur.fetchone()
        if not dp_row:
            return {
                "symbol": symbol_u,
                "client_id": client_id,
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
                "error": "no_market_data",
                "message": f"No daily_prices row found for {symbol_u}",
            }
        dp = dict(dp_row)

        # 2. Latest cas_recommendation for confidence_stars
        cur.execute(
            """
            SELECT confidence_stars, cas, action, recommendation_date
            FROM cas_recommendations
            WHERE symbol = %(symbol)s
            ORDER BY recommendation_date DESC
            LIMIT 1
            """,
            {"symbol": symbol_u},
        )
        cas_row = cur.fetchone()
        if not cas_row:
            return {
                "symbol": symbol_u,
                "client_id": client_id,
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
                "error": "no_cas_recommendation",
                "message": (
                    f"No CAS recommendation found for {symbol_u}. "
                    "Run indicator engine + CAS scanner first."
                ),
            }
        cas = dict(cas_row)

        # 3. has_existing_position from client_portfolio
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM client_portfolio
                WHERE client_id = %(client_id)s
                  AND symbol = %(symbol)s
                  AND is_open = true
            ) AS has_position
            """,
            {"client_id": client_id, "symbol": symbol_u},
        )
        has_position = bool(cur.fetchone()["has_position"])

        # 4. decision_score + mri_technical_score via the radar enrichment path.
        # Build a single-row list shaped like a radar row, then call the
        # existing _enrich_with_mosi_lite helper (same code path /api/breakout/radar uses).
        cur.execute(
            "SELECT close, volume, ema_50, ema_200 FROM daily_prices WHERE symbol = %(symbol)s ORDER BY date DESC LIMIT 1",
            {"symbol": symbol_u},
        )
        radar_row = dict(cur.fetchone() or {})
        radar_row["symbol"] = symbol_u
        radar_row["breakout_state"] = dp.get("breakout_state")
        radar_row["breakout_age"] = dp.get("breakout_age")
        enriched_rows = _enrich_with_mosi_lite(conn, [radar_row])
        enriched = enriched_rows[0] if enriched_rows else {}
        decision_score = float(enriched.get("decision_score") or 0)
        mri_technical_score = float(enriched.get("mri_technical_score") or 0)

        # 5. Build gate_inputs dict (matches P3 engine contract)
        bdvr = dp.get("breakout_day_volume_ratio")
        gate_inputs: dict[str, Any] = {
            "decision_score": decision_score,
            "mri_technical_score": mri_technical_score,
            "weekly_close_above_resistance": bool(dp.get("weekly_close_above_resistance") or False),
            "breakout_day_volume_ratio": float(bdvr) if bdvr is not None else 0.0,
            "breakout_age": int(dp.get("breakout_age")) if dp.get("breakout_age") is not None else 999,
            "confidence_stars": int(cas.get("confidence_stars") or 0),
            "resistance_source": dp.get("resistance_source"),
        }

        # 6. Load V2 config + evaluate gates + derive final_state
        config = _get_cas_config()
        gate_result = evaluate_add_gates(gate_inputs, config)
        final_state = compute_layered_state(
            decision_score,
            gate_result.blocked_gates,
            has_position,
            config,
        )

        # 7. Build config_snapshot for the UI (matches C5 auditability)
        add_gate_cfg = (config.get("add_gate") or {}) if isinstance(config, dict) else {}
        config_snapshot = {
            "version": add_gate_cfg.get("version", "2.0.0"),
            "decision_score_min": add_gate_cfg.get("decision_score_min", 85),
            "mri_technical_min": add_gate_cfg.get("mri_technical_min", 80),
            "breakout_age_max": add_gate_cfg.get("breakout_age_max", 15),
            "breakout_volume_ratio": add_gate_cfg.get("breakout_volume_ratio", 1.3),
            "confidence_stars_min": add_gate_cfg.get("confidence_stars_min", 4),
        }

        return {
            "symbol": symbol_u,
            "client_id": client_id,
            "has_existing_position": has_position,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "gate_inputs": gate_inputs,
            "gate_result": {
                "passed": gate_result.gates_passed,
                "total": gate_result.gates_total,
                "blocked": list(gate_result.blocked_gates),
                "score_pct": gate_result.gate_score_pct,
            },
            "final_state": final_state,
            "config_snapshot": config_snapshot,
            "breakout_state": dp.get("breakout_state"),
            "cas_action": cas.get("action"),
            "cas_score": float(cas.get("cas") or 0),
        }
    except Exception as e:
        log.error(f"add-eligibility error for {symbol_u}/{client_id}: {e}")
        return {
            "symbol": symbol_u,
            "client_id": client_id,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "error": "internal_error",
            "message": str(e),
        }
    finally:
        cur.close()
