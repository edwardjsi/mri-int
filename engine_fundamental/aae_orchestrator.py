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
    Synthesizes Governance, Structural Delta, Narrative, Ownership, and Market layers.
    """
    
    def __init__(self, symbol):
        self.symbol = symbol.upper()

    def run_full_scan(self):
        logger.info(f"Starting AAE V3 Full Scan for {self.symbol}...")
        
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
            SELECT sentiment_score, narrative_delta, summary 
            FROM aae_narrative_intelligence 
            WHERE symbol = %s 
            ORDER BY date DESC LIMIT 1
        """, (self.symbol,))
        
        narrative_score = 50
        narrative_summary = None
        if latest_narrative is not None and not latest_narrative.empty:
            score_val = latest_narrative.iloc[0]['sentiment_score']
            narrative_score = float(score_val) * 100 if score_val is not None else 50
            narrative_summary = latest_narrative.iloc[0]['summary']
            
        # Layer 5: Market Confirmation
        market = MarketConfirmationEngine(self.symbol)
        market_result = market.evaluate()
        
        # Layer 6: Valuation Asymmetry
        valuation = ValuationEngine(self.symbol)
        val_result = valuation.evaluate()
        
        # Layer 7: Forensic Feedback (Graveyard)
        graveyard = GraveyardEngine(self.symbol)
        forensic = graveyard.evaluate_penalty()
        
        master_score = (
            (sector_result.get('score', 50) * 0.30) +
            (narrative_score * 0.25) +
            (market_result.get('score', 50) * 0.25) +
            (own_result.get('score', 50) * 0.10) +
            (val_result.get('valuation_score', 50) * 0.10)
        )
        
        # Apply Forensic Penalty
        if forensic['penalty'] > 0:
            master_score -= forensic['penalty']
        
        result = {
            "symbol": self.symbol,
            "status": "ACTIVE",
            "master_score": round(max(0, master_score), 1),
            "sector": sector_result.get('sector'),
            "market_confirmation": market_result.get('confirmation_status'),
            "narrative_score": round(narrative_score, 1),
            "reasons": sector_result.get('reasons', []) + market_result.get('reasons', []) + own_result.get('reasons', []) + val_result.get('reasons', [])
        }
        
        if forensic['reason']:
            result["reasons"].append(forensic['reason'])
        
        if narrative_summary:
            result["reasons"].insert(0, f"Narrative: {narrative_summary}")
            
        # Layer 8: Forensic Debate (Stress Test) - Only for high scorers
        if master_score > 70:
            debate_engine = ForensicDebateEngine(self.symbol)
            debate_result = debate_engine.run_debate(result)
            verdict = debate_result['verdict']
            result['debate_conviction'] = verdict.get('conviction_score')
            result['risk_summary'] = verdict.get('critical_risk')
            result['debate_summary'] = verdict.get('summary')
            logger.info(f"Forensic Debate Complete for {self.symbol}. Verdict: {verdict.get('verdict')}")
            
        logger.info(f"AAE Scan Complete for {self.symbol}. Master Score: {result['master_score']}")
        return result

if __name__ == "__main__":
    # Test with HDFC Bank
    orchestrator = AAEOrchestrator("HDFCBANK")
    print(orchestrator.run_full_scan())
