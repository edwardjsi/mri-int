-- Migration 005 — QIF agent_details JSONB column
-- Adds per-year detail dict to quality_verdicts so the bear/bull debate
-- can argue from full trajectory instead of summary score + flags.
--
-- Phase D1 of docs/INITIATIVE_DATA_RICHNESS_2026-06-19.md.
-- Decision 027 RDS-protection rules apply — additive only, idempotent.
--
-- Companion: engine_fundamental/agents.py (extended to return per-year detail)
--             engine_fundamental/pipeline.py (persists the JSONB)
-- JSONB shape:
--   {
--     "by_year": [
--       {"year": 2026, "revenue": ..., "ebitda": ..., "scores": {...},
--        "detail": {"revenue": {...}, "margin": {...}, ...}},
--       ...
--     ],
--     "trajectory": {
--       "score_trend": "improving|stable|declining",
--       "score_change_yoy": 1.5,
--       "roce_change_yoy_bps": -180,
--       "margin_compression_bps_yoy": -340,
--       "revenue_cagr_3y_pct": 12.3,
--       "years_observed": 4
--     }
--   }

ALTER TABLE public.quality_verdicts
    ADD COLUMN IF NOT EXISTS agent_details JSONB DEFAULT '{}'::jsonb;

-- GIN index for ad-hoc JSONB queries (e.g. finding stocks where trajectory.score_trend='declining')
CREATE INDEX IF NOT EXISTS idx_quality_verdicts_agent_details_gin
    ON public.quality_verdicts USING GIN (agent_details);
