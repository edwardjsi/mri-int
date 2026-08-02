import datetime
from typing import Optional
from psycopg2.extras import DictCursor

from engine_core.db import get_connection
from engine_core.investment_model import InvestmentModel
from engine_core.model_results_repository import ModelResult
from engine_core.knowledge_evidence_service import KnowledgeEvidenceService

class CanslimModel(InvestmentModel):
    """
    Ported CANSLIM Model using the InvestmentModel interface.
    """
    
    def __init__(self):
        self.evidence_service = KnowledgeEvidenceService()

    @property
    def id(self) -> str:
        return "CANSLIM"
        
    @property
    def version(self) -> str:
        return "1.0"
        
    def evaluate(self, symbol: str, evaluation_date: Optional[datetime.date] = None) -> ModelResult:
        eval_date = evaluation_date or datetime.date.today()
        
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                # We need to get the latest scores, quality, and regime on or before eval_date
                # For simplicity in this direct port, we match the existing query structure 
                # but scoped to a single symbol and date.
                query = """
                WITH latest_regime AS (
                    SELECT classification AS regime FROM market_regime 
                    WHERE date <= %(eval_date)s
                    ORDER BY date DESC LIMIT 1
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
                    WHERE symbol = %(symbol)s AND date <= %(eval_date)s
                    ORDER BY symbol, date DESC
                ),
                latest_quality AS (
                    SELECT symbol, score AS quality_score, revenue_score
                    FROM quality_verdicts
                    WHERE symbol = %(symbol)s
                )
                SELECT 
                    %(symbol)s AS symbol,
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
                FROM (SELECT 1) dummy
                LEFT JOIN latest_scores s ON true
                LEFT JOIN latest_quality q ON true
                CROSS JOIN latest_regime r
                """
                cur.execute(query, {"symbol": symbol, "eval_date": eval_date})
                row = cur.fetchone()
                
                if not row or (row["condition_rs"] is None and row["quality_score"] is None):
                     return ModelResult(
                        symbol=symbol,
                        model_id=self.id,
                        model_version=self.version,
                        evaluation_date=eval_date,
                        status="FAILED",
                        score=None,
                        payload=None,
                        error_message="CANSLIM primitives not found"
                    )
                
                # Execute exactly the same logic
                old_result = self._evaluate_candidate(dict(row))
                
                return ModelResult(
                    symbol=symbol,
                    model_id=self.id,
                    model_version=self.version,
                    evaluation_date=eval_date,
                    status="SUCCESS",
                    score=old_result["canslim_score"],
                    payload=old_result
                )
        finally:
            conn.close()

    def _evaluate_candidate(self, row):
        """Exact copy of the old evaluate_candidate logic to guarantee identical outputs."""
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
        
        # N: Catalyst & I: Institutional (via Company Knowledge)
        catalyst_status = "UNKNOWN"
        catalyst_rules = []
        catalyst_obs = []
        catalyst_evidence = []
        
        try:
            payload = self.evidence_service.evaluate(symbol, "CANSLIM")
            
            # Map evidence to component verdicts
            for ev in payload.evidence:
                catalyst_rules.append(ev.rule)
                if ev.status == "PASS":
                    catalyst_status = "PASS"
                    catalyst_obs.extend(ev.observations)
                    catalyst_evidence.extend(ev.quotes)
                elif catalyst_status != "PASS":
                    catalyst_status = "FAIL"
        except ValueError:
            # No knowledge found for symbol
            pass
            
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
                "Catalyst": {"status": "UNKNOWN" if not catalyst_rules else catalyst_status, "observations": catalyst_obs, "rules": catalyst_rules, "evidence": catalyst_evidence},
                "Institutional": {"status": "UNKNOWN", "observations": [], "rules": [], "evidence": []}
            }
        }
