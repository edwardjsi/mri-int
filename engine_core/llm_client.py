"""
Shared LLM Client Factory — DeepSeek-first with OpenAI fallback.

DeepSeek's API is OpenAI-compatible (same Python client, different base_url).
Priority: DEEPSEEK_API_KEY → OPENAI_API_KEY → None.

Usage:
    from engine_core.llm_client import get_llm_client
    client, model = get_llm_client()
    if not client:
        raise RuntimeError("No LLM API key configured")
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "..."}],
        temperature=0,
    )
"""
from __future__ import annotations

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_llm_cache: Optional[tuple] = None


def get_llm_client():
    """
    Return (client, model_name) tuple for the best available LLM.

    Priority:
      1. DEEPSEEK_API_KEY → deepseek-chat (base_url=https://api.deepseek.com)
      2. OPENAI_API_KEY  → gpt-4o-mini  (default OpenAI)
      3. Neither         → (None, None)
    """
    global _llm_cache
    if _llm_cache is not None:
        return _llm_cache

    try:
        from openai import OpenAI
        import httpx
    except ImportError:
        logger.warning("openai package not installed — LLM features disabled")
        _llm_cache = (None, None)
        return _llm_cache

    http_client = httpx.Client()

    # ── DeepSeek ──────────────────────────────────────────────────
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    if deepseek_key:
        logger.info("Using DeepSeek API (deepseek-chat)")
        client = OpenAI(
            api_key=deepseek_key,
            base_url="https://api.deepseek.com",
            http_client=http_client,
        )
        _llm_cache = (client, "deepseek-chat")
        return _llm_cache

    # ── OpenAI fallback ──────────────────────────────────────────
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        logger.info("Using OpenAI API (gpt-4o-mini)")
        client = OpenAI(api_key=openai_key, http_client=http_client)
        _llm_cache = (client, "gpt-4o-mini")
        return _llm_cache

    logger.warning("Neither DEEPSEEK_API_KEY nor OPENAI_API_KEY set — LLM features disabled")
    _llm_cache = (None, None)
    return _llm_cache


def clear_llm_cache():
    """Reset cached client (use after env var changes)."""
    global _llm_cache
    _llm_cache = None
