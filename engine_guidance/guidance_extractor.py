"""
Guidance Extractor — GPT-4o-mini extracts forward-looking statements from concall transcripts.

Usage:
    python3 -m engine_guidance.guidance_extractor --symbol TCS
"""

import json
import logging
import os
from engine_core.db import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("guidance_extractor")


def get_openai_client():
    """Get OpenAI client — mirrors engine_qualitative.extractor pattern."""
    try:
        from openai import OpenAI
        import httpx
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set")
            return None
        http_client = httpx.Client()
        return OpenAI(api_key=api_key, http_client=http_client)
    except ImportError:
        logger.warning("openai package not installed")
        return None


GUIDANCE_PROMPT = """You are analyzing an earnings call transcript for {symbol}.

Extract ONLY forward-looking statements about FUTURE performance. A forward-looking statement:
- Describes something management expects, plans, targets, or aims to achieve in the FUTURE
- Uses language like "we expect", "we plan", "we target", "we aim", "we will", "we are targeting", "outlook", "pipeline"

CRITICAL RULES:
- DO NOT extract descriptions of CURRENT/Past state (e.g. "revenue is $1.8B" = current state, not a target)
- DO extract directional commitments without specific numbers (e.g. "we expect margin expansion")
- DO extract quantitative targets when stated (e.g. "operating margin of 25%")
- target_value: the FUTURE target number, or null if only directional guidance given
- target_quarter: WHEN management expects this. Extract from transcript. Use Q1FY26/Q2FY26/Q3FY26/Q4FY26 for quarters, FY26 for full year, H1FY26 for half-year, CY2026 for calendar year. If they say "next quarter" and transcript is Q4FY25, use Q1FY26. If "by March 2026", use Q4FY26. If no timeframe, set null.
- Even if management says "we don't give guidance", still extract any forward-looking claims they DO make

For EACH valid statement return:
{{
    "guidance_text": "exact quote or close paraphrase of the FUTURE promise",
    "guidance_type": "MARGIN|REVENUE_GROWTH|CAPEX|DEBT_REDUCTION|CAPACITY_EXPANSION|WORKING_CAPITAL|DIVIDEND|MARKET_SHARE|HIRING|DEAL_PIPELINE|OTHER",
    "metric": "specific metric name",
    "target_value": 8.0,
    "target_unit": "pct|cr|months|units|people|na",
    "target_quarter": "Q4FY26 or null if unspecified",
    "confidence": "low|medium|high",
    "caveats": "any hedges or conditions"
}}

Return JSON: {{"statements": [...]}}. Only include genuine forward-looking commitments.
If none found, return {{"statements": []}}.

Transcript:
{transcript_text}"""


class GuidanceExtractor:
    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
        self.client = get_openai_client()

    def extract_from_transcript(self, transcript_text: str) -> list[dict]:
        if not self.client:
            logger.warning("OpenAI client not available")
            return []

        prompt = GUIDANCE_PROMPT.format(
            symbol=self.symbol, transcript_text=transcript_text[:12000]
        )

        try:
            resp = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an institutional analyst tracking management guidance. Be precise and conservative."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
            result = json.loads(resp.choices[0].message.content)
            statements = result.get("statements", [])
            logger.info(f"Extracted {len(statements)} statements for {self.symbol}")
            return statements
        except Exception as e:
            logger.error(f"GPT extraction failed: {e}")
            return []

    def store_guidance(self, transcript_id: int, statements: list[dict]) -> int:
        if not statements:
            return 0
        conn = get_connection()
        try:
            cur = conn.cursor()
            stored = 0
            for s in statements:
                try:
                    cur.execute(
                        """INSERT INTO public.management_guidance
                        (symbol, transcript_id, guidance_text, guidance_type,
                         metric, target_value, target_unit, target_date, confidence)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (symbol, transcript_id, guidance_text) DO NOTHING""",
                        (self.symbol, transcript_id, s.get("guidance_text", ""),
                         s.get("guidance_type", "OTHER"), s.get("metric"),
                         s.get("target_value"), s.get("target_unit"),
                         s.get("target_quarter"), s.get("confidence", "medium")),
                    )
                    stored += 1
                except Exception:
                    pass
            conn.commit()
            logger.info(f"Stored {stored} statements")
            return stored
        finally:
            conn.close()

    def scan_all_transcripts(self) -> int:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT t.id, t.raw_text FROM public.aae_transcripts t
                   WHERE t.symbol = %s
                     AND t.id NOT IN (SELECT DISTINCT transcript_id
                                      FROM public.management_guidance
                                      WHERE symbol = %s AND transcript_id IS NOT NULL)
                   ORDER BY t.date DESC""",
                (self.symbol, self.symbol),
            )
            transcripts = cur.fetchall()
        finally:
            conn.close()

        processed = 0
        for t in transcripts:
            tid = t[0] if isinstance(t, (list, tuple)) else t["id"]
            ttext = t[1] if isinstance(t, (list, tuple)) else t["raw_text"]
            if not ttext or len(str(ttext).strip()) < 100:
                continue
            statements = self.extract_from_transcript(str(ttext))
            if statements:
                self.store_guidance(tid, statements)
                processed += 1
        return processed


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", "-s", required=True)
    args = ap.parse_args()
    e = GuidanceExtractor(args.symbol)
    n = e.scan_all_transcripts()
    print(f"\nProcessed {n} transcripts for {args.symbol}")
