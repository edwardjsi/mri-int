from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from engine_core.db import get_connection
from engine_core.portfolio_os_snapshot import StockSnapshot, StockSnapshotBuilder


class StockSnapshotNotFoundError(LookupError):
    """Raised when no latest indicator row exists for a requested symbol."""


class StockSnapshotRepository:
    """Fetch live source rows and build a deterministic PortfolioOS snapshot."""

    INDICATOR_SQL = """
        SELECT
            symbol,
            date,
            close,
            volume,
            ema_10,
            ema_20,
            ema_50,
            ema_100,
            ema_200,
            ema_100_slope_5d,
            ema_200_slope_20,
            rs_90d,
            avg_volume_20d,
            rolling_high_52w,
            weekly_trend_score,
            overhead_supply_score,
            breakout_state,
            breakout_age,
            condition_breakout_10d,
            condition_price_quality
        FROM daily_prices
        WHERE symbol = %s
        ORDER BY date DESC
        LIMIT 1
    """

    SCORE_SQL = """
        SELECT
            symbol,
            date,
            total_score,
            condition_ema_50_200,
            condition_ema_200_slope,
            condition_rs,
            condition_6m_high,
            condition_volume,
            condition_breakout_10d,
            condition_price_quality
        FROM stock_scores
        WHERE symbol = %s
        ORDER BY date DESC
        LIMIT 1
    """

    QUALITY_SQL = """
        SELECT
            symbol,
            updated_at,
            score,
            category
        FROM quality_verdicts
        WHERE symbol = %s
        ORDER BY updated_at DESC
        LIMIT 1
    """

    REGIME_SQL = """
        SELECT
            date,
            classification
        FROM market_regime
        ORDER BY date DESC
        LIMIT 1
    """

    def __init__(self, builder: Optional[StockSnapshotBuilder] = None):
        self.builder = builder or StockSnapshotBuilder()

    def build_latest_for_symbol(
        self,
        symbol: str,
        conn: Any | None = None,
        generated_at: datetime | None = None,
    ) -> StockSnapshot:
        normalized_symbol = symbol.upper().strip()
        if not normalized_symbol:
            raise ValueError('symbol is required')

        should_close = False
        if conn is None:
            conn = get_connection()
            should_close = True

        try:
            source_rows = self.fetch_source_rows(normalized_symbol, conn)
            return self.builder.build(
                symbol=normalized_symbol,
                indicator_row=source_rows['indicator_row'],
                score_row=source_rows.get('score_row'),
                quality_row=source_rows.get('quality_row'),
                regime_row=source_rows.get('regime_row'),
                generated_at=generated_at or datetime.now(timezone.utc),
            )
        finally:
            if should_close:
                conn.close()

    def fetch_source_rows(self, symbol: str, conn: Any) -> dict[str, Any]:
        indicator_row = self._fetch_one(conn, self.INDICATOR_SQL, (symbol,))
        if not indicator_row:
            raise StockSnapshotNotFoundError(f'No indicator row found for {symbol}')

        score_row = self._fetch_one(conn, self.SCORE_SQL, (symbol,))
        quality_row = self._fetch_one(conn, self.QUALITY_SQL, (symbol,))
        if quality_row and quality_row.get('updated_at') is not None and quality_row.get('date') is None:
            quality_row = dict(quality_row)
            quality_row['date'] = quality_row['updated_at']
            quality_row['qif_score'] = quality_row.get('score')

        regime_row = self._fetch_one(conn, self.REGIME_SQL)
        return {
            'indicator_row': indicator_row,
            'score_row': score_row,
            'quality_row': quality_row,
            'regime_row': regime_row,
        }

    @staticmethod
    def _fetch_one(conn: Any, sql: str, params: tuple[Any, ...] | None = None) -> dict[str, Any] | None:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            row = cur.fetchone()
        if row is None:
            return None
        return dict(row)
