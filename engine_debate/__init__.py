"""
engine_debate — Bear vs Bull debate engine (FeatureRequest 2026-06-19).

Generates contrasting bear/bull cases grounded in the deterministic
context payload that already powers GuidanceCheck, Expansion Lens,
and AAE V3. Optional third-turn adjudicator.

Public surface:
    run_debate(symbol, context_kind, context_payload) -> DebateResult
    build_guidance_context(symbol)                     -> dict
    build_pe_expansion_context(symbol)                 -> dict   # Phase 3

Cache: results are persisted in conviction_debates keyed by
(symbol, context_kind, sha256(canonical_payload)). Re-opening a
report whose underlying data hasn't changed is instant + free.
"""
from engine_debate.debate_engine import run_debate, DebateResult  # noqa: F401
