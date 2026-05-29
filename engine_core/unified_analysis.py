"""
Unified Analysis Engine — PERX + AAE + GuidanceCheck + MOSI Gaps

Composes all three MRI institutional engines into a single unified report,
plus closes MOSI AI Master Analysis gaps (multi-bagger rubric, peer fundamentals).

Architecture:
    UnifiedAnalyzer.run(symbol)
        ├── generate_perx_report()        [PERX: scoring, lifecycle, investor context]
        ├── ReRatingOrchestrator          [AAE: 10-layer forensic, governance, debate]
        ├── CredibilityScorer             [GuidanceCheck: management credibility]
        └── MOSI gap functions:
            ├── compute_multi_bagger_score()     [7-dim rubric (0-10)]
            ├── get_ps_ratio()                   [P/S valuation]
            ├── get_formatted_quarterly_table()  [6Q performance table]
            └── get_peer_fundamental_comparison() [OPM/ROCE/CAGR vs peers]
"""
from __future__ import annotations

import logging
from typing import Any

from engine_core.db import get_connection

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# MOSI Gap 1.4: Multi-Bagger Probability Score (MOSI Step 14)
# ═══════════════════════════════════════════════════════════════════════════════

def _safe_float(v: Any) -> float:
    if v is None:
        return 0.0
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def compute_multi_bagger_score(
    perx_report: dict,
    aae_scan: dict | None = None,
    guidance_data: dict | None = None,
    quarterly_table: dict | None = None,
) -> dict[str, Any]:
    """
    MOSI Step 14: Multi-Bagger Probability Score (0-10).

    Scored across 7 weighted dimensions using the MOSI rubric:
      Revenue growth (1.5) + Margin expansion (1.5) + ROCE quality (1.5)
      + TAM headroom (1.5) + Balance sheet (1) + Narrative confirmation (1)
      + Stage cycle (1) = Maximum 10.0
    """
    total = 0.0
    breakdown: dict[str, dict] = {}

    # ── Data Sources ────────────────────────────────────────────────────
    # PERX engine outputs
    engine = perx_report.get("engine_outputs", {})
    qif = engine.get("qif", {})
    mri_block = engine.get("mri", {})
    investor_ctx = perx_report.get("investor_context", {})

    # AAE scan
    aae = aae_scan or {}

    # Earnings momentum
    earnings = investor_ctx.get("earnings_momentum", {})

    # ── Dimension 1: Revenue Growth (max 1.5) ───────────────────────────
    rev_cagr = None
    latest_q_growth = None
    if quarterly_table and quarterly_table.get("quarters"):
        qs = quarterly_table["quarters"]
        # Revenue CAGR from quarterly data: latest vs 4Q ago
        if len(qs) >= 4:
            latest_4q_rev = sum(q.get("revenue_cr", 0) or 0 for q in qs[-4:])
            prior_4q_rev = sum(q.get("revenue_cr", 0) or 0 for q in qs[:min(4, len(qs))])
            if prior_4q_rev and prior_4q_rev > 0:
                rev_cagr = ((latest_4q_rev - prior_4q_rev) / prior_4q_rev) * 100
        # Latest quarter YoY
        if qs:
            latest_q = qs[-1]
            latest_q_growth = latest_q.get("rev_yoy_pct")

    if rev_cagr is not None and rev_cagr >= 25 and latest_q_growth is not None and latest_q_growth >= 25:
        rev_score = 1.5
        rev_reason = f"CAGR {rev_cagr:.1f}%, latest Q {latest_q_growth:.1f}% — full score"
    elif rev_cagr is not None and rev_cagr >= 15:
        rev_score = 0.75
        rev_reason = f"CAGR {rev_cagr:.1f}% — half score"
    elif rev_cagr is not None:
        rev_score = 0.0
        rev_reason = f"CAGR {rev_cagr:.1f}% < 15% — zero"
    else:
        # Fallback: use earnings momentum growth
        rev_growth = earnings.get("revenue_growth_4q_pct")
        if rev_growth is not None and rev_growth >= 25:
            rev_score = 0.75
            rev_reason = f"H2 vs H1 growth {rev_growth:.1f}% — half (insufficient quarterly data for full check)"
        elif rev_growth is not None and rev_growth >= 15:
            rev_score = 0.5
            rev_reason = f"H2 vs H1 growth {rev_growth:.1f}%"
        else:
            rev_score = 0.0
            rev_reason = "Revenue growth data insufficient or below threshold"

    breakdown["revenue_growth"] = {"score": rev_score, "full_available": 1.5, "reason": rev_reason}
    total += rev_score

    # ── Dimension 2: Margin Expansion (max 1.5) ──────────────────────────
    margin_score = 0.0
    margin_reason = "Insufficient margin data"

    # Check PRDE margin quality component if available
    prde = investor_ctx.get("prde_score", {})
    components = prde.get("components", {})
    margin_comp = components.get("margin_quality", {})
    if margin_comp and margin_comp.get("score"):
        ms = float(margin_comp["score"])
        if ms >= 80:
            margin_score = 1.5
            margin_reason = f"Structural margin expansion (PRDE margin score {ms:.0f}/100)"
        elif ms >= 60:
            margin_score = 0.75
            margin_reason = f"Stable/gradual expansion (PRDE margin score {ms:.0f}/100)"
        else:
            margin_score = 0.0
            margin_reason = f"Margin pressure (PRDE margin score {ms:.0f}/100)"
    else:
        # Fallback: check earnings acceleration
        accel = earnings.get("acceleration", "")
        profit_growth = earnings.get("profit_growth_4q_pct")
        if profit_growth is not None and profit_growth > 0 and accel == "ACCELERATING":
            margin_score = 0.75
            margin_reason = f"Profit growth {profit_growth:.1f}% with acceleration — indicative of margin expansion"
        elif profit_growth is not None and profit_growth > 0:
            margin_score = 0.5
            margin_reason = f"Profit growth {profit_growth:.1f}% — stable"

    breakdown["margin_expansion"] = {"score": margin_score, "full_available": 1.5, "reason": margin_reason}
    total += margin_score

    # ── Dimension 3: ROCE Quality (max 1.5) ─────────────────────────────
    roce_score = 0.0
    roce_reason = "Insufficient ROCE data"
    roce_comp = components.get("capital_efficiency", {})
    if roce_comp and roce_comp.get("score"):
        rs = float(roce_comp["score"])
        if rs >= 80:
            roce_score = 1.5
            roce_reason = f"ROCE > 20%, rising (PRDE capital efficiency {rs:.0f}/100)"
        elif rs >= 60:
            roce_score = 0.75
            roce_reason = f"ROCE 15-20%, stable (PRDE capital efficiency {rs:.0f}/100)"
        else:
            roce_score = 0.0
            roce_reason = f"ROCE < 15% or falling (PRDE capital efficiency {rs:.0f}/100)"

    breakdown["roce_quality"] = {"score": roce_score, "full_available": 1.5, "reason": roce_reason}
    total += roce_score

    # ── Dimension 4: TAM Headroom (max 1.5) ─────────────────────────────
    # TAM data not available in our data sources — estimate from revenue vs sector
    # Default to half score since we can't measure TAM precisely
    tam_score = 0.75
    tam_reason = "TAM not directly measurable from current data sources. Default half score — assume 3-10x headroom for listed Indian companies with re-rating potential."
    breakdown["tam_headroom"] = {"score": tam_score, "full_available": 1.5, "reason": tam_reason}
    total += tam_score

    # ── Dimension 5: Balance Sheet Quality (max 1.0) ────────────────────
    bs_score = 0.0
    bs_reason = "Insufficient balance sheet data"
    bs_comp = components.get("balance_sheet", {})
    ev_ebitda_data = investor_ctx.get("ev_ebitda", {})
    nd_ebitda = ev_ebitda_data.get("net_debt_ebitda")

    if bs_comp and bs_comp.get("score"):
        bss = float(bs_comp["score"])
        if bss >= 80 and nd_ebitda is not None and nd_ebitda < 1.5:
            bs_score = 1.0
            bs_reason = f"D/E low, net debt/EBITDA {nd_ebitda:.1f}x (PRDE BS score {bss:.0f}/100)"
        elif bss >= 60:
            bs_score = 0.5
            bs_reason = f"D/E moderate (PRDE BS score {bss:.0f}/100)"
        else:
            bs_score = 0.0
            bs_reason = f"D/E elevated (PRDE BS score {bss:.0f}/100)"

    breakdown["balance_sheet"] = {"score": bs_score, "full_available": 1.0, "reason": bs_reason}
    total += bs_score

    # ── Dimension 6: Narrative Confirmation (max 1.0) ───────────────────
    narrative_score = 0.0
    narrative_reason = "Insufficient guidance data"

    if guidance_data and guidance_data.get("total_promises", 0) > 0:
        accuracy = guidance_data.get("accuracy_pct", 0)
        trend = guidance_data.get("trend", "")
        if trend == "IMPROVING" and accuracy >= 70:
            narrative_score = 1.0
            narrative_reason = f"CONFIRMED — management delivers on promises ({accuracy:.0f}%, {trend})"
        elif accuracy >= 60:
            narrative_score = 0.5
            narrative_reason = f"AHEAD OF NUMBERS — mixed delivery ({accuracy:.0f}%)"
        else:
            narrative_score = 0.0
            narrative_reason = f"NARRATIVE TRAP concerns — low credibility ({accuracy:.0f}%)"
    else:
        # Fallback: check AAE narrative layer
        aae_layers = aae.get("layers", {})
        aae_narrative = aae_layers.get("narrative", {})
        if aae_narrative and aae_narrative.get("score"):
            ns = float(aae_narrative["score"])
            if ns >= 70:
                narrative_score = 0.5
                narrative_reason = f"Narrative score {ns:.0f}/100 — positive (no verified track record yet)"
            else:
                narrative_score = 0.0
                narrative_reason = f"Narrative score {ns:.0f}/100 — caution"
        else:
            narrative_score = 0.25
            narrative_reason = "No management guidance track record — default low score"

    breakdown["narrative_confirmation"] = {"score": narrative_score, "full_available": 1.0, "reason": narrative_reason}
    total += narrative_score

    # ── Dimension 7: Stage Cycle (max 1.0) ──────────────────────────────
    stage_score = 0.0
    stage_reason = "Unknown lifecycle stage"
    lifecycle = perx_report.get("lifecycle", {})
    stage = lifecycle.get("stage", "") if isinstance(lifecycle, dict) else perx_report.get("header", {}).get("lifecycle_phase", "")

    early_stages = ["Early Rerating", "Accumulation", "Early Stage"]
    expansion_stages = ["Institutional Expansion", "Expansion Stage"]

    if stage in early_stages:
        stage_score = 1.0
        stage_reason = f"Early stage — {stage} (max re-rating potential ahead)"
    elif stage in expansion_stages:
        stage_score = 1.0
        stage_reason = f"Expansion stage — {stage} (growing institutional attention)"
    elif stage == "Early Maturity":
        stage_score = 0.5
        stage_reason = "Early Maturity — partial re-rating already priced in"
    elif stage in ("Distribution", "Euphoria", "Mature", "Ex-growth"):
        stage_score = 0.0
        stage_reason = f"{stage} — late cycle, limited re-rating upside"
    elif stage:
        stage_score = 0.5
        stage_reason = f"{stage} — not clearly early/expansion"

    breakdown["stage_cycle"] = {"score": stage_score, "full_available": 1.0, "reason": stage_reason}
    total += stage_score

    # ── Final Rating ────────────────────────────────────────────────────
    total = round(total, 1)
    if total >= 7.0:
        rating = "READY"      # ✅ Strong alignment
    elif total >= 4.5:
        rating = "GETTING READY"  # 🟡 Early signals
    else:
        rating = "NOT READY"  # 🔴 Structural risks

    return {
        "probability_score": total,
        "max_score": 10.0,
        "rating": rating,
        "breakdown": breakdown,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Unified Orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

class UnifiedAnalyzer:
    """
    Composes PERX, AAE, GuidanceCheck, and MOSI gap functions into a single
    unified institutional analysis report.

    Error isolation: if one engine fails, the others still produce results.
    """

    def __init__(self, symbol: str):
        self.symbol = symbol.upper().replace(".NS", "").replace(".BO", "")

    def run(self) -> dict[str, Any]:
        """Run all engines and return unified report payload."""
        conn = get_connection()
        warnings = []

        report = {
            "symbol": self.symbol,
            "generated_at": None,
            "signal": {},
            "perx": {},
            "aae": {},
            "guidance": {},
            "mosi_additions": {},
            "_warnings": [],
        }

        # ── PERX ────────────────────────────────────────────────────────
        try:
            from engine_perx.orchestrator import generate_perx_report
            perx_result = generate_perx_report(
                symbol=self.symbol,
                conn=conn,
                client_id=None,
                include_debate=True,
                persist=False,
            )
            report["perx"] = perx_result.get("report", perx_result)
            if perx_result.get("report", {}).get("header", {}).get("report_timestamp"):
                report["generated_at"] = perx_result["report"]["header"]["report_timestamp"]
        except Exception as e:
            logger.error(f"PERX scan failed for {self.symbol}: {e}")
            report["perx"] = {"error": str(e)}
            warnings.append(f"PERX: {str(e)[:120]}")

        # ── AAE ─────────────────────────────────────────────────────────
        try:
            from engine_core.aae_re_rating_orchestrator import ReRatingOrchestrator
            aae_orch = ReRatingOrchestrator(self.symbol)
            aae_result = aae_orch.build_profile()
            report["aae"] = aae_result
        except Exception as e:
            logger.error(f"AAE scan failed for {self.symbol}: {e}")
            report["aae"] = {"error": str(e)}
            warnings.append(f"AAE: {str(e)[:120]}")

        # ── GuidanceCheck ───────────────────────────────────────────────
        try:
            from engine_guidance.credibility_scorer import CredibilityScorer
            scorer = CredibilityScorer()
            guidance_result = scorer.compute_score(self.symbol)
            report["guidance"] = guidance_result
        except Exception as e:
            logger.error(f"GuidanceCheck failed for {self.symbol}: {e}")
            report["guidance"] = {"error": str(e), "total_promises": 0}
            warnings.append(f"GuidanceCheck: {str(e)[:120]}")

        # ── MOSI Additions ──────────────────────────────────────────────
        mosi = {}
        try:
            cur = conn.cursor()

            # P/S Ratio
            try:
                from engine_perx.investor_context import get_ps_ratio
                mosi["ps_ratio"] = get_ps_ratio(cur, self.symbol)
            except Exception as e:
                mosi["ps_ratio"] = {"verdict": f"Unavailable: {str(e)[:80]}"}

            # Formatted 6-quarter table
            try:
                from engine_perx.investor_context import get_formatted_quarterly_table
                mosi["quarterly_table"] = get_formatted_quarterly_table(cur, self.symbol)
            except Exception as e:
                mosi["quarterly_table"] = {"verdict": f"Unavailable: {str(e)[:80]}"}

            # Peer fundamental comparison
            try:
                # Get sector from perx report
                perx_report_data = report.get("perx", {})
                sector = perx_report_data.get("header", {}).get("sector", "UNKNOWN")
                from engine_perx.sector import get_peer_fundamental_comparison
                mosi["peer_fundamentals"] = get_peer_fundamental_comparison(cur, self.symbol, sector)
            except Exception as e:
                mosi["peer_fundamentals"] = {"verdict": f"Unavailable: {str(e)[:80]}"}

        except Exception as e:
            logger.error(f"MOSI additions failed: {e}")
            warnings.append(f"MOSI additions: {str(e)[:120]}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

        report["mosi_additions"] = mosi

        # ── Multi-Bagger Signal ─────────────────────────────────────────
        try:
            multi_bagger = compute_multi_bagger_score(
                perx_report=report["perx"],
                aae_scan=report["aae"],
                guidance_data=report["guidance"],
                quarterly_table=mosi.get("quarterly_table"),
            )
            report["signal"] = multi_bagger
        except Exception as e:
            logger.error(f"Multi-bagger scoring failed: {e}")
            report["signal"] = {"error": str(e)}
            warnings.append(f"Multi-bagger: {str(e)[:120]}")

        report["_warnings"] = warnings
        return report


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Unified Analysis Engine")
    parser.add_argument("--symbol", "-s", required=True, help="NSE ticker symbol")
    args = parser.parse_args()

    analyzer = UnifiedAnalyzer(args.symbol)
    result = analyzer.run()

    print(json.dumps(result, indent=2, default=str))
