import logging
from engine_fundamental.governance_engine import GovernanceEngine
from engine_fundamental.sector_engine import get_sector_engine
from engine_fundamental.ownership_engine import OwnershipEngine
from engine_fundamental.valuation_engine import ValuationEngine
from engine_fundamental.narrative_engine import NarrativeEngine
from engine_fundamental.market_confirmation import MarketConfirmationEngine
from engine_fundamental.graveyard_engine import GraveyardEngine, fetch_credibility
from engine_fundamental.forensic_debate import ForensicDebateEngine
from engine_core.db import fetch_df, get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Management integrity context (AAE Phase 3) ──────────────────────────
# Combines the credibility track-record score (deterministic) with the
# latest LLM credibility_assessment from Phase 1 and promise counts from
# the narrative timeline. Used by the Layer 9-10 bear/bull debate so the
# AI can cite "management has missed 3 of 5 promises" with concrete data.
def _build_management_integrity(symbol: str) -> dict | None:
    """Build the management_integrity block for AAE debate context.

    Returns a dict with has_data flag and all sub-fields, or None if there
    is no credibility data AND no narrative timeline data for the symbol.
    """
    cred = fetch_credibility(symbol)

    # Aggregate promise counts from the narrative timeline (the same
    # source NarrativeCredibilityScorer reads).
    counts = {
        "FULFILLED": 0, "REVISED_UP": 0, "ON_TRACK": 0,
        "PARTIALLY_FULFILLED": 0, "REVISED_DOWN": 0, "MISSED": 0,
        "PENDING": 0, "NEW": 0,
    }
    total_promises_in_timeline = 0
    actionable_promises = 0
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT current_status FROM management_narrative_timeline
               WHERE symbol = %s""",
            (symbol.upper(),),
        )
        for r in cur.fetchall():
            s = r["current_status"]
            if s in counts:
                counts[s] += 1
            total_promises_in_timeline += 1
            if s in ("FULFILLED", "REVISED_UP", "ON_TRACK",
                     "PARTIALLY_FULFILLED", "REVISED_DOWN", "MISSED"):
                actionable_promises += 1

        # Latest LLM credibility_assessment (Phase 1).
        cur.execute(
            """SELECT credibility_assessment, credibility_score_at_analysis
               FROM aae_narrative_intelligence
               WHERE symbol = %s
               ORDER BY date DESC LIMIT 1""",
            (symbol.upper(),),
        )
        narr_row = cur.fetchone()
    finally:
        conn.close()

    narrative_assessment = narr_row["credibility_assessment"] if narr_row else None
    narrative_score_at_analysis = (
        float(narr_row["credibility_score_at_analysis"])
        if narr_row and narr_row["credibility_score_at_analysis"] is not None
        else None
    )

    if not cred and total_promises_in_timeline == 0:
        return None  # Nothing to ground the debate on.

    return {
        "has_data": True,
        "credibility_score": cred["score"] if cred else None,
        "verdict": cred["verdict"] if cred else None,
        "previous_verdict": cred["previous_verdict"] if cred else None,
        "trend": cred["trend"] if cred else "INSUFFICIENT_DATA",
        "consecutive_miss_quarters": cred["consecutive_miss_quarters"] if cred else 0,
        "lag_score": cred["lag_score"] if cred else 0.0,
        "promise_counts": counts,
        "total_promises": total_promises_in_timeline,
        "actionable_promises": actionable_promises,
        "verdict_flipped_recently": (
            cred["previous_verdict"] is not None
            and cred["previous_verdict"] != cred["verdict"]
        ) if cred else False,
        "narrative_assessment": narrative_assessment,
        "narrative_score_at_analysis": narrative_score_at_analysis,
    }

class AAEOrchestrator:
    """
    AAE V3 Master Orchestrator.
    Synthesizes a 10-layer institutional forensic intelligence pipeline.
    Layers 0-7: Deterministic Forensic Audit.
    Layers 9-10: Multi-agent AI Stress Test (Bear vs. Bull).

    Master score weights (Phase 4, AAE × Management Integrity plan):
        sector       0.25
        narrative    0.20  (down from 0.25 — narrative now incorporates credibility via Phase 1)
        market       0.20  (down from 0.25)
        ownership    0.10
        valuation    0.10
        credibility  0.15  (NEW — from management_credibility_scores)
    Sum = 1.00.

    Credibility defaults to 50 (neutral) when no track record exists yet,
    so missing data never hurts and never helps.
    """
    W_SECTOR      = 0.25
    W_NARRATIVE   = 0.20
    W_MARKET      = 0.20
    W_OWNERSHIP   = 0.10
    W_VALUATION   = 0.10
    W_CREDIBILITY = 0.15

    def __init__(self, symbol):
        self.symbol = symbol.upper()

    @property
    def _weight_sum(self) -> float:
        return (self.W_SECTOR + self.W_NARRATIVE + self.W_MARKET
                + self.W_OWNERSHIP + self.W_VALUATION + self.W_CREDIBILITY)

    def run_full_scan(self):
        logger.info(f"Starting AAE V3 10-Layer Scan for {self.symbol}...")
        
        # Layer 0: Governance Kill Switch
        gov = GovernanceEngine(self.symbol)
        gov_data = gov.fetch_governance_data()
        killed, kill_reason = gov.evaluate_kill_switch(gov_data)
        
        if killed:
            logger.warning(f"AAE Kill Switch Triggered for {self.symbol}: {kill_reason}")
            return {"symbol": self.symbol, "status": "REJECTED", "reason": kill_reason}

        # Layer 1 & 2: Structural Delta (Sector Specific)
        sector_engine = get_sector_engine(self.symbol)
        sector_result = sector_engine.evaluate()
        
        # Layer 3: Ownership
        own = OwnershipEngine(self.symbol)
        own_result = own.evaluate()
        
        # Layer 4: Narrative
        narrative = NarrativeEngine(self.symbol)
        latest_narrative = fetch_df("""
            SELECT sentiment_score, narrative_delta, summary, numeric_divergence_score
            FROM aae_narrative_intelligence 
            WHERE symbol = %s 
            ORDER BY date DESC LIMIT 1
        """, (self.symbol,))
        
        narrative_score = 50
        narrative_summary = None
        narrative_source = "SYNTHETIC_PROXY"
        divergence_penalty = 0
        
        if latest_narrative is not None and not latest_narrative.empty:
            score_val = latest_narrative.iloc[0]['sentiment_score']
            div_val = latest_narrative.iloc[0]['numeric_divergence_score']
            
            narrative_score = float(score_val) * 100 if score_val is not None else 50
            narrative_summary = f"[OFFICIAL CONCALL TRANSCRIPT] {latest_narrative.iloc[0]['summary']}"
            narrative_source = "OFFICIAL_TRANSCRIPT"
            
            # Numeric-Narrative Divergence Penalty
            if div_val is not None and float(div_val) < -0.3:
                divergence_penalty = 10
                logger.warning(f"Narrative Divergence Penalty for {self.symbol}: Management too bullish vs financials ({div_val})")
        else:
            # Synthetic Narrative Fallback
            delta_score = sector_result.get('score', 50)
            if delta_score >= 75:
                narrative_score = 65
                narrative_summary = "[SYNTHETIC PROXY] Significant structural inflection in margins and efficiency detected. Management narrative likely focused on operating leverage. (Full concall analysis pending backfill)."
            elif delta_score >= 60:
                narrative_score = 55
                narrative_summary = "[SYNTHETIC PROXY] Positive financial trajectory detected. Narrative likely stable with focus on growth execution. (Full concall analysis pending backfill)."
            else:
                narrative_score = 50
                narrative_summary = "[SYNTHETIC PROXY] Neutral financial trajectory. No significant narrative inflection detected via financials. (Full concall analysis pending backfill)."
            
        # Layer 5: Market Confirmation
        market = MarketConfirmationEngine(self.symbol)
        sector_rs = sector_result.get('sector_rs')
        market_result = market.evaluate(sector_rs=sector_rs)
        
        # Layer 6: Valuation Asymmetry
        valuation = ValuationEngine(self.symbol)
        val_result = valuation.evaluate()
        
        # Layer 7: Forensic Feedback (Graveyard)
        graveyard = GraveyardEngine(self.symbol)
        forensic = graveyard.evaluate_penalty()

        # Phase 3 (AAE × Management Integrity): build the integrity context
        # once, BEFORE the master_score calc, so we can fold it into the
        # weighted formula. Same dict is reused in ai_context for the debate.
        management_integrity = _build_management_integrity(self.symbol)

        # Master Score Calculation (Deterministic)
        # Phase 4: weights rebalanced to include credibility at 15%.
        # Credibility defaults to 50 (neutral) when no track record exists.
        credibility_score_for_weighting = (
            management_integrity["credibility_score"]
            if (management_integrity
                and management_integrity.get("credibility_score") is not None)
            else 50
        )
        sector_score = sector_result.get('score', 50)
        market_score = market_result.get('score', 50)
        own_score = own_result.get('score', 50)
        val_score = val_result.get('valuation_score', 50)

        # Per-layer contribution breakdown (handy for Phase 5 UI + debugging)
        contrib = {
            "sector":      sector_score * self.W_SECTOR,
            "narrative":   narrative_score * self.W_NARRATIVE,
            "market":      market_score * self.W_MARKET,
            "ownership":   own_score * self.W_OWNERSHIP,
            "valuation":   val_score * self.W_VALUATION,
            "credibility": credibility_score_for_weighting * self.W_CREDIBILITY,
        }
        master_score = sum(contrib.values())

        # Apply Penalties (additive knock-downs on top of the weighted formula)
        master_score -= divergence_penalty
        if forensic['penalty'] > 0:
            master_score -= forensic['penalty']

        # Layer 9 & 10: AI Stress Test Agents
        debate_engine = ForensicDebateEngine(self.symbol)

        # Prepare context for AI agents
        ai_context = {
            "symbol": self.symbol,
            "master_score": master_score,
            "sector": sector_result.get('sector'),
            "financial_delta": sector_result.get('reasons'),
            "narrative_summary": narrative_summary,
            "valuation": val_result.get('reasons'),
            "market_confirmation": market_result.get('confirmation_status'),
            "management_integrity": management_integrity,
            "graveyard_rule": forensic.get('rule'),
            "graveyard_penalty": forensic.get('penalty', 0),
            "master_score_breakdown": contrib,
        }
        
        bear_case = debate_engine.run_bear_layer(ai_context)
        bull_case = debate_engine.run_bull_layer(ai_context)

        # Data quality check: count how many engine layers returned real data.
        # Phase 4: now includes credibility (6 layers total).
        credibility_score_value = (
            management_integrity.get("credibility_score")
            if management_integrity else None
        )
        score_sources = [
            sector_result.get('score'),
            narrative_score,
            market_result.get('score'),
            own_result.get('score'),
            val_result.get('valuation_score'),
            credibility_score_value,
        ]
        real_layer_count = sum(1 for s in score_sources
            if s is not None and isinstance(s, (int, float)) and s not in (50, 0))

        data_quality_warning = None
        if real_layer_count <= 1:
            data_quality_warning = (
                f"⚠️ Only {real_layer_count}/6 engine layers returned real data for {self.symbol}. "
                "The master score is heavily influenced by default values. "
                "Check if this symbol has been ingested into all AAE data pipelines."
            )
            logger.warning(data_quality_warning)

        result = {
            "symbol": self.symbol,
            "status": "ACTIVE",
            "master_score": round(max(0, master_score), 1),
            "divergence_penalty": divergence_penalty,
            "sector": sector_result.get('sector'),
            "market_confirmation": market_result.get('confirmation_status'),
            "narrative_score": round(narrative_score, 1),
            "reasons": sector_result.get('reasons', []) + market_result.get('reasons', []) + own_result.get('reasons', []) + val_result.get('reasons', []),

            "data_quality": {
                "layers_with_real_data": real_layer_count,
                "total_engine_layers": 6,
                "warning": data_quality_warning,
            },

            # Phase 4: master score contribution breakdown + final credibility score used
            "master_score_breakdown": {
                k: round(v, 2) for k, v in contrib.items()
            },
            "credibility_score_used": credibility_score_for_weighting,
            "weights": {
                "sector":      self.W_SECTOR,
                "narrative":   self.W_NARRATIVE,
                "market":      self.W_MARKET,
                "ownership":   self.W_OWNERSHIP,
                "valuation":   self.W_VALUATION,
                "credibility": self.W_CREDIBILITY,
            },

            # 10-Layer Results
            "bear_case": bear_case, # Layer 9
            "bull_case": bull_case, # Layer 10

            "layers": {
                "governance": gov_data,
                "structural_delta": sector_result,
                "ownership": own_result,
                "narrative": {
                    "score": round(narrative_score, 1),
                    "summary": narrative_summary,
                    "source": narrative_source
                },
                "valuation": val_result,
                "market": market_result,
                "forensic": forensic,
                "management_integrity": management_integrity,
                "bear_agent": bear_case,
                "bull_agent": bull_case
            }
        }
        
        if forensic['reason']:
            result["reasons"].append(forensic['reason'])
        
        if narrative_summary:
            result["reasons"].insert(0, f"Narrative: {narrative_summary}")
            
        logger.info(f"AAE 10-Layer Scan Complete for {self.symbol}. Master Score: {result['master_score']}")
        return result

if __name__ == "__main__":
    # Test with HDFC Bank
    orchestrator = AAEOrchestrator("HDFCBANK")
    print(orchestrator.run_full_scan())
