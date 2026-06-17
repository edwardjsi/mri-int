"""
Tests for AAE Phase 3 — Layers 9-10 (Bear/Bull Debate) management_integrity context.

Covers:
- _build_management_integrity: None for unknown symbol, full dict for known
- _build_management_integrity: aggregates promise counts correctly
- _build_management_integrity: pulls latest credibility_assessment from Phase 1
- ForensicDebateEngine: bear prompt contains integrity block when context has data
- ForensicDebateEngine: bull prompt contains integrity block when context has data
- ForensicDebateEngine: prompt stays clean when no integrity data
- ForensicDebateEngine: bear prompt nudges for DISTRUSTED, bull for TRUSTED

Uses disposable `_MI_CTX_<uuid>` symbols so it never collides with real
data. Cleans up afterwards.
"""

import os
import sys
import unittest
import uuid
from datetime import date
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine_core.db import get_connection
from engine_fundamental.aae_orchestrator import _build_management_integrity
from engine_fundamental.forensic_debate import ForensicDebateEngine


def _make_test_symbol() -> str:
    # VARCHAR(20) cap: 7 + 8 = 15, leaves margin.
    return f"_MI_CTX_{uuid.uuid4().hex[:8].upper()}"


def _seed_credibility(cur, symbol: str, *,
                     accuracy_pct: float = None,
                     total: int = 5,
                     achieved: int = 0,
                     missed: int = 0,
                     cons_miss: int = 0,
                     lag: float = 0.0,
                     verdict: str = "WATCHING",
                     prev_verdict: str = None,
                     trend: str = "INSUFFICIENT_DATA") -> None:
    cur.execute(
        """INSERT INTO management_credibility_scores
           (symbol, total_promises, achieved_count, missed_count,
            accuracy_pct, avg_variance_pct, trend,
            consecutive_miss_quarters, lag_score, last_verdict_flip,
            current_verdict, previous_verdict)
           VALUES (%s, %s, %s, %s, %s, NULL, %s, %s, %s, NULL, %s, %s)
           ON CONFLICT (symbol) DO UPDATE SET
             accuracy_pct = EXCLUDED.accuracy_pct,
             total_promises = EXCLUDED.total_promises,
             achieved_count = EXCLUDED.achieved_count,
             missed_count = EXCLUDED.missed_count,
             consecutive_miss_quarters = EXCLUDED.consecutive_miss_quarters,
             lag_score = EXCLUDED.lag_score,
             current_verdict = EXCLUDED.current_verdict,
             previous_verdict = EXCLUDED.previous_verdict,
             trend = EXCLUDED.trend""",
        (symbol, total, achieved, missed, accuracy_pct, trend, cons_miss, lag,
         verdict, prev_verdict),
    )


def _seed_promises(cur, symbol: str) -> None:
    """Seed a mix of statuses to verify count aggregation."""
    rows = [
        ("Q1FY26", "FULFILLED"),
        ("Q2FY26", "ON_TRACK"),
        ("Q3FY26", "ON_TRACK"),
        ("Q4FY26", "MISSED"),
        ("Q4FY26", "PENDING"),
    ]
    for first_q, status in rows:
        promise_key = uuid.uuid4().hex[:16]
        cur.execute(
            """INSERT INTO management_narrative_timeline
               (symbol, promise_key, first_seen_quarter,
                guidance_text, guidance_type, current_status, current_quarter,
                quote_verified)
               VALUES (%s, %s, %s, %s, 'OTHER', %s, %s, TRUE)""",
            (symbol, promise_key, first_q, f"Test promise {promise_key[:6]}",
             status, "Q4FY26"),
        )


def _seed_narrative_assessment(cur, symbol: str, assessment: str,
                                score: float = 78.0,
                                when: date = None) -> None:
    when = when or date(2026, 6, 15)
    cur.execute(
        """INSERT INTO aae_narrative_intelligence
           (symbol, date, sentiment_score, summary, narrative_delta,
            credibility_assessment, credibility_score_at_analysis)
           VALUES (%s, %s, 0.7, 'Test summary', 0.3, %s, %s)
           ON CONFLICT (symbol, date) DO UPDATE SET
             credibility_assessment = EXCLUDED.credibility_assessment,
             credibility_score_at_analysis = EXCLUDED.credibility_score_at_analysis""",
        (symbol, when, assessment, score),
    )


def _cleanup(symbol: str) -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM management_credibility_scores WHERE symbol = %s", (symbol,))
        cur.execute("DELETE FROM management_narrative_timeline WHERE symbol = %s", (symbol,))
        cur.execute("DELETE FROM aae_narrative_intelligence WHERE symbol = %s", (symbol,))
        conn.commit()
    finally:
        conn.close()


class BuildManagementIntegrityTests(unittest.TestCase):

    def tearDown(self):
        if hasattr(self, "symbol"):
            _cleanup(self.symbol)

    def test_returns_none_when_no_credibility_and_no_timeline(self):
        self.symbol = _make_test_symbol()
        self.assertIsNone(_build_management_integrity(self.symbol))

    def test_returns_full_dict_for_known_symbol(self):
        self.symbol = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, self.symbol, accuracy_pct=80.0,
                              total=5, achieved=4, missed=1, cons_miss=0,
                              verdict="ADD ZONE", trend="STABLE")
            _seed_promises(cur, self.symbol)
            _seed_narrative_assessment(cur, self.symbol, "TRUSTED", score=80.0)
            conn.commit()
        finally:
            conn.close()

        mi = _build_management_integrity(self.symbol)
        self.assertIsNotNone(mi)
        self.assertTrue(mi["has_data"])
        self.assertEqual(mi["credibility_score"], 80.0)
        self.assertEqual(mi["verdict"], "ADD ZONE")
        self.assertEqual(mi["trend"], "STABLE")
        self.assertEqual(mi["consecutive_miss_quarters"], 0)
        self.assertFalse(mi["verdict_flipped_recently"])

        # Promise counts from the seeded timeline (1 FULFILLED + 2 ON_TRACK + 1 MISSED + 1 PENDING)
        self.assertEqual(mi["promise_counts"]["FULFILLED"], 1)
        self.assertEqual(mi["promise_counts"]["ON_TRACK"], 2)
        self.assertEqual(mi["promise_counts"]["MISSED"], 1)
        self.assertEqual(mi["promise_counts"]["PENDING"], 1)
        self.assertEqual(mi["total_promises"], 5)
        self.assertEqual(mi["actionable_promises"], 4)  # excludes PENDING

        # Phase 1 narrative assessment is pulled through.
        self.assertEqual(mi["narrative_assessment"], "TRUSTED")
        self.assertEqual(mi["narrative_score_at_analysis"], 80.0)

    def test_verdict_flipped_recently_flag(self):
        self.symbol = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, self.symbol, accuracy_pct=42.0,
                              total=5, achieved=2, missed=3, cons_miss=3,
                              verdict="REDUCE ZONE", prev_verdict="HOLD ZONE",
                              trend="DETERIORATING")
            conn.commit()
        finally:
            conn.close()

        mi = _build_management_integrity(self.symbol)
        self.assertTrue(mi["verdict_flipped_recently"])
        self.assertEqual(mi["previous_verdict"], "HOLD ZONE")
        self.assertEqual(mi["verdict"], "REDUCE ZONE")

    def test_narrative_assessment_none_when_no_phase1_data(self):
        """If Phase 1 narrative hasn't run yet, narrative_assessment is None
        but the integrity block is still useful (just lacks LLM color)."""
        self.symbol = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, self.symbol, accuracy_pct=60.0,
                              total=4, achieved=2, missed=2, cons_miss=2,
                              verdict="HOLD ZONE", trend="DETERIORATING")
            conn.commit()
        finally:
            conn.close()

        mi = _build_management_integrity(self.symbol)
        self.assertIsNotNone(mi)
        self.assertIsNone(mi["narrative_assessment"])
        self.assertIsNone(mi["narrative_score_at_analysis"])


class DebatePromptIntegrityTests(unittest.TestCase):
    """Capture the prompt the debate engine actually sends to the LLM."""

    def setUp(self):
        self.captured_prompts = []

        # Mock the LLM client + model so we don't hit OpenAI/DeepSeek.
        self.mock_client = MagicMock()
        self.mock_response = MagicMock()
        self.mock_response.choices = [MagicMock()]
        self.mock_response.choices[0].message.content = "MOCK RESPONSE"

        def _capture(**kwargs):
            # Capture the user-message prompt.
            msgs = kwargs.get("messages", [])
            for m in msgs:
                if m.get("role") == "user":
                    self.captured_prompts.append(m["content"])
            return self.mock_response

        self.mock_client.chat.completions.create.side_effect = _capture

    def _engine_with_mock_client(self) -> ForensicDebateEngine:
        engine = ForensicDebateEngine("TEST")
        engine.client = self.mock_client
        engine.model = "mock-model"
        return engine

    def test_bear_prompt_contains_integrity_block_when_data_present(self):
        engine = self._engine_with_mock_client()
        context = {
            "symbol": "CGCL",
            "management_integrity": {
                "has_data": True,
                "credibility_score": 80.4,
                "verdict": "ADD ZONE",
                "previous_verdict": None,
                "trend": "STABLE",
                "consecutive_miss_quarters": 0,
                "lag_score": 0.0,
                "promise_counts": {
                    "FULFILLED": 5, "REVISED_UP": 1, "ON_TRACK": 7,
                    "MISSED": 0, "PENDING": 3,
                },
                "total_promises": 16,
                "actionable_promises": 13,
                "verdict_flipped_recently": False,
                "narrative_assessment": "TRUSTED",
                "narrative_score_at_analysis": 80.4,
            },
        }

        engine.run_bear_layer(context)

        self.assertEqual(len(self.captured_prompts), 1)
        prompt = self.captured_prompts[0]
        self.assertIn("Management Integrity", prompt)
        self.assertIn("80.4/100", prompt)
        self.assertIn("ADD ZONE", prompt)
        self.assertIn("STABLE", prompt)
        self.assertIn("FULFILLED", prompt)
        self.assertIn("5 FULFILLED", prompt)
        # CGCL has 0 MISSED so the formatted count line must omit it.
        # (Raw JSON context above will mention "MISSED":0, but the
        # human-readable formatted block should not print "0 MISSED".)
        self.assertIn("- Promise counts: 5 FULFILLED, 1 REVISED_UP, 7 ON_TRACK", prompt)
        self.assertNotIn("0 MISSED", prompt)
        self.assertIn("TRUSTED", prompt)
        # Bear-specific nudge
        self.assertIn("critical", prompt.lower())
        self.assertIn("thesis risk", prompt.lower())

    def test_bull_prompt_contains_integrity_block_when_data_present(self):
        engine = self._engine_with_mock_client()
        context = {
            "symbol": "ASHOKA",
            "management_integrity": {
                "has_data": True,
                "credibility_score": 47.2,
                "verdict": "REDUCE ZONE",
                "previous_verdict": "HOLD ZONE",
                "trend": "DETERIORATING",
                "consecutive_miss_quarters": 4,
                "lag_score": 100.0,
                "promise_counts": {
                    "FULFILLED": 0, "REVISED_UP": 0, "ON_TRACK": 0,
                    "MISSED": 7, "PENDING": 0,
                },
                "total_promises": 7,
                "actionable_promises": 7,
                "verdict_flipped_recently": True,
                "narrative_assessment": "DISTRUSTED",
                "narrative_score_at_analysis": 47.2,
            },
        }

        engine.run_bull_layer(context)

        self.assertEqual(len(self.captured_prompts), 1)
        prompt = self.captured_prompts[0]
        self.assertIn("Management Integrity", prompt)
        self.assertIn("47.2/100", prompt)
        self.assertIn("REDUCE ZONE", prompt)
        self.assertIn("Consecutive missed quarters: 4", prompt)
        self.assertIn("DETERIORATING", prompt)
        self.assertIn("Verdict recently flipped", prompt)
        self.assertIn("HOLD ZONE", prompt)
        self.assertIn("7 MISSED", prompt)
        self.assertIn("DISTRUSTED", prompt)
        # Bull-specific nudge
        self.assertIn("de-risks", prompt.lower())

    def test_bear_prompt_omits_integrity_block_when_no_data(self):
        engine = self._engine_with_mock_client()
        context = {
            "symbol": "FRESH",
            "management_integrity": None,  # brand-new symbol, nothing in DB
        }

        engine.run_bear_layer(context)

        self.assertEqual(len(self.captured_prompts), 1)
        prompt = self.captured_prompts[0]
        # Should NOT contain the integrity block (only the focus hint in Focus line).
        self.assertNotIn("verified cross-transcript track record", prompt)

    def test_bull_prompt_omits_integrity_block_when_data_is_empty(self):
        engine = self._engine_with_mock_client()
        context = {
            "symbol": "FRESH",
            "management_integrity": {"has_data": False},
        }

        engine.run_bull_layer(context)

        self.assertEqual(len(self.captured_prompts), 1)
        prompt = self.captured_prompts[0]
        self.assertNotIn("verified cross-transcript track record", prompt)

    def test_bear_prompt_omits_integrity_block_when_no_management_key(self):
        engine = self._engine_with_mock_client()
        context = {"symbol": "FRESH"}  # no management_integrity key at all

        engine.run_bear_layer(context)

        self.assertEqual(len(self.captured_prompts), 1)
        prompt = self.captured_prompts[0]
        self.assertNotIn("verified cross-transcript track record", prompt)


class AAEOrchestratorContextWiringTests(unittest.TestCase):
    """Verify the orchestrator's ai_context includes management_integrity."""

    def setUp(self):
        self.symbol = _make_test_symbol()
        # Seed just enough data for the orchestrator's helpers to not crash.
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, self.symbol, accuracy_pct=72.0,
                              total=4, achieved=3, missed=1, cons_miss=0,
                              verdict="HOLD ZONE", trend="STABLE")
            _seed_promises(cur, self.symbol)
            conn.commit()
        finally:
            conn.close()

    def tearDown(self):
        _cleanup(self.symbol)

    def test_ai_context_contains_management_integrity(self):
        """Mock every layer + the debate engine so we can inspect the
        ai_context dict that the orchestrator passes to the bear/bull calls.
        """
        from engine_fundamental.aae_orchestrator import AAEOrchestrator

        # Capture the ai_context the orchestrator hands to the debate engine.
        captured = {}

        class _StubDebate:
            def __init__(self, sym): pass
            def run_bear_layer(self, ctx):
                captured["ai_context"] = ctx
                return "BEAR"
            def run_bull_layer(self, ctx):
                captured["ai_context"] = captured.get("ai_context") or ctx
                captured["bull_context"] = ctx
                return "BULL"

        # Patch every heavy layer to return minimal valid data.
        # Also patch fetch_df (used for narrative step) to return None so
        # we hit the synthetic fallback path.
        with patch("engine_fundamental.aae_orchestrator.GovernanceEngine") as G, \
             patch("engine_fundamental.aae_orchestrator.get_sector_engine") as S, \
             patch("engine_fundamental.aae_orchestrator.OwnershipEngine") as O, \
             patch("engine_fundamental.aae_orchestrator.NarrativeEngine") as N, \
             patch("engine_fundamental.aae_orchestrator.MarketConfirmationEngine") as M, \
             patch("engine_fundamental.aae_orchestrator.ValuationEngine") as V, \
             patch("engine_fundamental.aae_orchestrator.GraveyardEngine") as GR, \
             patch("engine_fundamental.aae_orchestrator.ForensicDebateEngine", _StubDebate), \
             patch("engine_fundamental.aae_orchestrator.fetch_df", return_value=None):

            G.return_value.fetch_governance_data.return_value = {"ok": True}
            G.return_value.evaluate_kill_switch.return_value = (False, None)
            S.return_value.evaluate.return_value = {"score": 50, "sector": "IT",
                                                     "sector_rs": None, "reasons": []}
            O.return_value.evaluate.return_value = {"score": 50}
            N.return_value.get_latest_transcript.return_value = None
            M.return_value.evaluate.return_value = {"score": 50, "confirmation_status": "PENDING", "reasons": []}
            V.return_value.evaluate.return_value = {"valuation_score": 50, "reasons": []}
            GR.return_value.evaluate_penalty.return_value = {"penalty": 0, "reason": None, "rule": "NONE"}

            result = AAEOrchestrator(self.symbol).run_full_scan()

        self.assertIn("ai_context", captured, "Debate engine was never called")
        ctx = captured["ai_context"]
        self.assertIn("management_integrity", ctx)
        self.assertIsNotNone(ctx["management_integrity"])
        self.assertTrue(ctx["management_integrity"]["has_data"])
        # The integrity block must include the seeded data.
        self.assertEqual(ctx["management_integrity"]["verdict"], "HOLD ZONE")
        self.assertEqual(ctx["management_integrity"]["credibility_score"], 72.0)
        # And the graveyard rule for the result layer.
        self.assertIn("graveyard_rule", ctx)
        self.assertIn("graveyard_penalty", ctx)


if __name__ == "__main__":
    unittest.main(verbosity=2)
