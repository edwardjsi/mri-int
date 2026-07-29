from typing import Dict, Any

from engine_core.portfolio_os_snapshot import IndicatorSnapshot


class MriEngine:
    """
    Evaluates raw indicator facts to compute standardized MRI scores (0-100).
    Follows deterministic logic; no external dependencies or models.
    """

    def compute_scores(self, indicators: IndicatorSnapshot) -> Dict[str, float]:
        """
        Computes all MRI component scores based on the provided IndicatorSnapshot.
        """
        if not indicators:
            return {
                "trend_score": 0.0,
                "breakout_score": 0.0,
                "risk_score": 100.0,  # Max risk if no data
                "mri_score": 0.0
            }

        trend_score = self._compute_trend_score(indicators)
        breakout_score = self._compute_breakout_score(indicators)
        risk_score = self._compute_risk_score(indicators)

        # Basic equally-weighted MRI score for Phase 1 (Quality is usually external, leaving it out of this pure technical calc for now)
        mri_score = (trend_score + breakout_score + (100.0 - risk_score)) / 3.0

        return {
            "trend_score": round(trend_score, 2),
            "breakout_score": round(breakout_score, 2),
            "risk_score": round(risk_score, 2),
            "mri_score": round(mri_score, 2)
        }

    def _compute_trend_score(self, indicators: IndicatorSnapshot) -> float:
        """
        Evaluates Trend using EMA alignment and RS.
        """
        score = 0.0
        # 1. EMA Alignment (40 points)
        if indicators.close and indicators.ema_20 and indicators.close > indicators.ema_20:
            score += 10.0
        if indicators.ema_20 and indicators.ema_50 and indicators.ema_20 > indicators.ema_50:
            score += 10.0
        if indicators.ema_50 and indicators.ema_100 and indicators.ema_50 > indicators.ema_100:
            score += 10.0
        if indicators.ema_100 and indicators.ema_200 and indicators.ema_100 > indicators.ema_200:
            score += 10.0

        # 2. Slopes (20 points)
        if indicators.ema_100_slope_5d and indicators.ema_100_slope_5d > 0:
            score += 10.0
        if indicators.ema_200_slope_20 and indicators.ema_200_slope_20 > 0:
            score += 10.0

        # 3. Relative Strength (20 points) - Assumes RS >= 0 is positive momentum
        if indicators.rs_90d and indicators.rs_90d > 0:
            score += min(20.0, indicators.rs_90d * 2.0)  # scale RS up to 20

        # 4. Fallback to precomputed trend score if alignment logic is incomplete
        if score == 0.0 and indicators.weekly_trend_score:
            return float(indicators.weekly_trend_score)

        return min(100.0, max(0.0, score))

    def _compute_breakout_score(self, indicators: IndicatorSnapshot) -> float:
        """
        Evaluates Breakout conviction.
        """
        score = 0.0
        
        # 1. State (50 points)
        if indicators.breakout_state == "BROKEN_OUT":
            score += 50.0
            
            # Age penalty: newer breakouts are better
            if indicators.breakout_age is not None:
                penalty = min(20.0, indicators.breakout_age * 2.0)
                score -= penalty
                
        # 2. Volume expansion (30 points)
        if indicators.volume and indicators.avg_volume_20d and indicators.avg_volume_20d > 0:
            vol_ratio = indicators.volume / indicators.avg_volume_20d
            if vol_ratio > 1.5:
                score += 30.0
            elif vol_ratio > 1.0:
                score += 15.0

        # 3. Overhead supply penalty
        if indicators.overhead_supply_score:
            score -= indicators.overhead_supply_score

        return min(100.0, max(0.0, score))

    def _compute_risk_score(self, indicators: IndicatorSnapshot) -> float:
        """
        Evaluates Risk (Lower is better/safer, Higher means more risk).
        """
        risk = 50.0  # Base risk
        
        # Proximity to 52W High (closer = less overhead risk = lower risk score)
        if indicators.rolling_high_52w and indicators.close and indicators.rolling_high_52w > 0:
            distance_pct = ((indicators.rolling_high_52w - indicators.close) / indicators.rolling_high_52w) * 100
            
            if distance_pct < 5.0:
                risk -= 20.0
            elif distance_pct > 20.0:
                risk += 20.0

        # Volume liquidity (higher volume = less liquidity risk)
        if indicators.avg_volume_20d:
            if indicators.avg_volume_20d > 500000:
                risk -= 10.0
            elif indicators.avg_volume_20d < 100000:
                risk += 20.0

        return min(100.0, max(0.0, risk))
