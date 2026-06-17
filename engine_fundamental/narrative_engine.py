import os
import json
import logging
from engine_core.db import get_connection, fetch_df
from engine_core.llm_client import get_llm_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Credibility context helper ────────────────────────────────────────────
# AAE × Management Integrity (Decision 097 + 2026-06-17 plan, Phase 1).
# Before calling the LLM, fetch the credibility track-record for the symbol
# from management_credibility_scores + management_narrative_timeline so the
# AI can ground its narrative summary in *verifiable* management behavior
# rather than reacting to the most recent transcript in isolation.

_CREDIBILITY_ASSESSMENT_PROMPT_BLOCK = """
Management Track Record (verified across {n_promises} promises tracked over {n_quarters} transcript quarter(s)){track_record_flip_note}:
  Credibility: {credibility_pct} / 100  ({verdict})
  Promise timeline counts: {counts_line}
  Trend: {trend}
  Consecutive missed quarters (latest streak): {cons_miss}

{recent_promises_block}

You MUST also produce a field `management_credibility_assessment` with ONE of:
  - TRUSTED       — track record supports what management is saying; numbers + commitments consistent
  - NEUTRAL       — track record is mixed or insufficient; take narrative at face value but flag uncertainty
  - DISTRUSTED    — track record contradicts what management is saying, or management has missed recent quarters
If no credibility data exists for this symbol, set management_credibility_assessment = "INSUFFICIENT_DATA".
"""


def _fetch_credibility_context(symbol: str) -> dict:
    """Fetch credibility score + recent promise timeline for prompt injection.

    Returns a dict with:
        has_data: bool                 # False if no credibility or timeline rows
        prompt_section: str            # formatted string to inject into LLM prompt
        credibility_pct: float|None    # 0-100 from management_credibility_scores
        verdict: str|None              # ADD ZONE / HOLD ZONE / REDUCE ZONE / THESIS BROKEN / WATCHING
        trend: str|None                # IMPROVING / STABLE / DETERIORATING / INSUFFICIENT_DATA
        consecutive_miss_quarters: int
        verdict_flipped: bool
        previous_verdict: str|None
        recent_promises: list[dict]    # up to 5 most recent actionable promises
    """
    sym = symbol.upper()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """SELECT accuracy_pct, total_promises, achieved_count, missed_count,
                      trend, current_verdict, previous_verdict,
                      consecutive_miss_quarters, lag_score, last_verdict_flip
               FROM management_credibility_scores WHERE symbol = %s""",
            (sym,),
        )
        score_row = cur.fetchone()

        cur.execute(
            """SELECT guidance_text, current_status, current_quarter,
                      target_value, target_unit, target_date, first_seen_quarter
               FROM management_narrative_timeline
               WHERE symbol = %s
                 AND current_status IN ('FULFILLED', 'REVISED_UP', 'ON_TRACK',
                                        'PARTIALLY_FULFILLED', 'REVISED_DOWN', 'MISSED')
               ORDER BY first_seen_quarter DESC
               LIMIT 5""",
            (sym,),
        )
        promise_rows = cur.fetchall()
    finally:
        conn.close()

    if not score_row and not promise_rows:
        return {"has_data": False, "prompt_section": "",
                "credibility_pct": None, "verdict": None, "trend": None,
                "consecutive_miss_quarters": 0, "verdict_flipped": False,
                "previous_verdict": None, "recent_promises": []}

    score_data = None
    if score_row:
        score_data = {
            "accuracy_pct": float(score_row["accuracy_pct"]) if score_row["accuracy_pct"] is not None else None,
            "total_promises": int(score_row["total_promises"] or 0),
            "achieved_count": int(score_row["achieved_count"] or 0),
            "missed_count": int(score_row["missed_count"] or 0),
            "trend": score_row["trend"] or "INSUFFICIENT_DATA",
            "current_verdict": score_row["current_verdict"] or "WATCHING",
            "previous_verdict": score_row["previous_verdict"],
            "consecutive_miss_quarters": int(score_row["consecutive_miss_quarters"] or 0),
            "lag_score": float(score_row["lag_score"]) if score_row["lag_score"] is not None else 0.0,
        }
        score_data["verdict_flipped"] = (
            score_data["previous_verdict"] is not None
            and score_data["previous_verdict"] != score_data["current_verdict"]
        )

    recent_promises = [
        {
            "guidance_text": (p["guidance_text"] or "")[:140],
            "current_status": p["current_status"],
            "current_quarter": p["current_quarter"],
            "first_seen_quarter": p["first_seen_quarter"],
            "target_value": float(p["target_value"]) if p["target_value"] is not None else None,
            "target_unit": p["target_unit"],
            "target_date": p["target_date"],
        }
        for p in promise_rows
    ]

    # Build the prompt section (only when we have BOTH score + at least one
    # actionable promise — otherwise the LLM has too little to ground on).
    if not score_data or not recent_promises:
        return {
            "has_data": bool(score_data or recent_promises),
            "prompt_section": "",
            "credibility_pct": score_data["accuracy_pct"] if score_data else None,
            "verdict": score_data["current_verdict"] if score_data else None,
            "trend": score_data["trend"] if score_data else None,
            "consecutive_miss_quarters": score_data["consecutive_miss_quarters"] if score_data else 0,
            "verdict_flipped": score_data["verdict_flipped"] if score_data else False,
            "previous_verdict": score_data["previous_verdict"] if score_data else None,
            "recent_promises": recent_promises,
        }

    counts_line = (
        f"{score_data['achieved_count']} FULFILLED, "
        f"{score_data['missed_count']} MISSED"
        + (f", {score_data['total_promises'] - score_data['achieved_count'] - score_data['missed_count']} ON_TRACK/PARTIAL"
           if score_data["total_promises"] - score_data["achieved_count"] - score_data["missed_count"] > 0
           else "")
    )

    promises_lines = []
    for p in recent_promises:
        target = ""
        if p["target_value"] is not None:
            target = f" → {p['target_value']}{(' ' + p['target_unit']) if p['target_unit'] else ''}"
        promises_lines.append(
            f'  • "{p["guidance_text"]}"{target} — {p["current_status"]} (in {p["current_quarter"] or p["first_seen_quarter"] or "?"})'
        )

    flip_note = ""
    if score_data["verdict_flipped"]:
        flip_note = f" — ⚠ Verdict recently flipped from {score_data['previous_verdict']} → {score_data['current_verdict']}"

    prompt_section = _CREDIBILITY_ASSESSMENT_PROMPT_BLOCK.format(
        n_promises=score_data["total_promises"],
        n_quarters=len({p["first_seen_quarter"] for p in recent_promises if p["first_seen_quarter"]}),
        track_record_flip_note=flip_note,
        credibility_pct=f"{score_data['accuracy_pct']:.1f}" if score_data["accuracy_pct"] is not None else "n/a",
        verdict=score_data["current_verdict"],
        counts_line=counts_line,
        trend=score_data["trend"],
        cons_miss=score_data["consecutive_miss_quarters"],
        recent_promises_block="\n".join(promises_lines),
    )

    return {
        "has_data": True,
        "prompt_section": prompt_section,
        "credibility_pct": score_data["accuracy_pct"],
        "verdict": score_data["current_verdict"],
        "trend": score_data["trend"],
        "consecutive_miss_quarters": score_data["consecutive_miss_quarters"],
        "verdict_flipped": score_data["verdict_flipped"],
        "previous_verdict": score_data["previous_verdict"],
        "recent_promises": recent_promises,
    }


class NarrativeEngine:
    """
    Analyzes management transcripts to detect structural shifts and narrative divergence.
    AAE Layer 2: Narrative Evolution.

    AAE × Management Integrity (Phase 1, 2026-06-17):
    `analyze_transcript` now pulls the management credibility track-record for the
    symbol and injects it into the LLM prompt. The AI is asked to emit a
    `management_credibility_assessment` (TRUSTED | NEUTRAL | DISTRUSTED) in
    addition to the existing fields. Persisted on aae_narrative_intelligence.
    """

    def __init__(self, symbol):
        self.symbol = symbol.upper()
        self.client, self.model = get_llm_client()

    def get_latest_transcript(self):
        query = "SELECT * FROM aae_transcripts WHERE symbol = %s ORDER BY date DESC LIMIT 1"
        return fetch_df(query, (self.symbol,))

    def analyze_transcript(self, text, date, financial_deltas=None):
        if not self.client:
            logger.warning("OpenAI client not available for narrative analysis.")
            return None

        # ── Pull credibility context (Phase 1) ────────────────────────
        cred = _fetch_credibility_context(self.symbol)
        cred_block = cred["prompt_section"] if cred["has_data"] else ""

        prompt = f"""
        Analyze the following earnings call transcript for {self.symbol}.
        Financial Inflections Detected (Deterministic): {json.dumps(financial_deltas)}

        {cred_block}

        Extract:
        1. sentiment_score (0.0-1.0, 0.5 neutral)
        2. key_themes (list of strings)
        3. numeric_divergence (Is management more bullish or cautious than the numbers suggest? -1.0 to +1.0)
        4. ceo_confidence (low|medium|high)
        5. narrative_delta (numeric 0.0-1.0: How much has the story changed since the last quarter?)
        6. summary (2 sentence institutional overview)
        7. management_credibility_assessment (TRUSTED | NEUTRAL | DISTRUSTED | INSUFFICIENT_DATA) — base this on the Management Track Record block above. If no track record is shown, output "INSUFFICIENT_DATA".
        """

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an institutional equity analyst specializing in structural business inflections."},
                    {"role": "user", "content": prompt + "\n\nTranscript Snippet:\n" + text[:15000]}
                ],
                temperature=0,
                response_format={ "type": "json_object" }
            )
            analysis = json.loads(resp.choices[0].message.content)
            # Persist with the credibility context we injected (for audit trail).
            self.store_analysis(date, analysis, cred=cred)
            return analysis
        except Exception as e:
            logger.error(f"Failed to analyze narrative for {self.symbol}: {e}")
            return None

    def store_analysis(self, date, analysis, cred=None):
        if not analysis: return

        cred_assessment = analysis.get("management_credibility_assessment")
        cred_score_at_analysis = None
        if cred and cred.get("has_data"):
            cred_score_at_analysis = cred.get("credibility_pct")
            # Fallback: if LLM didn't emit the field but we have data, default to NEUTRAL.
            if not cred_assessment:
                cred_assessment = "NEUTRAL"
        elif not cred_assessment:
            cred_assessment = "INSUFFICIENT_DATA"

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO public.aae_narrative_intelligence (
                symbol, date, sentiment_score, key_themes,
                numeric_divergence_score, ceo_confidence_level,
                summary, narrative_delta,
                credibility_assessment, credibility_score_at_analysis
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, date) DO UPDATE SET
                sentiment_score = EXCLUDED.sentiment_score,
                key_themes = EXCLUDED.key_themes,
                numeric_divergence_score = EXCLUDED.numeric_divergence_score,
                ceo_confidence_level = EXCLUDED.ceo_confidence_level,
                summary = EXCLUDED.summary,
                narrative_delta = EXCLUDED.narrative_delta,
                credibility_assessment = EXCLUDED.credibility_assessment,
                credibility_score_at_analysis = EXCLUDED.credibility_score_at_analysis,
                updated_at = NOW()
        """, (
            self.symbol, date, analysis.get('sentiment_score'),
            analysis.get('key_themes'), analysis.get('numeric_divergence'),
            analysis.get('ceo_confidence'), analysis.get('summary'),
            analysis.get('narrative_delta'),
            cred_assessment, cred_score_at_analysis,
        ))

        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Stored narrative analysis for {self.symbol} on {date} (credibility_assessment={cred_assessment})")

if __name__ == "__main__":
    # Mock test
    import datetime
    engine = NarrativeEngine("TCS")
    mock_text = "We are seeing a massive structural shift in AI spending. Our order pipeline is at an all-time high."
    # result = engine.analyze_transcript(mock_text, datetime.date.today())
    # print(result)
