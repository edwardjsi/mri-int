"""PE Expansion Signals — scorer and universe iterator.

Combines two data sources for the most complete PE Expansion scoring possible
across the 140-company universe:

  PRIMARY  — `management_narrative_timeline` (LLM-extracted promises from
             the 2026-06-16 narrative tracer run, quote-verified).
             Each row's guidance_text + guidance_type is mapped against the
             PE Dictionary, and current_status contributes to signal strength.

  SECONDARY — `aae_transcripts.raw_text` (raw earnings-call corpus).
             Keyword scan for environmental categories (MOAT_IP, EXPORT_EXPANSION,
             TECHNOLOGY, STRUCTURAL_TAILWIND, VERTICAL_INTEGRATION,
             PRODUCTION_INFLECTION) that usually don't materialize as discrete
             promises but live as background commentary.

Formula (per PRD §PE Expansion Score):
    PE Score = Σ (Category_Weight × Signal_Strength)
    Signal_Strength ∈ {0..5}  per the 0-5 ladder in pe_dictionary module docstring.

Output:
    - perx_pe_signals  : per (symbol, transcript_id, category_code) row with raw counts
    - perx_pe_scores   : per (symbol) aggregate score + top drivers + metadata

Cost: keyword scan + DB reads only. No LLM. Re-runnable any time.
"""
from __future__ import annotations

import json
import logging
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Iterable

from engine_core.db import get_connection
from engine_perx.pe_dictionary import (
    KEYWORD_INDEX,
    MAX_PE_SCORE,
    PE_DICTIONARY,
    WEIGHT_BY_CODE,
)
from engine_perx.scoring import clamp_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("pe_signals")


# ── Category → guidance_type bridge (primary source) ──────────────────
# When a promise row in management_narrative_timeline has one of these
# guidance_type values, it counts toward the corresponding PE category
# WITHOUT requiring a keyword hit. This is the LLM-extracted truth.
GUIDANCE_TYPE_TO_CATEGORY: dict[str, str] = {
    "REVENUE_GROWTH": "REVENUE_VISIBILITY",
    "REVENUE_GUIDANCE": "REVENUE_VISIBILITY",
    "REVENUE": "REVENUE_VISIBILITY",
    "DEAL_PIPELINE": "REVENUE_VISIBILITY",
    "MARGIN": "MARGIN_EXPANSION",
    "MARGIN_GUIDANCE": "MARGIN_EXPANSION",
    "CAPACITY_EXPANSION": "CAPACITY_EXPANSION",
    "CAPEX": "CAPACITY_EXPANSION",
    "MARKET_SHARE": "MARKET_SHARE",
    "HIRING": "SCALABILITY",
    "WORKING_CAPITAL": "ROCE_IMPROVEMENT",
    "DEBT_REDUCTION": "ROCE_IMPROVEMENT",
    "DIVIDEND": "ROCE_IMPROVEMENT",
    "CREDIT_RATING": "ROCE_IMPROVEMENT",
    "OTHER": None,  # resolved by keyword match in guidance_text
}

# status values that should boost signal_strength vs. just "PENDING"
# PRD ladder: 0=none, 1=mentioned, 2=repeated, 3=emphasis, 4=evidence, 5=execution visible
STATUS_STRENGTH_BONUS: dict[str, int] = {
    "INITIAL": 1,
    "NEW": 1,
    "PENDING": 0,
    "ON_TRACK": 2,
    "PARTIALLY_FULFILLED": 2,
    "FULFILLED": 4,
    "REVISED_UP": 4,
    "REVISED_DOWN": 1,
    "MISSED": -1,
    "NEVER_MENTIONED_AGAIN": -1,
}


# ── Keyword scan helper ──────────────────────────────────────────────

# A keyword hits if it appears as a word/phrase boundary in the lowercased
# text. To keep this fast on ~989 transcripts, we pre-compile a single
# combined regex with alternation and use word-boundary-ish matching where
# reasonable. For multi-word keywords, the entire phrase must appear.

def _compile_pattern(keywords: Iterable[str]) -> re.Pattern[str]:
    """Compile keywords into a single case-insensitive alternation regex.

    For single tokens we require word boundaries; for multi-word phrases
    we just substring-match (whitespace is preserved).
    """
    parts: list[str] = []
    for kw in keywords:
        # Escape regex specials.
        esc = re.escape(kw)
        # Heuristic: tokens without internal spaces get \b anchors.
        if " " not in kw and "-" not in kw:
            parts.append(rf"\b{esc}\b")
        else:
            parts.append(esc)
    return re.compile("|".join(parts), re.IGNORECASE)


_CATEGORY_PATTERNS: dict[str, re.Pattern[str]] = {
    cat["code"]: _compile_pattern(cat["keywords"]) for cat in PE_DICTIONARY
}


def scan_text_for_categories(text: str) -> dict[str, dict[str, Any]]:
    """Scan a transcript (or any text) and return per-category counts."""
    if not text:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for code, pat in _CATEGORY_PATTERNS.items():
        matches = pat.findall(text)
        if matches:
            # Get a few sample snippets for context (first 3).
            snippets: list[str] = []
            for m in pat.finditer(text):
                start = max(0, m.start() - 40)
                end = min(len(text), m.end() + 40)
                snippet = text[start:end].replace("\n", " ").strip()
                snippets.append(snippet[:120])
                if len(snippets) >= 3:
                    break
            out[code] = {"mentions": len(matches), "snippets": snippets}
    return out


# ── Signal-strength ladder ───────────────────────────────────────────

def mentions_to_strength(n_mentions: int, has_execution: bool = False) -> int:
    """Map raw mention count to 0-5 signal strength (per PRD ladder).

    Ladder (with execution flag):
      0 = no evidence       (<1)
      1 = mentioned         (1)
      2 = repeated          (2-3)
      3 = management emphasis (4-6)
      4 = evidence provided (7+)
      5 = execution visible (execution keyword co-occurs with the mentions)

    execution = presence of words like 'delivered', 'achieved', 'booked',
    'commissioned', 'exported', 'shipped', 'cleared', 'certified', 'inducted'.
    """
    if n_mentions <= 0:
        return 0
    if n_mentions == 1:
        base = 1
    elif n_mentions <= 3:
        base = 2
    elif n_mentions <= 6:
        base = 3
    else:
        base = 4
    if has_execution and base >= 3:
        base = min(5, base + 1)
    return base


_EXECUTION_WORDS = re.compile(
    r"\b("
    r"delivered|achieved|booked|commissioned|exported|shipped|cleared|certified|"
    r"inducted|deployed|fielded|completed|secured|won|signed|awarded|realised|"
    r"realized|crossed|surpassed|exceeded"
    r")\b",
    re.IGNORECASE,
)


# ── Per-symbol PE scoring (combines both sources) ───────────────────

def score_symbol_from_promises(symbol: str) -> dict[str, Any]:
    """Score a symbol using PRIMARY source: management_narrative_timeline.

    Returns per-category aggregates:
        {
          "symbol": str,
          "n_promises_total": int,
          "n_quote_verified": int,
          "n_quarter_span": int,
          "categories": {
              "MARGIN_EXPANSION": {
                  "weight": 9,
                  "n_promises": 4,
                  "weighted_status_score": 6.0,
                  "signal_strength": 4,  # 0-5
                  "evidence_quotes": ["...", "..."]
              },
              ...
          }
        }
    """
    sym = symbol.upper()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT promise_key, guidance_type, guidance_text,
                      current_status, current_evidence_quote, quote_verified,
                      first_seen_quarter, current_quarter
               FROM management_narrative_timeline
               WHERE symbol = %s""",
            (sym,),
        )
        rows = cur.fetchall() or []
    finally:
        conn.close()

    cats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "n_promises": 0,
            "weighted_status_score": 0.0,
            "evidence_quotes": [],
            "guidance_types": Counter(),
        }
    )
    # Coverage = number of distinct quarters across first_seen_quarter (since
    # current_quarter is always the latest, it's not a useful coverage proxy).
    quarters_seen: set[str] = set()

    for r in rows:
        quarters_seen.add(r["first_seen_quarter"] or "")
        # Resolve category: GUIDANCE_TYPE bridge first, then keyword fallback.
        cat_code = GUIDANCE_TYPE_TO_CATEGORY.get(r["guidance_type"] or "")
        if cat_code is None and r["guidance_text"]:
            # Try keyword match on guidance_text.
            k = _resolve_category_from_text(r["guidance_text"])
            cat_code = k
        if cat_code is None:
            continue  # truly off-topic (e.g. governance misc)

        cats[cat_code]["n_promises"] += 1
        cats[cat_code]["guidance_types"][r["guidance_type"]] += 1
        status = r["current_status"] or "PENDING"
        # Weighted score: status bonus + small bonus for quote-verified.
        bonus = STATUS_STRENGTH_BONUS.get(status, 0)
        if r["quote_verified"]:
            bonus += 0.5
        cats[cat_code]["weighted_status_score"] += bonus
        if r["current_evidence_quote"]:
            cats[cat_code]["evidence_quotes"].append(r["current_evidence_quote"])

    # Convert weighted scores to 0-5 signal_strength.
    for code, agg in cats.items():
        agg["guidance_types"] = dict(agg["guidance_types"])
        ws = agg["weighted_status_score"]
        n = agg["n_promises"]
        # avg bonus per promise → 0-5 ladder; clamp top of ladder at 5
        avg = ws / max(1, n)
        if avg <= 0.5:
            strength = 1
        elif avg <= 1.0:
            strength = 2
        elif avg <= 1.75:
            strength = 3
        elif avg <= 2.5:
            strength = 4
        else:
            strength = 5
        agg["signal_strength"] = strength

    return {
        "symbol": sym,
        "n_promises_total": len(rows),
        "n_quote_verified": sum(1 for r in rows if r["quote_verified"]),
        "n_quarter_span": len({q for q in quarters_seen if q}),
        "categories": dict(cats),
    }


def _resolve_category_from_text(text: str) -> str | None:
    """Keyword-match a single piece of text against the dictionary. First hit wins."""
    if not text:
        return None
    lower = text.lower()
    for code, pat in _CATEGORY_PATTERNS.items():
        if pat.search(lower):
            return code
    return None


def score_symbol_from_transcripts(symbol: str) -> dict[str, Any]:
    """Score a symbol using SECONDARY source: raw transcripts (environmental cats)."""
    sym = symbol.upper()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, date, raw_text FROM public.aae_transcripts
               WHERE symbol = %s AND raw_text IS NOT NULL
                 AND LENGTH(raw_text) > 200
               ORDER BY date ASC""",
            (sym,),
        )
        rows = cur.fetchall() or []
    finally:
        conn.close()

    agg: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"mentions": 0, "snippets": [], "transcripts_with_hits": 0}
    )
    for r in rows:
        cats = scan_text_for_categories(r["raw_text"])
        for code, info in cats.items():
            agg[code]["mentions"] += info["mentions"]
            agg[code]["snippets"].extend(info["snippets"][:2])
            agg[code]["transcripts_with_hits"] += 1

    # Compute signal_strength using mentions ladder + execution-word detection.
    for code, info in agg.items():
        joined_snippets = " ".join(info["snippets"])
        has_exec = bool(_EXECUTION_WORDS.search(joined_snippets))
        info["has_execution_language"] = has_exec
        info["signal_strength"] = mentions_to_strength(
            info["mentions"], has_execution=has_exec
        )

    return {
        "symbol": sym,
        "n_transcripts": len(rows),
        "categories": dict(agg),
    }


def compute_pe_score(
    promise_score: dict[str, Any],
    transcript_score: dict[str, Any],
) -> dict[str, Any]:
    """Combine primary + secondary scores into final PE Score 0-100.

    Per-category: take the MAX signal_strength between primary and secondary
    (a category that is both explicitly promised AND discussed in commentary
    is stronger than either alone), then Σ (weight × strength).

    Returns:
        {
          "symbol": str,
          "pe_score": float (0-100),
          "category_breakdown": {code: {weight, strength, sources: [primary|secondary]}},
          "top_drivers": [list of category labels sorted by contribution desc]
        }
    """
    pcats = promise_score.get("categories", {})
    tcats = transcript_score.get("categories", {})

    breakdown: dict[str, dict[str, Any]] = {}
    total = 0.0
    drivers: list[tuple[str, float]] = []

    for cat in PE_DICTIONARY:
        code = cat["code"]
        weight = cat["weight"]
        p_str = pcats.get(code, {}).get("signal_strength", 0) or 0
        t_str = tcats.get(code, {}).get("signal_strength", 0) or 0
        strength = max(p_str, t_str)
        if strength == 0:
            continue
        sources = []
        if p_str:
            sources.append("primary")
        if t_str:
            sources.append("secondary")
        contribution = weight * strength
        total += contribution
        breakdown[code] = {
            "weight": weight,
            "signal_strength": strength,
            "contribution": contribution,
            "sources": sources,
        }
        drivers.append((cat["label"], contribution))

    drivers.sort(key=lambda x: x[1], reverse=True)
    pe_score = round((total / MAX_PE_SCORE) * 100, 1)

    return {
        "symbol": promise_score.get("symbol") or transcript_score.get("symbol"),
        "pe_score": clamp_score(pe_score),
        "category_breakdown": breakdown,
        "top_drivers": [d[0] for d in drivers[:5]],
        "n_promises_total": promise_score.get("n_promises_total", 0),
        "n_quote_verified": promise_score.get("n_quote_verified", 0),
        "n_transcripts": transcript_score.get("n_transcripts", 0),
        "n_quarter_span": promise_score.get("n_quarter_span", 0),
    }


def score_symbol(symbol: str) -> dict[str, Any]:
    """End-to-end: PRIMARY (promises) + SECONDARY (transcripts) → PE Score."""
    p = score_symbol_from_promises(symbol)
    t = score_symbol_from_transcripts(symbol)
    return compute_pe_score(p, t)


# ── Universe iterator ─────────────────────────────────────────────────

def iter_symbols_with_promises() -> list[str]:
    """Return all symbols that have at least 1 promise row OR 1 transcript."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT symbol FROM management_narrative_timeline
            UNION
            SELECT symbol FROM aae_transcripts WHERE raw_text IS NOT NULL
              AND LENGTH(raw_text) > 200
            ORDER BY symbol
            """
        )
        return [r["symbol"] for r in cur.fetchall()]
    finally:
        conn.close()


def score_universe(symbols: list[str] | None = None) -> list[dict[str, Any]]:
    """Score all symbols (or provided subset). Returns list of score dicts."""
    if symbols is None:
        symbols = iter_symbols_with_promises()
    logger.info(f"Scoring {len(symbols)} symbols...")
    results: list[dict[str, Any]] = []
    for i, sym in enumerate(symbols, 1):
        try:
            res = score_symbol(sym)
            results.append(res)
            if i % 10 == 0:
                logger.info(f"  [{i}/{len(symbols)}] scored (last={sym} pe={res['pe_score']})")
        except Exception as e:
            logger.error(f"  [{i}/{len(symbols)}] FAILED {sym}: {type(e).__name__}: {e}")
    results.sort(key=lambda r: r["pe_score"], reverse=True)
    logger.info(f"Done. Scored {len(results)} symbols.")
    return results


# ── Persistence ──────────────────────────────────────────────────────

def persist_results(results: list[dict[str, Any]]) -> None:
    """Write per-symbol aggregates to perx_pe_scores AND per-category provenance to
    perx_pe_signals (idempotent upsert on both)."""
    if not results:
        return
    conn = get_connection()
    try:
        cur = conn.cursor()
        for r in results:
            cur.execute(
                """
                INSERT INTO perx_pe_scores (
                    symbol, pe_score, n_promises_total, n_quote_verified,
                    n_transcripts, n_quarter_span, top_drivers,
                    category_breakdown, generated_at
                ) VALUES (
                    %(symbol)s, %(pe_score)s, %(n_promises_total)s, %(n_quote_verified)s,
                    %(n_transcripts)s, %(n_quarter_span)s, %(top_drivers)s::jsonb,
                    %(category_breakdown)s::jsonb, NOW()
                )
                ON CONFLICT (symbol) DO UPDATE SET
                    pe_score = EXCLUDED.pe_score,
                    n_promises_total = EXCLUDED.n_promises_total,
                    n_quote_verified = EXCLUDED.n_quote_verified,
                    n_transcripts = EXCLUDED.n_transcripts,
                    n_quarter_span = EXCLUDED.n_quarter_span,
                    top_drivers = EXCLUDED.top_drivers,
                    category_breakdown = EXCLUDED.category_breakdown,
                    generated_at = NOW()
                """,
                {
                    "symbol": r["symbol"],
                    "pe_score": r["pe_score"],
                    "n_promises_total": r["n_promises_total"],
                    "n_quote_verified": r["n_quote_verified"],
                    "n_transcripts": r["n_transcripts"],
                    "n_quarter_span": r["n_quarter_span"],
                    "top_drivers": json.dumps(r["top_drivers"]),
                    "category_breakdown": json.dumps(r["category_breakdown"]),
                },
            )
        conn.commit()
        logger.info(f"Persisted {len(results)} rows to perx_pe_scores")
    finally:
        conn.close()

    # Now write per-category provenance to perx_pe_signals.
    # We re-score each symbol here so we have access to the per-source breakdown.
    persist_signals_for_symbols([r["symbol"] for r in results])


def persist_signals_for_symbols(symbols: list[str]) -> None:
    """Write per-(symbol, source, category_code) rows to perx_pe_signals.

    Re-runs the per-source scoring (cheap) so we get the per-source breakdown.
    Idempotent ON CONFLICT (symbol, source, category_code).
    """
    if not symbols:
        return
    conn = get_connection()
    try:
        cur = conn.cursor()
        n_rows = 0
        for sym in symbols:
            p = score_symbol_from_promises(sym)
            t = score_symbol_from_transcripts(sym)
            # Primary rows
            for code, agg in p.get("categories", {}).items():
                weight = WEIGHT_BY_CODE.get(code, 0)
                cur.execute(
                    """
                    INSERT INTO perx_pe_signals (
                        symbol, source, category_code, weight, signal_strength,
                        n_promises, weighted_status_score,
                        evidence_quotes, guidance_types,
                        created_at, updated_at
                    ) VALUES (
                        %s, 'primary', %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, NOW(), NOW()
                    )
                    ON CONFLICT (symbol, source, category_code) DO UPDATE SET
                        weight = EXCLUDED.weight,
                        signal_strength = EXCLUDED.signal_strength,
                        n_promises = EXCLUDED.n_promises,
                        weighted_status_score = EXCLUDED.weighted_status_score,
                        evidence_quotes = EXCLUDED.evidence_quotes,
                        guidance_types = EXCLUDED.guidance_types,
                        updated_at = NOW()
                    """,
                    (
                        sym, code, weight, agg.get("signal_strength", 0),
                        agg.get("n_promises", 0),
                        agg.get("weighted_status_score", 0.0),
                        json.dumps(agg.get("evidence_quotes", [])),
                        json.dumps(agg.get("guidance_types", {})),
                    ),
                )
                n_rows += 1
            # Secondary rows
            for code, agg in t.get("categories", {}).items():
                weight = WEIGHT_BY_CODE.get(code, 0)
                cur.execute(
                    """
                    INSERT INTO perx_pe_signals (
                        symbol, source, category_code, weight, signal_strength,
                        mentions, has_execution_language,
                        evidence_quotes, n_transcripts_with_hits,
                        created_at, updated_at
                    ) VALUES (
                        %s, 'secondary', %s, %s, %s, %s, %s, %s::jsonb, %s, NOW(), NOW()
                    )
                    ON CONFLICT (symbol, source, category_code) DO UPDATE SET
                        weight = EXCLUDED.weight,
                        signal_strength = EXCLUDED.signal_strength,
                        mentions = EXCLUDED.mentions,
                        has_execution_language = EXCLUDED.has_execution_language,
                        evidence_quotes = EXCLUDED.evidence_quotes,
                        n_transcripts_with_hits = EXCLUDED.n_transcripts_with_hits,
                        updated_at = NOW()
                    """,
                    (
                        sym, code, weight, agg.get("signal_strength", 0),
                        agg.get("mentions", 0),
                        agg.get("has_execution_language", False),
                        json.dumps(agg.get("snippets", [])),
                        agg.get("transcripts_with_hits", 0),
                    ),
                )
                n_rows += 1
        conn.commit()
        logger.info(f"Persisted {n_rows} provenance rows to perx_pe_signals")
    finally:
        conn.close()


# ── Report builder (used by both screen and email) ────────────────────

from engine_perx.pe_dictionary import PE_DICTIONARY as _PE_DICT  # alias for local clarity

_REPORT_CATEGORY_ORDER = [c["code"] for c in _PE_DICT]


def _extract_quote_text(item: Any) -> str:
    """Defensive: evidence_quotes items can be plain strings or dicts."""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return (
            item.get("text")
            or item.get("quote")
            or item.get("snippet")
            or item.get("evidence")
            or ""
        )
    return ""


def _fetch_category_quotes(symbol: str, category_codes: list[str]) -> dict[str, dict[str, str]]:
    """Fetch one representative evidence quote per (symbol, category).

    Returns {category_code: {text, source, quarter}}. Prefers primary-source
    quotes (verbatim from management narrative tracer); falls back to
    secondary (transcript keyword scan) if no primary quote exists.
    Omitted categories are simply absent from the returned dict.
    """
    if not category_codes:
        return {}
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT category_code, source, evidence_quotes
               FROM perx_pe_signals
               WHERE symbol = %s
                 AND category_code = ANY(%s)
                 AND jsonb_array_length(evidence_quotes) > 0
               ORDER BY CASE source WHEN 'primary' THEN 0 ELSE 1 END,
                        category_code""",
            (symbol.upper(), category_codes),
        )
        out: dict[str, dict[str, str]] = {}
        for row in cur.fetchall():
            code = row["category_code"]
            if code in out:
                continue  # primary-source quote already captured for this category
            quotes = row["evidence_quotes"]
            if not isinstance(quotes, list) or not quotes:
                continue
            text = _extract_quote_text(quotes[0]).strip()
            if not text:
                continue
            entry: dict[str, str] = {
                "text": text[:400],  # truncate to safe rendering length
                "source": str(row["source"] or ""),
            }
            first = quotes[0]
            if isinstance(first, dict):
                q = first.get("quarter") or first.get("period") or first.get("date")
                if q:
                    entry["quarter"] = str(q)[:20]
            out[code] = entry
        return out
    finally:
        conn.close()


def _score_bucket(score: float) -> str:
    if score >= 80: return "Strong"
    if score >= 65: return "Moderate"
    if score >= 50: return "Watch"
    if score >= 30: return "Weak"
    return "Negligible"


def _company_meta(symbol: str) -> dict[str, Any]:
    """Pull company_name + sector from stock_sectors. Returns {} if missing."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT company_name, industry FROM stock_sectors WHERE symbol = %s",
            (symbol.upper(),),
        )
        r = cur.fetchone()
        if not r:
            return {}
        return {"company_name": r["company_name"], "sector": r["industry"]}
    except Exception:
        return {}
    finally:
        conn.close()


def _universe_rank(symbol: str, pe_score: float) -> dict[str, Any]:
    """Compute rank + total in universe for the symbol."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) AS c FROM perx_pe_scores WHERE pe_score > %s",
            (pe_score,),
        )
        rank = (cur.fetchone() or {"c": 0})["c"] + 1
        cur.execute("SELECT COUNT(*) AS c FROM perx_pe_scores")
        total = (cur.fetchone() or {"c": 0})["c"]
        return {"rank": rank, "total": total}
    except Exception:
        return {"rank": None, "total": None}
    finally:
        conn.close()


def _primary_detail_rows(symbol: str) -> list[dict[str, Any]]:
    """Pull per-promise detail for the primary-source panel.

    Sorted: most recent quarter first, then by guidance_type, then by target_value desc.
    Capped at 20 to keep the email under 100 KB.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT promise_key, guidance_type, guidance_text,
                      current_status, current_quarter, first_seen_quarter,
                      target_value, target_unit, target_date, quote_verified,
                      current_evidence_quote
               FROM management_narrative_timeline
               WHERE symbol = %s
               ORDER BY current_quarter DESC, first_seen_quarter DESC,
                        guidance_type, target_value DESC NULLS LAST
               LIMIT 20""",
            (symbol.upper(),),
        )
        return list(cur.fetchall())
    except Exception:
        return []
    finally:
        conn.close()


def build_pe_expansion_report(symbol: str) -> dict[str, Any]:
    """Assemble the full PE Expansion report dict for a symbol.

    Shape (consumed by both the screen and the HTML email):
      {
        "header": {symbol, company_name, sector, pe_score, rank, total,
                   bucket, generated_at_iso, generated_at_ist},
        "coverage": {n_promises_total, n_quote_verified, n_transcripts,
                     n_quarter_span},
        "category_breakdown": [   # ordered, all 12 categories
          {"code", "label", "weight", "signal_strength", "contribution",
           "sources": [primary|secondary], "missing": bool},
          ...
        ],
        "top_drivers": [label, ...],
        "primary_detail": [
          {category_code, guidance_type, current_status, current_quarter,
           target_value, target_unit, target_date, guidance_text,
           evidence_quote, quote_verified},
          ...
        ],
        "secondary_detail": [   # only categories with mentions>0
          {category_code, mentions, transcripts_with_hits, has_execution,
           signal_strength, snippets: [...]},
          ...
        ],
        "totals": {raw_score, max_possible, scaled_percent}
      }
    """
    sym = symbol.upper()
    meta = _company_meta(sym)
    score_doc = score_symbol(sym)
    rank_doc = _universe_rank(sym, score_doc["pe_score"])
    primary_detail = _primary_detail_rows(sym)

    # Secondary detail: re-scan transcripts to get snippet list (cheap)
    secondary_scan = score_symbol_from_transcripts(sym)

    # Build category_breakdown ordered list with all 12 categories
    breakdown: list[dict[str, Any]] = []
    raw_total = 0
    for code in _REPORT_CATEGORY_ORDER:
        cat = next(c for c in _PE_DICT if c["code"] == code)
        info = score_doc["category_breakdown"].get(code)
        if info:
            breakdown.append({
                "code": code,
                "label": cat["label"],
                "weight": cat["weight"],
                "signal_strength": info["signal_strength"],
                "contribution": info["contribution"],
                "sources": info["sources"],
                "missing": False,
            })
            raw_total += info["contribution"]
        else:
            breakdown.append({
                "code": code,
                "label": cat["label"],
                "weight": cat["weight"],
                "signal_strength": 0,
                "contribution": 0,
                "sources": [],
                "missing": True,
            })

    # Attach one representative evidence quote per non-missing category.
    # This grounds the abstract scores with a verbatim citation from the
    # management narrative tracer (primary source) or transcript keyword
    # scan (secondary source).
    quotes_by_cat = _fetch_category_quotes(sym, _REPORT_CATEGORY_ORDER)
    for row in breakdown:
        if row.get("missing"):
            continue
        q = quotes_by_cat.get(row["code"])
        if q:
            row["quote"] = q

    # Pull secondary snippet detail
    secondary_detail: list[dict[str, Any]] = []
    for code, info in secondary_scan.get("categories", {}).items():
        if info.get("mentions", 0) > 0:
            cat = next((c for c in _PE_DICT if c["code"] == code), None)
            secondary_detail.append({
                "category_code": code,
                "label": cat["label"] if cat else code,
                "mentions": info.get("mentions", 0),
                "transcripts_with_hits": info.get("transcripts_with_hits", 0),
                "has_execution": info.get("has_execution_language", False),
                "signal_strength": info.get("signal_strength", 0),
                "snippets": info.get("snippets", [])[:3],
            })
    secondary_detail.sort(key=lambda x: x["mentions"], reverse=True)

    # IST timestamp (UTC+5:30)
    from datetime import datetime, timezone, timedelta
    ist = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist)

    return {
        "header": {
            "symbol": sym,
            "company_name": meta.get("company_name") or sym,
            "sector": meta.get("sector"),
            "pe_score": score_doc["pe_score"],
            "rank": rank_doc["rank"],
            "total": rank_doc["total"],
            "bucket": _score_bucket(score_doc["pe_score"]),
            "generated_at_iso": now_ist.isoformat(),
            "generated_at_ist": now_ist.strftime("%Y-%m-%d %H:%M IST"),
        },
        "coverage": {
            "n_promises_total": score_doc["n_promises_total"],
            "n_quote_verified": score_doc["n_quote_verified"],
            "n_transcripts": score_doc["n_transcripts"],
            "n_quarter_span": score_doc["n_quarter_span"],
        },
        "category_breakdown": breakdown,
        "top_drivers": score_doc["top_drivers"],
        "primary_detail": primary_detail,
        "secondary_detail": secondary_detail,
        "totals": {
            "raw_score": raw_total,
            "max_possible": MAX_PE_SCORE,
            "scaled_percent": score_doc["pe_score"],
        },
    }


if __name__ == "__main__":
    import argparse
    import sys
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", "-s", help="Score a single symbol")
    ap.add_argument("--limit", "-n", type=int, default=0,
                    help="Score only first N symbols (after sort)")
    ap.add_argument("--persist", action="store_true",
                    help="Write results to perx_pe_scores")
    ap.add_argument("--top", type=int, default=20,
                    help="Print top N by score (default 20)")
    args = ap.parse_args()

    if args.symbol:
        r = score_symbol(args.symbol)
        print(json.dumps(r, indent=2, default=str))
        sys.exit(0)

    syms = iter_symbols_with_promises()
    if args.limit:
        syms = syms[: args.limit]
    results = score_universe(syms)

    print(f"\n=== TOP {args.top} by PE Expansion Score ===\n")
    print(f"{'Rank':<5}{'Symbol':<14}{'PE':<7}{'Prom':<7}{'Verif':<7}{'TX':<5}{'Q':<4}  Top drivers")
    for i, r in enumerate(results[: args.top], 1):
        drivers = ", ".join(r["top_drivers"][:3])
        print(
            f"{i:<5}{r['symbol']:<14}"
            f"{r['pe_score']:<7.1f}"
            f"{r['n_promises_total']:<7}"
            f"{r['n_quote_verified']:<7}"
            f"{r['n_transcripts']:<5}"
            f"{r['n_quarter_span']:<4}  {drivers}"
        )

    if args.persist:
        persist_results(results)
