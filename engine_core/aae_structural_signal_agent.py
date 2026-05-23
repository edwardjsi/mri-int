"""AAE Structural Signal Agent.

Maps qualitative events to six structural improvement signals and
quantifies conviction. Maintains rolling 3-5 year signal history.

The six signals:
  Margin Quality, TAM Expansion, Backward Integration,
  Forward Integration, Moat Strengthening, Geographic Expansion

Usage:
    python engine_core/aae_structural_signal_agent.py --symbol RELIANCE
"""

from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Any

from engine_core.db import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("aae_structural_signal")

# ---------------------------------------------------------------------------
# Event type → Signal mapping
# ---------------------------------------------------------------------------

EVENT_TO_SIGNAL: dict[str, str] = {
    # Margin Quality signals
    "COST_OPTIMIZATION":      "MARGIN_QUALITY",
    "CAPITAL_ALLOCATION":     "MARGIN_QUALITY",  # buybacks/dividends = capital discipline

    # TAM Expansion signals
    "NEW_PRODUCT_SEGMENT":    "TAM_EXPANSION",
    "CAPACITY_ADDITION":      "TAM_EXPANSION",
    "GREENFIELD_EXPANSION":   "TAM_EXPANSION",
    "BROWNFIELD_EXPANSION":   "TAM_EXPANSION",

    # Backward Integration
    "BACKWARD_INTEGRATION":   "BACKWARD_INTEGRATION",

    # Forward Integration
    "FORWARD_INTEGRATION":    "FORWARD_INTEGRATION",

    # Moat Strengthening
    "MOAT_STRENGTHENING":     "MOAT_STRENGTHENING",

    # Geographic Expansion
    "GEOGRAPHIC_EXPANSION":   "GEOGRAPHIC_EXPANSION",
}

SIGNAL_DESCRIPTIONS = {
    "MARGIN_QUALITY":         "Structural margin improvement through cost optimization, operating leverage, or capital discipline",
    "TAM_EXPANSION":          "Expanding addressable market via new products, segments, or capacity",
    "BACKWARD_INTEGRATION":   "Moving upstream in the value chain — raw material security, in-house production",
    "FORWARD_INTEGRATION":    "Moving closer to end customers — D2C, branded retail, own distribution",
    "MOAT_STRENGTHENING":     "Strengthening competitive position — patents, brand, network effects, tech moat",
    "GEOGRAPHIC_EXPANSION":   "Entering new countries or regions with concrete timelines and investments",
}

# Window for "active" signals (months)
SIGNAL_ACTIVE_WINDOW_MONTHS = 18
HIGH_CONVICTION_MIN_SIGNALS = 4
HIGH_CONVICTION_MIN_STRENGTH = 0.4


class StructuralSignalAgent:
    """Maps AAE events to the six structural signals and computes conviction."""

    def __init__(self, symbol: str):
        self.symbol = symbol.upper()

    def evaluate(self) -> dict[str, Any]:
        """Compute the six-signal vector and structural conviction score.

        Returns:
            dict with signal_vector, conviction_score, high_conviction flag,
            justifications, and timestamp.
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                # Fetch events within the active window
                window_start = date.today() - timedelta(days=SIGNAL_ACTIVE_WINDOW_MONTHS * 30)

                cur.execute(
                    """
                    SELECT event_type, confidence, event_date, description
                    FROM public.aae_events
                    WHERE symbol = %s
                      AND (event_date IS NULL OR event_date >= %s)
                    ORDER BY event_date DESC NULLS LAST
                    """,
                    (self.symbol, window_start),
                )
                events = [dict(row) for row in cur.fetchall()]

            if not events:
                return self._empty_result("no events in active window")

            # Map events to signals and accumulate strengths
            signal_strengths: dict[str, list[float]] = {s: [] for s in SIGNAL_DESCRIPTIONS}
            signal_evidence: dict[str, list[str]] = {s: [] for s in SIGNAL_DESCRIPTIONS}

            for event in events:
                event_type = event["event_type"]
                signal = EVENT_TO_SIGNAL.get(event_type)
                if signal is None:
                    continue

                confidence = float(event["confidence"]) if event["confidence"] else 0.5
                signal_strengths[signal].append(confidence)
                if event["description"]:
                    signal_evidence[signal].append(str(event["description"])[:200])

            # Compute signal scores (0-1)
            signal_vector = {}
            for signal_name in SIGNAL_DESCRIPTIONS:
                strengths = signal_strengths[signal_name]
                if not strengths:
                    signal_vector[signal_name] = 0.0
                else:
                    # Weighted: more events = higher conviction, capped at 1.0
                    count_bonus = min(len(strengths) / 3.0, 1.0)  # saturates at 3 events
                    avg_strength = sum(strengths) / len(strengths)
                    signal_vector[signal_name] = round(min(avg_strength * (0.6 + 0.4 * count_bonus), 1.0), 2)

            # Count active signals above threshold
            active_signals = [
                name for name, score in signal_vector.items()
                if score >= HIGH_CONVICTION_MIN_STRENGTH
            ]
            active_count = len(active_signals)

            # Structural conviction score (0-100)
            conviction_score = round(sum(signal_vector.values()) / len(signal_vector) * 100, 1)

            # High conviction if 4+ signals active
            high_conviction = active_count >= HIGH_CONVICTION_MIN_SIGNALS

            # Build justifications
            justifications = []
            for signal_name in SIGNAL_DESCRIPTIONS:
                score = signal_vector[signal_name]
                if score > 0:
                    evidence = signal_evidence[signal_name]
                    justifications.append({
                        "signal": signal_name,
                        "score": score,
                        "description": SIGNAL_DESCRIPTIONS[signal_name],
                        "events_found": len(signal_strengths[signal_name]),
                        "sample_evidence": evidence[:3],
                    })

            return {
                "symbol": self.symbol,
                "timestamp": str(date.today()),
                "signal_vector": signal_vector,
                "conviction_score": conviction_score,
                "active_signals": active_signals,
                "active_count": active_count,
                "high_conviction": high_conviction,
                "total_events_analyzed": len(events),
                "justifications": justifications,
                "verdict": self._verdict(conviction_score, high_conviction, active_count),
            }

        finally:
            conn.close()

    def _empty_result(self, reason: str) -> dict:
        return {
            "symbol": self.symbol,
            "timestamp": str(date.today()),
            "signal_vector": {s: 0.0 for s in SIGNAL_DESCRIPTIONS},
            "conviction_score": 0.0,
            "active_signals": [],
            "active_count": 0,
            "high_conviction": False,
            "total_events_analyzed": 0,
            "justifications": [],
            "verdict": f"INSUFFICIENT — {reason}",
        }

    def _verdict(self, score: float, high_conviction: bool, active_count: int) -> str:
        if high_conviction:
            return f"HIGH CONVICTION — {active_count}/6 structural signals active ({score:.0f}/100)"
        elif score >= 50:
            return f"EMERGING — {active_count}/6 signals active ({score:.0f}/100)"
        elif score >= 25:
            return f"MONITORING — {active_count}/6 signals active ({score:.0f}/100)"
        else:
            return f"NO CONVICTION — {active_count}/6 signals, insufficient structural evidence"


def main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="AAE Structural Signal Agent")
    parser.add_argument("--symbol", required=True, help="Ticker symbol")
    args = parser.parse_args()

    agent = StructuralSignalAgent(args.symbol)
    result = agent.evaluate()
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
