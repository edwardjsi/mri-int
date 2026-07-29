import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_core.portfolio_os_snapshot import IndicatorSnapshot
from engine_core.portfolio_os_mri_engine import MriEngine  # noqa: E402


class TestMriEngine:
    def setup_method(self):
        self.engine = MriEngine()

    def test_computes_perfect_trend_score_with_full_alignment(self):
        indicator = IndicatorSnapshot(
            close=120.0, volume=1000, ema_10=115.0, ema_20=110.0, ema_50=100.0,
            ema_100=90.0, ema_200=80.0, ema_100_slope_5d=1.5, ema_200_slope_20=0.5,
            rs_90d=15.0, avg_volume_20d=900, rolling_high_52w=125.0,
            weekly_trend_score=0.0, overhead_supply_score=0.0,
            breakout_state="NONE", breakout_age=0,
            condition_breakout_10d=False, condition_price_quality=1.0
        )
        scores = self.engine.compute_scores(indicator)
        
        # 40 (alignment) + 20 (slopes) + 20 (capped RS) = 80.0
        assert scores["trend_score"] == 80.0

    def test_computes_breakout_score_with_penalties(self):
        indicator = IndicatorSnapshot(
            close=120.0, volume=200000, ema_10=115.0, ema_20=110.0, ema_50=100.0,
            ema_100=90.0, ema_200=80.0, ema_100_slope_5d=1.5, ema_200_slope_20=0.5,
            rs_90d=15.0, avg_volume_20d=100000, rolling_high_52w=125.0,
            weekly_trend_score=0.0, overhead_supply_score=10.0,
            breakout_state="BROKEN_OUT", breakout_age=2,
            condition_breakout_10d=True, condition_price_quality=1.0
        )
        scores = self.engine.compute_scores(indicator)
        
        # Base 50 - 4 (age penalty 2*2) + 30 (vol ratio > 1.5) - 10 (overhead) = 66.0
        assert scores["breakout_score"] == 66.0

    def test_computes_risk_score_based_on_distance_and_volume(self):
        indicator = IndicatorSnapshot(
            close=80.0, volume=50000, ema_10=115.0, ema_20=110.0, ema_50=100.0,
            ema_100=90.0, ema_200=80.0, ema_100_slope_5d=1.5, ema_200_slope_20=0.5,
            rs_90d=15.0, avg_volume_20d=50000, rolling_high_52w=125.0,
            weekly_trend_score=0.0, overhead_supply_score=0.0,
            breakout_state="NONE", breakout_age=0,
            condition_breakout_10d=False, condition_price_quality=1.0
        )
        scores = self.engine.compute_scores(indicator)
        
        # Distance = (125-80)/125 = 36% (>20% -> +20 risk)
        # Volume = 50,000 (<100k -> +20 risk)
        # Base 50 + 20 + 20 = 90.0 risk
        assert scores["risk_score"] == 90.0

    def test_handles_none_indicators(self):
        scores = self.engine.compute_scores(None)
        assert scores["trend_score"] == 0.0
        assert scores["risk_score"] == 100.0
        assert scores["mri_score"] == 0.0
