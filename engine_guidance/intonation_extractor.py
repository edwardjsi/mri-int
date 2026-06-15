"""
Intonation Extractor — GPT-4o-mini scores management tone per transcript.

Captures 9 dimensions of how management *sounds* on a concall, none of which
are derivable from financials alone:

    confidence, hedging, aggression, transparency, optimism, pessimism,
    accountability, numerical_density, headwind_acknowledged

Each transcript gets one row in management_intonation (UNIQUE on transcript_id).
Extraction is idempotent: re-runs are no-ops unless --force is passed.

Usage:
    from engine_guidance.intonation_extractor import IntonationExtractor
    IntonationExtractor().extract_transcript(transcript_row)
"""

import json
import logging
import os
from datetime import date

from engine_core.db import get_connection
from engine_core.llm_client import get_llm_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("intonation_extractor")


INTONATION_PROMPT = """You are scoring the TONE of management's language in this
earnings-call transcript for {symbol} ({fy_q} of FY{fy}).

Score each dimension on the scale indicated. Use the EXACT JSON shape below —
no commentary, no prose. All scores are integers 0-100 unless noted.

DIMENSIONS (0-100 each):

- confidence: forward-commitment language. High = "we will", "we are committed
  to", "definitely", "without doubt". Low = "we hope", "we wish", silence on
  guidance.

- hedging: conditional / speculative language. High = "may", "could", "we
  anticipate", "subject to", "depending on". Low = declarative language.

- aggression: growth / effort intensity. High = "aggressively expand", "double
  down", "rapid scale-up", "invest aggressively", "push hard". Low = passive
  or contractionary tone.

- transparency: how much they reveal. High = specific numbers given
  unprompted, explicit admission of negatives, named headwinds, reasons for
  misses. Low = vague generalities, deflecting to "macro", no specifics.

- optimism: net positive outlook language. High = bullish phrasing, momentum,
  excitement. Low = muted, cautious.

- pessimism: net negative outlook / caution language. High = explicit worry,
  defensive phrasing, downward guidance. Low = confident, no negatives.

- accountability: first-person ownership vs diffusion of blame. High = "we
  missed", "our execution was poor", "I take responsibility". Low = "market
  conditions caused", "headwinds impacted us", passive constructions.

- numerical_density: integer 0-100 representing fraction of sentences that
  contain a specific number (e.g. "23%", "Rs 1,200 cr", "Q4 FY26"). 100 = every
  sentence has a number. 0 = no numbers anywhere.

- headwind_acknowledged: integer COUNT of distinct headwinds explicitly named
  (e.g. "raw material inflation", "currency headwind", "demand softness",
  "supply chain disruption", "regulatory delays"). 0 = no headwinds named.

Return JSON only:
{{
  "confidence": <int 0-100>,
  "hedging": <int 0-100>,
  "aggression": <int 0-100>,
  "transparency": <int 0-100>,
  "optimism": <int 0-100>,
  "pessimism": <int 0-100>,
  "accountability": <int 0-100>,
  "numerical_density": <int 0-100>,
  "headwind_acknowledged": <int>,
  "headwinds_named": ["<short phrase>", ...],
  "one_line_summary": "<one sentence describing the overall tone>"
}}

Transcript (first 12000 chars):
{transcript_text}"""


class IntonationExtractor:
    def __init__(self):
        self.client, self.model = get_llm_client()

    def score_transcript(self, transcript_text: str, symbol: str, fy_q: str = "", fy: int = 0) -> dict | None:
        """Call GPT-4o-mini, parse JSON response. Returns dict of 9 dims + summary."""
        if not self.client:
            logger.warning("LLM client not available")
            return None
        if not transcript_text or len(transcript_text.strip()) < 500:
            logger.info(f"Skipping {symbol} — transcript too short ({len(transcript_text or '')} chars)")
            return None

        prompt = INTONATION_PROMPT.format(
            symbol=symbol,
            fy_q=fy_q,
            fy=fy,
            transcript_text=transcript_text[:12000],
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a senior equity research analyst scoring management tone. Be objective and consistent across calls."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
            result = json.loads(resp.choices[0].message.content)
            return result
        except Exception as e:
            logger.error(f"Intonation scoring failed for {symbol}: {e}")
            return None

    def extract_transcript(self, transcript_row: dict, force: bool = False) -> bool:
        """Score one transcript and upsert into management_intonation.

        `transcript_row` must contain: id, symbol, date, raw_text
        Returns True if a row was inserted/updated.
        """
        tid = transcript_row["id"]
        sym = transcript_row["symbol"]
        text = transcript_row.get("raw_text") or ""
        dt = transcript_row.get("date")
        fy, fq = (0, 0)
        fy_q = ""
        if dt:
            # Indian fiscal calendar
            m, y = dt.month, dt.year
            if 4 <= m <= 6:    fy, fq = y, 1
            elif 7 <= m <= 9:  fy, fq = y, 2
            elif 10 <= m <= 12: fy, fq = y, 3
            else:               fy, fq = y, 4
            fy_q = f"Q{fq}"

        # Skip if already extracted (idempotent)
        conn = get_connection()
        try:
            cur = conn.cursor()
            if not force:
                cur.execute(
                    "SELECT 1 FROM management_intonation WHERE transcript_id=%s",
                    (tid,),
                )
                if cur.fetchone():
                    logger.debug(f"Skip {sym} transcript {tid} — already extracted")
                    return False
        finally:
            conn.close()

        result = self.score_transcript(text, sym, fy_q=fy_q, fy=fy)
        if not result:
            return False

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO management_intonation
                   (symbol, transcript_id, fiscal_year, fiscal_quarter,
                    confidence, hedging, aggression, transparency,
                    optimism, pessimism, accountability, numerical_density,
                    headwind_acknowledged, raw, extracted_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,NOW())
                   ON CONFLICT (transcript_id) DO UPDATE SET
                    confidence=EXCLUDED.confidence,
                    hedging=EXCLUDED.hedging,
                    aggression=EXCLUDED.aggression,
                    transparency=EXCLUDED.transparency,
                    optimism=EXCLUDED.optimism,
                    pessimism=EXCLUDED.pessimism,
                    accountability=EXCLUDED.accountability,
                    numerical_density=EXCLUDED.numerical_density,
                    headwind_acknowledged=EXCLUDED.headwind_acknowledged,
                    raw=EXCLUDED.raw,
                    extracted_at=NOW()""",
                (
                    sym, tid, fy, fq,
                    _to_pct(result.get("confidence")),
                    _to_pct(result.get("hedging")),
                    _to_pct(result.get("aggression")),
                    _to_pct(result.get("transparency")),
                    _to_pct(result.get("optimism")),
                    _to_pct(result.get("pessimism")),
                    _to_pct(result.get("accountability")),
                    _to_pct(result.get("numerical_density")),
                    int(result.get("headwind_acknowledged", 0) or 0),
                    json.dumps(result),
                ),
            )
            conn.commit()
            logger.info(f"Scored {sym} transcript {tid}: conf={result.get('confidence')} "
                        f"hedg={result.get('hedging')} trans={result.get('transparency')} "
                        f"num_density={result.get('numerical_density')}")
            return True
        finally:
            conn.close()


def _to_pct(v) -> float:
    """Normalize 0-100 or 0-1 score to 0.000-1.000 decimal."""
    if v is None:
        return 0.0
    try:
        f = float(v)
    except (TypeError, ValueError):
        return 0.0
    if f > 1.0:        # 0-100 scale → divide by 100
        f = f / 100.0
    return max(0.0, min(1.0, round(f, 3)))


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", help="Extract for one symbol")
    ap.add_argument("--limit", type=int, default=0, help="Max transcripts to process")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="Re-score even if already extracted")
    args = ap.parse_args()

    conn = get_connection()
    try:
        cur = conn.cursor()
        where = ""
        params = []
        if args.symbol:
            where = "WHERE symbol=%s"
            params.append(args.symbol.upper())
        if not args.force:
            where += " AND id NOT IN (SELECT transcript_id FROM management_intonation)" if where else "WHERE id NOT IN (SELECT transcript_id FROM management_intonation)"
        limit = f"LIMIT {int(args.limit)}" if args.limit else ""
        cur.execute(
            f"SELECT id, symbol, date, raw_text FROM aae_transcripts {where} ORDER BY date DESC {limit}",
            params,
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    print(f"Found {len(rows)} transcripts to score")
    if args.dry_run:
        for r in rows[:10]:
            print(f"  {r['symbol']:12s} {r['date']} ({len(r.get('raw_text') or '')} chars)")
        if len(rows) > 10:
            print(f"  ... and {len(rows) - 10} more")
        return 0

    extractor = IntonationExtractor()
    ok = fail = skip = 0
    for r in rows:
        try:
            did = extractor.extract_transcript(r, force=args.force)
            if did: ok += 1
            else:   skip += 1
        except Exception as e:
            print(f"  FAIL {r['symbol']} {r['date']}: {e}")
            fail += 1
    print(f"\nDone. {ok} scored, {skip} skipped (already extracted), {fail} failed.")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
