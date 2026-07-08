# Updated: 2026-04-24
import logging

import numpy as np
import pandas as pd
from psycopg2.extras import execute_batch

from engine_core.db import get_connection
try:
    from engine_core.email_service import send_alert_email
except Exception:  # pragma: no cover
    def send_alert_email(subject, body):
        # No‑op placeholder when email services are unavailable (e.g., during unit tests)
        pass
from engine_core.cas_indicators import (
    compute_ema_100,
    compute_overhead_supply_score,
    compute_rolling_high_52w,
    compute_weekly_trend_score,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Calibration wiring (Decision 102 — no Magic Numbers; YAML is source of truth).
# Reading these at module import means changes to capital_allocation.yaml
# require a process restart. That's intentional: indicator recomputation is
# a batch operation, not a hot path.
def _get_overhead_max_count() -> int:
    """Read overhead_supply_score max_count_for_100 from capital_allocation.yaml.

    Falls back to cas_indicators.OVERHEAD_MAX_COUNT if YAML is unavailable
    (e.g., during unit tests that don't have the config on disk).
    """
    try:
        from engine_core.capital_allocation import load_config
        cfg = load_config("config/capital_allocation.yaml")
        return int(cfg.get("subscore", {}).get("overhead_supply", {}).get(
            "max_count_for_100", 20))
    except Exception:
        # Config not loadable (test env, missing file, etc.) — use default.
        from engine_core.cas_indicators import OVERHEAD_MAX_COUNT
        return OVERHEAD_MAX_COUNT


class IndicatorComputationError(Exception):
    """Raised when indicator computation or validation fails."""


INDICATOR_COLUMNS = (
    ("ema_10", "NUMERIC"),
    ("ema_20", "NUMERIC"),
    ("ema_50", "NUMERIC"),
    ("ema_200", "NUMERIC"),
    ("ema_100", "NUMERIC"),  # CAS V1.0 (Decision 100)
    ("ema_100_slope_5d", "NUMERIC"),  # CAS V1.1a (Decision 101, Gap 1)
    ("rsi_14", "NUMERIC"),
    ("below_200ema", "BOOLEAN"),
    ("ema_200_slope_20", "NUMERIC"),
    ("rolling_high_6m", "NUMERIC"),
    ("rolling_high_52w", "NUMERIC"),  # CAS V1.0 (Decision 100)
    ("weekly_trend_score", "NUMERIC"),  # CAS V1.0 (Decision 100)
    ("overhead_supply_score", "NUMERIC"),  # CAS V1.0 (Decision 100)
    ("avg_volume_20d", "NUMERIC"),
    ("rs_90d", "NUMERIC"),
    ("high_10d", "NUMERIC"),
    ("low_5d", "NUMERIC"),
    ("atr_14", "NUMERIC"),
    ("condition_breakout_10d", "BOOLEAN"),
    ("condition_price_quality", "NUMERIC"),
    ("breakout_state", "VARCHAR(30) DEFAULT 'CONSOLIDATING'"),
    ("breakout_age", "INTEGER DEFAULT NULL"),
)

# The daily pipeline needs current and near-current indicators, while writing
# the entire history every run is too expensive for the runtime budget.
# PERSIST_ROWS=60 provides approx 3 months of buffer for the dashboard history.
PERSIST_ROWS = 60


def add_indicator_columns_if_missing():
    """Ensure the indicator columns exist on daily_prices."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for col_name, col_type in INDICATOR_COLUMNS:
                cur.execute(
                    f"""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM information_schema.columns
                            WHERE table_name = 'daily_prices'
                              AND column_name = '{col_name}'
                        ) THEN
                            ALTER TABLE daily_prices ADD COLUMN {col_name} {col_type};
                        END IF;
                    END $$;
                    """
                )
        conn.commit()
    finally:
        conn.close()


def fetch_symbols_needing_repair():
    """Return symbols that have NULL indicators, RS gaps, or stale data."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Fetch NULLs
            # 2. Fetch RS Gaps (RS=0 usually means merge failure)
            # 3. Fetch Stale Indicators (no change vs prev day)
            cur.execute(
                """
                WITH latest_date AS (SELECT MAX(date) FROM daily_prices),
                prev_date AS (SELECT DISTINCT date FROM daily_prices WHERE date < (SELECT MAX(date) FROM daily_prices) ORDER BY date DESC LIMIT 1)
                SELECT DISTINCT symbol
                FROM daily_prices
                WHERE (
                    ema_50 IS NULL
                    OR ema_200 IS NULL
                    OR ema_100 IS NULL         -- CAS V1.0 (Decision 100)
                    OR ema_100_slope_5d IS NULL -- CAS V1.1a (Decision 101, Gap 1)
                    OR rs_90d IS NULL
                    OR rs_90d = 0
                    OR avg_volume_20d IS NULL
                    OR rolling_high_6m IS NULL
                    OR rolling_high_52w IS NULL    -- CAS V1.0 (Decision 100)
                    OR weekly_trend_score IS NULL  -- CAS V1.0 (Decision 100)
                    OR overhead_supply_score IS NULL  -- CAS V1.0 (Decision 100)
                )
                OR (
                    date = (SELECT * FROM latest_date)
                    AND symbol IN (
                        SELECT curr.symbol
                        FROM daily_prices curr
                        JOIN daily_prices prev ON curr.symbol = prev.symbol AND prev.date = (SELECT * FROM prev_date)
                        WHERE curr.date = (SELECT * FROM latest_date)
                          AND curr.ema_50 = prev.ema_50
                          AND curr.volume > 0
                    )
                )
                ORDER BY symbol
                """
            )
            return [row["symbol"] for row in cur.fetchall()]
    finally:
        conn.close()


def chunked(items, chunk_size):
    """Yield successive chunks from a list."""
    for start in range(0, len(items), chunk_size):
        yield items[start : start + chunk_size]


def fetch_data(symbols=None):
    """Fetch the history needed to recompute indicators for the target symbols."""
    conn = get_connection()
    try:
        if not symbols:
            symbols = fetch_symbols_needing_repair()

        if not symbols:
            logger.info("All symbols already have indicators computed.")
            return pd.DataFrame(), pd.DataFrame()

        logger.info("Computing indicators for %d symbols with missing data", len(symbols))

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT symbol, date, open, high, low, close, volume,
                       ema_10, ema_20, ema_50, ema_200, ema_100,
                       ema_100_slope_5d
                FROM daily_prices
                WHERE symbol = ANY(%s)
                ORDER BY symbol, date
                """,
                (symbols,),
            )
            rows = cur.fetchall()

            cur.execute(
                """
                SELECT date, close AS idx_close
                FROM market_index_prices
                WHERE symbol = 'NIFTY50'
                ORDER BY date
                """
            )
            idx_rows = cur.fetchall()

        if not rows:
            return pd.DataFrame(), pd.DataFrame()

        df = pd.DataFrame([dict(r) for r in rows])
        df["date"] = pd.to_datetime(df["date"])
        df["close"] = pd.to_numeric(df["close"])
        df["high"] = pd.to_numeric(df["high"])
        df["volume"] = pd.to_numeric(df["volume"])

        for column in ("open", "high", "low", "close", "volume",
                       "ema_10", "ema_20", "ema_50", "ema_200", "ema_100",
                       "ema_100_slope_5d"):
            if column in df.columns:
                df[column] = pd.to_numeric(df[column], errors="coerce")

        idx_df = pd.DataFrame([dict(r) for r in idx_rows]) if idx_rows else pd.DataFrame()
        if not idx_df.empty:
            idx_df["date"] = pd.to_datetime(idx_df["date"])
            idx_df["idx_close"] = pd.to_numeric(idx_df["idx_close"])

        return df, idx_df
    finally:
        conn.close()


def compute_indicators(df, idx_df):
    """Compute all technical indicators and prepare row-level updates."""
    if df.empty:
        return []

    updates = []
    for symbol in df["symbol"].unique():
        # reset_index(drop=True) is critical: when df contains multiple symbols,
        # the filtered subset has non-contiguous indices from the original df.
        # Leaving them intact causes downstream functions (notably
        # compute_weekly_trend_score, which does pd.date_range reindex) to
        # silently return NaN for non-first symbols. The fix: reset to a clean
        # 0..N-1 index before any per-symbol computation.
        s_df = df[df["symbol"] == symbol].copy().reset_index(drop=True)
        if len(s_df) < 20:
            logger.warning("Symbol %s has insufficient data: %d rows", symbol, len(s_df))
            continue

        s_df["ema_10"] = s_df["close"].ewm(span=10, adjust=False).mean()
        s_df["ema_20"] = s_df["close"].ewm(span=20, adjust=False).mean()
        s_df["ema_50"] = s_df["close"].ewm(span=50, adjust=False).mean()
        s_df["ema_200"] = (
            s_df["close"].ewm(span=200, adjust=False).mean()
            if len(s_df) >= 200
            else s_df["ema_50"]
        )

        s_df["ema_200_slope_20"] = s_df["ema_200"].diff(20)

        # CAS V1.0 (Decision 100) — four new indicator columns.
        # These are computed via pure functions in engine_core/cas_indicators.py
        # (testable in isolation, no DB access).
        s_df["ema_100"] = compute_ema_100(s_df["close"])
        # ema_100_slope_5d (V1.1a, Decision 101 Gap 1): the ema100_rising
        # eligibility gate reads this. Without it, the gate always fails.
        # diff(5) = EMA-100 today minus EMA-100 five trading days ago.
        # Positive → "rising"; gate passes.
        s_df["ema_100_slope_5d"] = s_df["ema_100"].diff(5)
        s_df["rolling_high_52w"] = compute_rolling_high_52w(s_df["high"])
        s_df["weekly_trend_score"] = compute_weekly_trend_score(s_df, s_df["rolling_high_52w"])
        s_df["overhead_supply_score"] = compute_overhead_supply_score(
            s_df["high"], s_df["close"],
            max_count=_get_overhead_max_count(),
        )

        delta = s_df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        s_df["rsi_14"] = 100 - (100 / (1 + rs))

        s_df["below_200ema"] = s_df["close"] < s_df["ema_200"]
        s_df["rolling_high_6m"] = s_df["close"].rolling(window=126, min_periods=20).max()
        s_df["avg_volume_20d"] = s_df["volume"].rolling(window=20).mean()

        # STEE Indicators
        s_df["high_10d"] = s_df["high"].rolling(window=10).max().shift(1)
        s_df["low_5d"] = s_df["low"].rolling(window=5).min().shift(1)
        s_df["condition_breakout_10d"] = s_df["close"] > s_df["high_10d"]

        # ATR Calculation
        tr1 = s_df["high"] - s_df["low"]
        tr2 = (s_df["high"] - s_df["close"].shift(1)).abs()
        tr3 = (s_df["low"] - s_df["close"].shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        s_df["atr_14"] = tr.rolling(window=14).mean()
        
        # Compute additional metrics for breakout classification
        # 5‑day price range percentage (volatility contraction)
        price_range_5d = (
            s_df['high'].rolling(5).max() - s_df['low'].rolling(5).min()
        ) / s_df['low'].rolling(5).min().replace({0: None})
        s_df['price_range_5d'] = price_range_5d

        # Volume multiplier vs 20‑day average
        s_df['vol_multiplier'] = s_df['volume'] / s_df['avg_volume_20d']

        # Proximity to 6‑month high (fraction of distance)
        s_df['proximity_to_high'] = (
            s_df['rolling_high_6m'] - s_df['close']
        ) / s_df['rolling_high_6m']

        # Approximate Weekly RSI (70 trading days) using 5-day diff
        delta_w = s_df["close"].diff(5)
        gain_w = delta_w.where(delta_w > 0, 0).rolling(window=14).mean()
        loss_w = (-delta_w.where(delta_w < 0, 0)).rolling(window=14).mean()
        rs_w = gain_w / (loss_w + 1e-9)
        s_df["weekly_rsi_14"] = 100 - (100 / (1 + rs_w))

        # Standard MACD (12, 26, 9)
        ema_12 = s_df["close"].ewm(span=12, adjust=False).mean()
        ema_26 = s_df["close"].ewm(span=26, adjust=False).mean()
        s_df["macd_line"] = ema_12 - ema_26
        s_df["macd_signal"] = s_df["macd_line"].ewm(span=9, adjust=False).mean()
        s_df["macd_hist"] = s_df["macd_line"] - s_df["macd_signal"]

        # Breakout state classification
        def _classify_breakout(row):
            # Active breakout
            if (
                row.get('condition_breakout_10d')
                and row.get('vol_multiplier', 0) >= 1.3
                and row['close'] > row.get('ema_50', 0) > row.get('ema_200', 0)
                and row.get('weekly_rsi_14', 0) >= 60
                and row.get('macd_hist', 0) > 0  # Standard MACD Positive Cross
            ):
                return 'BROKEN_OUT'
            # Ready‑to‑breakout (Volatility Contraction Pattern)
            if (
                row.get('proximity_to_high', 1) <= 0.03
                and row.get('price_range_5d', 1) <= 0.025
                and row.get('vol_multiplier', 1) <= 0.85
                and row['close'] > row.get('ema_50', 0) > row.get('ema_200', 0)
                and row.get('weekly_rsi_14', 0) >= 50
                and row.get('macd_hist', 0) > 0  # Standard MACD Positive Cross
            ):
                return 'READY_TO_BREAKOUT'
            return 'CONSOLIDATING'

        s_df['breakout_state'] = s_df.apply(_classify_breakout, axis=1)

        # Breakout Age calculation
        # Age resets to 0 on state change, increments on continuation, NULL when CONSOLIDATING
        prev_state = None
        prev_age = None
        for idx in s_df.index:
            curr_state = s_df.at[idx, 'breakout_state']
            
            if curr_state == 'CONSOLIDATING':
                s_df.at[idx, 'breakout_age'] = None
                prev_age = None
            elif curr_state == prev_state and prev_age is not None:
                s_df.at[idx, 'breakout_age'] = prev_age + 1
                prev_age = prev_age + 1
            else:
                s_df.at[idx, 'breakout_age'] = 0
                prev_age = 0
            prev_state = curr_state

        for _, row in s_df.tail(PERSIST_ROWS).iterrows():
            updates.append(
                {
                    "symbol": row["symbol"],
                    "date": row["date"],
                    "ema_10": row.get("ema_10"),
                    "ema_20": row.get("ema_20"),
                    "ema_50": row.get("ema_50"),
                    "ema_200": row.get("ema_200"),
                    "ema_100": row.get("ema_100"),
                    "ema_100_slope_5d": row.get("ema_100_slope_5d"),
                    "rsi_14": row.get("rsi_14") if row.get("rsi_14") is not None else 50,
                    "below_200ema": bool(row.get("below_200ema", False)),
                    "ema_200_slope_20": row.get("ema_200_slope_20"),
                    "rolling_high_6m": row.get("rolling_high_6m"),
                    "rolling_high_52w": row.get("rolling_high_52w"),
                    "weekly_trend_score": row.get("weekly_trend_score"),
                    "overhead_supply_score": row.get("overhead_supply_score"),
                    "avg_volume_20d": row.get("avg_volume_20d"),
                    "rs_90d": row.get("rs_90d"),
                    "rs_21d": row.get("rs_21d"),
                    "rs_63d": row.get("rs_63d"),
                    "rs_126d": row.get("rs_126d"),
                    "rs_252d": row.get("rs_252d"),
                    "high_10d": row.get("high_10d"),
                    "low_5d": row.get("low_5d"),
                    "atr_14": row.get("atr_14"),
                    "condition_breakout_10d": bool(row.get("condition_breakout_10d", False)),
                    "condition_price_quality": row.get("price_quality"),
                    "breakout_state": row.get("breakout_state", "CONSOLIDATING"),
                    "breakout_age": row.get("breakout_age")
                }
            )
            merged = pd.merge(
                s_df[["date", "close"]],
                idx_df[["date", "idx_close"]],
                on="date",
                how="inner",
            )
            if len(merged) > 90:
                merged["stock_ret"] = merged["close"] / merged["close"].shift(90)
                merged["idx_ret"] = merged["idx_close"] / merged["idx_close"].shift(90)
                merged["rs_90d"] = (merged["stock_ret"] / merged["idx_ret"]) * 100
                merge_cols = ["date", "rs_90d"]
                # Multi-timeframe RS (only compute when enough history exists)
                for window, col in [(21, "rs_21d"), (63, "rs_63d"), (126, "rs_126d"), (252, "rs_252d")]:
                    if len(merged) > window:
                        merged["stock_ret_w"] = merged["close"] / merged["close"].shift(window)
                        merged["idx_ret_w"] = merged["idx_close"] / merged["idx_close"].shift(window)
                        merged[col] = (merged["stock_ret_w"] / merged["idx_ret_w"]) * 100
                        merge_cols.append(col)
                s_df = pd.merge(
                    s_df.drop(columns=[c for c in merge_cols if c != "date"], errors='ignore'),
                    merged[merge_cols], on="date", how="left"
                )

        s_df = s_df.replace({np.nan: None})

        for _, row in s_df.tail(PERSIST_ROWS).iterrows():
            updates.append(
                {
                    "symbol": row["symbol"],
                    "date": row["date"],
                    "ema_10": row.get("ema_10"),
                    "ema_20": row.get("ema_20"),
                    "ema_50": row.get("ema_50"),
                    "ema_200": row.get("ema_200"),
                    "ema_100": row.get("ema_100"),
                    "ema_100_slope_5d": row.get("ema_100_slope_5d"),
                    "rsi_14": row.get("rsi_14") if row.get("rsi_14") is not None else 50,
                    "below_200ema": bool(row.get("below_200ema", False)),
                    "ema_200_slope_20": row.get("ema_200_slope_20"),
                    "rolling_high_6m": row.get("rolling_high_6m"),
                    "rolling_high_52w": row.get("rolling_high_52w"),
                    "weekly_trend_score": row.get("weekly_trend_score"),
                    "overhead_supply_score": row.get("overhead_supply_score"),
                    "avg_volume_20d": row.get("avg_volume_20d"),
                    "rs_90d": row.get("rs_90d"),
                    "rs_21d": row.get("rs_21d"),
                    "rs_63d": row.get("rs_63d"),
                    "rs_126d": row.get("rs_126d"),
                    "rs_252d": row.get("rs_252d"),
                    "high_10d": row.get("high_10d"),
                    "low_5d": row.get("low_5d"),
                    "atr_14": row.get("atr_14"),
                    "condition_breakout_10d": bool(row.get("condition_breakout_10d", False)),
                    "condition_price_quality": row.get("price_quality"),
                    "breakout_state": row.get("breakout_state", "CONSOLIDATING"),
                    "breakout_age": row.get("breakout_age")
                }
            )

    logger.info(
        "Prepared %d indicator updates across %d symbols (persisting last %d rows per symbol)",
        len(updates),
        df["symbol"].nunique(),
        PERSIST_ROWS,
    )
    return updates


def verify_updates_written(updates, sample_size=50):
    """Verify a sample of the updates actually made it into the database."""
    if not updates:
        raise IndicatorComputationError("No updates to verify")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sample_size = min(sample_size, len(updates))
            sample_indices = np.random.choice(len(updates), sample_size, replace=False)
            verified_count = 0

            for idx in sample_indices:
                update = updates[idx]
                cur.execute(
                    """
                    SELECT ema_50
                    FROM daily_prices
                    WHERE symbol = %s AND date = %s
                    """,
                    (update["symbol"], update["date"]),
                )
                result = cur.fetchone()
                if result and result["ema_50"] is not None:
                    verified_count += 1
                else:
                    logger.warning(
                        "Update not verified for %s on %s",
                        update["symbol"],
                        update["date"],
                    )

            verification_rate = (verified_count / sample_size) * 100
            logger.info(
                "Update verification rate: %d/%d (%.1f%%)",
                verified_count,
                sample_size,
                verification_rate,
            )

            if verification_rate < 90:
                raise IndicatorComputationError(
                    f"Low update verification rate: {verification_rate:.1f}%"
                )
    finally:
        conn.close()


def update_db_with_indicators(updates, max_retries=3):
    """Write computed indicators back to daily_prices with retry logic."""
    if not updates:
        raise IndicatorComputationError("No indicator updates produced")

    for attempt in range(1, max_retries + 1):
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                sql = """
                    UPDATE daily_prices
                    SET ema_10 = %(ema_10)s,
                        ema_20 = %(ema_20)s,
                        ema_50 = %(ema_50)s,
                        ema_200 = %(ema_200)s,
                        ema_100 = %(ema_100)s,
                        ema_100_slope_5d = %(ema_100_slope_5d)s,
                        rsi_14 = %(rsi_14)s,
                        below_200ema = %(below_200ema)s,
                        ema_200_slope_20 = %(ema_200_slope_20)s,
                        rolling_high_6m = %(rolling_high_6m)s,
                        rolling_high_52w = %(rolling_high_52w)s,
                        weekly_trend_score = %(weekly_trend_score)s,
                        overhead_supply_score = %(overhead_supply_score)s,
                        avg_volume_20d = %(avg_volume_20d)s,
                        rs_90d = %(rs_90d)s,
                        rs_21d = %(rs_21d)s,
                        rs_63d = %(rs_63d)s,
                        rs_126d = %(rs_126d)s,
                        rs_252d = %(rs_252d)s,
                        high_10d = %(high_10d)s,
                        low_5d = %(low_5d)s,
                        atr_14 = %(atr_14)s,
                        condition_breakout_10d = %(condition_breakout_10d)s,
                        condition_price_quality = %(condition_price_quality)s,
                        breakout_state = %(breakout_state)s,
                        breakout_age = %(breakout_age)s
                    WHERE symbol = %(symbol)s AND date = %(date)s
                """
                execute_batch(cur, sql, updates, page_size=2000)
            conn.commit()
            logger.info("Wrote %d indicator updates to DB (Attempt %d)", len(updates), attempt)
            verify_updates_written(updates)
            return  # Success
        except Exception as exc:
            if conn:
                conn.rollback()
            logger.warning("Attempt %d failed to update indicators: %s", attempt, exc)
            if attempt == max_retries:
                raise IndicatorComputationError(f"Failed to update indicators after {max_retries} attempts: {exc}") from exc
            import time
            time.sleep(2 * attempt)  # Exponential backoff
        finally:
            if conn:
                conn.close()


def validate_indicators_after_update():
    """Fail loudly if EMA-50 coverage is still above the threshold."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(DISTINCT symbol) AS total_symbols,
                    COUNT(DISTINCT CASE WHEN ema_50 IS NULL THEN symbol END) AS null_ema_count
                FROM daily_prices
                WHERE date = (SELECT MAX(date) FROM daily_prices)
                """
            )
            result = cur.fetchone()
            total_symbols = result["total_symbols"] or 0
            null_ema_count = result["null_ema_count"] or 0

            if total_symbols == 0:
                raise IndicatorComputationError("No data found for latest date")

            null_rate = (null_ema_count / total_symbols) * 100
            logger.info(
                "Post-update validation: %d/%d NULL EMA-50 (%.1f%%)",
                null_ema_count,
                total_symbols,
                null_rate,
            )

            if null_rate > 20:
                error_msg = f"CRITICAL: {null_rate:.1f}% symbols still have NULL EMA-50"
                send_alert_email(
                    "Indicator Validation Failure",
                    f"<p>{error_msg}</p><p>Total symbols: {total_symbols}<br>NULL EMA-50: {null_ema_count}</p>"
                )
                raise IndicatorComputationError(error_msg)

            cur.execute(
                """
                SELECT COUNT(*) AS zero_ema_count
                FROM daily_prices
                WHERE date = (SELECT MAX(date) FROM daily_prices)
                  AND ema_50 = 0
                """
            )
            zero_ema_count = cur.fetchone()["zero_ema_count"] or 0
            if zero_ema_count > total_symbols * 0.5:
                raise IndicatorComputationError(
                    f"Suspicious: {zero_ema_count}/{total_symbols} symbols have EMA-50 = 0"
                )

            logger.info("Indicator validation passed: NULL rate %.1f%%", null_rate)
            return null_rate
    finally:
        conn.close()


def compute_indicators_for_symbols(symbols: list):
    """Public helper for on-demand scoring of specific symbols."""
    if not symbols:
        return
    add_indicator_columns_if_missing()
    data_df, idx_df = fetch_data(symbols)
    updates = compute_indicators(data_df, idx_df)
    update_db_with_indicators(updates)
    validate_indicators_after_update()


def compute_indicators_all(symbol_batch_size=25, max_batches=None):
    """Recompute indicators for every symbol that still needs them."""
    logger.info("Starting validated indicator recomputation")
    try:
        add_indicator_columns_if_missing()
        symbols = fetch_symbols_needing_repair()

        if not symbols:
            logger.info("All symbols already have indicators computed")
            validate_indicators_after_update()
            return

        logger.info("Found %d symbols with NULL indicators", len(symbols))

        total_updates = 0
        for batch_num, symbol_batch in enumerate(chunked(symbols, symbol_batch_size), start=1):
            logger.info(
                "Processing indicator batch %d (%d symbols)",
                batch_num,
                len(symbol_batch),
            )

            data_df, idx_df = fetch_data(symbol_batch)
            updates = compute_indicators(data_df, idx_df)
            if not updates:
                logger.warning(
                    "Batch %d produced no updates for %d symbols",
                    batch_num,
                    len(symbol_batch),
                )
                continue

            update_db_with_indicators(updates)
            total_updates += len(updates)
            logger.info(
                "Completed batch %d: %d updates written; running total %d",
                batch_num,
                len(updates),
                total_updates,
            )

            if max_batches is not None and batch_num >= max_batches:
                logger.info(
                    "Reached configured batch limit of %d; pausing recompute for this run",
                    max_batches,
                )
                break

        if total_updates == 0:
            raise IndicatorComputationError("Indicator computation produced zero updates")

        null_rate = validate_indicators_after_update()
        logger.info(
            "Indicator fix complete; NULL EMA-50 rate: %.1f%%; total updates written: %d",
            null_rate,
            total_updates,
        )
    except IndicatorComputationError:
        logger.exception("Indicator computation failed validation")
        raise
    except Exception as exc:
        logger.exception("Unexpected indicator engine error")
        raise IndicatorComputationError(f"Unexpected error: {exc}") from exc


if __name__ == "__main__":
    import os

    batch_limit_raw = os.environ.get("MRI_INDICATOR_MAX_BATCHES")
    batch_limit = int(batch_limit_raw) if batch_limit_raw else None
    compute_indicators_all(max_batches=batch_limit)
