from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Mapping, Optional
from engine_core.xai_framework import ExplanationNode


_MISSING = object()


@dataclass(frozen=True)
class IndicatorSnapshot:
    """Immutable view of already-computed technical facts for one symbol."""

    close: Optional[float]
    volume: Optional[float]
    ema_10: Optional[float]
    ema_20: Optional[float]
    ema_50: Optional[float]
    ema_100: Optional[float]
    ema_200: Optional[float]
    ema_100_slope_5d: Optional[float]
    ema_200_slope_20: Optional[float]
    rs_90d: Optional[float]
    avg_volume_20d: Optional[float]
    rolling_high_52w: Optional[float]
    weekly_trend_score: Optional[float]
    overhead_supply_score: Optional[float]
    breakout_state: Optional[str]
    breakout_age: Optional[int]
    condition_breakout_10d: Optional[bool]
    condition_price_quality: Optional[float]


@dataclass(frozen=True)
class StockSnapshot:
    """Immutable PortfolioOS contract for downstream decision layers."""

    symbol: str
    generated_at: datetime
    as_of_date: date
    indicators: IndicatorSnapshot
    market_regime: Optional[str]
    mri_score: Optional[float]
    mri_grade: Optional[str]
    trend_score: Optional[float]
    breakout_score: Optional[float]
    quality_score: Optional[float]
    risk_score: Optional[float]
    supporting_flags: tuple[str, ...]
    mri_explanation: Optional[ExplanationNode] = None


class StockSnapshotBuilder:
    """Build deterministic stock snapshots from precomputed MRI platform data.

    This builder consumes existing indicator facts and applies the deterministic MriEngine
    to generate the final normalized scores (Trend, Breakout, Risk, etc.).
    """

    def __init__(self):
        from engine_core.portfolio_os_mri_engine import MriEngine
        self.mri_engine = MriEngine()

    INDICATOR_FIELD_NAMES: tuple[str, ...] = (
        'close',
        'volume',
        'ema_10',
        'ema_20',
        'ema_50',
        'ema_100',
        'ema_200',
        'ema_100_slope_5d',
        'ema_200_slope_20',
        'rs_90d',
        'avg_volume_20d',
        'rolling_high_52w',
        'weekly_trend_score',
        'overhead_supply_score',
        'breakout_state',
        'breakout_age',
        'condition_breakout_10d',
    )

    FLAG_KEYS: tuple[str, ...] = (
        'condition_ema_50_200',
        'condition_ema_200_slope',
        'condition_rs',
        'condition_6m_high',
        'condition_volume',
        'condition_breakout_10d',
    )

    def build(
        self,
        symbol: str,
        indicator_row: Mapping[str, Any],
        score_row: Optional[Mapping[str, Any]] = None,
        quality_row: Optional[Mapping[str, Any]] = None,
        regime_row: Optional[Mapping[str, Any]] = None,
        generated_at: Optional[datetime] = None,
    ) -> StockSnapshot:
        if not symbol or not symbol.strip():
            raise ValueError('symbol is required')
        if indicator_row is None:
            raise ValueError('indicator_row is required')

        norm_indicator = normalize_mapping(indicator_row)
        norm_score = normalize_mapping(score_row or {})
        norm_quality = normalize_mapping(quality_row or {})
        norm_regime = normalize_mapping(regime_row or {})

        snapshot_date = self._resolve_as_of_date(norm_indicator, norm_score, norm_quality)
        timestamp = generated_at or datetime.now(timezone.utc)

        indicators = IndicatorSnapshot(
            close=_as_float(norm_indicator.get('close')),
            volume=_as_float(norm_indicator.get('volume')),
            ema_10=_as_float(norm_indicator.get('ema_10')),
            ema_20=_as_float(norm_indicator.get('ema_20')),
            ema_50=_as_float(norm_indicator.get('ema_50')),
            ema_100=_as_float(norm_indicator.get('ema_100')),
            ema_200=_as_float(norm_indicator.get('ema_200')),
            ema_100_slope_5d=_as_float(norm_indicator.get('ema_100_slope_5d')),
            ema_200_slope_20=_as_float(norm_indicator.get('ema_200_slope_20')),
            rs_90d=_as_float(norm_indicator.get('rs_90d')),
            avg_volume_20d=_as_float(norm_indicator.get('avg_volume_20d')),
            rolling_high_52w=_as_float(norm_indicator.get('rolling_high_52w')),
            weekly_trend_score=_as_float(norm_indicator.get('weekly_trend_score')),
            overhead_supply_score=_as_float(norm_indicator.get('overhead_supply_score')),
            breakout_state=_as_str_or_none(norm_indicator.get('breakout_state')),
            breakout_age=_as_int(norm_indicator.get('breakout_age')),
            condition_breakout_10d=_as_bool_or_none(norm_indicator.get('condition_breakout_10d')),
            condition_price_quality=_as_float(norm_indicator.get('condition_price_quality')),
        )

        # Compute deterministic MRI scores
        computed_scores, mri_explanation = self.mri_engine.compute_scores(indicators)
        
        mri_score = computed_scores.get('mri_score')
        trend_score = computed_scores.get('trend_score')
        breakout_score = computed_scores.get('breakout_score')
        risk_score = computed_scores.get('risk_score')

        quality_score = _first_numeric(norm_quality, 'qif_score', 'score')
        market_regime = _first_string(norm_regime, 'classification', 'regime')
        mri_grade = _first_string(norm_score, 'mri_grade', 'grade') or derive_mri_grade(mri_score)
        supporting_flags = self._collect_supporting_flags(norm_score, norm_indicator)

        return StockSnapshot(
            symbol=symbol.upper().strip(),
            generated_at=timestamp,
            as_of_date=snapshot_date,
            indicators=indicators,
            market_regime=market_regime,
            mri_score=mri_score,
            mri_grade=mri_grade,
            trend_score=trend_score,
            breakout_score=breakout_score,
            quality_score=quality_score,
            risk_score=risk_score,
            supporting_flags=supporting_flags,
            mri_explanation=mri_explanation,
        )

    def _resolve_as_of_date(
        self,
        indicator_row: Mapping[str, Any],
        score_row: Mapping[str, Any],
        quality_row: Mapping[str, Any],
    ) -> date:
        for row in (indicator_row, score_row, quality_row):
            raw = row.get('date', _MISSING)
            if raw is _MISSING:
                continue
            return _coerce_date(raw)
        raise ValueError('at least one source row must include a date')

    def _collect_supporting_flags(
        self,
        score_row: Mapping[str, Any],
        indicator_row: Mapping[str, Any],
    ) -> tuple[str, ...]:
        flags = []
        for key in self.FLAG_KEYS:
            value = score_row.get(key, indicator_row.get(key, _MISSING))
            if _is_truthy_flag(value):
                flags.append(key)
        return tuple(flags)


def normalize_mapping(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return a new dict with Decimal values converted to float."""
    normalized: dict[str, Any] = {}
    for key, value in row.items():
        if isinstance(value, Decimal):
            normalized[key] = float(value)
        else:
            normalized[key] = value
    return normalized


def derive_mri_grade(score: Optional[float]) -> Optional[str]:
    if score is None:
        return None
    if score >= 80:
        return 'HIGH_CONVICTION_BUY'
    if score >= 60:
        return 'WATCH_LIST'
    if score >= 40:
        return 'HOLD_MONITOR'
    return 'AVOID'


def _first_numeric(row: Mapping[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        value = _as_float(row.get(key, _MISSING))
        if value is not None:
            return value
    return None


def _first_string(row: Mapping[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        value = _as_str_or_none(row.get(key, _MISSING))
        if value is not None:
            return value
    return None


def _coerce_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError(f'unsupported date type: {type(value)}')


def _as_float(value: Any) -> Optional[float]:
    if value is _MISSING or value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_int(value: Any) -> Optional[int]:
    if value is _MISSING or value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def _as_bool_or_none(value: Any) -> Optional[bool]:
    if value is _MISSING or value is None:
        return None
    if isinstance(value, bool):
        return value
    return None


def _as_str_or_none(value: Any) -> Optional[str]:
    if value is _MISSING or value is None:
        return None
    if isinstance(value, str):
        return value
    return None


def _is_truthy_flag(value: Any) -> bool:
    if value is True:
        return True
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value > 0
    return False
