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

    def get_peer_median_pe(self):
        query_map = "SELECT sector_id FROM aae_sector_mapping WHERE symbol = %s"
        mapping = fetch_df(query_map, (self.symbol,))
        if mapping is None or mapping.empty:
            return None
        sector_id = int(mapping.iloc[0]['sector_id'])
        
        query = """
            WITH latest_prices AS (
                SELECT symbol, close
                FROM daily_prices
                WHERE date = (SELECT MAX(date) FROM daily_prices)
            ),
            ttm_eps AS (
                SELECT symbol, SUM(eps) as total_eps
                FROM (
                    SELECT symbol, eps,
                           ROW_NUMBER() OVER(PARTITION BY symbol ORDER BY year DESC, quarter DESC) as rn
                    FROM aae_quarterly_financials
                ) t
                WHERE rn <= 4
                GROUP BY symbol
                HAVING SUM(eps) > 0
            )
            SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY (p.close / e.total_eps)) as median_pe
            FROM aae_sector_mapping m
            JOIN latest_prices p ON m.symbol = p.symbol
            JOIN ttm_eps e ON m.symbol = e.symbol
            WHERE m.sector_id = %s
        """
        try:
            df = fetch_df(query, (sector_id,))
            if df is not None and not df.empty and pd.notnull(df.iloc[0]['median_pe']):
                return float(df.iloc[0]['median_pe'])
        except Exception as e:
            logger.error(f"Failed to calculate peer PE for {self.symbol}: {e}")
        return None

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
            
        peer_pe = self.get_peer_median_pe()
        if peer_pe and pe > 0:
            if pe < (peer_pe * 0.8):
                score += 15
                reasons.append(f"Discount to Sector Peer Median ({pe:.1f}x vs {peer_pe:.1f}x)")
            elif pe > (peer_pe * 1.5):
                score -= 15
                reasons.append(f"Premium to Sector Peer Median ({pe:.1f}x vs {peer_pe:.1f}x)")
                
        return {
            "valuation_score": min(100, max(0, score)),
            "reasons": reasons,
            "ttm_eps": eps,
            "pe_ratio": pe,
            "peer_median_pe": peer_pe
        }
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
