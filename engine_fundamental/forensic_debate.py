import logging
from engine_core.llm_client import get_llm_client
import os
from engine_core.db import fetch_df

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ForensicDebateEngine:
    """
    AAE V3 Layers 9 & 10: Institutional Stress Test.
    Provides contrasting Bear and Bull perspectives for final human decision-making.
    """
    
    def __init__(self, symbol):
        self.symbol = symbol.upper()
        self.client, self.model = get_llm_client()

    def run_bear_layer(self, context_data):
        """Layer 9: The Short-Seller / Forensic Bear perspective.

        AAE × Management Integrity (Phase 3, 2026-06-17):
        If management_integrity is present in context_data and indicates a
        poor track record (low credibility score, recent verdict downgrade,
        consecutive missed quarters, verdict flip, or DISTRUSTED narrative
        assessment), the bear MUST factor it into the case. A bull thesis
        that ignores a credibility-broken management is a trap.
        """
        logger.info(f"Starting Layer 9 (Bear) for {self.symbol}...")
        integrity_block = self._integrity_focus_block(context_data, side="bear")
        prompt = f"""
        You are a Short-Seller / Forensic Bear Analyst.
        Context: {context_data}

        {integrity_block}

        Task: Argue why {self.symbol} is a 'Value Trap' or a cyclical peak.
        Constraint: Provide exactly 5 concise bullet points. No introductory or concluding text.
        Focus: Margin risks, valuation extremes, sector fatigue, management integrity concerns, or hidden traps.
        """
        return self.get_llm_response(prompt)

    def run_bull_layer(self, context_data):
        """Layer 10: The Institutional Bull perspective.

        AAE × Management Integrity (Phase 3, 2026-06-17):
        If management_integrity is present in context_data and indicates a
        strong track record (high credibility score, ADD ZONE verdict,
        stable/improving trend, TRUSTED narrative assessment), the bull
        MUST factor it into the case. A clean management track record
        significantly de-risks a rerating thesis.
        """
        logger.info(f"Starting Layer 10 (Bull) for {self.symbol}...")
        integrity_block = self._integrity_focus_block(context_data, side="bull")
        prompt = f"""
        You are an Institutional Bull Analyst.
        Context: {context_data}

        {integrity_block}

        Task: Argue why {self.symbol} is a high-conviction rerating candidate.
        Constraint: Provide exactly 5 concise bullet points. No introductory or concluding text.
        Focus: Structural inflections, narrative momentum, market confirmation leadership, or management credibility strength.
        """
        return self.get_llm_response(prompt)

    @staticmethod
    def _integrity_focus_block(context_data, side: str) -> str:
        """Render the management-integrity summary for the debate prompt.

        Only emits a block when management_integrity is present and
        has_data=True. Returns empty string otherwise so the prompt stays
        clean for fresh symbols with no credibility history.
        """
        mi = (context_data or {}).get("management_integrity")
        if not mi or not mi.get("has_data"):
            return ""

        lines = ["Management Integrity (verified cross-transcript track record):"]
        score = mi.get("credibility_score")
        verdict = mi.get("verdict")
        trend = mi.get("trend")
        cons = mi.get("consecutive_miss_quarters", 0)
        lag = mi.get("lag_score", 0)
        narr = mi.get("narrative_assessment")

        if score is not None and verdict is not None:
            lines.append(f"  - Credibility score: {score:.1f}/100 ({verdict})")
        if trend:
            lines.append(f"  - Trend: {trend}")
        if cons:
            lines.append(f"  - Consecutive missed quarters: {cons} (lag score {lag:.0f}/100)")
        if mi.get("verdict_flipped_recently"):
            lines.append(
                f"  - Verdict recently flipped from {mi.get('previous_verdict')} → {verdict}"
            )
        counts = mi.get("promise_counts") or {}
        actionable = [
            f"{counts.get(k, 0)} {k}" for k in
            ("FULFILLED", "REVISED_UP", "ON_TRACK", "PARTIALLY_FULFILLED",
             "REVISED_DOWN", "MISSED")
            if counts.get(k, 0)
        ]
        if actionable:
            lines.append(f"  - Promise counts: {', '.join(actionable)}")
        if narr:
            lines.append(f"  - Latest LLM credibility assessment: {narr}")

        # Side-specific nudge — explicit but not overbearing.
        if side == "bear":
            lines.append(
                "  -> If credibility is broken or DISTRUSTED, this is a critical "
                "thesis risk you MUST address in your bear case."
            )
        else:
            lines.append(
                "  -> If credibility is strong or TRUSTED, this significantly "
                "de-risks the rerating thesis — cite it directly."
            )

        return "\n".join(lines)

    def get_llm_response(self, prompt, json_mode=False):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": "You are a professional institutional investment analyst."},
                      {"role": "user", "content": prompt}],
            response_format={ "type": "json_object" } if json_mode else None
        )
        return response.choices[0].message.content

if __name__ == "__main__":
    # Test with dummy data
    pass
