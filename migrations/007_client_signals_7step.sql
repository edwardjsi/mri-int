-- migrations/007_client_signals_7step.sql
-- Add the 5 missing 7-step forensic condition columns to client_signals.
--
-- Why this exists:
-- The CREATE TABLE statement in api/schema.py (and the legacy migrations/001_client_tables.sh)
-- defined 7 forensic columns, but only the 2 newest (condition_breakout_10d,
-- condition_price_quality) were added to the api/schema.py auto-heal block.
-- Existing production client_signals tables (created via the legacy RDS migration or via
-- an older api/schema.py that lacked these columns) therefore had zero or only the 2 newest
-- condition columns, causing:
--   psycopg2.errors.UndefinedColumn: column "condition_ema_50_200" of relation
--   "client_signals" does not exist
-- from engine_core/signal_generator.py at the daily INSERT (2026-07-06).
--
-- This migration is the explicit, runnable form of the auto-heal that api/schema.py now
-- performs idempotently on every API startup. Run manually if you want to heal the DB
-- without restarting the API:
--   psql "$DATABASE_URL" -f migrations/007_client_signals_7step.sql

ALTER TABLE client_signals
  ADD COLUMN IF NOT EXISTS condition_ema_50_200     BOOLEAN,
  ADD COLUMN IF NOT EXISTS condition_ema_200_slope  BOOLEAN,
  ADD COLUMN IF NOT EXISTS condition_rs             BOOLEAN,
  ADD COLUMN IF NOT EXISTS condition_6m_high        BOOLEAN,
  ADD COLUMN IF NOT EXISTS condition_volume         BOOLEAN;

-- Note: condition_breakout_10d and condition_price_quality were already added by the
-- existing api/schema.py auto-heal block prior to this migration. Including them here
-- would be redundant but harmless — left out for diff clarity.
