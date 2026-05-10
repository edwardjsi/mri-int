import logging
import pandas as pd
from engine_core.db import fetch_df

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseSectorEngine:
    def __init__(self, symbol):
        self.symbol = symbol.upper()

    def get_financials(self, limit=8):
        query = """
            SELECT * FROM aae_quarterly_financials 
            WHERE symbol = %s 
            ORDER BY year DESC, quarter DESC 
            LIMIT %s
        """
        df = fetch_df(query, (self.symbol, limit))
        if df is not None and not df.empty:
            # Convert Decimals to floats
            for col in df.columns:
                if df[col].dtype == object:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    def evaluate(self):
        raise NotImplementedError("Subclasses must implement evaluate()")

class ManufacturingEngine(BaseSectorEngine):
    """
    Standard industrial/manufacturing engine focusing on margins and asset turns.
    """
    def evaluate(self):
        df = self.get_financials()
        if df is None or df.empty or len(df) < 2:
            return {"score": 50, "reasons": ["Insufficient data"]}
        
        # Chronological order
        df = df.iloc[::-1].reset_index(drop=True)
        
        # Metrics: EBITDA Margin, Asset Turns (Revenue / Total Assets)
        df['ebitda_margin'] = df['ebitda'] / df['revenue']
        df['asset_turn'] = df['revenue'] / df['total_assets']
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        score = 60
        reasons = []
        
        if latest.get('ebitda_margin') and prev.get('ebitda_margin') and latest['ebitda_margin'] > prev['ebitda_margin']:
            score += 10
            reasons.append("Margin Expansion")
            
        if latest.get('asset_turn') and prev.get('asset_turn') and latest['asset_turn'] > prev['asset_turn']:
            score += 10
            reasons.append("Efficiency Improvement (Asset Turns)")
            
        return {"score": min(100, score), "reasons": reasons, "sector": "Manufacturing"}

class BankEngine(BaseSectorEngine):
    """
    Bank-specific engine focusing on NII growth and Asset Quality proxies.
    """
    def evaluate(self):
        df = self.get_financials()
        if df is None or df.empty or len(df) < 2:
            return {"score": 50, "reasons": ["Insufficient data"]}
            
        df = df.iloc[::-1].reset_index(drop=True)
        
        # Ensure NII exists (might be None for some quarters if yf missed it)
        df['net_interest_income'] = df['net_interest_income'].fillna(0)
        
        # Metrics: NII Growth, Non-Interest Income contribution
        df['nii_growth'] = df['net_interest_income'].pct_change()
        df['non_interest_mix'] = df['non_interest_income'] / df['revenue']
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        score = 60
        reasons = []
        
        if latest.get('nii_growth') and latest['nii_growth'] > 0.05:
            score += 15
            reasons.append(f"Strong NII Growth: {latest['nii_growth']*100:.1f}%")
            
        if latest.get('non_interest_mix') and prev.get('non_interest_mix') and latest['non_interest_mix'] > prev['non_interest_mix']:
            score += 5
            reasons.append("Diversifying Income (Non-Interest Mix UP)")
            
        return {"score": min(100, score), "reasons": reasons, "sector": "Banking"}

class ElectricalEngine(BaseSectorEngine):
    """
    Specialized engine for Electrical/Capital Goods.
    Focuses on Operating Leverage (EBITDA growth vs Revenue growth).
    """
    def evaluate(self):
        df = self.get_financials()
        if df is None or df.empty or len(df) < 2:
            return {"score": 50, "reasons": ["Insufficient data"]}
            
        df = df.iloc[::-1].reset_index(drop=True)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        score = 65 # Higher baseline for Capex cycle
        reasons = []
        
        # 1. Operating Leverage Test: EBITDA should grow faster than Revenue
        rev_growth = (latest['revenue'] - prev['revenue']) / prev['revenue'] if prev['revenue'] > 0 else 0
        ebitda_growth = (latest['ebitda'] - prev['ebitda']) / prev['ebitda'] if prev['ebitda'] > 0 else 0
        
        if ebitda_growth > rev_growth + 0.05:
            score += 20
            reasons.append(f"Operating Leverage Detected (EBITDA growth > Revenue growth)")
        elif ebitda_growth > 0:
            score += 10
            reasons.append("Positive Margin Trajectory")
            
        # 2. Asset Turn (Efficiency)
        latest_turn = latest['revenue'] / latest['total_assets'] if latest['total_assets'] > 0 else 0
        prev_turn = prev['revenue'] / prev['total_assets'] if prev['total_assets'] > 0 else 0
        if latest_turn > prev_turn:
            score += 10
            reasons.append("Improving Asset Utilization")
            
        return {"score": min(100, score), "reasons": reasons, "sector": "Electrical Infrastructure"}

class EnergyEngine(BaseSectorEngine):
    """
    Specialized engine for Power & Renewables.
    Focuses on Deleveraging (Debt/Equity) and Receivable improvement.
    """
    def evaluate(self):
        df = self.get_financials()
        if df is None or df.empty or len(df) < 2:
            return {"score": 50, "reasons": ["Insufficient data"]}
            
        df = df.iloc[::-1].reset_index(drop=True)
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        score = 60
        reasons = []
        
        # 1. Deleveraging (Debt Reduction)
        if latest.get('debt') and prev.get('debt') and latest['debt'] < prev['debt'] * 0.95:
            score += 20
            reasons.append("Significant Deleveraging (Debt Reduction)")
            
        # 2. Receivable Days Improvement
        if latest.get('receivables') and prev.get('receivables') and latest['receivables'] < prev['receivables']:
            score += 15
            reasons.append("Improving Cash Flow (Receivables Down)")
            
        # 3. EBITDA Margin
        if latest.get('ebitda') / latest.get('revenue') > prev.get('ebitda') / prev.get('revenue'):
            score += 5
            reasons.append("Operational Efficiency Gained")
            
        return {"score": min(100, score), "reasons": reasons, "sector": "Energy & Power"}

def get_sector_engine(symbol):
    """
    Factory method to return the correct sector engine.
    """
    query = "SELECT industry FROM stock_sectors WHERE symbol = %s"
    df = fetch_df(query, (symbol.upper(),))
    
    if df is None or df.empty:
        # Hardcoded overrides for missing metadata
        if symbol.upper() == "VOLTAMP":
            return ElectricalEngine(symbol)
        if symbol.upper() == "SUZLON":
            return EnergyEngine(symbol)
        
        logger.warning(f"No sector info for {symbol}, defaulting to ManufacturingEngine")
        return ManufacturingEngine(symbol)
        
    industry = str(df.iloc[0]['industry']).upper()
    if 'BANK' in industry or 'FINANCIAL SERVICES' in industry:
        logger.info(f"Using BankEngine for {symbol} ({industry})")
        return BankEngine(symbol)
    elif 'ELECTRICAL' in industry or 'CAPITAL GOODS' in industry:
        logger.info(f"Using ElectricalEngine for {symbol} ({industry})")
        return ElectricalEngine(symbol)
    elif 'POWER' in industry or 'ENERGY' in industry or 'UTILITIES' in industry:
        logger.info(f"Using EnergyEngine for {symbol} ({industry})")
        return EnergyEngine(symbol)
    else:
        logger.info(f"Using ManufacturingEngine for {symbol} ({industry})")
        return ManufacturingEngine(symbol)

if __name__ == "__main__":
    # Test with HDFC Bank and TCS
    for sym in ["HDFCBANK", "TCS"]:
        engine = get_sector_engine(sym)
        result = engine.evaluate()
        print(f"\nResult for {sym}:")
        print(result)
