from dataclasses import dataclass
from typing import Optional

from engine_core.portfolio_os_context import DecisionContext
from engine_core.portfolio_os_rule_engine import RuleEvaluationResult
from engine_core.xai_framework import ExplanationNode, XaiRule, XaiEvidence, XaiCalculation, XaiDecision


@dataclass(frozen=True)
class CaiRecommendation:
    """The final recommendation output from the CAI Engine."""
    action: str
    review_status: str
    review_reason: Optional[str]
    confidence: float
    action_score: float
    primary_reason: str
    secondary_reason: Optional[str]
    supporting_evidence: list[str]
    position_size_recommendation: Optional[float]
    explanation_tree: Optional[ExplanationNode] = None
    rules: Optional[list[XaiRule]] = None
    evidence: Optional[list[XaiEvidence]] = None
    calculations: Optional[list[XaiCalculation]] = None


class CaiEngine:
    """
    Module 8: CAI Engine.
    Takes a DecisionContext and the deterministic RuleEvaluationResult.
    Computes Confidence, Action Score, and assembles the Explanation payload.
    """

    def generate_recommendation(
        self, context: DecisionContext, rule_result: RuleEvaluationResult
    ) -> CaiRecommendation:
        
        # 1. Action is fully determined by the Rule Engine
        action = rule_result.action or "WAIT"
        
        # Evaluate Review Status based on PRD v2.0
        review_status = "NONE"
        review_reason = None
        
        # Example review triggers
        if context.stock_snapshot.trend_score and context.stock_snapshot.trend_score < 50:
            review_status = "REVIEW_REQUIRED"
            review_reason = "Trend weakening"
        elif context.portfolio_position.current_allocation > 0.10:
            review_status = "REVIEW_REQUIRED"
            review_reason = "Allocation exceeds target"
            
        if action == "REVIEW":
            action = "HOLD"
            review_status = "REVIEW_REQUIRED"
            review_reason = "Manually flagged for review"
            
        # 2. Compute Confidence based on PRD Section 7
        confidence = self._compute_confidence(context)
        
        # 3. Action Score (Quality/Conviction combination)
        action_score = self._compute_action_score(context)
        
        # 4. Position Size Recommendation
        pos_size = self._compute_position_size(action, confidence, context)
        
        # 5. Explanations (Template/Stub for LLM hand-off)
        primary_reason = rule_result.reason or f"Determined by rule: {rule_result.triggered_rule}"
        secondary_reason = f"Market Regime is {context.stock_snapshot.market_regime}"
        evidence = []
        if context.stock_snapshot.trend_score:
            evidence.append(f"Trend Score: {context.stock_snapshot.trend_score}")
        if context.stock_snapshot.risk_score:
            evidence.append(f"Risk Score: {context.stock_snapshot.risk_score}")

        cai_node = ExplanationNode("CAI Engine", action)
        cai_node.details["confidence"] = round(confidence, 2)
        cai_node.details["action_score"] = round(action_score, 2)
        cai_node.details["position_size"] = pos_size
        
        # Pull in rule engine node if exists
        if rule_result.explanation_node:
            cai_node.add_child(rule_result.explanation_node)
            
        xai_evidence = []
        if context.stock_snapshot.trend_score:
            xai_evidence.append(XaiEvidence("Trend Score", str(context.stock_snapshot.trend_score), "MRI Engine", "90 Days", "now", "Trend Calculation"))

        return CaiRecommendation(
            action=action,
            review_status=review_status,
            review_reason=review_reason,
            confidence=round(confidence, 2),
            action_score=round(action_score, 2),
            primary_reason=primary_reason,
            secondary_reason=secondary_reason,
            supporting_evidence=evidence,
            position_size_recommendation=pos_size,
            explanation_tree=cai_node,
            rules=rule_result.evaluated_rules or [],
            evidence=xai_evidence,
            calculations=[]
        )

    def _compute_confidence(self, context: DecisionContext) -> float:
        """
        Confidence depends on data completeness, market regime, risk, and agreement.
        """
        confidence = 100.0
        snapshot = context.stock_snapshot
        
        # Data Completeness Penalty
        if not snapshot.indicators.volume or not snapshot.indicators.avg_volume_20d:
            confidence -= 20.0
            
        # Market Regime Penalty
        if snapshot.market_regime in ["BEARISH", "CORRECTION"]:
            confidence -= 15.0
            
        # Risk Penalty
        if snapshot.risk_score and snapshot.risk_score > 75.0:
            confidence -= 10.0
            
        return max(0.0, min(100.0, confidence))

    def _compute_action_score(self, context: DecisionContext) -> float:
        """
        Overall quality of the actionable setup.
        """
        return context.stock_snapshot.mri_score or 50.0

    def _compute_position_size(self, action: str, confidence: float, context: DecisionContext) -> Optional[float]:
        """
        Returns a target allocation percentage based on action and confidence.
        """
        if action in ["EXIT"]:
            return 0.0
        if action in ["BUY", "ADD"]:
            if confidence >= 80:
                return 0.10  # 10% max allocation
            elif confidence >= 60:
                return 0.05  # 5% half allocation
            else:
                return 0.02  # 2% pilot allocation
        
        # KEEP existing allocation if HOLD/WAIT
        if context.portfolio_position:
            return context.portfolio_position.current_allocation
            
        return None
