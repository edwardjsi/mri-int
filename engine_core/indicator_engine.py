import logging

import numpy as np
import pandas as pd
from psycopg2.extras import execute_batch

from engine_core.db import get_connection
from engine_core.email_service import send_alert_email

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IndicatorComputationError(Exception):
    """Raised when indicator computation or validation fails."""


INDICATOR_COLUMNS = (
    ("ema_20", "NUMERIC"),
    ("ema_50", "NUMERIC"),
    ("ema_200", "NUMERIC"),
    ("rsi_14", "NUMERIC"),
    ("below_200ema", "BOOLEAN"),
    ("ema_200_slope_20", "NUMERIC"),
    ("rolling_high_6m", "NUMERIC"),
    ("avg_volume_20d", "NUMERIC"),
    ("rs_90d", "NUMERIC"),
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


def fetch_all_symbols_with_null_indicators():
    """Return every symbol that still has any NULL core indicator."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT symbol
                FROM daily_prices
                WHERE ema_50 IS NULL
                   OR ema_200 IS NULL
                   OR rs_90d IS NULL
                   OR avg_volume_20d IS NULL
                   OR rolling_high_6m IS NULL
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
            symbols = fetch_all_symbols_with_null_indicators()

        if not symbols:
            logger.info("All symbols already have indicators computed.")
            return pd.DataFrame(), pd.DataFrame()

        logger.info("Computing indicators for %d symbols with missing data", len(symbols))

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT symbol, date, high, close, volume, ema_20, ema_50, ema_200
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

        for column in ("ema_20", "ema_50", "ema_200"):
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
        s_df = df[df["symbol"] == symbol].copy().sort_values("date")
        if len(s_df) < 20:
            logger.warning("Symbol %s has insufficient data: %d rows", symbol, len(s_df))
            continue

        s_df["ema_20"] = s_df["close"].ewm(span=20, adjust=False).mean()
        s_df["ema_50"] = s_df["close"].ewm(span=50, adjust=False).mean()
        s_df["ema_200"] = (
            s_df["close"].ewm(span=200, adjust=False).mean()
            if len(s_df) >= 200
            else s_df["ema_50"]
        )

        s_df["ema_200_slope_20"] = s_df["ema_200"].diff(20)

        delta = s_df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        s_df["rsi_14"] = 100 - (100 / (1 + rs))

        s_df["below_200ema"] = s_df["close"] < s_df["ema_200"]
        s_df["rolling_high_6m"] = s_df["close"].rolling(window=126, min_periods=20).max()
        s_df["avg_volume_20d"] = s_df["volume"].rolling(window=20).mean()

        if not idx_df.empty:
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
                s_df = pd.merge(s_df, merged[["date", "rs_90d"]], on="date", how="left")

        s_df = s_df.replace({np.nan: None})

        for _, row in s_df.tail(PERSIST_ROWS).iterrows():
            updates.append(
                {
                    "symbol": row["symbol"],
                    "date": row["date"],
                    "ema_20": row.get("ema_20"),
                    "ema_50": row.get("ema_50"),
                    "ema_200": row.get("ema_200"),
                    "rsi_14": row.get("rsi_14") if row.get("rsi_14") is not None else 50,
                    "below_200ema": bool(row.get("below_200ema", False)),
                    "ema_200_slope_20": row.get("ema_200_slope_20"),
                    "rolling_high_6m": row.get("rolling_high_6m"),
                    "avg_volume_20d": row.get("avg_volume_20d"),
                    "rs_90d": row.get("rs_90d"),
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


def update_db_with_indicators(updates):
    """Write computed indicators back to daily_prices."""
    if not updates:
        raise IndicatorComputationError("No indicator updates produced")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                UPDATE daily_prices
                SET ema_20 = %(ema_20)s,
                    ema_50 = %(ema_50)s,
                    ema_200 = %(ema_200)s,
                    rsi_14 = %(rsi_14)s,
                    below_200ema = %(below_200ema)s,
                    ema_200_slope_20 = %(ema_200_slope_20)s,
                    rolling_high_6m = %(rolling_high_6m)s,
                    avg_volume_20d = %(avg_volume_20d)s,
                    rs_90d = %(rs_90d)s
                WHERE symbol = %(symbol)s AND date = %(date)s
            """
            execute_batch(cur, sql, updates, page_size=2000)
        conn.commit()
        logger.info("Wrote %d indicator updates to DB", len(updates))
        verify_updates_written(updates)
    except Exception as exc:
        conn.rollback()
        raise IndicatorComputationError(f"Failed to update indicators: {exc}") from exc
    finally:
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
        symbols = fetch_all_symbols_with_null_indicators()

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
