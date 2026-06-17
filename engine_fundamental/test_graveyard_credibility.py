"""
Tests for AAE Layer 7 (Graveyard) credibility-driven rules — Phase 2 of
the AAE × Management Integrity integration (2026-06-17 plan).

Covers:
- No penalty: no credibility + no burial
- Soft penalty: 2-3 consecutive missed quarters, score above 40
- No penalty at threshold edge (3 misses, score=39) — must hit 4 misses
- Auto-bury: 4+ consecutive misses AND score < 40 → writes to aae_graveyard
- Threshold edges: exactly 4 misses + score=39.99 → auto-bury;
  score=40.00 → no auto-bury
- Manual burial preserved: already-buried symbol gets manual reason, not auto
- Auto-bury idempotency: running evaluate_penalty twice does not double-penalize
- Auto-bury reason includes [AUTO] marker

Uses disposable `_GRV_CTX_<uuid>` symbols so it never collides with real
data. Cleans up afterwards.
"""

import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine_core.db import get_connection, fetch_df
from engine_fundamental.graveyard_engine import (
    GraveyardEngine,
    fetch_credibility,
)


def _make_test_symbol() -> str:
    # VARCHAR(20) cap: 8 + 8 = 16, leaves margin.
    return f"_GRV_CTX_{uuid.uuid4().hex[:8].upper()}"


def _seed_credibility(cur, symbol: str, *,
                     accuracy_pct: float = None,
                     total: int = 5,
                     achieved: int = 0,
                     missed: int = 0,
                     cons_miss: int = 0,
                     lag: float = 0.0,
                     verdict: str = "WATCHING",
                     trend: str = "INSUFFICIENT_DATA") -> None:
    cur.execute(
        """INSERT INTO management_credibility_scores
           (symbol, total_promises, achieved_count, missed_count,
            accuracy_pct, avg_variance_pct, trend,
            consecutive_miss_quarters, lag_score, last_verdict_flip,
            current_verdict, previous_verdict)
           VALUES (%s, %s, %s, %s, %s, NULL, %s, %s, %s, NULL, %s, NULL)
           ON CONFLICT (symbol) DO UPDATE SET
             accuracy_pct = EXCLUDED.accuracy_pct,
             total_promises = EXCLUDED.total_promises,
             achieved_count = EXCLUDED.achieved_count,
             missed_count = EXCLUDED.missed_count,
             consecutive_miss_quarters = EXCLUDED.consecutive_miss_quarters,
             lag_score = EXCLUDED.lag_score,
             current_verdict = EXCLUDED.current_verdict,
             trend = EXCLUDED.trend""",
        (symbol, total, achieved, missed, accuracy_pct, trend, cons_miss, lag, verdict),
    )


def _cleanup(symbol: str) -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM management_credibility_scores WHERE symbol = %s", (symbol,))
        cur.execute("DELETE FROM aae_graveyard WHERE symbol = %s", (symbol,))
        conn.commit()
    finally:
        conn.close()


class GraveyardCredibilityTests(unittest.TestCase):

    def tearDown(self):
        # Per-test cleanup. Symbols are recorded by each test on self.symbol.
        if hasattr(self, "symbol"):
            _cleanup(self.symbol)

    # ── Baseline: no penalty cases ───────────────────────────────────

    def test_no_penalty_when_no_credibility_and_no_burial(self):
        self.symbol = _make_test_symbol()
        engine = GraveyardEngine(self.symbol)
        result = engine.evaluate_penalty()

        self.assertEqual(result["penalty"], 0)
        self.assertIsNone(result["reason"])
        self.assertEqual(result["rule"], "NONE")
        self.assertIsNone(result["credibility"])

    def test_no_penalty_when_credibility_strong_no_lag(self):
        self.symbol = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, self.symbol, accuracy_pct=82.0,
                              total=5, achieved=5, missed=0, cons_miss=0,
                              verdict="ADD ZONE", trend="STABLE")
            conn.commit()
        finally:
            conn.close()

        result = GraveyardEngine(self.symbol).evaluate_penalty()
        self.assertEqual(result["penalty"], 0)
        self.assertIsNone(result["reason"])
        self.assertEqual(result["rule"], "NONE")
        self.assertEqual(result["credibility"]["verdict"], "ADD ZONE")

    # ── Soft penalty ─────────────────────────────────────────────────

    def test_soft_penalty_two_consecutive_misses(self):
        self.symbol = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, self.symbol, accuracy_pct=70.0,
                              total=4, achieved=2, missed=2, cons_miss=2,
                              lag=50.0, verdict="HOLD ZONE", trend="DETERIORATING")
            conn.commit()
        finally:
            conn.close()

        result = GraveyardEngine(self.symbol).evaluate_penalty()
        self.assertEqual(result["penalty"], GraveyardEngine.SOFT_PENALTY)
        self.assertEqual(result["rule"], "SOFT_LAG_PENALTY")
        self.assertIn("2 consecutive", result["reason"])
        self.assertIn("lag score", result["reason"].lower())

        # Soft penalty must NOT bury the symbol
        burial = GraveyardEngine(self.symbol).check_burial_status()
        self.assertIsNone(burial)

    def test_soft_penalty_three_consecutive_misses(self):
        self.symbol = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, self.symbol, accuracy_pct=55.0,
                              total=4, achieved=1, missed=3, cons_miss=3,
                              lag=75.0, verdict="REDUCE ZONE", trend="DETERIORATING")
            conn.commit()
        finally:
            conn.close()

        result = GraveyardEngine(self.symbol).evaluate_penalty()
        self.assertEqual(result["penalty"], GraveyardEngine.SOFT_PENALTY)
        self.assertEqual(result["rule"], "SOFT_LAG_PENALTY")

    # ── Threshold edges (no auto-bury) ───────────────────────────────

    def test_no_auto_bury_at_three_misses_even_with_low_score(self):
        """3 consecutive misses + score 39 → still soft penalty, NOT auto-bury."""
        self.symbol = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, self.symbol, accuracy_pct=39.0,
                              total=4, achieved=1, missed=3, cons_miss=3,
                              lag=75.0, verdict="REDUCE ZONE", trend="DETERIORATING")
            conn.commit()
        finally:
            conn.close()

        result = GraveyardEngine(self.symbol).evaluate_penalty()
        self.assertEqual(result["penalty"], GraveyardEngine.SOFT_PENALTY)
        self.assertEqual(result["rule"], "SOFT_LAG_PENALTY")

    def test_no_auto_bury_when_score_equals_40(self):
        """4 misses + score=40.00 → NOT auto-bury (boundary is strict <)."""
        self.symbol = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, self.symbol, accuracy_pct=40.0,
                              total=5, achieved=1, missed=4, cons_miss=4,
                              lag=80.0, verdict="REDUCE ZONE", trend="DETERIORATING")
            conn.commit()
        finally:
            conn.close()

        result = GraveyardEngine(self.symbol).evaluate_penalty()
        self.assertNotEqual(result["rule"], "AUTO_BURY")
        # At score=40 it's still soft-penalty territory
        self.assertEqual(result["rule"], "SOFT_LAG_PENALTY")

    # ── Auto-bury happy path ─────────────────────────────────────────

    def test_auto_bury_four_misses_low_score(self):
        """4 consecutive misses + score < 40 → auto-bury + 30 penalty."""
        self.symbol = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, self.symbol, accuracy_pct=38.0,
                              total=5, achieved=1, missed=4, cons_miss=4,
                              lag=80.0, verdict="REDUCE ZONE", trend="DETERIORATING")
            conn.commit()
        finally:
            conn.close()

        result = GraveyardEngine(self.symbol).evaluate_penalty()
        self.assertEqual(result["penalty"], GraveyardEngine.HARD_PENALTY)
        self.assertEqual(result["rule"], "AUTO_BURY")
        self.assertIn("AUTO-BURIED", result["reason"])
        self.assertIn("4 consecutive", result["reason"])

        # Burial row should exist with [AUTO] prefix
        burial = GraveyardEngine(self.symbol).check_burial_status()
        self.assertIsNotNone(burial)
        self.assertTrue(str(burial["reason_for_death"]).startswith("[AUTO]"))

    def test_auto_bury_just_under_40_score(self):
        """Edge: score=39.99 with 4+ misses still triggers auto-bury."""
        self.symbol = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, self.symbol, accuracy_pct=39.99,
                              total=5, achieved=1, missed=4, cons_miss=4,
                              lag=80.0, verdict="REDUCE ZONE", trend="DETERIORATING")
            conn.commit()
        finally:
            conn.close()

        result = GraveyardEngine(self.symbol).evaluate_penalty()
        self.assertEqual(result["rule"], "AUTO_BURY")

    def test_auto_bury_high_miss_count(self):
        """Extreme case: 6 consecutive misses, score 25, THESIS BROKEN."""
        self.symbol = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, self.symbol, accuracy_pct=25.0,
                              total=7, achieved=1, missed=6, cons_miss=6,
                              lag=85.7, verdict="THESIS BROKEN", trend="DETERIORATING")
            conn.commit()
        finally:
            conn.close()

        result = GraveyardEngine(self.symbol).evaluate_penalty()
        self.assertEqual(result["rule"], "AUTO_BURY")
        self.assertIn("THESIS BROKEN", result["reason"])

    # ── Manual burial preserved ──────────────────────────────────────

    def test_manual_burial_preserved_over_auto(self):
        """If already buried for a manual reason, evaluate_penalty returns
        the manual reason and does NOT overwrite with [AUTO]."""
        self.symbol = _make_test_symbol()
        engine = GraveyardEngine(self.symbol)
        engine.bury_symbol(
            self.symbol,
            reason="Accountant fraud case under SEBI investigation",
            score=15.0,
            auto=False,
        )

        # Even though the symbol has zero credibility data, the manual
        # burial rule fires first and wins.
        result = engine.evaluate_penalty()
        self.assertEqual(result["rule"], "MANUAL_BURIAL")
        self.assertEqual(result["penalty"], GraveyardEngine.HARD_PENALTY)
        self.assertIn("Previously buried", result["reason"])

        # Verify reason_for_death in DB still has the manual text, no [AUTO].
        burial = engine.check_burial_status()
        self.assertIn("SEBI investigation", str(burial["reason_for_death"]))
        self.assertFalse(str(burial["reason_for_death"]).startswith("[AUTO]"))

    def test_manual_burial_wins_over_auto_even_when_credibility_collapsed(self):
        """Symbol manually buried AND would qualify for auto-bury → manual wins."""
        self.symbol = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, self.symbol, accuracy_pct=15.0,
                              total=8, achieved=1, missed=7, cons_miss=6,
                              lag=87.5, verdict="THESIS BROKEN", trend="DETERIORATING")
            conn.commit()
        finally:
            conn.close()

        engine = GraveyardEngine(self.symbol)
        engine.bury_symbol(self.symbol, reason="Original human-set reason",
                           score=15.0, auto=False)

        result = engine.evaluate_penalty()
        self.assertEqual(result["rule"], "MANUAL_BURIAL")
        self.assertIn("Original human-set reason", result["reason"])

    # ── Idempotency ──────────────────────────────────────────────────

    def test_auto_bury_idempotent_on_repeated_calls(self):
        """Calling evaluate_penalty twice in a row should not double-penalize.

        After auto-bury, the next call falls into MANUAL_BURIAL rule (since
        the symbol is now in aae_graveyard) and returns the same hard
        penalty without modifying the row again.
        """
        self.symbol = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, self.symbol, accuracy_pct=32.0,
                              total=5, achieved=1, missed=4, cons_miss=5,
                              lag=100.0, verdict="THESIS BROKEN", trend="DETERIORATING")
            conn.commit()
        finally:
            conn.close()

        engine = GraveyardEngine(self.symbol)

        first = engine.evaluate_penalty()
        self.assertEqual(first["rule"], "AUTO_BURY")
        first_date = engine.check_burial_status()["date_buried"]

        second = engine.evaluate_penalty()
        self.assertEqual(second["rule"], "MANUAL_BURIAL")  # falls through to manual now
        self.assertEqual(second["penalty"], GraveyardEngine.HARD_PENALTY)

        # date_buried should NOT have been overwritten by the second call's
        # manual-burial path (which doesn't call bury_symbol — it only reads).
        final_date = engine.check_burial_status()["date_buried"]
        self.assertEqual(first_date, final_date)


class FetchCredibilityTests(unittest.TestCase):
    """Direct unit tests of the credibility read helper."""

    def tearDown(self):
        if hasattr(self, "symbol"):
            _cleanup(self.symbol)

    def test_returns_none_for_missing_symbol(self):
        self.symbol = _make_test_symbol()
        self.assertIsNone(fetch_credibility(self.symbol))

    def test_returns_dict_for_known_symbol(self):
        self.symbol = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, self.symbol, accuracy_pct=55.5,
                              total=4, achieved=2, missed=2, cons_miss=2,
                              lag=50.0, verdict="HOLD ZONE", trend="STABLE")
            conn.commit()
        finally:
            conn.close()

        cred = fetch_credibility(self.symbol)
        self.assertIsNotNone(cred)
        self.assertEqual(cred["score"], 55.5)
        self.assertEqual(cred["verdict"], "HOLD ZONE")
        self.assertEqual(cred["consecutive_miss_quarters"], 2)
        self.assertEqual(cred["lag_score"], 50.0)
        self.assertEqual(cred["trend"], "STABLE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
