from typing import Dict, Any

from engine_core.portfolio_os_snapshot import IndicatorSnapshot
from engine_core.xai_framework import ExplanationNode, XaiCalculation
from typing import Dict, Any, Tuple


class MriEngine:
    """
    Evaluates raw indicator facts to compute standardized MRI scores (0-100).
    Follows deterministic logic; no external dependencies or models.
    """

    def compute_scores(self, indicators: IndicatorSnapshot) -> Tuple[Dict[str, float], ExplanationNode]:
        """
        Computes all MRI component scores based on the provided IndicatorSnapshot.
        Returns a tuple of (scores_dict, explanation_node).
        """
        if not indicators:
            explanation = ExplanationNode("MRI Engine", "0.0", {"reason": "No indicator data available"})
            return {
                "trend_score": 0.0,
                "breakout_score": 0.0,
                "risk_score": 100.0,
                "mri_score": 0.0
            }, explanation

        trend_score, trend_exp = self._compute_trend_score(indicators)
        breakout_score, breakout_exp = self._compute_breakout_score(indicators)
        risk_score, risk_exp = self._compute_risk_score(indicators)

        # Basic equally-weighted MRI score for Phase 1
        mri_score = (trend_score + breakout_score + (100.0 - risk_score)) / 3.0

        mri_node = ExplanationNode("MRI Engine", str(round(mri_score, 2)))
        mri_node.add_child(trend_exp)
        mri_node.add_child(breakout_exp)
        mri_node.add_child(risk_exp)
        
        calc = XaiCalculation("MRI Score", "(Trend + Breakout + (100 - Risk)) / 3", f"Trend: {trend_score}, Breakout: {breakout_score}, Risk: {risk_score}", "now", str(round(mri_score, 2)))
        mri_node.details["calculations"] = [calc.to_dict()]

        return {
            "trend_score": round(trend_score, 2),
            "breakout_score": round(breakout_score, 2),
            "risk_score": round(risk_score, 2),
            "mri_score": round(mri_score, 2)
        }, mri_node

    def _compute_trend_score(self, indicators: IndicatorSnapshot) -> Tuple[float, ExplanationNode]:
        """
        Evaluates Trend using EMA alignment and RS.
        """
        score = 0.0
        details = {}
        
        # 1. EMA Alignment (40 points)
        alignment_points = 0.0
        if indicators.close and indicators.ema_20 and indicators.close > indicators.ema_20:
            alignment_points += 10.0
        if indicators.ema_20 and indicators.ema_50 and indicators.ema_20 > indicators.ema_50:
            alignment_points += 10.0
        if indicators.ema_50 and indicators.ema_100 and indicators.ema_50 > indicators.ema_100:
            alignment_points += 10.0
        if indicators.ema_100 and indicators.ema_200 and indicators.ema_100 > indicators.ema_200:
            alignment_points += 10.0
            
        score += alignment_points
        details["ema_alignment_points"] = alignment_points

        # 2. Slopes (20 points)
        slope_points = 0.0
        if indicators.ema_100_slope_5d and indicators.ema_100_slope_5d > 0:
            slope_points += 10.0
        if indicators.ema_200_slope_20 and indicators.ema_200_slope_20 > 0:
            slope_points += 10.0
            
        score += slope_points
        details["slope_points"] = slope_points

        # 3. Relative Strength (20 points) - Assumes RS >= 0 is positive momentum
        rs_points = 0.0
        if indicators.rs_90d and indicators.rs_90d > 0:
            rs_points = min(20.0, indicators.rs_90d * 2.0)
            score += rs_points
            
        details["rs_points"] = rs_points

        # 4. Fallback to precomputed trend score if alignment logic is incomplete
        if score == 0.0 and indicators.weekly_trend_score:
            return float(indicators.weekly_trend_score), ExplanationNode("Trend Score", str(indicators.weekly_trend_score), {"fallback": "Used weekly_trend_score"})

        final_score = min(100.0, max(0.0, score))
        node = ExplanationNode("Trend Score", str(final_score), details)
        return final_score, node

    def _compute_breakout_score(self, indicators: IndicatorSnapshot) -> Tuple[float, ExplanationNode]:
        """
        Evaluates Breakout conviction.
        """
        score = 0.0
        details = {}
        
        # 1. State (50 points)
        state_points = 0.0
        if indicators.breakout_state == "BROKEN_OUT":
            state_points += 50.0
            
            # Age penalty: newer breakouts are better
            if indicators.breakout_age is not None:
                penalty = min(20.0, indicators.breakout_age * 2.0)
                state_points -= penalty
                details["age_penalty"] = penalty
                
        score += state_points
        details["state_points"] = state_points
                
        # 2. Volume expansion (30 points)
        vol_points = 0.0
        if indicators.volume and indicators.avg_volume_20d and indicators.avg_volume_20d > 0:
            vol_ratio = indicators.volume / indicators.avg_volume_20d
            if vol_ratio > 1.5:
                vol_points += 30.0
            elif vol_ratio > 1.0:
                vol_points += 15.0
                
        score += vol_points
        details["volume_points"] = vol_points

        # 3. Overhead supply penalty
        if indicators.overhead_supply_score:
            score -= indicators.overhead_supply_score
            details["overhead_penalty"] = indicators.overhead_supply_score

        final_score = min(100.0, max(0.0, score))
        node = ExplanationNode("Breakout Score", str(final_score), details)
        return final_score, node

    def _compute_risk_score(self, indicators: IndicatorSnapshot) -> Tuple[float, ExplanationNode]:
        """
        Evaluates Risk (Lower is better/safer, Higher means more risk).
        """
        risk = 50.0  # Base risk
        details = {"base_risk": 50.0}
        
        # Proximity to 52W High (closer = less overhead risk = lower risk score)
        if indicators.rolling_high_52w and indicators.close and indicators.rolling_high_52w > 0:
            distance_pct = ((indicators.rolling_high_52w - indicators.close) / indicators.rolling_high_52w) * 100
            
            if distance_pct < 5.0:
                risk -= 20.0
                details["proximity_adjustment"] = -20.0
            elif distance_pct > 20.0:
                risk += 20.0
                details["proximity_adjustment"] = 20.0

        # Volume liquidity (higher volume = less liquidity risk)
        if indicators.avg_volume_20d:
            if indicators.avg_volume_20d > 500000:
                risk -= 10.0
                details["liquidity_adjustment"] = -10.0
            elif indicators.avg_volume_20d < 100000:
                risk += 20.0
                details["liquidity_adjustment"] = 20.0

        final_score = min(100.0, max(0.0, risk))
        node = ExplanationNode("Risk Score", str(final_score), details)
        return final_score, node
