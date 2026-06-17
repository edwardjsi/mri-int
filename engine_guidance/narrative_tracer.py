"""
Narrative Tracer — Iterative cross-transcript management-promise tracker.

Approach (per user direction, June 2026):
    1. Take the EARLIEST transcript. Extract all forward-looking statements.
    2. Read the NEXT transcript. For each existing promise, check whether
       management fulfilled / revised / missed / reaffirmed / dropped it.
       Also extract any NEW promises made in this transcript.
    3. Repeat for each subsequent transcript in chronological order.
    4. After the latest transcript, return the full per-promise timeline.

Strict rules:
    - No outside data. Verification source = management's own later words.
    - No hallucination. Every status claim must include an evidence_quote
      copied verbatim from the relevant transcript.
    - Status only set to FULFILLED / MISSED / REVISED if explicitly confirmed
      in a later transcript. Otherwise PENDING.

Usage:
    python3 -m engine_guidance.narrative_tracer --symbol CGCL
    python3 -m engine_guidance.narrative_tracer --symbol CGCL --limit 15000
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Optional

from engine_core.db import get_connection
from engine_core.llm_client import get_llm_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("narrative_tracer")


# ── Prompt templates ──────────────────────────────────────────────────

INITIAL_EXTRACTION_PROMPT = """You are analyzing the EARLIEST available earnings call transcript
for {symbol} (quarter: {quarter}, date: {date}).

Your job: extract EVERY forward-looking COMMITMENT management made about FUTURE
performance. A "commitment" is a SPECIFIC, VERIFIABLE pledge — not a vague
aspiration or corporate boilerplate.

═══════════════════════════════════════════════════════════════════════
WHAT COUNTS AS A PROMISE (must have at least ONE of these)
═══════════════════════════════════════════════════════════════════════
  ✓ Specific numeric target + unit + timeframe
    "AUM target of INR55,000 crores by FY28"
    "Total CAPEX of ₹1,000 crores this year"
    "Expand to 100 branches by end of FY27"
  ✓ Specific binary outcome with deadline
    "Unit-III phase-I to be fully operational in 6 months"
    "Commercial volumes for 3 CS projects to start in Q3-Q4 calendar 2026"
  ✓ Specific directional commitment with timeframe
    "Expect car loan origination to grow 12-15% YoY"
    "Maintain NIM in the 6.5-7% range"

═══════════════════════════════════════════════════════════════════════
REJECT — these are NOT promises (do NOT extract them)
═══════════════════════════════════════════════════════════════════════
  ✗ Past/present results — already happened, can't be a future commitment
    "we delivered X", "we achieved Y", "revenue was Z"
    "we maintained stability", "we maintained margins"
  ✗ Vague corporate positioning — no specific outcome
    "we are well positioned", "we are confident", "we remain committed"
    "we see opportunities", "we are excited about"
    "we maintain our focus", "we stay on track"
  ✗ Vague aspiration — no metric, no deadline, no binary outcome
    "the objective is to enhance", "we aim to be a leader"
    "we focus on quality", "we believe in innovation"
    "we strive for excellence", "the underlying focus has not changed"
  ✗ Ongoing practices — not a future commitment, just a current activity
    "we have continued to invest in", "we are investing in"
    "we have been expanding", "we continue to focus on"
  ✗ Industry-level statements — not company-specific
    "the industry is growing", "demand is strong"
  ✗ Product/technology descriptions — features, not commitments
    "we are developing new products", "we launched X"
  ✗ Repeats / paraphrases of the same idea within the transcript
    (deduplicate to ONE entry per unique commitment)

═══════════════════════════════════════════════════════════════════════
WHEN IN DOUBT, EXCLUDE. A short list of high-quality, specific commitments
is far more valuable than a long list of vague boilerplate.
═══════════════════════════════════════════════════════════════════════

If a range is given (e.g. "12-15%"), set target_value to the midpoint and
include range_low and range_high.

Return JSON in EXACTLY this format:
{{
  "promises": [
    {{
      "guidance_text": "concise paraphrase, ≤120 chars",
      "guidance_type": "MARGIN|REVENUE_GROWTH|CAPEX|DEBT_REDUCTION|CAPACITY_EXPANSION|WORKING_CAPITAL|DIVIDEND|MARKET_SHARE|HIRING|DEAL_PIPELINE|CREDIT_RATING|OTHER",
      "metric": "specific metric or null",
      "target_value": <number or null>,
      "target_unit": "<pct|crore|rs_cr|bps|units|null>",
      "range_low": <number or null>,
      "range_high": <number or null>,
      "target_date": "<Q4FY26|FY27|null>",
      "evidence_quote": "exact sentence(s) from this transcript, ≤200 chars",
      "confidence": "low|medium|high"
    }}
  ]
}}

Transcript ({quarter}):
{transcript_text}
"""


UPDATE_PROMPT = """You are tracing the EVOLUTION of {symbol}'s forward-looking promises
across earnings calls. This is quarter {quarter} (date: {date}).

You already have this list of promises from earlier transcripts:
{existing_promises}

Now read the NEW transcript ({quarter}) and for EACH existing promise,
determine what management said (if anything) about it in THIS transcript.

ALSO: extract any NEW forward-looking commitments management made in THIS
transcript that aren't in the existing list yet.

STRICT RULES — no hallucination, no outside data:
  - Status PENDING: promise was not mentioned in this transcript, OR was
    mentioned but with no update.
  - Status FULFILLED: management explicitly says the target was achieved or
    the goal was met in this transcript. evidence_quote must show this.
  - Status PARTIALLY_FULFILLED: management gives a number that's better
    than baseline but below target, OR explicitly says "partially".
  - Status MISSED: management explicitly says they fell short, OR
    explicitly walks back the commitment, OR explicitly restates a
    significantly lower target without acknowledging the change.
  - Status REVISED_UP / REVISED_DOWN: management explicitly raises or
    lowers the target. Old value is implicitly superseded.
  - Status NEVER_MENTIONED_AGAIN: not addressed in this OR any earlier
    transcript since first_seen. (Use cautiously — prefer PENDING.)
  - Status ON_TRACK: management gives reassuring commentary that the goal
    is still achievable, without a numeric update.
  - Status NEW: this promise is being added for the first time in this
    transcript.

For each promise in the EXISTING list, output ONE entry in the timeline
for THIS quarter — even if it's PENDING with no new evidence.

For each NEW promise extracted from this transcript, also output one entry.

Return JSON in EXACTLY this format:
{{
  "updates": [
    {{
      "promise_key": "<matches the key from existing list, OR a new key for new promises>",
      "guidance_text": "<for NEW promises only, concise paraphrase>",
      "guidance_type": "<for NEW only>",
      "metric": "<for NEW only or null>",
      "target_value": <for NEW only or null>,
      "target_unit": "<for NEW only or null>",
      "range_low": <for NEW only or null>,
      "range_high": <for NEW only or null>,
      "target_date": "<for NEW only or null>",
      "status_this_quarter": "PENDING|FULFILLED|PARTIALLY_FULFILLED|MISSED|REVISED_UP|REVISED_DOWN|NEVER_MENTIONED_AGAIN|ON_TRACK|NEW",
      "evidence_quote": "exact sentence(s) from THIS transcript, ≤200 chars, OR null if PENDING with no mention"
    }}
  ]
}}

Existing promise keys (use these for updates, generate new sha256-style keys for new promises):
{existing_keys}

Transcript ({quarter}):
{transcript_text}
"""


# ── Helpers ──────────────────────────────────────────────────────────

def make_promise_key(symbol: str, quarter: str, text: str) -> str:
    """Stable hash so re-runs identify the same promise."""
    norm = f"{symbol}|{quarter}|{(text or '').strip().lower()[:80]}"
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def _norm(text: str) -> str:
    """Normalize whitespace for substring matching."""
    import re
    return re.sub(r"\s+", " ", (text or "").strip())


def verify_quote_in_transcript(quote: str, transcript: str) -> tuple[bool, str]:
    """Check if the evidence_quote actually appears in the source text.

    Returns (verified, method) where method is one of:
      - "exact"      — verbatim substring (after whitespace normalization)
      - "fuzzy"      — high-similarity match (SequenceMatcher ratio ≥ 0.88)
      - "not_found"  — quote doesn't appear in source (treat as hallucination)
    """
    if not quote or not transcript:
        return False, "not_found"
    nq = _norm(quote)
    nt = _norm(transcript)
    if not nq or len(nq) < 8:
        return False, "not_found"
    if nq in nt:
        return True, "exact"
    # Fuzzy: try to find a window in the transcript with high similarity.
    # Use the LLM's quote length as the window size.
    try:
        from difflib import SequenceMatcher
        qlen = len(nq)
        if qlen > len(nt):
            return False, "not_found"
        # Slide a window of quote length across the transcript, check best ratio.
        step = max(50, qlen // 4)
        best = 0.0
        for i in range(0, len(nt) - qlen + 1, step):
            window = nt[i:i + qlen + 40]  # a bit longer to handle paraphrasing
            r = SequenceMatcher(None, nq, window).ratio()
            if r > best:
                best = r
            if best >= 0.95:
                break
        if best >= 0.88:
            return True, "fuzzy"
        return False, "not_found"
    except Exception:
        return False, "not_found"


def parse_quarter(date_str) -> Optional[str]:
    """Map a date to 'Q{1-4}FY{YY}' Indian fiscal format."""
    if not date_str:
        return None
    try:
        from datetime import datetime, date
        if isinstance(date_str, str):
            d = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        elif isinstance(date_str, date):
            d = date_str
        else:
            return None
        # Indian FY: Apr=start. FY26 = Apr 2025 to Mar 2026.
        if d.month >= 4:
            fy = d.year + 1
            q = (d.month - 4) // 3 + 1
        else:
            fy = d.year
            q = (d.month + 8) // 3 + 1
        return f"Q{q}FY{str(fy)[-2:]}"
    except Exception:
        return None


def load_transcripts(symbol: str) -> list[dict]:
    """Load all transcripts for a symbol, oldest first."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT id, date, raw_text FROM public.aae_transcripts
               WHERE symbol = %s AND raw_text IS NOT NULL
                 AND LENGTH(raw_text) > 200
               ORDER BY date ASC""",
            (symbol.upper(),),
        )
        out = []
        for r in cur.fetchall():
            d = r["date"]
            q = parse_quarter(d.isoformat() if hasattr(d, "isoformat") else str(d))
            out.append({
                "id": r["id"],
                "date": d,
                "quarter": q,
                "raw_text": r["raw_text"] or "",
            })
        return out
    finally:
        conn.close()


# ── Core tracer ──────────────────────────────────────────────────────

class NarrativeTracer:
    def __init__(self, symbol: str, max_chars_per_call: int = 15000):
        self.symbol = symbol.upper()
        self.client, self.model = get_llm_client()
        self.max_chars = max_chars_per_call
        self._corpus: Optional[str] = None  # full company corpus (all transcripts concatenated)

    def _load_corpus(self) -> str:
        """Load and concatenate ALL transcripts for the company once.
        Used for quote verification across the full history, not just
        the current transcript being processed.
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT raw_text FROM public.aae_transcripts
                   WHERE symbol = %s AND raw_text IS NOT NULL
                   ORDER BY date ASC""",
                (self.symbol,),
            )
            return "\n\n---TRANSCRIPT_BOUNDARY---\n\n".join(
                r["raw_text"] or "" for r in cur.fetchall()
            )
        finally:
            conn.close()

    def _corpus_text(self) -> str:
        if self._corpus is None:
            self._corpus = self._load_corpus()
        return self._corpus

    def _call(self, prompt: str, label: str) -> Optional[dict]:
        if not self.client:
            logger.warning("LLM client not available")
            return None
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content":
                     "You are a precise, conservative institutional analyst. "
                     "You only make claims supported by direct quotes from source text. "
                     "You never invent numbers, and you never use outside data."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content
            usage = getattr(resp, "usage", None)
            if usage:
                logger.info(f"[{label}] tokens: in={usage.prompt_tokens} out={usage.completion_tokens}")
            return json.loads(content)
        except Exception as e:
            logger.error(f"[{label}] LLM call failed: {e}")
            return None

    def _initial_extract(self, t: dict) -> list[dict]:
        prompt = INITIAL_EXTRACTION_PROMPT.format(
            symbol=self.symbol,
            quarter=t["quarter"] or "?",
            date=str(t["date"]),
            transcript_text=t["raw_text"][:self.max_chars],
        )
        out = self._call(prompt, f"initial-{t['quarter']}")
        if not out:
            return []
        promises = out.get("promises", [])
        transcript = t["raw_text"][:self.max_chars]
        verified_count = 0
        for p in promises:
            p["promise_key"] = make_promise_key(self.symbol, t["quarter"], p.get("guidance_text", ""))
            p["first_seen_transcript_id"] = t["id"]
            p["first_seen_date"] = t["date"]
            p["first_seen_quarter"] = t["quarter"]
            p.setdefault("status_by_quarter", {})
            p.setdefault("evidence_by_quarter", {})
            p.setdefault("quote_source_by_quarter", {})
            # Mechanical validation: does the evidence_quote actually exist in source?
            ok, method = verify_quote_in_transcript(p.get("evidence_quote"), transcript)
            p["quote_verified"] = ok
            p["quote_verification_method"] = method
            if ok:
                verified_count += 1
                p["status_by_quarter"][t["quarter"]] = "INITIAL"
                p["evidence_by_quarter"][t["quarter"]] = p.get("evidence_quote")
                p["quote_source_by_quarter"][t["quarter"]] = "current_transcript"
            else:
                # Hallucinated quote: still track the promise but flag it.
                p["status_by_quarter"][t["quarter"]] = "INITIAL_UNVERIFIED"
                p["evidence_by_quarter"][t["quarter"]] = None
                p["quote_source_by_quarter"][t["quarter"]] = None
                p["guidance_text"] = (p.get("guidance_text") or "") + " [QUOTE_UNVERIFIED]"
        logger.info(
            f"[{t['quarter']}] initial: {len(promises)} extracted, "
            f"{verified_count} quote-verified, {len(promises) - verified_count} unverified"
        )
        return promises

    def _update_with(self, promises: list[dict], t: dict) -> list[dict]:
        # Compact JSON of existing promises for the prompt
        compact = [
            {
                "promise_key": p["promise_key"],
                "guidance_text": p["guidance_text"],
                "target_value": p.get("target_value"),
                "target_unit": p.get("target_unit"),
                "target_date": p.get("target_date"),
                "guidance_type": p.get("guidance_type"),
            }
            for p in promises
        ]
        existing_keys = [p["promise_key"] for p in promises]
        prompt = UPDATE_PROMPT.format(
            symbol=self.symbol,
            quarter=t["quarter"] or "?",
            date=str(t["date"]),
            existing_promises=json.dumps(compact, indent=2),
            existing_keys=json.dumps(existing_keys, indent=2),
            transcript_text=t["raw_text"][:self.max_chars],
        )
        out = self._call(prompt, f"update-{t['quarter']}")
        if not out:
            return promises
        updates = out.get("updates", [])
        # Build lookup: existing promises by key
        by_key = {p["promise_key"]: p for p in promises}
        transcript = t["raw_text"][:self.max_chars]
        corpus = self._corpus_text()  # full company corpus for verification
        for u in updates:
            key = u.get("promise_key")
            status = u.get("status_this_quarter")
            quote = u.get("evidence_quote")
            # Validate the update evidence_quote against the CURRENT transcript
            # first, then fall back to the full company corpus. If found
            # only in the corpus (not in current), it's still real — just
            # from a different transcript; we record quote_source.
            quote_source = None
            quote_verified = False
            if quote:
                ok_cur, _ = verify_quote_in_transcript(quote, transcript)
                if ok_cur:
                    quote_source = "current_transcript"
                    quote_verified = True
                else:
                    ok_corp, _ = verify_quote_in_transcript(quote, corpus)
                    if ok_corp:
                        quote_source = "company_corpus"
                        quote_verified = True
                    else:
                        # Quote not found anywhere — likely hallucination.
                        # Keep the LLM's status decision (may still be useful as a
                        # directional read), but null the quote so we don't show
                        # fabricated evidence to the user.
                        logger.warning(
                            f"[{t['quarter']}] unverified quote for key={key} "
                            f"(status kept as {status}): \"{quote[:80]}...\""
                        )
                        quote = None
                        quote_source = None
            if key in by_key:
                # Update existing
                p = by_key[key]
                p["status_by_quarter"][t["quarter"]] = status
                if quote:
                    p["evidence_by_quarter"][t["quarter"]] = quote
                    p["quote_source_by_quarter"][t["quarter"]] = quote_source
                    # Update verification flags based on this quote
                    p["quote_verified"] = True
                    p["quote_verification_method"] = quote_source or "current_transcript"
                p["current_status"] = status
                p["current_quarter"] = t["quarter"]
                p["current_evidence_quote"] = quote
                p["total_transcripts_traced"] = len(p["status_by_quarter"])
            else:
                # New promise first seen in this transcript
                new_promise = {
                    "promise_key": key or make_promise_key(
                        self.symbol, t["quarter"], u.get("guidance_text", "")),
                    "guidance_text": u.get("guidance_text", ""),
                    "guidance_type": u.get("guidance_type"),
                    "metric": u.get("metric"),
                    "target_value": u.get("target_value"),
                    "target_unit": u.get("target_unit"),
                    "range_low": u.get("range_low"),
                    "range_high": u.get("range_high"),
                    "target_date": u.get("target_date"),
                    "first_seen_transcript_id": t["id"],
                    "first_seen_date": t["date"],
                    "first_seen_quarter": t["quarter"],
                    "status_by_quarter": {t["quarter"]: status or "NEW"},
                    "evidence_by_quarter": {t["quarter"]: quote},
                    "quote_source_by_quarter": {t["quarter"]: quote_source if quote else None},
                    "current_status": status or "NEW",
                    "current_quarter": t["quarter"],
                    "current_evidence_quote": quote,
                    "total_transcripts_traced": 1,
                    "quote_verified": bool(quote),  # only true if quote survived validation
                    "quote_verification_method": "exact" if quote else "not_found",
                }
                promises.append(new_promise)
                by_key[new_promise["promise_key"]] = new_promise
        return promises

    def trace(self) -> list[dict]:
        transcripts = load_transcripts(self.symbol)
        if not transcripts:
            logger.warning(f"No transcripts found for {self.symbol}")
            return []
        logger.info(f"Tracing {len(transcripts)} transcripts for {self.symbol}: "
                    f"{transcripts[0]['quarter']} → {transcripts[-1]['quarter']}")
        promises = self._initial_extract(transcripts[0])
        logger.info(f"Initial extraction: {len(promises)} promises")
        for t in transcripts[1:]:
            promises = self._update_with(promises, t)
            logger.info(f"After {t['quarter']}: tracking {len(promises)} promises")
        return promises


# ── Persistence ──────────────────────────────────────────────────────

def upsert_timeline(symbol: str, promises: list[dict]) -> int:
    """Idempotent insert/update of the narrative timeline for a symbol."""
    if not promises:
        return 0
    conn = get_connection()
    try:
        cur = conn.cursor()
        n = 0
        for p in promises:
            cur.execute(
                """
                INSERT INTO public.management_narrative_timeline (
                    symbol, promise_key,
                    first_seen_transcript_id, first_seen_date, first_seen_quarter,
                    guidance_text, guidance_type, metric,
                    target_value, target_unit, target_date,
                    status_by_quarter, evidence_by_quarter,
                    current_status, current_quarter, current_evidence_quote,
                    total_transcripts_traced,
                    quote_verified, quote_verification_method,
                    updated_at
                ) VALUES (
                    %(symbol)s, %(promise_key)s,
                    %(first_seen_transcript_id)s, %(first_seen_date)s, %(first_seen_quarter)s,
                    %(guidance_text)s, %(guidance_type)s, %(metric)s,
                    %(target_value)s, %(target_unit)s, %(target_date)s,
                    %(status_by_quarter)s::jsonb, %(evidence_by_quarter)s::jsonb,
                    %(current_status)s, %(current_quarter)s, %(current_evidence_quote)s,
                    %(total_transcripts_traced)s,
                    %(quote_verified)s, %(quote_verification_method)s,
                    NOW()
                )
                ON CONFLICT (symbol, promise_key) DO UPDATE SET
                    status_by_quarter = EXCLUDED.status_by_quarter,
                    evidence_by_quarter = EXCLUDED.evidence_by_quarter,
                    current_status = EXCLUDED.current_status,
                    current_quarter = EXCLUDED.current_quarter,
                    current_evidence_quote = EXCLUDED.current_evidence_quote,
                    total_transcripts_traced = EXCLUDED.total_transcripts_traced,
                    quote_verified = EXCLUDED.quote_verified,
                    quote_verification_method = EXCLUDED.quote_verification_method,
                    updated_at = NOW()
                """,
                {
                    "symbol": symbol.upper(),
                    "promise_key": p["promise_key"],
                    "first_seen_transcript_id": p.get("first_seen_transcript_id"),
                    "first_seen_date": p.get("first_seen_date"),
                    "first_seen_quarter": p.get("first_seen_quarter"),
                    "guidance_text": p.get("guidance_text", ""),
                    "guidance_type": p.get("guidance_type"),
                    "metric": p.get("metric"),
                    "target_value": p.get("target_value"),
                    "target_unit": p.get("target_unit"),
                    "target_date": p.get("target_date"),
                    "status_by_quarter": json.dumps(p.get("status_by_quarter", {})),
                    "evidence_by_quarter": json.dumps(p.get("evidence_by_quarter", {})),
                    "current_status": p.get("current_status"),
                    "current_quarter": p.get("current_quarter"),
                    "current_evidence_quote": p.get("current_evidence_quote"),
                    "total_transcripts_traced": p.get("total_transcripts_traced", 0),
                    "quote_verified": bool(p.get("quote_verified", False)),
                    "quote_verification_method": p.get("quote_verification_method"),
                    "quote_source_by_quarter": json.dumps(p.get("quote_source_by_quarter", {})),
                },
            )
            n += 1
        conn.commit()
        return n
    finally:
        conn.close()


# ── CLI ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", "-s", required=True)
    ap.add_argument("--max-chars", type=int, default=15000,
                    help="Max chars per transcript sent to LLM (default 15000)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Trace but don't persist")
    args = ap.parse_args()

    tracer = NarrativeTracer(args.symbol, max_chars_per_call=args.max_chars)
    promises = tracer.trace()

    # Persist
    if not args.dry_run:
        n = upsert_timeline(args.symbol, promises)
        print(f"\nUpserted {n} promises into management_narrative_timeline for {args.symbol}")
    else:
        print(f"\n[DRY-RUN] Traced {len(promises)} promises for {args.symbol}")

    # Print compact summary
    if promises:
        print(f"\n=== Summary for {args.symbol} ===")
        from collections import Counter
        c = Counter(p.get("current_status") for p in promises)
        for status, n in c.most_common():
            print(f"  {status:<25} {n}")
        print(f"\n=== All promises ===")
        for i, p in enumerate(promises, 1):
            q = p.get("first_seen_quarter", "?")
            txt = (p.get("guidance_text") or "")[:90]
            cur = p.get("current_status", "?")
            cur_q = p.get("current_quarter", "?")
            tv = p.get("target_value")
            tu = p.get("target_unit") or ""
            target = f" → {tv} {tu}".rstrip() if tv is not None else ""
            print(f"  {i}. [{q}] {txt}{target}")
            print(f"     now [{cur_q}]: {cur}")
