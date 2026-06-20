"""
engine_debate.cache — read/write helpers for the conviction_debates table.

Key contract: cache key is (symbol, context_kind, sha256 hex of canonical JSON
payload). Cache miss is OK — caller fires LLM and writes via store_debate().

All helpers use the existing engine_core.db.get_connection() pattern.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional

from engine_core.db import get_connection

logger = logging.getLogger("engine_debate.cache")


def canonical_hash(payload: dict) -> str:
    """Stable sha256 hex of a JSON payload. sort_keys=True ensures determinism
    across runs regardless of dict insertion order."""
    canonical = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def lookup_debate(symbol: str, context_kind: str, context_hash: str) -> Optional[dict]:
    """Return cached debate row, or None on miss. On hit, increments cache_hits."""
    sym = symbol.upper().strip()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, bear_text, bull_text, adjudicator, model_used,
                      generated_at, cache_hits
               FROM conviction_debates
               WHERE symbol = %s AND context_kind = %s AND context_hash = %s""",
            (sym, context_kind, context_hash),
        )
        row = cur.fetchone()
        if not row:
            return None

        # Increment cache_hits as telemetry — fire-and-forget so a hit is still fast.
        try:
            if isinstance(row, dict):
                row_id = row["id"]
            else:
                row_id = row[0]
            cur.execute(
                "UPDATE conviction_debates SET cache_hits = cache_hits + 1 WHERE id = %s",
                (row_id,),
            )
            conn.commit()
        except Exception:
            conn.rollback()

        if isinstance(row, dict):
            return {
                "bear": row["bear_text"],
                "bull": row["bull_text"],
                "adjudicator": row["adjudicator"],
                "model_used": row["model_used"],
                "generated_at": row["generated_at"].isoformat() if row["generated_at"] else None,
                "cache_hits": (row["cache_hits"] or 0) + 1,
                "cached": True,
            }
        # Tuple fallback
        return {
            "bear": row[1],
            "bull": row[2],
            "adjudicator": row[3],
            "model_used": row[4],
            "generated_at": row[5].isoformat() if row[5] else None,
            "cache_hits": (row[6] or 0) + 1,
            "cached": True,
        }
    finally:
        conn.close()


def store_debate(
    symbol: str,
    context_kind: str,
    context_hash: str,
    context_payload: dict,
    bear: str,
    bull: str,
    adjudicator: Optional[str],
    model_used: str,
) -> int:
    """Persist a fresh debate. ON CONFLICT (idempotent on hash) — safe to re-call."""
    sym = symbol.upper().strip()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO conviction_debates
               (symbol, context_kind, context_hash, context_payload,
                bear_text, bull_text, adjudicator, model_used)
               VALUES (%s, %s, %s, %s::jsonb, %s, %s, %s, %s)
               ON CONFLICT (symbol, context_kind, context_hash) DO NOTHING
               RETURNING id""",
            (
                sym,
                context_kind,
                context_hash,
                json.dumps(context_payload, default=str, ensure_ascii=False),
                bear,
                bull,
                adjudicator,
                model_used,
            ),
        )
        row = cur.fetchone()
        conn.commit()
        if row:
            return row[0] if not isinstance(row, dict) else row["id"]
        # ON CONFLICT triggered — row already exists, return its id.
        cur.execute(
            "SELECT id FROM conviction_debates WHERE symbol=%s AND context_kind=%s AND context_hash=%s",
            (sym, context_kind, context_hash),
        )
        existing = cur.fetchone()
        return existing[0] if not isinstance(existing, dict) else existing["id"]
    finally:
        conn.close()


def get_latest_debate_for_symbol(symbol: str, context_kind: str) -> Optional[dict]:
    """Return the most recently cached debate for a symbol + context_kind,
    regardless of hash. Uses SELECT … ORDER BY generated_at DESC LIMIT 1.
    Email path uses this because we don't want to build the context just
    to compute a hash (expensive on the email send-path).
    """
    sym = symbol.upper().strip()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT bear_text, bull_text, adjudicator, model_used,
                      generated_at, cache_hits
               FROM conviction_debates
               WHERE symbol = %s AND context_kind = %s
               ORDER BY generated_at DESC
               LIMIT 1""",
            (sym, context_kind),
        )
        row = cur.fetchone()
        if not row:
            return None
        if isinstance(row, dict):
            return {
                "bear": row["bear_text"],
                "bull": row["bull_text"],
                "adjudicator": row["adjudicator"],
                "model_used": row["model_used"],
                "generated_at": row["generated_at"].isoformat() if row["generated_at"] else None,
                "cache_hits": row["cache_hits"] or 0,
                "cached": True,
            }
        return {
            "bear": row[0],
            "bull": row[1],
            "adjudicator": row[2],
            "model_used": row[3],
            "generated_at": row[4].isoformat() if row[4] else None,
            "cache_hits": row[5] or 0,
            "cached": True,
        }
    finally:
        conn.close()
