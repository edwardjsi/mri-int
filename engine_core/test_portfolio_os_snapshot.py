import os
import sys
from dataclasses import FrozenInstanceError
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine_core.portfolio_os_snapshot import (  # noqa: E402
    IndicatorSnapshot,
    StockSnapshotBuilder,
    derive_mri_grade,
    normalize_mapping,
)


class TestNormalizeMapping:
    def test_decimal_values_become_float_without_mutating_input(self):
        row = {'close': Decimal('1022.25'), 'weekly_trend_score': Decimal('75')}
        out = normalize_mapping(row)
        assert row['close'] == Decimal('1022.25')
        assert out['close'] == 1022.25
        assert out['weekly_trend_score'] == 75.0


class TestDeriveMriGrade:
    @pytest.mark.parametrize(
        'score,expected',
        [
            (85, 'HIGH_CONVICTION_BUY'),
            (65, 'WATCH_LIST'),
            (45, 'HOLD_MONITOR'),
            (20, 'AVOID'),
            (None, None),
        ],
    )
    def test_grade_bands_follow_existing_mri_thresholds(self, score, expected):
        assert derive_mri_grade(score) == expected


class TestStockSnapshotBuilder:
    def test_builds_snapshot_with_deterministic_mri_engine(self):
        builder = StockSnapshotBuilder()
        generated_at = datetime(2026, 7, 29, 6, 0, tzinfo=timezone.utc)
        snapshot = builder.build(
            symbol='indusinDbk',
            indicator_row={
                'date': date(2026, 7, 28),
                'close': Decimal('1022.25'),
                'volume': Decimal('350000'),
                'ema_10': Decimal('980'),
                'ema_20': Decimal('941.80'),
                'ema_50': Decimal('919.00'),
                'ema_100': Decimal('899.88'),
                'ema_200': Decimal('887.42'),
                'ema_100_slope_5d': Decimal('12.5'),
                'ema_200_slope_20': Decimal('4.5'),
                'rs_90d': Decimal('18.2'),
                'avg_volume_20d': Decimal('250000'),
                'rolling_high_52w': Decimal('1040'),
                'weekly_trend_score': Decimal('100'),
                'overhead_supply_score': Decimal('0'),
                'breakout_state': 'BROKEN_OUT',
                'breakout_age': 1,
                'condition_breakout_10d': True,
                'condition_price_quality': Decimal('0.82'),
            },
            score_row={
                'date': date(2026, 7, 28),
                'total_score': Decimal('86'),
                'condition_ema_50_200': True,
                'condition_ema_200_slope': True,
                'condition_rs': True,
                'condition_6m_high': True,
                'condition_volume': True,
            },
            quality_row={
                'date': date(2026, 7, 28),
                'qif_score': Decimal('82'),
            },
            regime_row={'classification': 'BULLISH'},
            generated_at=generated_at,
        )

        assert snapshot.symbol == 'INDUSINDBK'
        assert snapshot.as_of_date == date(2026, 7, 28)
        assert snapshot.generated_at == generated_at
        assert snapshot.market_regime == 'BULLISH'
        assert snapshot.mri_score == 71.0
        assert snapshot.mri_grade == 'WATCH_LIST'
        assert snapshot.trend_score == 80.0
        assert snapshot.quality_score == 82.0
        assert snapshot.indicators.breakout_state == 'BROKEN_OUT'
        assert snapshot.indicators.breakout_age == 1
        assert snapshot.indicators.condition_price_quality == 0.82
        assert snapshot.supporting_flags == (
            'condition_ema_50_200',
            'condition_ema_200_slope',
            'condition_rs',
            'condition_6m_high',
            'condition_volume',
            'condition_breakout_10d',
        )

    def test_uses_explicit_grade_when_provided(self):
        builder = StockSnapshotBuilder()
        snapshot = builder.build(
            symbol='titan',
            indicator_row={'date': '2026-07-28', 'close': 10.0},
            score_row={'grade': 'CUSTOM_GRADE', 'total_score': 81},
        )
        assert snapshot.mri_grade == 'CUSTOM_GRADE'

    def test_supporting_flags_keep_falsey_conditions_out(self):
        builder = StockSnapshotBuilder()
        snapshot = builder.build(
            symbol='paytm',
            indicator_row={
                'date': date(2026, 7, 28),
                'close': 10.0,
                'condition_breakout_10d': False,
                'condition_price_quality': 0.0,
            },
            score_row={
                'total_score': 55,
                'condition_ema_50_200': True,
                'condition_rs': False,
                'condition_volume': 0,
            },
        )
        assert snapshot.supporting_flags == ('condition_ema_50_200',)

    def test_requires_at_least_one_source_date(self):
        builder = StockSnapshotBuilder()
        with pytest.raises(ValueError, match='at least one source row must include a date'):
            builder.build(symbol='TCS', indicator_row={'close': 1.0})

    def test_snapshot_objects_are_immutable(self):
        builder = StockSnapshotBuilder()
        snapshot = builder.build(
            symbol='tcs',
            indicator_row={'date': date(2026, 7, 28), 'close': 100.0},
        )
        with pytest.raises(FrozenInstanceError):
            snapshot.symbol = 'INFY'
        with pytest.raises(FrozenInstanceError):
            snapshot.indicators = IndicatorSnapshot(
                close=1.0,
                volume=None,
                ema_10=None,
                ema_20=None,
                ema_50=None,
                ema_100=None,
                ema_200=None,
                ema_100_slope_5d=None,
                ema_200_slope_20=None,
                rs_90d=None,
                avg_volume_20d=None,
                rolling_high_52w=None,
                weekly_trend_score=None,
                overhead_supply_score=None,
                breakout_state=None,
                breakout_age=None,
                condition_breakout_10d=None,
                condition_price_quality=None,
            )
