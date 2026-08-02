import os
import sys
import psycopg2
from psycopg2.extras import DictCursor

sys.path.append(os.path.abspath(os.path.dirname(__file__) + "/.."))
from engine_core.db import get_connection

class CanslimModel:
    def evaluate_candidate(self, row):
        """Pure logic for evaluating CANSLIM verdicts from consumed primitives."""
        symbol = row.get("symbol", "UNKNOWN")
        regime = row.get("regime", "UNKNOWN")
        
        # M: Market Regime
        m_pass = regime not in ("BEARISH", "RISK-OFF")
        
        # L: Leadership
        condition_rs = bool(row.get("condition_rs", False))
        condition_6m_high = bool(row.get("condition_6m_high", False))
        l_pass = condition_rs and condition_6m_high
        
        # S: Momentum / Demand
        condition_volume = bool(row.get("condition_volume", False))
        condition_ema_200_slope = bool(row.get("condition_ema_200_slope", False))
        s_pass = condition_volume or condition_ema_200_slope
        
        # C & A: Growth and Quality
        quality_score = float(row.get("quality_score") or 0)
        c_pass = quality_score >= 60
        a_pass = quality_score >= 60
        
        score = 0
        if m_pass: score += 20
        if l_pass: score += 20
        if s_pass: score += 20
        if c_pass: score += 20
        if a_pass: score += 20
        
        return {
            "symbol": symbol,
            "canslim_score": score,
            "knowledge_age_days": None,
            "compiler_version": None,
            "components": {
                "Growth": {"status": "PASS" if c_pass else "FAIL", "observations": [], "rules": ["RULE-FND-001"], "evidence": [f"Fundamental Score: {quality_score:.1f} >= 60"]},
                "Quality": {"status": "PASS" if a_pass else "FAIL", "observations": [], "rules": ["RULE-FND-002"], "evidence": [f"Fundamental Score: {quality_score:.1f} >= 60"]},
                "Momentum": {"status": "PASS" if s_pass else "FAIL", "observations": [], "rules": ["RULE-TEC-001"], "evidence": [f"Vol Surge: {condition_volume}, Trend: {condition_ema_200_slope}"]},
                "Leadership": {"status": "PASS" if l_pass else "FAIL", "observations": [], "rules": ["RULE-TEC-002"], "evidence": [f"RS: {condition_rs}, 6m High: {condition_6m_high}"]},
                "Market": {"status": "PASS" if m_pass else "FAIL", "observations": [], "rules": ["RULE-MKT-001"], "evidence": [f"Regime: {regime}"]},
                "Catalyst": {"status": "UNKNOWN", "observations": [], "rules": [], "evidence": []},
                "Institutional": {"status": "UNKNOWN", "observations": [], "rules": [], "evidence": []}
            }
        }

    def run_quant_screen(self):
        """
        Executes the Phase 1 CANSLIM Quant Filter by consuming pre-computed primitives
        from the MRI database.
        """
        conn = get_connection()
        cur = conn.cursor(cursor_factory=DictCursor)
        
        try:
            query = """
            WITH latest_regime AS (
                SELECT classification AS regime FROM market_regime ORDER BY date DESC LIMIT 1
            ),
            latest_scores AS (
                SELECT DISTINCT ON (symbol) 
                    symbol,
                    condition_ema_50_200,
                    condition_ema_200_slope,
                    condition_rs,
                    condition_6m_high,
                    condition_volume,
                    condition_breakout_10d,
                    condition_price_quality
                FROM stock_scores
                ORDER BY symbol, date DESC
            ),
            latest_quality AS (
                SELECT symbol, score AS quality_score, revenue_score
                FROM quality_verdicts
            )
            SELECT 
                s.symbol,
                s.condition_ema_50_200,
                s.condition_ema_200_slope,
                s.condition_rs,
                s.condition_6m_high,
                s.condition_volume,
                s.condition_breakout_10d,
                s.condition_price_quality,
                q.quality_score,
                q.revenue_score,
                COALESCE(r.regime, 'UNKNOWN') AS regime
            FROM latest_scores s
            LEFT JOIN latest_quality q ON s.symbol = q.symbol
            CROSS JOIN latest_regime r
            """
            cur.execute(query)
            rows = cur.fetchall()
            
            candidates = []
            for row in rows:
                candidate = self.evaluate_candidate(dict(row))
                if candidate["canslim_score"] >= 60:
                    candidates.append(candidate)
                    
            candidates.sort(key=lambda x: x["canslim_score"], reverse=True)
            return candidates[:30]
            
        finally:
            cur.close()
            conn.close()

if __name__ == "__main__":
    model = CanslimModel()
    results = model.run_quant_screen()
    for r in results:
        print(f"{r['symbol']} - Score: {r['canslim_score']}")
