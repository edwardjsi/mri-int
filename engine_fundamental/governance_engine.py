import yfinance as yf
import logging
import numpy as np
from engine_core.db import get_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sanitize_val(val):
    if val is None or (isinstance(val, (float, int)) and np.isnan(val)):
        return None
    if hasattr(val, 'item'):
        return val.item()
    return val

class GovernanceEngine:
    """
    Evaluates governance risks including promoter pledging, auditor flags, and management changes.
    AAE Layer 0: Governance Kill Switch.
    """
    
    def __init__(self, symbol):
        self.symbol = symbol
        self.yf_symbol = symbol if (".NS" in symbol or ".BO" in symbol) else f"{symbol}.NS"
        self.stock = yf.Ticker(self.yf_symbol)
        self.base_symbol = symbol.replace(".NS", "").replace(".BO", "").upper()

    def fetch_governance_data(self):
        """
        Fetch governance-related data from yfinance.
        """
        try:
            info = self.stock.info
            major_holders = self.stock.major_holders
            
            # 1. Promoter Holding
            promoter_holding = 0
            if major_holders is not None and not major_holders.empty:
                if isinstance(major_holders, pd.DataFrame):
                    # For some versions/symbols, it's a DF with 'Value' column
                    if 'Value' in major_holders.columns:
                        val = major_holders.loc[major_holders.index == 'insidersPercentHeld', 'Value']
                        if not val.empty:
                            promoter_holding = val.iloc[0]
                    else:
                        # Fallback for different DF shapes
                        promoter_holding = major_holders.get('insidersPercentHeld', 0)
                else:
                    promoter_holding = major_holders.get('insidersPercentHeld', 0)
                
                if isinstance(promoter_holding, (pd.Series, pd.DataFrame)):
                    promoter_holding = promoter_holding.iloc[0]
            
            # 2. Pledged Shares (Hard to get from yf directly, using placeholder or info check)
            # Some tickers might have it in info under obscure names
            pledged_pct = info.get('pledgedSharesPct', 0) # Placeholder key
            
            # 3. Auditor & Audit Risk
            audit_risk = info.get('auditRisk', 5) # 1-10, 10 is high risk
            auditor_flag = True if audit_risk >= 9 else False
            
            # 4. CFO/Management Changes (Proxy via shareHolderRightsRisk or similar)
            rights_risk = info.get('shareHolderRightsRisk', 5)
            cfo_exit_flag = True if rights_risk >= 9 else False
            
            # 5. Related Party Risk (Proxy)
            related_party_risk = True if audit_risk >= 8 and rights_risk >= 8 else False
            
            # 6. Governance Score (0-100, 100 is perfect)
            # Formula: 100 - (auditRisk * 5) - (rightsRisk * 5)
            gov_score = 100 - (audit_risk * 5) - (rights_risk * 5)
            gov_score = max(0, min(100, gov_score))
            
            return {
                "promoter_holding_pct": sanitize_val(promoter_holding * 100 if promoter_holding else None),
                "pledged_shares_pct": sanitize_val(pledged_pct),
                "auditor_flag": auditor_flag,
                "cfo_exit_flag": cfo_exit_flag,
                "related_party_risk": related_party_risk,
                "governance_score": sanitize_val(gov_score)
            }
        except Exception as e:
            logger.error(f"Failed to fetch governance data for {self.symbol}: {e}")
            return None

    def evaluate_kill_switch(self, data):
        """
        Check if any hard exclusion conditions are met.
        """
        if not data:
            return True, "No governance data available"
        
        reasons = []
        if data['pledged_shares_pct'] and data['pledged_shares_pct'] > 25:
            reasons.append(f"High Promoter Pledge: {data['pledged_shares_pct']}%")
        
        if data['auditor_flag']:
            reasons.append("High Audit Risk Flag")
            
        if data['cfo_exit_flag']:
            reasons.append("Management Continuity Risk")
            
        if reasons:
            return True, "; ".join(reasons)
        
        return False, "Governance Clean"

    def store_governance(self, data, year, quarter):
        """
        Store in aae_governance_metrics table.
        """
        if not data: return
        
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO public.aae_governance_metrics (
                symbol, fiscal_year, fiscal_quarter, promoter_holding_pct, 
                pledged_shares_pct, auditor_flag, cfo_exit_flag, 
                related_party_risk, governance_score
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, fiscal_year, fiscal_quarter) DO UPDATE SET
                promoter_holding_pct = EXCLUDED.promoter_holding_pct,
                pledged_shares_pct = EXCLUDED.pledged_shares_pct,
                auditor_flag = EXCLUDED.auditor_flag,
                cfo_exit_flag = EXCLUDED.cfo_exit_flag,
                related_party_risk = EXCLUDED.related_party_risk,
                governance_score = EXCLUDED.governance_score,
                updated_at = NOW()
        """, (
            self.base_symbol, year, quarter, 
            data['promoter_holding_pct'], data['pledged_shares_pct'],
            data['auditor_flag'], data['cfo_exit_flag'],
            data['related_party_risk'], data['governance_score']
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Stored governance metrics for {self.base_symbol} (FY{year} Q{quarter})")

import pandas as pd # Needed for major_holders check

if __name__ == "__main__":
    engine = GovernanceEngine("TCS")
    data = engine.fetch_governance_data()
    print(data)
    if data:
        killed, reason = engine.evaluate_kill_switch(data)
        print(f"Kill Switch: {killed}, Reason: {reason}")
        engine.store_governance(data, 2024, 1)
