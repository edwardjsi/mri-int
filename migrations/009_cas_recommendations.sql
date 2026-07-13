-- migrations/009_cas_recommendations.sql
-- Decision 101 — CAS V1.1: Outcome Tracking
--
-- Why this exists:
-- V1.0 (Decision 100) computes CAS but doesn't persist it anywhere. That means
-- we have no way to:
--   * audit "why did we recommend this 3 weeks ago?"
--   * measure outcomes ("did the recommendation work?")
--   * validate assumptions through historical outcomes
--   * detect recommendation drift ("are we changing our minds daily?")
--
-- Two tables per expert architectural review (Decision 101):
--
--   1. cas_recommendations       — IMMUTABLE, written once at Event A
--      (immediate on API CAS computation). One row per (symbol, date).
--      Stores the recommendation AS IT WAS MADE: full factor_snapshot JSONB
--      (not just CAS=91), plus engine_signature for provenance. Three years
--      from now, asking "why did CAS 1.1 recommend X?" is answerable.
--
--   2. cas_recommendation_outcomes — MUTABLE, updated daily at Event B
--      (separate cron worker, after market close). Fills milestone prices
--      based on ELAPSED trading days since recommendation, NOT calendar
--      weeks — catches Friday→Monday gap events that weekly sampling misses.
--
-- Milestones: 7d / 14d / 28d / 63d / 126d (matches expert's
-- "path tracking" requirement: every eligible stock should have its
-- progress tracked at multiple time points, not just terminal return).
--
-- Recommendation ID format: CAS-YYYY-MM-DD-SYMBOL (deterministic, human-
-- readable, sortable, matches Decision 101's recommendation_id format).
-- UUID would also work but isn't necessary — date+symbol is unique.
--
-- Run manually:
--   venv/bin/python -c "from engine_core.db import get_connection; \
--     c=get_connection(); cur=c.cursor(); cur.execute(open( \
--     'migrations/009_cas_recommendations.sql').read()); c.commit()"
--
-- Migration is idempotent — safe to re-run against any DB state.

-- ============================================================
-- Table 1: cas_recommendations (immutable)
-- ============================================================
CREATE TABLE IF NOT EXISTS cas_recommendations (
    id                    BIGSERIAL PRIMARY KEY,

    -- Public ID — deterministic from (date, symbol). Easy to cite in
    -- dashboards, log lines, and support tickets.
    recommendation_id     TEXT        UNIQUE NOT NULL,

    recommendation_date   DATE        NOT NULL,
    symbol                TEXT        NOT NULL,
    regime                TEXT        NOT NULL,

    -- Scoring output
    market_score          NUMERIC     NOT NULL,
    cas                   NUMERIC     NOT NULL,
    confidence_stars      INTEGER     NOT NULL,

    -- Action verb (Layer 3 vocabulary per Decision 101):
    --   BUY  = first tranche, fresh position
    --   ADD  = adding to existing position (was 'ADD SECOND TRANCHE')
    --   WATCH = eligible but no action yet
    -- NO_ACTION is NOT persisted — every recommendation has an action.
    action                TEXT        NOT NULL,

    -- Price + factor provenance. factor_snapshot is JSONB so we can
    -- add/remove sub-scores without DDL changes.
    price_at_recommendation NUMERIC   NOT NULL,
    factor_snapshot        JSONB      NOT NULL,

    -- Engine signature (Decision 101 expert rec): composite
    -- CAS_VERSION + CONFIG_HASH + COMMIT_SHA. Without this, three years
    -- from now we can't answer "why did CAS 1.1 outperform CAS 1.3?"
    cas_version           TEXT        NOT NULL,
    config_hash           TEXT        NOT NULL,
    commit_sha            TEXT        NOT NULL,
    engine_signature      TEXT        NOT NULL,

    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One recommendation per (symbol, date). If the API recomputes CAS
    -- for the same symbol on the same day, we UPSERT the latest. Keeps
    -- the table small and matches "final recommendation of the day".
    CONSTRAINT cas_recommendations_unique UNIQUE (symbol, recommendation_date)
);

CREATE INDEX IF NOT EXISTS idx_cas_recommendations_date
    ON cas_recommendations (recommendation_date DESC);

CREATE INDEX IF NOT EXISTS idx_cas_recommendations_symbol_date
    ON cas_recommendations (symbol, recommendation_date DESC);

-- GIN index on factor_snapshot for fast ad-hoc queries
-- ("show me all recommendations where breakout_state was BROKEN_OUT
-- and regime was BEAR_TRANSITION").
CREATE INDEX IF NOT EXISTS idx_cas_recommendations_factor_snapshot_gin
    ON cas_recommendations USING GIN (factor_snapshot);

-- ============================================================
-- Table 2: cas_recommendation_outcomes (mutable, daily updates)
-- ============================================================
-- One row per recommendation. The daily EOD outcome worker (Event B)
-- updates price_w1 when 7 trading days have elapsed, price_w2 at 14,
-- etc. milestones_reached[] tracks which milestones are filled.
--
-- Path tracking per Decision 101: every recommendation gets full
-- week 1 / week 2 / week 4 / month 3 / month 6 progression recorded.
-- If a stock is held longer (year 1+), V1.2+ can extend the schema.
CREATE TABLE IF NOT EXISTS cas_recommendation_outcomes (
    id                          BIGSERIAL PRIMARY KEY,

    recommendation_id           TEXT UNIQUE NOT NULL
        REFERENCES cas_recommendations(recommendation_id)
        ON DELETE CASCADE,

    -- Latest price as of the most recent EOD update
    current_price               NUMERIC,
    current_price_date          DATE,

    -- Milestone prices (filled at 7/14/28/63/126 trading days elapsed)
    price_w1                    NUMERIC,  -- 7d
    price_w2                    NUMERIC,  -- 14d
    price_w4                    NUMERIC,  -- 28d
    price_m3                    NUMERIC,  -- 63d
    price_m6                    NUMERIC,  -- 126d

    -- Milestone return percentages (relative to price_at_recommendation)
    return_pct_w1               NUMERIC,
    return_pct_w2               NUMERIC,
    return_pct_w4               NUMERIC,
    return_pct_m3               NUMERIC,
    return_pct_m6               NUMERIC,

    -- Max favorable / adverse excursion since recommendation
    -- (running high/low). Captures the "drawup" / "drawdown" path,
    -- not just terminal return — supports path-tracking analysis.
    max_favorable_excursion_pct NUMERIC,
    max_adverse_excursion_pct   NUMERIC,

    -- Which milestones are filled. e.g., {'w1','w2','w4'}
    -- Used for filtering in V1.2+ dashboards / calibration analysis.
    milestones_reached          TEXT[]    NOT NULL DEFAULT '{}',

    -- open / closed-w4 / closed-m6. "open" = still tracking,
    -- "closed-*" = all milestones filled up to that horizon.
    status                      TEXT      NOT NULL DEFAULT 'open',

    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cas_recommendation_outcomes_status
    ON cas_recommendation_outcomes (status);

CREATE INDEX IF NOT EXISTS idx_cas_recommendation_outcomes_updated
    ON cas_recommendation_outcomes (updated_at DESC);

-- Note: a JOIN view can be created in V1.2+ for calibration analysis:
--   CREATE OR REPLACE VIEW v_cas_outcomes AS
--   SELECT r.*, o.*
--   FROM cas_recommendations r
--   JOIN cas_recommendation_outcomes o USING (recommendation_id);
-- (out of scope for V1.1b — collect data first, build views later.)
