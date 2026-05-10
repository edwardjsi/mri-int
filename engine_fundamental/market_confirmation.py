import logging
import pandas as pd
from engine_core.db import fetch_df

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketConfirmationEngine:
    """
    AAE Layer 5: Market Confirmation.
    Checks if institutional footprints (Volume, RS, Highs) confirm the rerating thesis.
    """
    
    def __init__(self, symbol):
        self.symbol = symbol.upper()

    def get_latest_indicators(self):
        query = """
            SELECT * FROM stock_scores 
            WHERE symbol = %s 
            ORDER BY date DESC LIMIT 1
        """
        return fetch_df(query, (self.symbol,))

    def evaluate(self):
        df = self.get_latest_indicators()
        if df is None or df.empty:
            return {"score": 50, "reasons": ["No technical data available"]}
            
        latest = df.iloc[0]
        
        score = 60 # Baseline for being in the universe
        reasons = []
        
        # 1. Volume Confirmation (Institutional Buying)
        if latest.get('condition_volume'):
            score += 15
            reasons.append("Institutional Volume Footprint")
            
        # 2. Relative Strength (Outperforming Market)
        if latest.get('condition_rs'):
            score += 15
            reasons.append("Relative Strength Confirmation")
            
        # 3. Near Highs (Accumulation Zone)
        if latest.get('condition_6m_high'):
            score += 10
            reasons.append("Accumulation near Multi-Month Highs")
            
        # 4. Trend Quality
        if latest.get('condition_ema_50_200'):
            score += 10
            reasons.append("Structural Uptrend (EMA 50 > 200)")
        else:
            score -= 20
            reasons.append("Lacks Structural Uptrend (Technical Friction)")

        return {
            "score": min(100, max(0, score)),
            "reasons": reasons,
            "confirmation_status": "CONFIRMED" if score >= 80 else "PENDING"
        }

if __name__ == "__main__":
    engine = MarketConfirmationEngine("360ONE")
    print(engine.evaluate())
