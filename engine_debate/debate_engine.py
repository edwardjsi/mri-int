"""
engine_debate.debate_engine — main entry point for bear/bull debates.

Phase 1 skeleton: lookup → LLM → store. Falls back to a stub bear/bull when
no LLM is configured (so the API stays callable in test environments).

Phase 2 wires real prompts via engine_debate.prompts_guidance.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

from engine_core.llm_client import get_llm_client

from engine_debate.cache import canonical_hash, lookup_debate, store_debate

logger = logging.getLogger("engine_debate.engine")


@dataclass
class DebateResult:
    bear: str
    bull: str
    adjudicator: Optional[str]
    model_used: Optional[str]
    generated_at: str
    cache_hits: int
    cached: bool
    context_hash: str

    def to_dict(self) -> dict:
        return {
            "bear": self.bear,
            "bull": self.bull,
            "adjudicator": self.adjudicator,
            "model_used": self.model_used,
            "generated_at": self.generated_at,
            "cache_hits": self.cache_hits,
            "cached": self.cached,
            "context_hash": self.context_hash,
        }


def _stub_bear(context_payload: dict) -> str:
    sym = context_payload.get("symbol", "UNKNOWN")
    return (
        f"[STUB — no LLM configured] Bear case for {sym}: based on the context, "
        f"the bear argues that management credibility concerns, recent misses, "
        f"or sector headwinds create downside risk. Replace with real LLM call "
        f"by setting DEEPSEEK_API_KEY or OPENAI_API_KEY."
    )


def _stub_bull(context_payload: dict) -> str:
    sym = context_payload.get("symbol", "UNKNOWN")
    return (
        f"[STUB — no LLM configured] Bull case for {sym}: based on the context, "
        f"the bull argues that the on-track promises, improving trend, and "
        f"category strength support a constructive thesis. Replace with real "
        f"LLM call by setting DEEPSEEK_API_KEY or OPENAI_API_KEY."
    )


def _call_llm(system: str, user: str, model: str) -> str:
    """Single chat.completions call. Plain text response (no JSON mode)."""
    client, resolved_model = get_llm_client()
    if not client:
        raise RuntimeError("No LLM client available")
    resp = client.chat.completions.create(
        model=resolved_model or model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,  # some variation so bear != bull mechanically
    )
    return resp.choices[0].message.content or ""


def run_debate(
    symbol: str,
    context_kind: str,
    context_payload: dict,
    include_adjudicator: bool = False,
) -> DebateResult:
    """Bear vs Bull debate. Looks up cache first; fires LLM on miss.

    Args:
        symbol:           e.g. "POLYCAB"
        context_kind:     "guidance" or "pe_expansion"
        context_payload:  the deterministic dict assembled by the caller
        include_adjudicator: whether to fire a 3rd LLM call that picks a winner

    Returns:
        DebateResult with bear/bull text, optional adjudicator, cache metadata.
    """
    sym = symbol.upper().strip()
    ctx_hash = canonical_hash(context_payload)
    logger.info(f"run_debate symbol={sym} kind={context_kind} hash={ctx_hash[:12]}…")

    # ── Cache lookup ───────────────────────────────────────────────────
    cached = lookup_debate(sym, context_kind, ctx_hash)
    if cached:
        logger.info(f"Cache hit for {sym}/{context_kind} ({cached['cache_hits']} hits)")
        return DebateResult(
            bear=cached["bear"],
            bull=cached["bull"],
            adjudicator=cached["adjudicator"],
            model_used=cached["model_used"],
            generated_at=cached["generated_at"],
            cache_hits=cached["cache_hits"],
            cached=True,
            context_hash=ctx_hash,
        )

    # ── Build prompts (lazy import so Phase 1 stays light) ─────────────
    from engine_debate.prompts_guidance import (
        GUIDANCE_BEAR_SYSTEM,
        GUIDANCE_BEAR_USER,
        GUIDANCE_BULL_SYSTEM,
        GUIDANCE_BULL_USER,
    )

    client, model = get_llm_client()
    if not client:
        logger.warning("No LLM configured — returning stub bear/bull")
        bear_text = _stub_bear(context_payload)
        bull_text = _stub_bull(context_payload)
        model_used = "stub"
    else:
        model_used = model
        t0 = time.time()
        try:
            bear_text = _call_llm(
                GUIDANCE_BEAR_SYSTEM,
                GUIDANCE_BEAR_USER.format(
                    symbol=sym,
                    context_json=_format_context(context_payload),
                ),
                model=model,
            )
        except Exception as e:
            logger.exception(f"Bear call failed: {e}")
            bear_text = f"[Bear call failed: {e}]"

        try:
            bull_text = _call_llm(
                GUIDANCE_BULL_SYSTEM,
                GUIDANCE_BULL_USER.format(
                    symbol=sym,
                    context_json=_format_context(context_payload),
                ),
                model=model,
            )
        except Exception as e:
            logger.exception(f"Bull call failed: {e}")
            bull_text = f"[Bull call failed: {e}]"

        logger.info(f"Debate for {sym} completed in {time.time()-t0:.1f}s")

    # ── Optional adjudicator ───────────────────────────────────────────
    adjudicator = None
    if include_adjudicator and client:
        try:
            from engine_debate.prompts_guidance import ADJUDICATOR_SYSTEM, ADJUDICATOR_USER
            adjudicator = _call_llm(
                ADJUDICATOR_SYSTEM,
                ADJUDICATOR_USER.format(symbol=sym, bear=bear_text, bull=bull_text),
                model=model,
            )
        except Exception as e:
            logger.exception(f"Adjudicator call failed: {e}")
            adjudicator = f"[Adjudicator call failed: {e}]"

    # ── Persist ────────────────────────────────────────────────────────
    row_id = store_debate(
        symbol=sym,
        context_kind=context_kind,
        context_hash=ctx_hash,
        context_payload=context_payload,
        bear=bear_text,
        bull=bull_text,
        adjudicator=adjudicator,
        model_used=model_used,
    )
    logger.info(f"Stored debate row id={row_id} for {sym}/{context_kind}")

    return DebateResult(
        bear=bear_text,
        bull=bull_text,
        adjudicator=adjudicator,
        model_used=model_used,
        generated_at=_now_iso(),
        cache_hits=0,
        cached=False,
        context_hash=ctx_hash,
    )


def _format_context(payload: dict) -> str:
    """Pretty-print a context payload for inclusion in LLM prompts."""
    import json
    return json.dumps(payload, indent=2, default=str, ensure_ascii=False)


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
