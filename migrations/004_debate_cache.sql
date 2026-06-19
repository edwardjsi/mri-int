-- Migration 004 — conviction_debates cache table
-- Stores bear/bull debate outputs keyed by (symbol, context_kind, context_hash)
-- so re-opening the same report is free. Hash is sha256 of the canonical
-- context payload; cache miss = context changed since last debate.
--
-- Idempotent — safe to re-run. Decision 027 RDS-protection rules apply
-- (no destructive changes; ADD-only columns; CREATE TABLE IF NOT EXISTS).
--
-- Companion: engine_debate/ — debate_engine.py, cache.py, prompts_*.py
-- API surface: POST /api/guidance/{symbol}/debate
--              POST /api/pe-expansion/{symbol}/debate  (Phase 3)
-- FeatureRequest: docs/FEATURE_REQUEST_BEAR_BULL_DEBATE_2026-06-19.md

CREATE TABLE IF NOT EXISTS conviction_debates (
    id               BIGSERIAL PRIMARY KEY,
    symbol           VARCHAR(20) NOT NULL,
    context_kind     VARCHAR(20) NOT NULL,                 -- 'guidance' | 'pe_expansion'
    context_hash     VARCHAR(64) NOT NULL,                 -- sha256 hex digest of canonical payload
    context_payload  JSONB NOT NULL,                       -- full snapshot for audit + reproducibility
    bear_text        TEXT NOT NULL,
    bull_text        TEXT NOT NULL,
    adjudicator      TEXT,                                  -- nullable; null when user opted out
    model_used       VARCHAR(40),                           -- 'gpt-4o-mini' | 'deepseek-chat'
    generated_at     TIMESTAMPTZ DEFAULT NOW(),
    cache_hits       INT DEFAULT 0,                         -- increments on every cache hit (telemetry)
    UNIQUE (symbol, context_kind, context_hash)
);

CREATE INDEX IF NOT EXISTS idx_conviction_debates_lookup
    ON conviction_debates (symbol, context_kind, context_hash);

CREATE INDEX IF NOT EXISTS idx_conviction_debates_generated
    ON conviction_debates (generated_at DESC);
