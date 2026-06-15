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


from engine_core.llm_client import get_llm_client


GUIDANCE_PROMPT = """You are analyzing an earnings call transcript for {symbol}.

Extract ONLY forward-looking statements about FUTURE performance that have:
1. A QUANTITATIVE TARGET (a number): e.g. "revenue of Rs 1,200 cr", "margin of 25%", "20% revenue growth"
2. A defined TIMEFRAME: e.g. "by Q4FY26", "in FY26", "next year"

CRITICAL EXCLUSION RULES — DO NOT extract:
- Vague directional statements with no numbers: "we expect margin expansion", "we see good demand", "we are optimistic", "gearing up for growth", "future looks exciting", "we aim to capitalize" → EXCLUDE
- Descriptions of current/past state: "revenue is X", "we delivered Y" → EXCLUDE
- Aspirational statements without numbers or timeframes: "looking to scale meaningfully over 3 years" → EXCLUDE
- Product/technology statements: "developing next-gen products", "aligning with industry requirements" → EXCLUDE

INCLUDE ONLY if ALL THREE are present:
- Quantitative target (a specific number or %)
- Clear timeframe (quarter/year)
- A specific metric (revenue, margin, orders, etc.)

For EACH valid statement return:
{{
    "guidance_text": "concise paraphrase of what was promised",
    "guidance_type": "MARGIN|REVENUE_GROWTH|CAPEX|DEBT_REDUCTION|CAPACITY_EXPANSION|WORKING_CAPITAL|DIVIDEND|MARKET_SHARE|HIRING|DEAL_PIPELINE|OTHER",
    "metric": "specific metric name",
    "target_value": 8.5,
    "target_unit": "pct|crore|rs_cr|bps|units",
    "target_quarter": "Q4FY26",
    "confidence": "low|medium|high"
}}

Return JSON: {{"statements": [...]}}. Only output genuine quantitative commitments.
If none found, return {{"statements": []}}.

Transcript:
{transcript_text}"""


class GuidanceExtractor:
    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
        self.client, self.model = get_llm_client()

    def extract_from_transcript(self, transcript_text: str) -> list[dict]:
        if not self.client:
            logger.warning("OpenAI client not available")
            return []

        prompt = GUIDANCE_PROMPT.format(
            symbol=self.symbol, transcript_text=transcript_text[:12000]
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
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
