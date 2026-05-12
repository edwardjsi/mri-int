import logging
import pandas as pd
from engine_core.db import get_connection, fetch_df

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OwnershipEngine:
    """
    Tracks institutional ownership changes and promoter activity.
    AAE Layer 3: Ownership Confirmation.
    """
    
    def __init__(self, symbol):
        self.symbol = symbol.upper()

    def get_holding_history(self, limit=4):
        """
        Fetch historical governance/ownership metrics.
        """
        query = """
            SELECT fiscal_year, fiscal_quarter, promoter_holding_pct, governance_score
            FROM aae_governance_metrics
            WHERE symbol = %s
            ORDER BY fiscal_year DESC, fiscal_quarter DESC
            LIMIT %s
        """
        df = fetch_df(query, (self.symbol, limit))
        if df is not None and not df.empty:
            for col in ['promoter_holding_pct', 'governance_score']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    def evaluate(self):
        df = self.get_holding_history()
        if df is None or df.empty or len(df) < 2:
            return {"score": 50, "reasons": ["Insufficient Ownership History (Establish trend over 2+ quarters)"]}
            
        # Chronological
        df = df.iloc[::-1].reset_index(drop=True)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        score = 60
        reasons = []
        
        # 1. Promoter Activity
        if latest['promoter_holding_pct'] > prev['promoter_holding_pct'] + 0.1:
            score += 20
            reasons.append(f"Promoter Buying Detected: +{latest['promoter_holding_pct'] - prev['promoter_holding_pct']:.2f}%")
        elif latest['promoter_holding_pct'] < prev['promoter_holding_pct'] - 0.5:
            score -= 15
            reasons.append(f"Significant Promoter Selling: -{prev['promoter_holding_pct'] - latest['promoter_holding_pct']:.2f}%")
            
        # 2. Governance Score Stability
        if latest['governance_score'] > prev['governance_score']:
            score += 5
            reasons.append("Governance Score Improving")
            
        return {
            "score": min(100, max(0, score)),
            "reasons": reasons,
            "ownership_status": "STRONG" if score > 75 else "NEUTRAL"
        }

if __name__ == "__main__":
    engine = OwnershipEngine("TCS")
    print(engine.evaluate())
