import logging
from engine_fundamental.governance_engine import GovernanceEngine
from engine_fundamental.sector_engine import get_sector_engine
from engine_fundamental.ownership_engine import OwnershipEngine
from engine_fundamental.valuation_engine import ValuationEngine
from engine_fundamental.narrative_engine import NarrativeEngine
from engine_fundamental.market_confirmation import MarketConfirmationEngine
from engine_fundamental.graveyard_engine import GraveyardEngine
from engine_fundamental.forensic_debate import ForensicDebateEngine
from engine_core.db import fetch_df

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AAEOrchestrator:
    """
    AAE V3 Master Orchestrator.
    Synthesizes a 10-layer institutional forensic intelligence pipeline.
    Layers 0-7: Deterministic Forensic Audit.
    Layers 9-10: Multi-agent AI Stress Test (Bear vs. Bull).
    """
    
    def __init__(self, symbol):
        self.symbol = symbol.upper()

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
        
        # Master Score Calculation (Deterministic)
        master_score = (
            (sector_result.get('score', 50) * 0.30) +
            (narrative_score * 0.25) +
            (market_result.get('score', 50) * 0.25) +
            (own_result.get('score', 50) * 0.10) +
            (val_result.get('valuation_score', 50) * 0.10)
        )
        
        # Apply Penalties
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
            "market_confirmation": market_result.get('confirmation_status')
        }
        
        bear_case = debate_engine.run_bear_layer(ai_context)
        bull_case = debate_engine.run_bull_layer(ai_context)

        # Data quality check: count how many engine layers returned real data
        score_sources = [
            sector_result.get('score'),
            narrative_score,
            market_result.get('score'),
            own_result.get('score'),
            val_result.get('valuation_score'),
        ]
        real_layer_count = sum(1 for s in score_sources 
            if s is not None and isinstance(s, (int, float)) and s not in (50, 0))
        
        data_quality_warning = None
        if real_layer_count <= 1:
            data_quality_warning = (
                f"⚠️ Only {real_layer_count}/5 engine layers returned real data for {self.symbol}. "
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
                "total_engine_layers": 5,
                "warning": data_quality_warning,
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
