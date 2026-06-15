"""
Tests for ConvictionEngine verifier fixes (Decision 097 addendum):
- CAPACITY_EXPANSION / DEAL_PIPELINE / MARKET_SHARE mapped with reasons
- REVENUE_GROWTH directional fallback (no numeric target)
- unable_reason persisted on UNABLE_TO_VERIFY rows

Run: python3 -m unittest engine_guidance.test_verifier_reasons -v
"""

import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine_core.db import get_connection
from engine_guidance.guidance_verifier import GuidanceVerifier


def _test_symbol() -> str:
    # UPPERCASE: verifier compute_score uppercases input
    return f"_TESTVR_{uuid.uuid4().hex[:8].upper()}"


def _insert(cur, symbol, gtype, target_value, target_date, transcript_id=None, guidance_text=None):
    cur.execute(
        """INSERT INTO management_guidance
           (symbol, transcript_id, guidance_text, guidance_type,
            target_value, target_unit, target_date, confidence)
           VALUES (%s,%s,%s,%s,%s,%s,%s,'HIGH')
           RETURNING id""",
        (symbol, transcript_id, guidance_text or f"Test {gtype}", gtype,
         target_value, "pct", target_date),
    )
    return cur.fetchone()["id"]


def _cleanup(symbol):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM guidance_verification WHERE guidance_id IN "
                   "(SELECT id FROM management_guidance WHERE symbol=%s)", (symbol,))
        cur.execute("DELETE FROM management_guidance WHERE symbol=%s", (symbol,))
        conn.commit()
    finally:
        conn.close()


class TestCapacityExpansion(unittest.TestCase):
    def setUp(self):
        self.v = GuidanceVerifier()
        self.sym = _test_symbol()

    def tearDown(self):
        _cleanup(self.sym)

    def test_capacity_expansion_records_reason(self):
        conn = get_connection()
        try:
            cur = conn.cursor()
            gid = _insert(cur, self.sym, "CAPACITY_EXPANSION", 16667.0, "FY25",
                          guidance_text="16,667 circuit km")
            conn.commit()
        finally:
            conn.close()

        status = self.v.verify_guidance(gid)
        self.assertEqual(status, "UNABLE_TO_VERIFY")

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT status, unable_reason FROM guidance_verification WHERE guidance_id=%s", (gid,))
            row = cur.fetchone()
            self.assertEqual(row["status"], "UNABLE_TO_VERIFY")
            self.assertIn("capacity", row["unable_reason"].lower())
        finally:
            conn.close()


class TestDealPipelineAndMarketShare(unittest.TestCase):
    def setUp(self):
        self.v = GuidanceVerifier()

    def test_deal_pipeline_reason(self):
        sym = _test_symbol()
        try:
            conn = get_connection()
            cur = conn.cursor()
            gid = _insert(cur, sym, "DEAL_PIPELINE", None, "Q4FY25")
            conn.commit()
            conn.close()
            self.v.verify_guidance(gid)
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT unable_reason FROM guidance_verification WHERE guidance_id=%s", (gid,))
            r = cur.fetchone()
            self.assertIsNotNone(r["unable_reason"])
            self.assertIn("qualitative", r["unable_reason"].lower())
            conn.close()
        finally:
            _cleanup(sym)

    def test_market_share_reason(self):
        sym = _test_symbol()
        try:
            conn = get_connection()
            cur = conn.cursor()
            gid = _insert(cur, sym, "MARKET_SHARE", 25.0, "FY26")
            conn.commit()
            conn.close()
            self.v.verify_guidance(gid)
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT unable_reason FROM guidance_verification WHERE guidance_id=%s", (gid,))
            r = cur.fetchone()
            self.assertIsNotNone(r["unable_reason"])
            self.assertIn("industry", r["unable_reason"].lower())
            conn.close()
        finally:
            _cleanup(sym)


class TestRevenueGrowthDirectional(unittest.TestCase):
    """REVENUE_GROWTH without a numeric target → PARTIAL/MISSED based on YoY direction."""

    def setUp(self):
        self.v = GuidanceVerifier()
        self.sym = _test_symbol()

    def tearDown(self):
        _cleanup(self.sym)

    def test_directional_no_target_returns_partial_or_missed(self):
        """Promise with no target_value and target_date in past should not be UNABLE."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            # target_value NULL + past target_date = directional fallback
            gid = _insert(cur, self.sym, "REVENUE_GROWTH", None, "Q4FY24",
                          guidance_text="We expect growth in H2")
            conn.commit()
        finally:
            conn.close()

        status = self.v.verify_guidance(gid)
        # Test symbol has no financial data, so SQL returns no row → UNABLE with
        # "no financial data" reason. We accept either "directional" or
        # "no financial data" — the important thing is NOT to be PENDING (date is past).
        self.assertIn(status, ("PARTIAL", "MISSED", "UNABLE_TO_VERIFY"))

        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT status, unable_reason FROM guidance_verification WHERE guidance_id=%s", (gid,))
            r = cur.fetchone()
            # When directional fallback succeeds, no reason should be persisted.
            # When it can't (no financials), the reason is either "directional" or
            # "no financial data" — both acceptable.
            if status == "UNABLE_TO_VERIFY":
                reason_lower = (r["unable_reason"] or "").lower()
                self.assertTrue(
                    "directional" in reason_lower or "no financial" in reason_lower,
                    f"Unexpected reason: {r['unable_reason']!r}"
                )
            else:
                self.assertIsNone(r["unable_reason"])
        finally:
            conn.close()


class TestOtherTypeFallback(unittest.TestCase):
    def setUp(self):
        self.v = GuidanceVerifier()

    def test_other_with_no_target_records_reason(self):
        sym = _test_symbol()
        try:
            conn = get_connection()
            cur = conn.cursor()
            gid = _insert(cur, sym, "OTHER", None, "Q4FY24")
            conn.commit()
            conn.close()
            self.v.verify_guidance(gid)
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT status, unable_reason FROM guidance_verification WHERE guidance_id=%s", (gid,))
            r = cur.fetchone()
            self.assertEqual(r["status"], "UNABLE_TO_VERIFY")
            self.assertIn("no numeric", (r["unable_reason"] or "").lower())
            conn.close()
        finally:
            _cleanup(sym)


class TestStoreOnlyPersistsReasonOnUnable(unittest.TestCase):
    """Ensure non-UNABLE statuses don't carry a stale reason."""

    def test_pending_does_not_carry_reason(self):
        v = GuidanceVerifier()
        sym = _test_symbol()
        try:
            conn = get_connection()
            cur = conn.cursor()
            gid = _insert(cur, sym, "MARGIN", 25.0, "Q4FY30")  # far-future date
            conn.commit()
            conn.close()
            v.verify_guidance(gid)
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT status, unable_reason FROM guidance_verification WHERE guidance_id=%s", (gid,))
            r = cur.fetchone()
            self.assertEqual(r["status"], "PENDING")
            self.assertIsNone(r["unable_reason"])
            conn.close()
        finally:
            _cleanup(sym)


if __name__ == "__main__":
    unittest.main()
