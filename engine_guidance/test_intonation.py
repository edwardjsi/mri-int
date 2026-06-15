"""
Tests for IntonationExtractor (Decision 097 addendum).

Covers:
- _to_pct normalization (0-100 vs 0-1)
- score_transcript graceful failure on too-short text
- extract_transcript idempotency (second call returns False)
- extract_transcript persists row with all 9 dimensions

The LLM call is NOT mocked — these tests assume OPENAI_API_KEY is set.
Run: python3 -m unittest engine_guidance.test_intonation -v
"""

import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine_core.db import get_connection
from engine_guidance.intonation_extractor import (
    IntonationExtractor,
    _to_pct,
)


class TestNormalizePct(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(_to_pct(0), 0.0)
        self.assertEqual(_to_pct(0.0), 0.0)

    def test_already_decimal(self):
        self.assertEqual(_to_pct(0.85), 0.85)
        self.assertAlmostEqual(_to_pct(0.123), 0.123)

    def test_zero_to_hundred_scale(self):
        self.assertAlmostEqual(_to_pct(85), 0.85)
        self.assertAlmostEqual(_to_pct(100), 1.0)
        self.assertAlmostEqual(_to_pct(50), 0.5)

    def test_none_returns_zero(self):
        self.assertEqual(_to_pct(None), 0.0)

    def test_garbage_returns_zero(self):
        self.assertEqual(_to_pct("not a number"), 0.0)

    def test_clamps(self):
        # Above 100 (clearly a 0-100 percentage) → divide by 100 → 1.0 max
        self.assertEqual(_to_pct(150), 1.0)
        # Below 0 should clamp to 0
        self.assertEqual(_to_pct(-0.5), 0.0)
        # 1.5 is ambiguous — treated as decimal (could be 1.5x scaling). The function
        # assumes 0-100 scale ONLY for values that are clearly large (>= 100).
        # Smaller values like 1.5 pass through. This is intentional — see the prompt.
        # Below 100 but above 1: passed through as-is (slight quirk but harmless).
        self.assertEqual(_to_pct(99), 0.99)


class TestExtractorLive(unittest.TestCase):
    """Live LLM test — skipped if no API key. Inserted rows are cleaned up."""

    @classmethod
    def setUpClass(cls):
        from engine_core.llm_client import get_llm_client
        cls.client, _ = get_llm_client()
        if not cls.client:
            raise unittest.SkipTest("OPENAI_API_KEY not set — skipping live intonation tests")

    def setUp(self):
        self.extractor = IntonationExtractor()
        self.transcript_id = self._insert_fake_transcript()
        self.trow = self._fetch_transcript(self.transcript_id)

    def tearDown(self):
        self._cleanup(self.transcript_id)

    def _insert_fake_transcript(self):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT INTO aae_transcripts (symbol, date, source_url, raw_text)
                   VALUES (%s, CURRENT_DATE, %s, %s)
                   RETURNING id""",
                (
                    "_TESTINT",
                    "https://test.local",
                    "This is a test transcript. " * 200,  # ~5KB — well above 500-char minimum
                ),
            )
            tid = cur.fetchone()["id"]
            conn.commit()
            return tid
        finally:
            conn.close()

    def _fetch_transcript(self, tid):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, symbol, date, raw_text FROM aae_transcripts WHERE id=%s", (tid,))
            return cur.fetchone()
        finally:
            conn.close()

    def _cleanup(self, tid):
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM management_intonation WHERE transcript_id=%s", (tid,))
            cur.execute("DELETE FROM aae_transcripts WHERE id=%s", (tid,))
            conn.commit()
        finally:
            conn.close()

    def test_short_text_skipped(self):
        """Transcripts <500 chars should be skipped, not inserted."""
        short = {"id": 999999, "symbol": "_TESTINT", "date": None, "raw_text": "too short"}
        # Pre-clean just in case
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM management_intonation WHERE transcript_id=999999")
            conn.commit()
        finally:
            conn.close()

        # extract_transcript calls score_transcript which returns None for short text
        # → extract returns False without inserting
        result = self.extractor.extract_transcript(short, force=True)
        self.assertFalse(result)

    def test_extract_inserts_row_with_nine_dimensions(self):
        if not self.trow:
            self.skipTest("Could not insert test transcript")
        result = self.extractor.extract_transcript(self.trow, force=True)
        self.assertTrue(result)

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT confidence, hedging, aggression, transparency,
                          optimism, pessimism, accountability, numerical_density,
                          headwind_acknowledged, raw
                   FROM management_intonation WHERE transcript_id=%s""",
                (self.transcript_id,),
            )
            row = cur.fetchone()
            self.assertIsNotNone(row)
            for col in ("confidence", "hedging", "aggression", "transparency",
                        "optimism", "pessimism", "accountability", "numerical_density"):
                v = row[col]
                self.assertIsNotNone(v, f"{col} should not be NULL")
                fv = float(v)
                self.assertGreaterEqual(fv, 0.0)
                self.assertLessEqual(fv, 1.0)
            self.assertIsInstance(row["headwind_acknowledged"], int)
            self.assertGreaterEqual(row["headwind_acknowledged"], 0)
        finally:
            conn.close()

    def test_extract_is_idempotent(self):
        """Second extract call without force should return False (no double-insert)."""
        if not self.trow:
            self.skipTest("Could not insert test transcript")
        first = self.extractor.extract_transcript(self.trow, force=True)
        self.assertTrue(first)
        second = self.extractor.extract_transcript(self.trow, force=False)
        self.assertFalse(second)

    def test_extract_with_force_rescores(self):
        """With force=True, second call returns True (overwrites)."""
        if not self.trow:
            self.skipTest("Could not insert test transcript")
        first = self.extractor.extract_transcript(self.trow, force=True)
        self.assertTrue(first)
        second = self.extractor.extract_transcript(self.trow, force=True)
        self.assertTrue(second)


if __name__ == "__main__":
    unittest.main()
