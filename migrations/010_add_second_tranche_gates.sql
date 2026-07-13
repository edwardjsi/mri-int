-- migrations/010_add_second_tranche_gates.sql
-- Decision 103 — V2 Pyramiding Discipline Gates: G3 (weekly breakout) + G4
-- (volume-confirmed breakout) columns on daily_prices.
--
-- Why this exists:
-- The legacy ADD_SECOND_TRANCHE check was CAS-only (decision_score >= 85 +
-- 4-star confidence). Decision 103 introduces a 5-gate model that requires
-- the daily_prices row to carry two more pieces of evidence:
--
--   G3 — weekly close above resistance:
--       * prior_52w_high                          — max of last 52w highs,
--                                                   excluding current week
--       * all_time_high_before_current_week       — fallback for thin-history
--                                                   names (<52 weeks of data)
--       * resistance_source                       — enum-as-TEXT
--                                                   ('PRIOR_52W_HIGH' |
--                                                    'ALL_TIME_HIGH' | NULL);
--                                                   C9 keeps this as an enum,
--                                                   not free text
--       * weekly_close_above_resistance           — boolean per row, fwd-filled
--                                                   from the most recent
--                                                   weekly close (Fri on
--                                                   W-FRI resample)
--
--   G4 — breakout-day volume >= 1.3 × 20-day average:
--       * breakout_day_volume                     — close-day volume when
--                                                   breakout_state first
--                                                   became 'BROKEN_OUT'
--       * breakout_day_avg20_volume               — 20-day average volume
--                                                   ending that day
--       * breakout_day_volume_ratio               — computed ratio, frozen
--                                                   (NOT recomputed later)
--       * volume_threshold_used                   — ratio threshold applied
--                                                   (e.g., 1.3); persisted
--                                                   so we can audit historical
--                                                   rows under future
--                                                   calibration changes
--       * breakout_date_for_volume                — date when breakout_state
--                                                   first became BROKEN_OUT
--       * volume_confirmed_breakout               — boolean =
--                                                   (ratio >= threshold_used)
--
-- C2 (volume metadata versioned): all six G4 columns are persisted, not just
-- the boolean. Without volume_threshold_used + breakout_date_for_volume, we
-- cannot reproduce historical gate decisions when the threshold changes.
--
-- C9 (resistance source as enum): the `resistance_source` column stores the
-- enum *string* literally. Application code must validate against
-- `ResistanceSource` (defined in engine_core/cas_indicators.py alongside the
-- indicator functions). A CHECK constraint enforces valid values at the DB
-- level as defense in depth.
--
-- All ten columns are idempotent — safe to re-run against any DB state.
-- Rows stay NULL until the indicator pipeline (engine_core/indicator_engine.py
-- additions in Session N+4) runs.
--
-- Run manually:
--   psql "$DATABASE_URL" -f migrations/010_add_second_tranche_gates.sql
--
-- Defense in depth: api/schema.py auto-heal block will also execute these
-- ALTER statements on every API startup (mirrors Decision 099/100 pattern).

ALTER TABLE daily_prices
  -- ── G3: weekly breakout above resistance ──────────────────────────────
  ADD COLUMN IF NOT EXISTS prior_52w_high                     NUMERIC DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS all_time_high_before_current_week  NUMERIC DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS resistance_source                  TEXT    DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS weekly_close_above_resistance      BOOLEAN DEFAULT NULL,
  -- ── G4: breakout-day volume confirmation ──────────────────────────────
  ADD COLUMN IF NOT EXISTS breakout_day_volume                NUMERIC DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS breakout_day_avg20_volume          NUMERIC DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS breakout_day_volume_ratio          NUMERIC DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS volume_threshold_used              NUMERIC DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS breakout_date_for_volume           DATE    DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS volume_confirmed_breakout          BOOLEAN DEFAULT NULL;

-- Defense in depth: enforce resistance_source enum at the DB level.
-- Mirrors the application-layer `ResistanceSource` enum defined in
-- engine_core/cas_indicators.py. NULL is allowed (row not yet computed).
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'chk_daily_prices_resistance_source'
  ) THEN
    ALTER TABLE daily_prices
      ADD CONSTRAINT chk_daily_prices_resistance_source
      CHECK (
        resistance_source IS NULL
        OR resistance_source IN ('PRIOR_52W_HIGH', 'ALL_TIME_HIGH')
      );
  END IF;
END
$$;

-- Indexes for radar query performance.
-- Partial index on non-NULL rows only — most historical rows have NULL until
-- Session N+4 backfills. This mirrors the Decision 099/100 pattern.

-- Supports ADD-eligibility filtering on G3 (weekly close above resistance).
CREATE INDEX IF NOT EXISTS idx_daily_prices_weekly_close_above_resistance
  ON daily_prices (date, weekly_close_above_resistance)
  WHERE weekly_close_above_resistance IS NOT NULL;

-- Supports ADD-eligibility filtering on G4 (volume-confirmed breakout).
CREATE INDEX IF NOT EXISTS idx_daily_prices_volume_confirmed_breakout
  ON daily_prices (date, breakout_state, volume_confirmed_breakout)
  WHERE breakout_state = 'BROKEN_OUT';
