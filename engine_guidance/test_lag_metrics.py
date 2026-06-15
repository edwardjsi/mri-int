"""
Tests for ConvictionEngine lag metrics — Decision 097.

Covers:
- _compute_lag_metrics: streak counting across fiscal-quarter order
- _zone_for: zone classification per Decision 097 thresholds
- compute_score: end-to-end storage of new columns (consecutive_miss_quarters,
  lag_score, current_verdict, previous_verdict, last_verdict_flip)

Uses a disposable test symbol `_TEST_LAG_<random>` so it never collides with
real data. Each test inserts controlled verification rows, runs the scorer,
and cleans up afterwards.
"""

import os
import sys
import unittest
import uuid

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine_core.db import get_connection
from engine_guidance.credibility_scorer import CredibilityScorer


def _make_test_symbol() -> str:
    """Unique symbol per test run to avoid colliding with real data.

    UPPERCASE because CredibilityScorer.compute_score uppercases input and
    queries with `g.symbol = %s` — a mismatch would silently return 0 rows.
    """
    return f"_TESTLAG_{uuid.uuid4().hex[:8].upper()}"


def _insert_guidance_rows(cur, symbol: str, n: int) -> list:
    """Insert n management_guidance rows; return list of ids."""
    ids = []
    for i in range(n):
        cur.execute(
            """INSERT INTO management_guidance
               (symbol, transcript_id, guidance_text, guidance_type,
                target_value, target_unit, target_date, confidence)
               VALUES (%s, NULL, %s, 'MARGIN', 20.0, '%%', 'Q1FY27', 'HIGH')
               RETURNING id""",
            (symbol, f"Test promise {i} for {symbol}"),
        )
        ids.append(cur.fetchone()["id"])
    return ids


def _insert_verification(cur, guidance_id: int, fy: int, fq: int, status: str):
    """Insert a guidance_verification row."""
    cur.execute(
        """INSERT INTO guidance_verification
           (guidance_id, checked_fiscal_year, checked_fiscal_quarter,
            actual_value, status, variance_pct)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (guidance_id, fy, fq, 18.0, status, -10.0),
    )


def _cleanup(symbol: str):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM guidance_verification WHERE guidance_id IN "
            "(SELECT id FROM management_guidance WHERE symbol=%s)",
            (symbol,),
        )
        cur.execute("DELETE FROM management_guidance WHERE symbol=%s", (symbol,))
        cur.execute(
            "DELETE FROM management_credibility_scores WHERE symbol=%s", (symbol,)
        )
        conn.commit()
    finally:
        conn.close()


class TestZoneClassification(unittest.TestCase):
    """Pure-function tests for the zone decision logic."""

    def setUp(self):
        self.s = CredibilityScorer()

    def test_watching_below_threshold(self):
        self.assertEqual(self.s._zone_for(80.0, "IMPROVING", 2), "WATCHING")
        self.assertEqual(self.s._zone_for(0.0, "INSUFFICIENT_DATA", 0), "WATCHING")

    def test_add_zone_requires_stable_trend(self):
        self.assertEqual(self.s._zone_for(80.0, "IMPROVING", 5), "ADD ZONE")
        self.assertEqual(self.s._zone_for(80.0, "STABLE", 5), "ADD ZONE")
        # 80% with deteriorating trend drops to HOLD
        self.assertEqual(self.s._zone_for(80.0, "DETERIORATING", 5), "HOLD ZONE")

    def test_hold_zone_thresholds(self):
        self.assertEqual(self.s._zone_for(70.0, "STABLE", 5), "HOLD ZONE")
        self.assertEqual(self.s._zone_for(60.0, "STABLE", 5), "HOLD ZONE")
        # 60 with DETERIORATING is still HOLD (zone doesn't drop just for trend)
        self.assertEqual(self.s._zone_for(60.0, "DETERIORATING", 5), "HOLD ZONE")

    def test_reduce_zone(self):
        self.assertEqual(self.s._zone_for(50.0, "STABLE", 5), "REDUCE ZONE")
        self.assertEqual(self.s._zone_for(40.0, "STABLE", 5), "REDUCE ZONE")

    def test_thesis_broken(self):
        self.assertEqual(self.s._zone_for(30.0, "STABLE", 5), "THESIS BROKEN")
        self.assertEqual(self.s._zone_for(0.0, "STABLE", 5), "THESIS BROKEN")


class TestLagMetrics(unittest.TestCase):
    """Integration test: insert controlled verification rows then read lag."""

    def setUp(self):
        self.scorer = CredibilityScorer()
        self.symbol = _make_test_symbol()
        self._inserted_ids: list = []

    def tearDown(self):
        _cleanup(self.symbol)

    def _seed(self, rows: list[tuple[int, int, str]]):
        """rows = list of (fiscal_year, fiscal_quarter, status)."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            gids = _insert_guidance_rows(cur, self.symbol, len(rows))
            for gid, (fy, fq, status) in zip(gids, rows):
                _insert_verification(cur, gid, fy, fq, status)
            conn.commit()
            self._inserted_ids = gids
        finally:
            conn.close()

    def test_no_misses_returns_zero_streak(self):
        # All ACHIEVED → streak = 0
        self._seed([(2026, 1, "ACHIEVED"), (2026, 2, "ACHIEVED"), (2025, 4, "ACHIEVED")])
        result = self.scorer.compute_score(self.symbol)
        self.assertEqual(result["consecutive_miss_quarters"], 0)
        self.assertEqual(result["lag_score"], 0.0)

    def test_two_recent_misses_returns_two(self):
        # Most recent 2 quarters MISSED, prior one ACHIEVED
        self._seed([(2026, 2, "MISSED"), (2026, 1, "MISSED"), (2025, 4, "ACHIEVED")])
        result = self.scorer.compute_score(self.symbol)
        self.assertEqual(result["consecutive_miss_quarters"], 2)
        # lag_score = 2/3 * 100 = 66.67
        self.assertAlmostEqual(result["lag_score"], 66.67, places=1)

    def test_partial_breaks_streak(self):
        # PARTIAL in most recent → streak = 0
        self._seed([(2026, 2, "PARTIAL"), (2026, 1, "MISSED"), (2025, 4, "MISSED")])
        result = self.scorer.compute_score(self.symbol)
        self.assertEqual(result["consecutive_miss_quarters"], 0)

    def test_fiscal_quarter_ordering(self):
        # FY 2027 Q1 (newest) MISSED, FY 2026 Q4 MISSED, FY 2026 Q2 ACHIEVED → streak = 2
        self._seed([(2027, 1, "MISSED"), (2026, 4, "MISSED"), (2026, 2, "ACHIEVED")])
        result = self.scorer.compute_score(self.symbol)
        self.assertEqual(result["consecutive_miss_quarters"], 2)

    def test_compute_score_persists_new_columns(self):
        # All MISSED → 100% lag, THESIS BROKEN
        self._seed([(2026, 2, "MISSED"), (2026, 1, "MISSED"), (2025, 4, "MISSED")])
        self.scorer.compute_score(self.symbol)

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """SELECT consecutive_miss_quarters, lag_score,
                          current_verdict, previous_verdict, last_verdict_flip
                   FROM management_credibility_scores WHERE symbol=%s""",
                (self.symbol,),
            )
            row = cur.fetchone()
            self.assertEqual(row["consecutive_miss_quarters"], 3)
            self.assertAlmostEqual(float(row["lag_score"]), 100.0, places=1)
            self.assertEqual(row["current_verdict"], "THESIS BROKEN")
            # First run → previous_verdict should be NULL (no prior current)
            self.assertIsNone(row["previous_verdict"])
            # First run → no flip recorded
            self.assertIsNone(row["last_verdict_flip"])
        finally:
            conn.close()

    def test_verdict_flip_sets_date(self):
        # First run: ACHIEVED-heavy → HOLD ZONE
        self._seed([(2026, 2, "ACHIEVED"), (2026, 1, "ACHIEVED"), (2025, 4, "ACHIEVED")])
        first = self.scorer.compute_score(self.symbol)
        self.assertEqual(first["current_verdict"], "ADD ZONE")
        self.assertFalse(first["verdict_flipped"])  # first run = no flip
        self.assertIsNone(first["last_verdict_flip"])

        # Second run: shift all to MISSED → THESIS BROKEN
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE guidance_verification SET status='MISSED', actual_value=15.0, "
                "variance_pct=-25.0 WHERE guidance_id IN "
                "(SELECT id FROM management_guidance WHERE symbol=%s)",
                (self.symbol,),
            )
            conn.commit()
        finally:
            conn.close()

        second = self.scorer.compute_score(self.symbol)
        self.assertEqual(second["current_verdict"], "THESIS BROKEN")
        self.assertTrue(second["verdict_flipped"])
        self.assertIsNotNone(second["last_verdict_flip"])
        # previous_verdict should now be the first-run verdict
        self.assertEqual(second["previous_verdict"], "ADD ZONE")


if __name__ == "__main__":
    unittest.main()
