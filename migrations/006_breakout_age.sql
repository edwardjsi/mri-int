-- migrations/006_breakout_age.sql
-- Add breakout_age to track consecutive days in breakout_state
-- Decision 099

ALTER TABLE daily_prices
  ADD COLUMN IF NOT EXISTS breakout_age INTEGER DEFAULT NULL;

-- Index for radar query performance
CREATE INDEX IF NOT EXISTS idx_daily_prices_breakout_age
  ON daily_prices (date, breakout_state, breakout_age)
  WHERE breakout_state IN ('BROKEN_OUT', 'READY_TO_BREAKOUT');
