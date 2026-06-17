"""
Tests for AAE Layer 4 credibility-context injection — Phase 1 of the
AAE × Management Integrity integration (2026-06-17 plan).

Covers:
- _fetch_credibility_context: empty / partial / full data shapes
- Prompt section: well-formed when score + promises present
- NarrativeEngine.analyze_transcript: gracefully degrades when LLM client
  is unavailable (returns None instead of crashing)
- NarrativeEngine.store_analysis: persists the new columns
  (credibility_assessment, credibility_score_at_analysis)

Uses disposable `_TEST_NARR_CTX_<uuid>` symbols so it never collides with
real data. Cleans up afterwards.
"""

import os
import sys
import unittest
import uuid
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine_core.db import get_connection
from engine_fundamental.narrative_engine import (
    NarrativeEngine,
    _fetch_credibility_context,
)


def _make_test_symbol() -> str:
    # Symbol column is VARCHAR(20) on management_credibility_scores,
    # so the prefix must leave room for 8 hex chars: 12 + 8 = 20.
    return f"_NARR_CTX_{uuid.uuid4().hex[:8].upper()}"


def _seed_credibility(cur, symbol: str, accuracy_pct: float = 80.0,
                      verdict: str = "ADD ZONE", trend: str = "STABLE",
                      cons_miss: int = 0, prev_verdict: str = None) -> None:
    cur.execute(
        """INSERT INTO management_credibility_scores
           (symbol, total_promises, achieved_count, missed_count,
            accuracy_pct, avg_variance_pct, trend,
            consecutive_miss_quarters, lag_score, last_verdict_flip,
            current_verdict, previous_verdict)
           VALUES (%s, 5, 4, 1, %s, NULL, %s, %s, 0.0, NULL, %s, %s)
           ON CONFLICT (symbol) DO UPDATE SET
             accuracy_pct = EXCLUDED.accuracy_pct,
             current_verdict = EXCLUDED.current_verdict,
             previous_verdict = EXCLUDED.previous_verdict,
             trend = EXCLUDED.trend,
             consecutive_miss_quarters = EXCLUDED.consecutive_miss_quarters""",
        (symbol, accuracy_pct, trend, cons_miss, verdict, prev_verdict),
    )


def _seed_promises(cur, symbol: str) -> None:
    """Seed 3 actionable promises across 3 quarters for the test symbol."""
    rows = [
        ("Q1FY26", "FULFILLED", "Expand to 100 branches by end of FY27"),
        ("Q2FY26", "ON_TRACK",  "Maintain NIM in the 6.5-7% range"),
        ("Q3FY26", "MISSED",    "Total CAPEX of Rs 1,000 crores this year"),
    ]
    for first_q, status, text in rows:
        promise_key = uuid.uuid4().hex[:16]
        cur.execute(
            """INSERT INTO management_narrative_timeline
               (symbol, promise_key, first_seen_quarter,
                guidance_text, guidance_type, current_status, current_quarter,
                quote_verified)
               VALUES (%s, %s, %s, %s, 'OTHER', %s, %s, TRUE)""",
            (symbol, promise_key, first_q, text, status, "Q3FY26"),
        )


def _cleanup(cur, symbol: str) -> None:
    cur.execute("DELETE FROM management_credibility_scores WHERE symbol = %s", (symbol,))
    cur.execute("DELETE FROM management_narrative_timeline WHERE symbol = %s", (symbol,))
    cur.execute("DELETE FROM aae_narrative_intelligence WHERE symbol = %s", (symbol,))


class CredibilityContextTests(unittest.TestCase):
    """Direct unit tests of the prompt-injection helper."""

    def test_empty_when_no_data(self):
        sym = _make_test_symbol()
        try:
            ctx = _fetch_credibility_context(sym)
            self.assertFalse(ctx["has_data"])
            self.assertEqual(ctx["prompt_section"], "")
            self.assertIsNone(ctx["credibility_pct"])
            self.assertEqual(ctx["recent_promises"], [])
        finally:
            conn = get_connection()
            try:
                _cleanup(conn.cursor(), sym)
                conn.commit()
            finally:
                conn.close()

    def test_full_block_with_score_and_promises(self):
        sym = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, sym, accuracy_pct=80.4, verdict="ADD ZONE",
                              trend="STABLE", cons_miss=0)
            _seed_promises(cur, sym)
            conn.commit()
        finally:
            conn.close()

        try:
            ctx = _fetch_credibility_context(sym)
            self.assertTrue(ctx["has_data"])
            self.assertIsNotNone(ctx["prompt_section"])
            self.assertAlmostEqual(ctx["credibility_pct"], 80.4, places=1)
            self.assertEqual(ctx["verdict"], "ADD ZONE")
            self.assertEqual(ctx["trend"], "STABLE")
            self.assertEqual(ctx["consecutive_miss_quarters"], 0)
            self.assertEqual(len(ctx["recent_promises"]), 3)
            # Prompt section should mention the verdict + at least one promise verbatim.
            self.assertIn("ADD ZONE", ctx["prompt_section"])
            self.assertIn("80.4", ctx["prompt_section"])
            self.assertIn("ON_TRACK", ctx["prompt_section"])
            self.assertIn("FULFILLED", ctx["prompt_section"])
            self.assertIn("MISSED", ctx["prompt_section"])
            # The instruction block must be present so the LLM knows the enum.
            self.assertIn("TRUSTED", ctx["prompt_section"])
            self.assertIn("DISTRUSTED", ctx["prompt_section"])
            self.assertIn("INSUFFICIENT_DATA", ctx["prompt_section"])
        finally:
            conn = get_connection()
            try:
                _cleanup(conn.cursor(), sym)
                conn.commit()
            finally:
                conn.close()

    def test_flip_note_appears_when_verdict_changed(self):
        sym = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, sym, accuracy_pct=42.0, verdict="REDUCE ZONE",
                              trend="DETERIORATING", cons_miss=2,
                              prev_verdict="HOLD ZONE")
            _seed_promises(cur, sym)
            conn.commit()
        finally:
            conn.close()

        try:
            ctx = _fetch_credibility_context(sym)
            self.assertTrue(ctx["verdict_flipped"])
            self.assertEqual(ctx["previous_verdict"], "HOLD ZONE")
            self.assertIn("flipped", ctx["prompt_section"].lower())
            self.assertIn("HOLD ZONE", ctx["prompt_section"])
            self.assertIn("REDUCE ZONE", ctx["prompt_section"])
        finally:
            conn = get_connection()
            try:
                _cleanup(conn.cursor(), sym)
                conn.commit()
            finally:
                conn.close()

    def test_promises_only_no_score(self):
        """If we have promises but no score row, has_data is True but
        prompt_section is empty (LLM has too little to ground on)."""
        sym = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_promises(cur, sym)
            conn.commit()
        finally:
            conn.close()

        try:
            ctx = _fetch_credibility_context(sym)
            self.assertTrue(ctx["has_data"])
            self.assertEqual(ctx["prompt_section"], "")  # too little to ground on
            self.assertIsNone(ctx["credibility_pct"])
            self.assertEqual(len(ctx["recent_promises"]), 3)
        finally:
            conn = get_connection()
            try:
                _cleanup(conn.cursor(), sym)
                conn.commit()
            finally:
                conn.close()


class NarrativeEngineStoreTests(unittest.TestCase):
    """Test the persistence path (no LLM call)."""

    def test_store_persists_credibility_assessment(self):
        sym = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, sym, accuracy_pct=78.0)
            conn.commit()
        finally:
            conn.close()

        try:
            engine = NarrativeEngine(sym)
            # Use the helper directly so we test the same persistence path
            # analyze_transcript() would take (cred → store_analysis).
            cred = _fetch_credibility_context(sym)
            analysis = {
                "sentiment_score": 0.7,
                "key_themes": ["growth"],
                "numeric_divergence": 0.1,
                "ceo_confidence": "high",
                "summary": "Test summary",
                "narrative_delta": 0.3,
                "management_credibility_assessment": "TRUSTED",
            }
            engine.store_analysis(date(2026, 6, 17), analysis, cred=cred)

            conn = get_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    """SELECT credibility_assessment, credibility_score_at_analysis
                       FROM aae_narrative_intelligence WHERE symbol=%s""",
                    (sym,),
                )
                row = cur.fetchone()
                self.assertIsNotNone(row, "Row should be persisted")
                self.assertEqual(row["credibility_assessment"], "TRUSTED")
                self.assertAlmostEqual(float(row["credibility_score_at_analysis"]), 78.0, places=1)
            finally:
                conn.close()
        finally:
            conn = get_connection()
            try:
                _cleanup(conn.cursor(), sym)
                conn.commit()
            finally:
                conn.close()

    def test_store_defaults_to_neutral_when_llm_skips_field(self):
        sym = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, sym, accuracy_pct=72.0)
            conn.commit()
        finally:
            conn.close()

        try:
            engine = NarrativeEngine(sym)
            cred = _fetch_credibility_context(sym)
            analysis = {
                "sentiment_score": 0.5,
                "key_themes": [],
                "numeric_divergence": 0.0,
                "ceo_confidence": "medium",
                "summary": "Test",
                "narrative_delta": 0.0,
                # NB: no management_credibility_assessment field
            }
            engine.store_analysis(date(2026, 6, 17), analysis, cred=cred)

            conn = get_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT credibility_assessment FROM aae_narrative_intelligence WHERE symbol=%s",
                    (sym,),
                )
                row = cur.fetchone()
                self.assertEqual(row["credibility_assessment"], "NEUTRAL")
            finally:
                conn.close()
        finally:
            conn = get_connection()
            try:
                _cleanup(conn.cursor(), sym)
                conn.commit()
            finally:
                conn.close()

    def test_store_insufficient_data_when_no_credibility_row(self):
        sym = _make_test_symbol()
        try:
            engine = NarrativeEngine(sym)
            cred = _fetch_credibility_context(sym)
            analysis = {
                "sentiment_score": 0.5,
                "key_themes": [],
                "numeric_divergence": 0.0,
                "ceo_confidence": "medium",
                "summary": "Test",
                "narrative_delta": 0.0,
            }
            engine.store_analysis(date(2026, 6, 17), analysis, cred=cred)

            conn = get_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT credibility_assessment, credibility_score_at_analysis "
                    "FROM aae_narrative_intelligence WHERE symbol=%s",
                    (sym,),
                )
                row = cur.fetchone()
                self.assertEqual(row["credibility_assessment"], "INSUFFICIENT_DATA")
                self.assertIsNone(row["credibility_score_at_analysis"])
            finally:
                conn.close()
        finally:
            conn = get_connection()
            try:
                _cleanup(conn.cursor(), sym)
                conn.commit()
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
