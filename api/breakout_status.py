from fastapi import APIRouter, Depends
from api.deps import get_db
import psycopg2.extras
import logging
from typing import Any

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from engine_mosi.mosi_lite import analyze_stock
from engine_core.capital_allocation import (
    load_config, check_eligibility, compute_market_structure,
    compute_market_score, compute_portfolio_allocation_score,
    compute_confidence_stars, render_why_checklist,
    _regime_score, _weekly_score, _breakout_score,
    _rs_score, _volume_score, _sector_score
)

router = APIRouter(prefix="/api/breakout", tags=["Breakout Status"])
log = logging.getLogger(__name__)

# Load CAS configuration once on import
_cas_config = load_config("config/capital_allocation.yaml")


# ── Helper: enrich radar rows with MOSI Lite data ────────────────────────

def _enrich_with_mosi_lite(
    conn: Any,
    rows: list[dict],
) -> list[dict]:
    """
    Take base radar rows (symbol, close, volume, ema_50, ema_200, breakout_state)
    and add: mri_technical_score, QIF scores, fundamental data, then call
    analyze_stock() to compute mosi_lite_score, decision_score, etc.

    Returns the same list with new fields appended. Mutates in-place for
    simplicity.
    """
    if not rows:
        return rows

    symbols = [r["symbol"] for r in rows]
    placeholders = ",".join("%%(%(i)s)s" % {"i": i} for i in range(len(symbols)))
    # Actually simpler: use a single SQL with psycopg2 list param

    # ── 1. Fetch MRI technical scores from stock_scores ──
    score_sql = """
        SELECT DISTINCT ON (symbol)
            symbol,
            total_score
        FROM stock_scores
        WHERE symbol = ANY(%(symbols)s)
        ORDER BY symbol, date DESC
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(score_sql, {"symbols": symbols})
        scores = {r["symbol"]: r["total_score"] for r in cur.fetchall()}
    except Exception:
        scores = {}
    finally:
        cur.close()

    # ── 2. Fetch QIF / fundamental data ──
    fund_sql = """
        SELECT DISTINCT ON (symbol)
            symbol,
            roce_score,
            revenue_score,
            margin_score,
            leverage_score,
            wc_score,
            evolution_score,
            agent_details
        FROM quality_verdicts
        WHERE symbol = ANY(%(symbols)s)
        ORDER BY symbol
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(fund_sql, {"symbols": symbols})
        qif = {r["symbol"]: r for r in cur.fetchall()}
    except Exception:
        qif = {}
    finally:
        cur.close()

    # ── 3. Fetch latest 2-year financials (for YoY growth) ──
    ff_sql = """
        SELECT
            symbol,
            year,
            revenue,
            net_profit,
            debt,
            equity,
            capital_employed
        FROM fundamental_financials
        WHERE symbol = ANY(%(symbols)s)
        ORDER BY symbol, year DESC
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(ff_sql, {"symbols": symbols})
        ff_rows = cur.fetchall()
        # Group by symbol: {symbol: [year N, year N-1]}
        fin_year_map: dict[str, list[dict]] = {}
        for r in ff_rows:
            sym = r["symbol"]
            if sym not in fin_year_map:
                fin_year_map[sym] = []
            fin_year_map[sym].append(r)
    except Exception:
        fin_year_map = {}
    finally:
        cur.close()

    # ── 4. For each row, build StockData and call analyze_stock ──
    for row in rows:
        sym = row["symbol"]

        # MRI technical score
        row["mri_technical_score"] = scores.get(sym, 0)

        # QIF fields
        qif_row = qif.get(sym, {})
        row["roce_score"] = qif_row.get("roce_score", 0)
        row["revenue_score"] = qif_row.get("revenue_score", 0)
        row["margin_score"] = qif_row.get("margin_score", 0)
        row["leverage_score"] = qif_row.get("leverage_score", 0)
        row["wc_score"] = qif_row.get("wc_score", 0)
        row["evolution_score"] = qif_row.get("evolution_score", 0)

        # Agent details JSONB — extract key metrics
        agent_details = qif_row.get("agent_details")
        if agent_details and isinstance(agent_details, dict):
            row["sales_growth_pct"] = agent_details.get("growth_yoy_pct", 0)
            row["profit_growth_pct"] = agent_details.get("profit_growth_yoy", 0)
            row["roce_pct"] = agent_details.get("roce_pct", 0)
        else:
            row["sales_growth_pct"] = 0
            row["profit_growth_pct"] = 0
            row["roce_pct"] = 0

        # Fundamental financials: use latest 2 years
        fin_years = fin_year_map.get(sym, [])
        if len(fin_years) >= 2:
            cur_, prev_ = fin_years[0], fin_years[1]
            # Sales growth
            cur_rev = cur_.get("revenue", 0) or 0
            prev_rev = prev_.get("revenue", 0) or 0
            if prev_rev > 0:
                row["sales_growth_pct"] = ((cur_rev - prev_rev) / prev_rev) * 100
            # Profit growth
            cur_np = cur_.get("net_profit", 0) or 0
            prev_np = prev_.get("net_profit", 0) or 0
            if prev_np > 0:
                row["profit_growth_pct"] = ((cur_np - prev_np) / prev_np) * 100
            # Debt / Equity
            row["debt_to_equity"] = (cur_.get("debt", 0) or 0) / max((cur_.get("equity", 0) or 1), 1)
        else:
            # Use QIF fallback
            row["sales_growth_pct"] = row.get("sales_growth_pct", 0)
            row["profit_growth_pct"] = row.get("profit_growth_pct", 0)
            row["debt_to_equity"] = (
                (qif_row.get("debt", 0) or 0)
                / max((qif_row.get("equity", 0) or 1), 1)
            )

        # Call MOSI Lite scorer
        mosi_output = analyze_stock(row)
        row["mosi_lite_score"] = mosi_output["mosi_lite_score"]
        row["decision_score"] = mosi_output["decision_score"]
        row["confidence"] = mosi_output["confidence"]
        row["recommendation"] = mosi_output["recommendation"]
        row["m_macro_score"] = mosi_output["m_macro_score"]
        row["o_operating_score"] = mosi_output["o_operating_score"]
        row["s_structural_score"] = mosi_output["s_structural_score"]
        row["i_institutional_score"] = mosi_output["i_institutional_score"]

    return rows


AGE_DECAY = {
    0: 1.00,
    1: 1.00,
    2: 0.90,
    3: 0.85,
    4: 0.70,
    5: 0.65,
}
DEFAULT_DECAY = 0.40

def _age_label(state: str, age: int | None) -> dict:
    """Return human-readable label and emoji for breakout age."""
    if state == 'CONSOLIDATING' or state is None:
        return {"label": "CONSOLIDATING", "emoji": "⏳", "zone": "none"}

    # State is BROKEN_OUT or READY_TO_BREAKOUT, but age is unknown.
    # Show state-only fallback so the UI is useful even before the backfill
    # populates breakout_age. Distinguishes "no age data yet" from "no breakout".
    if age is None:
        if state == 'BROKEN_OUT':
            return {"label": "BROKEN OUT", "emoji": "🚀", "zone": "unknown"}
        if state == 'READY_TO_BREAKOUT':
            return {"label": "READY", "emoji": "⚡", "zone": "unknown"}
        return {"label": state, "emoji": "", "zone": "unknown"}

    if state == 'BROKEN_OUT':
        if age == 0:
            return {"label": "BREAKOUT TODAY", "emoji": "🔥", "zone": "fresh"}
        elif age == 1:
            return {"label": "FIRST FOLLOW-THROUGH", "emoji": "✅", "zone": "fresh"}
        elif age <= 3:
            return {"label": "EARLY CONTINUATION", "emoji": "📈", "zone": "early"}
        elif age <= 5:
            return {"label": "LATE ENTRY ZONE", "emoji": "⚠️", "zone": "late"}
        else:
            return {"label": "MATURE BREAKOUT", "emoji": "💤", "zone": "mature"}

    if state == 'READY_TO_BREAKOUT':
        if age <= 2:
            return {"label": "FRESH SETUP", "emoji": "⚡", "zone": "fresh"}
        elif age <= 7:
            return {"label": "VCP COILING", "emoji": "🌀", "zone": "coiling"}
        else:
            return {"label": "MATURE SETUP", "emoji": "⏳", "zone": "mature"}

    return {"label": state, "emoji": "", "zone": "unknown"}


@router.get("/top-by-cas")
def get_top_by_cas(limit: int = 5, conn=Depends(get_db)):
    """
    Return the top N breakouts by Capital Allocation Score (CAS).
    Reads daily_prices, applies 6 eligibility + 3 sub-gates, computes CAS
    for survivors, ranks by CAS DESC, returns the top `limit`.

    Decision 104 (N+3 — Browser Visibility) — this is the endpoint that
    makes Decision 100's CAS output visible in the browser.
    """
    # ── Fetch latest regime ──
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT classification FROM market_regime ORDER BY date DESC LIMIT 1")
        regime_row = cur.fetchone()
        regime = (regime_row["classification"] or "NEUTRAL") if regime_row else "NEUTRAL"
    except Exception as e:
        log.warning(f"Could not fetch regime, defaulting to NEUTRAL: {e}")
        regime = "NEUTRAL"
    finally:
        cur.close()

    query = """
        SELECT
            symbol, close, volume, breakout_state, breakout_age,
            ema_50, ema_200, ema_20, ema_100_slope_5d,
            weekly_trend_score, overhead_supply_score, rs_90d,
            qif_score, data_completeness_pct, data_age_days,
            avg_volume_20d, rolling_high_52w,
            winner_profit_pct, concentration_weight_pct
        FROM daily_prices
        WHERE date = (SELECT MAX(date) FROM daily_prices)
        ORDER BY symbol
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(query)
        rows = cur.fetchall()
    except Exception as e:
        log.error(f"Top-by-CAS query failed: {e}")
        return []
    finally:
        cur.close()

    if not rows:
        return []

    config = _cas_config
    results = []
    for row in rows:
        # 0. Enrich: proxy qif_score when missing (same fallback as CAS scanner)
        if row.get("qif_score") is None:
            proxy_q = config.get("market_subgates", {}).get("quality", {}).get("min_quality", 75)
            row["qif_score"] = proxy_q

        # 1. Eligibility (now includes regime)
        passed, _ = check_eligibility(row, regime, config)
        if not passed:
            continue

        # 2. Market structure
        passed, _ = compute_market_structure(row, config)
        if not passed:
            continue

        # 3. Build sub-scores and compute Market Score
        sub_scores = {
            "regime":          _regime_score(regime, config),
            "weekly":          _weekly_score(row, config),
            "breakout":        _breakout_score(row, config),
            "overhead_supply": row.get("overhead_supply_score") or 0,
            "rs":              _rs_score(row, config),
            "volume":          _volume_score(row, config),
            "sector":          _sector_score(row, config),
        }
        market_score = compute_market_score(sub_scores, config)

        # 4. Portfolio Allocation Score
        cas = compute_portfolio_allocation_score(
            market_score,
            row.get("winner_profit_pct"),
            row.get("concentration_weight_pct"),
            config
        )

        # 5. Confidence stars
        stars = compute_confidence_stars(row, sub_scores, {}, config)

        # 6. Why checklist
        why = render_why_checklist(row, config)

        results.append({
            "symbol": row["symbol"],
            "cas": round(cas, 1),
            "confidence_stars": stars,
            "why_checklist": why,
            "breakout_age": row.get("breakout_age"),
            "breakout_age_emoji": "🔥" if row.get("breakout_age") == 0
                                 else "🟢" if row.get("breakout_age") <= 1
                                 else "🟡" if row.get("breakout_age") <= 3
                                 else "⚪" if row.get("breakout_age") <= 5
                                 else "⚫"
        })

    # Sort by CAS DESC, take top N
    results.sort(key=lambda r: r["cas"], reverse=True)
    return results[:min(limit, len(results))]


@router.get("/map")
def get_breakout_map(conn=Depends(get_db)):
    """
    Return a dict {symbol: "READY_TO_BREAKOUT" | "BROKEN_OUT" | "CONSOLIDATING"}.
    Pulls directly from the engine-calculated `breakout_state` column in the daily_prices table.
    """
    query = """
        SELECT
            cw.symbol,
            COALESCE(dp.breakout_state, 'CONSOLIDATING') AS state
        FROM client_watchlist cw
        LEFT JOIN (
            SELECT DISTINCT ON (symbol)
                symbol,
                breakout_state
            FROM daily_prices
            ORDER BY symbol, date DESC
        ) dp ON dp.symbol = cw.symbol;
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(query)
        rows = cur.fetchall()
        return {r["symbol"]: r["state"] for r in rows}
    except Exception as e:
        log.error(f"Breakout map error: {e}")
        return {}
    finally:
        cur.close()

@router.get("/radar")
def get_breakout_radar(conn=Depends(get_db)):
    """
    Return: (1) all watchlist/portfolio stocks with their breakout state,
    plus (2) any BROKEN_OUT or READY_TO_BREAKOUT stocks from the full
    universe that aren't already in a watchlist (for discovery).
    
    Each row now also carries MOSI Lite fields: mri_technical_score,
    mosi_lite_score, decision_score, confidence, recommendation. These
    are computed server-side by calling analyze_stock() from
    engine_mosi.mosi_lite.
    """
    query = """
        SELECT symbol, close, volume, ema_50, ema_200, breakout_state, breakout_age, watchers, holders
        FROM (
            SELECT 
                dp.symbol, dp.close, dp.volume, dp.ema_50, dp.ema_200, dp.breakout_state, dp.breakout_age,
                -- Decision 103 V2 ADD_SECOND_TRANCHE gate indicators (P4b)
                dp.prior_52w_high, dp.all_time_high_before_current_week,
                dp.resistance_source, dp.weekly_close_above_resistance,
                dp.breakout_day_volume_ratio, dp.volume_confirmed_breakout,
                dp.breakout_date_for_volume,
                (SELECT COUNT(DISTINCT client_id) FROM client_watchlist WHERE symbol = dp.symbol) as watchers,
                (SELECT COUNT(DISTINCT client_id) FROM client_portfolio WHERE symbol = dp.symbol AND is_open = true) as holders,
                0 as sort_grp
            FROM daily_prices dp
            WHERE dp.date = (SELECT MAX(date) FROM daily_prices)
              AND (EXISTS (SELECT 1 FROM client_watchlist WHERE symbol = dp.symbol)
                   OR EXISTS (SELECT 1 FROM client_portfolio WHERE symbol = dp.symbol AND is_open = true))

            UNION

            SELECT 
                dp.symbol, dp.close, dp.volume, dp.ema_50, dp.ema_200, dp.breakout_state, dp.breakout_age,
                -- Decision 103 V2 ADD_SECOND_TRANCHE gate indicators (P4b)
                dp.prior_52w_high, dp.all_time_high_before_current_week,
                dp.resistance_source, dp.weekly_close_above_resistance,
                dp.breakout_day_volume_ratio, dp.volume_confirmed_breakout,
                dp.breakout_date_for_volume,
                (SELECT COUNT(DISTINCT client_id) FROM client_watchlist WHERE symbol = dp.symbol) as watchers,
                (SELECT COUNT(DISTINCT client_id) FROM client_portfolio WHERE symbol = dp.symbol AND is_open = true) as holders,
                1 as sort_grp
            FROM daily_prices dp
            WHERE dp.date = (SELECT MAX(date) FROM daily_prices)
              AND dp.breakout_state IN ('BROKEN_OUT', 'READY_TO_BREAKOUT')
              AND NOT (EXISTS (SELECT 1 FROM client_watchlist WHERE symbol = dp.symbol)
                       OR EXISTS (SELECT 1 FROM client_portfolio WHERE symbol = dp.symbol AND is_open = true))
        ) combined
        ORDER BY 
            sort_grp,
            CASE breakout_state
                WHEN 'BROKEN_OUT' THEN 1
                WHEN 'READY_TO_BREAKOUT' THEN 2
                ELSE 3
            END,
            COALESCE(breakout_age, 999) ASC,
            symbol;
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(query)
        rows = cur.fetchall()
        # ── Enrich each row with MOSI Lite scores ──
        rows = _enrich_with_mosi_lite(conn, rows)
        
        # ── Add Breakout Age labels and priority ──
        for row in rows:
            age = row.get("breakout_age")
            state = row.get("breakout_state", "CONSOLIDATING")
            row["age_info"] = _age_label(state, age)
            
            # Compute radar priority
            base_score = row.get("decision_score", 0)
            if state == 'BROKEN_OUT' and age is not None:
                decay = AGE_DECAY.get(age, DEFAULT_DECAY)
                row["radar_priority"] = round(base_score * decay, 1)
            else:
                row["radar_priority"] = base_score
                
        return rows
    except Exception as e:
        log.error(f"Breakout radar error: {e}")
        return []
    finally:
        cur.close()
