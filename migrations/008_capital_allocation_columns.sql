-- migrations/008_capital_allocation_columns.sql
-- Decision 100 — Capital Allocation Score V1.0: 4 new columns on daily_prices.
--
-- Why this exists:
-- The Capital Allocation Score (CAS) introduced in Decision 100 / rev 2 needs
-- four input columns that aren't yet on daily_prices:
--
--   * ema_100              — for the `ema100_rising` eligibility condition
--                            (slope(EMA100, 5d) > 0)
--   * rolling_high_52w     — for the 52w-position eligibility gate (within 10%
--                            of 52w high) and the Weekly Structure sub-score
--                            "within 5% of 52w high" component (+15)
--   * weekly_trend_score   — for the Weekly Structure sub-score (multi-component
--                            HH + HL + above weekly EMAs + near 52w high, max 100)
--                            AND the Market Sub-Gate "Trend" PASS/FAIL (>= 50)
--   * overhead_supply_score — for the new 14%-weighted Overhead Supply factor
--                            (0 = clear air, 100 = massive overhead resistance;
--                            counts distinct swing highs in last 6m above close)
--
-- All four are computed by engine_core/indicator_engine.py in Session N+2.
-- This migration only creates the columns; rows stay NULL until N+2 wires the
-- computation. Migration is idempotent — safe to re-run against any DB state.
--
-- Run manually:
--   psql "$DATABASE_URL" -f migrations/008_capital_allocation_columns.sql
--
-- Defense in depth: api/schema.py auto-heal block will also execute these
-- ALTER statements on every API startup (added in Session N+2 alongside the
-- indicator_engine.py wiring).

ALTER TABLE daily_prices
  ADD COLUMN IF NOT EXISTS ema_100               NUMERIC DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS rolling_high_52w      NUMERIC DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS weekly_trend_score    NUMERIC DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS overhead_supply_score NUMERIC DEFAULT NULL;

-- Indexes for radar query performance (CAS V1.0 banner + /top-by-cas endpoint).
-- weekly_trend_score: supports Trend sub-gate filtering + ORDER BY in radar.
-- overhead_supply_score: supports "clear air" filtering + ORDER BY.
-- Partial index on non-NULL rows only — most historical rows have NULL until
-- Session N+2 backfills.
CREATE INDEX IF NOT EXISTS idx_daily_prices_weekly_trend_score
  ON daily_prices (date, weekly_trend_score)
  WHERE weekly_trend_score IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_daily_prices_overhead_supply_score
  ON daily_prices (date, overhead_supply_score)
  WHERE overhead_supply_score IS NOT NULL;

-- Composite index for the future /top-by-cas query: combine breakout_state +
-- breakout_age (existing) + weekly_trend_score (new) for the eligibility +
-- sub-gate filtering in one pass. (Schema-only — query plan improves once
-- Session N+3 endpoint exists.)
CREATE INDEX IF NOT EXISTS idx_daily_prices_cas_eligible
  ON daily_prices (date, breakout_state, breakout_age, weekly_trend_score)
  WHERE breakout_state = 'BROKEN_OUT';
