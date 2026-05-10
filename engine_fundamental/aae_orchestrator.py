import logging
from engine_fundamental.governance_engine import GovernanceEngine
from engine_fundamental.sector_engine import get_sector_engine
from engine_fundamental.ownership_engine import OwnershipEngine
from engine_fundamental.valuation_engine import ValuationEngine
from engine_fundamental.narrative_engine import NarrativeEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AAEOrchestrator:
    """
    AAE V3 Master Orchestrator.
    Synthesizes all layers into a final Expected Rerating Score.
    """
    
    def __init__(self, symbol):
        self.symbol = symbol.upper()

    def run_full_scan(self):
        logger.info(f"Starting AAE V3 Full Scan for {self.symbol}...")
        
        # Layer 0: Governance Kill Switch
        gov = GovernanceEngine(self.symbol)
        gov_data = gov.fetch_governance_data()
        killed, reason = gov.evaluate_kill_switch(gov_data)
        
        if killed:
            logger.warning(f"AAE Kill Switch Triggered for {self.symbol}: {reason}")
            return {
                "symbol": self.symbol,
                "status": "REJECTED",
                "kill_reason": reason,
                "master_score": 0
            }

        # Layer 1 & 2: Sector-Specific Financials
        sector_engine = get_sector_engine(self.symbol)
        sector_result = sector_engine.evaluate()
        
        # Layer 3: Ownership Confirmation
        ownership = OwnershipEngine(self.symbol)
        own_result = ownership.evaluate()
        
        # Layer 4: Valuation Asymmetry
        valuation = ValuationEngine(self.symbol)
        val_result = valuation.evaluate()
        
        # Narrative Layer (Optional/Async in real pipeline, here we check for latest)
        narrative = NarrativeEngine(self.symbol)
        # Note: Narrative analysis usually requires a transcript to be present.
        # For the orchestrator, we'll check if a recent score exists in aae_narrative_intelligence.
        
        # Master Score Weighting
        # Sector (40%) + Ownership (30%) + Valuation (30%)
        master_score = (
            (sector_result.get('score', 50) * 0.40) +
            (own_result.get('score', 50) * 0.30) +
            (val_result.get('valuation_score', 50) * 0.30)
        )
        
        result = {
            "symbol": self.symbol,
            "status": "ACTIVE",
            "master_score": round(master_score, 1),
            "sector": sector_result.get('sector'),
            "sector_score": sector_result.get('score'),
            "ownership_score": own_result.get('score'),
            "valuation_status": val_result.get('asymmetry_status'),
            "valuation_score": val_result.get('valuation_score'),
            "reasons": sector_result.get('reasons', []) + own_result.get('reasons', []) + val_result.get('reasons', [])
        }
        
        logger.info(f"AAE Scan Complete for {self.symbol}. Master Score: {result['master_score']}")
        return result

if __name__ == "__main__":
    # Test with HDFC Bank
    orchestrator = AAEOrchestrator("HDFCBANK")
    print(orchestrator.run_full_scan())
