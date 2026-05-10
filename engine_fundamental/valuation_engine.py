import logging
import pandas as pd
import numpy as np
from engine_core.db import fetch_df, get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def safe_float(v):
    if v is None: return 0.0
    try:
        return float(v)
    except:
        return 0.0

class ValuationEngine:
    """
    Detects valuation asymmetry by comparing current multiples to historical ranges and sector medians.
    AAE Layer 4: Valuation Confirmation.
    """
    
    def __init__(self, symbol):
        self.symbol = symbol.upper()

    def get_current_metrics(self):
        """
        Fetch current price from daily_prices and latest technical score from stock_scores.
        """
        query = """
            SELECT d.close as price, s.total_score 
            FROM daily_prices d
            JOIN stock_scores s ON d.symbol = s.symbol AND d.date = s.date
            WHERE d.symbol = %s 
            ORDER BY d.date DESC 
            LIMIT 1
        """
        df = fetch_df(query, (self.symbol,))
        if df is None or df.empty:
            # Fallback to just price if score is missing
            query_price = "SELECT close as price FROM daily_prices WHERE symbol = %s ORDER BY date DESC LIMIT 1"
            df_price = fetch_df(query_price, (self.symbol,))
            if df_price is None or df_price.empty:
                return None
            return {"price": df_price.iloc[0]['price'], "total_score": 0}
            
        return df.iloc[0].to_dict()

    def get_financial_summary(self):
        """
        Fetch latest EPS and EBITDA from quarterly financials.
        """
        query = """
            SELECT eps, ebitda, revenue, total_assets, debt, equity
            FROM aae_quarterly_financials
            WHERE symbol = %s
            ORDER BY year DESC, quarter DESC
            LIMIT 4
        """
        df = fetch_df(query, (self.symbol,))
        if df is None or df.empty:
            return None
        
        # TTM (Trailing Twelve Months) approximation
        ttm_eps = df['eps'].sum()
        ttm_ebitda = df['ebitda'].sum()
        
        latest = df.iloc[0].to_dict()
        latest['ttm_eps'] = ttm_eps
        latest['ttm_ebitda'] = ttm_ebitda
        return latest

    def evaluate(self):
        """
        Compute valuation asymmetry score.
        """
        market = self.get_current_metrics()
        financials = self.get_financial_summary()
        
        if not market or not financials:
            return {"score": 50, "reason": "Insufficient data for valuation"}
            
        price = safe_float(market['price'])
        eps = safe_float(financials['ttm_eps'])
        
        pe = price / eps if eps > 0 else 0
        
        # Placeholder for historical percentile logic (simplified)
        # In a real system, we'd compare this PE to the 5-year distribution.
        # For now, we'll use a rule-based asymmetry detection.
        
        score = 50
        reasons = []
        
        if pe > 0 and pe < 15:
            score += 20
            reasons.append(f"Low absolute PE: {pe:.1f}x")
        elif pe > 40:
            score -= 10
            reasons.append(f"High absolute PE: {pe:.1f}x")
            
        # PEG ratio proxy (PE / Revenue Growth)
        # We need growth from delta engine ideally
        
        return {
            "symbol": self.symbol,
            "current_pe": round(pe, 1),
            "valuation_score": score,
            "reasons": reasons,
            "asymmetry_status": "HIGH" if score > 65 else "NORMAL"
        }

if __name__ == "__main__":
    # Test with TCS
    engine = ValuationEngine("TCS")
    result = engine.evaluate()
    print(result)
