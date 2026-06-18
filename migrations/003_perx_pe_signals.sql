-- Database migration for PE Expansion Scoring
-- Adds perx_pe_scores (per-symbol aggregate) and perx_pe_signals (per-row provenance)
-- Companion to engine_perx/pe_signals.py
--
-- Design:
--   perx_pe_signals — granular row per (symbol, source, category_code).
--                     Multiple rows per symbol, one per contributing category
--                     from each scoring source (primary=promises, secondary=transcripts).
--   perx_pe_scores  — denormalized aggregate per symbol. Updated by ON CONFLICT.
--
-- Both tables are idempotent. Re-running pe_signals.py only refreshes these.

CREATE TABLE IF NOT EXISTS perx_pe_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL,
    source VARCHAR(10) NOT NULL,            -- 'primary' (narrative_timeline) | 'secondary' (transcript keyword scan)
    category_code VARCHAR(40) NOT NULL,
    weight INTEGER NOT NULL,
    signal_strength INTEGER NOT NULL,       -- 0-5 per PRD ladder
    mentions INTEGER DEFAULT 0,
    n_promises INTEGER DEFAULT 0,
    weighted_status_score NUMERIC(8,2) DEFAULT 0,
    has_execution_language BOOLEAN DEFAULT FALSE,
    evidence_quotes JSONB DEFAULT '[]'::jsonb,
    guidance_types JSONB DEFAULT '{}'::jsonb,
    n_transcripts_with_hits INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (symbol, source, category_code)
);

CREATE INDEX IF NOT EXISTS idx_perx_pe_signals_symbol
    ON perx_pe_signals(symbol);
CREATE INDEX IF NOT EXISTS idx_perx_pe_signals_source
    ON perx_pe_signals(source);
CREATE INDEX IF NOT EXISTS idx_perx_pe_signals_category
    ON perx_pe_signals(category_code);
CREATE INDEX IF NOT EXISTS idx_perx_pe_signals_strength
    ON perx_pe_signals(signal_strength DESC);


CREATE TABLE IF NOT EXISTS perx_pe_scores (
    symbol VARCHAR(20) PRIMARY KEY,
    pe_score NUMERIC(5,1) NOT NULL,
    n_promises_total INTEGER DEFAULT 0,
    n_quote_verified INTEGER DEFAULT 0,
    n_transcripts INTEGER DEFAULT 0,
    n_quarter_span INTEGER DEFAULT 0,
    top_drivers JSONB DEFAULT '[]'::jsonb,
    category_breakdown JSONB DEFAULT '{}'::jsonb,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_perx_pe_scores_score
    ON perx_pe_scores(pe_score DESC);
CREATE INDEX IF NOT EXISTS idx_perx_pe_scores_generated
    ON perx_pe_scores(generated_at DESC);
