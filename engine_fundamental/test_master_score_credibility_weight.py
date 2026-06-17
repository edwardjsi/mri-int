"""
Tests for AAE Phase 4 — Master Score Credibility Weighting (rebalance option A).

Covers:
- Weights sum to exactly 1.0
- Per-layer contributions match expected values
- Master score with all 50s + no credibility = 50 (neutral baseline)
- Master score with credibility=100 (perfect manager) = 50 + 7.5 = 57.5
- Master score with credibility=0 (broken manager) = 50 - 7.5 = 42.5
- Credibility=None defaults to 50 (no effect, no penalty)
- Penalties still apply on top of the weighted formula
- Result dict exposes the breakdown + weights for the UI

Uses disposable `_MSW_<uuid>` symbols so it never collides with real data.
Cleans up afterwards. All layer scores come from mocks — no real DB
layer fetches, so we can isolate the formula behavior.
"""

import os
import sys
import unittest
import uuid
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine_core.db import get_connection
from engine_fundamental.aae_orchestrator import AAEOrchestrator


def _make_test_symbol() -> str:
    # VARCHAR(20) cap: 4 + 8 = 12, plenty of margin.
    return f"_MSW_{uuid.uuid4().hex[:8].upper()}"


def _seed_credibility(cur, symbol: str, *,
                     accuracy_pct: float = None,
                     verdict: str = "WATCHING") -> None:
    cur.execute(
        """INSERT INTO management_credibility_scores
           (symbol, total_promises, achieved_count, missed_count,
            accuracy_pct, avg_variance_pct, trend,
            consecutive_miss_quarters, lag_score, last_verdict_flip,
            current_verdict, previous_verdict)
           VALUES (%s, 5, 3, 2, %s, NULL, 'STABLE', 0, 0.0, NULL, %s, NULL)
           ON CONFLICT (symbol) DO UPDATE SET
             accuracy_pct = EXCLUDED.accuracy_pct,
             current_verdict = EXCLUDED.current_verdict""",
        (symbol, accuracy_pct, verdict),
    )


def _seed_promises(cur, symbol: str, n: int = 3) -> None:
    """Seed at least one actionable promise so _build_management_integrity
    returns non-None."""
    for i in range(n):
        cur.execute(
            """INSERT INTO management_narrative_timeline
               (symbol, promise_key, first_seen_quarter,
                guidance_text, guidance_type, current_status, current_quarter,
                quote_verified)
               VALUES (%s, %s, 'Q1FY26', %s, 'OTHER', 'ON_TRACK', 'Q3FY26', TRUE)""",
            (symbol, uuid.uuid4().hex[:16], f"Test promise {i} for {symbol}"),
        )


def _cleanup(symbol: str) -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM management_credibility_scores WHERE symbol = %s", (symbol,))
        cur.execute("DELETE FROM management_narrative_timeline WHERE symbol = %s", (symbol,))
        conn.commit()
    finally:
        conn.close()


class WeightConstantsTests(unittest.TestCase):
    """Static checks on the formula constants."""

    def test_weights_sum_to_one(self):
        orch = AAEOrchestrator("ANY")
        self.assertAlmostEqual(orch._weight_sum, 1.0, places=6)

    def test_credibility_weight_is_15_percent(self):
        orch = AAEOrchestrator("ANY")
        self.assertAlmostEqual(orch.W_CREDIBILITY, 0.15, places=6)

    def test_narrative_dropped_from_25_to_20(self):
        orch = AAEOrchestrator("ANY")
        self.assertAlmostEqual(orch.W_NARRATIVE, 0.20, places=6)

    def test_market_dropped_from_25_to_20(self):
        orch = AAEOrchestrator("ANY")
        self.assertAlmostEqual(orch.W_MARKET, 0.20, places=6)


class MasterScoreFormulaTests(unittest.TestCase):
    """End-to-end formula tests via mocked layers."""

    def tearDown(self):
        if hasattr(self, "symbol"):
            _cleanup(self.symbol)

    def _run_scan(self, sym: str, layer_score: int = 50,
                  credibility: float = None) -> dict:
        """Run the orchestrator with all layers returning `layer_score` and
        the optional credibility seeded in the DB.
        """
        # Patch every layer; fetch_df → None to hit synthetic narrative path.
        with patch("engine_fundamental.aae_orchestrator.GovernanceEngine") as G, \
             patch("engine_fundamental.aae_orchestrator.get_sector_engine") as S, \
             patch("engine_fundamental.aae_orchestrator.OwnershipEngine") as O, \
             patch("engine_fundamental.aae_orchestrator.NarrativeEngine") as N, \
             patch("engine_fundamental.aae_orchestrator.MarketConfirmationEngine") as M, \
             patch("engine_fundamental.aae_orchestrator.ValuationEngine") as V, \
             patch("engine_fundamental.aae_orchestrator.GraveyardEngine") as GR, \
             patch("engine_fundamental.aae_orchestrator.ForensicDebateEngine") as D, \
             patch("engine_fundamental.aae_orchestrator.fetch_df", return_value=None):

            G.return_value.fetch_governance_data.return_value = {"ok": True}
            G.return_value.evaluate_kill_switch.return_value = (False, None)
            S.return_value.evaluate.return_value = {
                "score": layer_score, "sector": "IT",
                "sector_rs": None, "reasons": [],
            }
            O.return_value.evaluate.return_value = {"score": layer_score}
            N.return_value.get_latest_transcript.return_value = None
            M.return_value.evaluate.return_value = {
                "score": layer_score, "confirmation_status": "PENDING", "reasons": [],
            }
            V.return_value.evaluate.return_value = {
                "valuation_score": layer_score, "reasons": [],
            }
            GR.return_value.evaluate_penalty.return_value = {
                "penalty": 0, "reason": None, "rule": "NONE",
            }
            D.return_value.run_bear_layer.return_value = "BEAR"
            D.return_value.run_bull_layer.return_value = "BULL"

            return AAEOrchestrator(sym).run_full_scan()

    def test_neutral_baseline_all_50_no_credibility(self):
        """All layers at 50, no credibility data → master_score = 50."""
        self.symbol = _make_test_symbol()
        result = self._run_scan(self.symbol, layer_score=50)

        self.assertEqual(result["master_score"], 50.0)
        # Credibility defaulted to 50 (neutral), no contribution swing.
        self.assertEqual(result["credibility_score_used"], 50)
        # All breakdown values should be exactly weight × 50.
        for layer, expected in [
            ("sector", 50 * 0.25),
            ("narrative", 50 * 0.20),
            ("market", 50 * 0.20),
            ("ownership", 50 * 0.10),
            ("valuation", 50 * 0.10),
            ("credibility", 50 * 0.15),
        ]:
            self.assertAlmostEqual(
                result["master_score_breakdown"][layer], expected, places=4,
                msg=f"breakdown[{layer}] = {result['master_score_breakdown'][layer]}, expected {expected}",
            )

    def test_perfect_credibility_boosts_master_score(self):
        """Credibility=100, other layers at 50 → boost by +7.5."""
        self.symbol = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, self.symbol, accuracy_pct=100.0, verdict="ADD ZONE")
            _seed_promises(cur, self.symbol)
            conn.commit()
        finally:
            conn.close()

        result = self._run_scan(self.symbol, layer_score=50)
        # Base from other 5 layers: 50 × (0.25 + 0.20 + 0.20 + 0.10 + 0.10) = 50 × 0.85 = 42.5
        # Plus credibility: 100 × 0.15 = 15.0
        # Total: 57.5
        self.assertAlmostEqual(result["master_score"], 57.5, places=1)
        self.assertEqual(result["credibility_score_used"], 100.0)
        self.assertAlmostEqual(result["master_score_breakdown"]["credibility"], 15.0, places=2)

    def test_zero_credibility_drops_master_score(self):
        """Credibility=0, other layers at 50 → drop by -7.5."""
        self.symbol = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, self.symbol, accuracy_pct=0.0, verdict="THESIS BROKEN")
            _seed_promises(cur, self.symbol)
            conn.commit()
        finally:
            conn.close()

        result = self._run_scan(self.symbol, layer_score=50)
        # Base from other 5 layers: 42.5
        # Plus credibility: 0 × 0.15 = 0
        # Total: 42.5
        self.assertAlmostEqual(result["master_score"], 42.5, places=1)
        self.assertEqual(result["credibility_score_used"], 0.0)

    def test_credibility_none_defaults_to_50(self):
        """Credibility row has NULL accuracy_pct → default to 50 (neutral)."""
        self.symbol = _make_test_symbol()
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_credibility(cur, self.symbol, accuracy_pct=None, verdict="WATCHING")
            _seed_promises(cur, self.symbol)  # still has timeline so helper returns non-None
            conn.commit()
        finally:
            conn.close()

        result = self._run_scan(self.symbol, layer_score=50)
        # Same as no credibility at all — credibility contribution = 50 × 0.15 = 7.5
        self.assertEqual(result["master_score"], 50.0)
        self.assertEqual(result["credibility_score_used"], 50)

    def test_no_credibility_row_at_all(self):
        """Symbol has no credibility row + no timeline rows → helper returns
        None, credibility defaults to 50 (neutral)."""
        self.symbol = _make_test_symbol()
        result = self._run_scan(self.symbol, layer_score=50)

        self.assertEqual(result["master_score"], 50.0)
        self.assertEqual(result["credibility_score_used"], 50)
        self.assertIsNone(result["layers"]["management_integrity"])

    def test_penalties_still_apply_on_top_of_weighted_formula(self):
        """Graveyard penalty (HARD -30) reduces master_score by 30."""
        self.symbol = _make_test_symbol()
        with patch("engine_fundamental.aae_orchestrator.GovernanceEngine") as G, \
             patch("engine_fundamental.aae_orchestrator.get_sector_engine") as S, \
             patch("engine_fundamental.aae_orchestrator.OwnershipEngine") as O, \
             patch("engine_fundamental.aae_orchestrator.NarrativeEngine") as N, \
             patch("engine_fundamental.aae_orchestrator.MarketConfirmationEngine") as M, \
             patch("engine_fundamental.aae_orchestrator.ValuationEngine") as V, \
             patch("engine_fundamental.aae_orchestrator.GraveyardEngine") as GR, \
             patch("engine_fundamental.aae_orchestrator.ForensicDebateEngine") as D, \
             patch("engine_fundamental.aae_orchestrator.fetch_df", return_value=None):

            G.return_value.fetch_governance_data.return_value = {"ok": True}
            G.return_value.evaluate_kill_switch.return_value = (False, None)
            S.return_value.evaluate.return_value = {"score": 50, "sector": "IT",
                                                     "sector_rs": None, "reasons": []}
            O.return_value.evaluate.return_value = {"score": 50}
            N.return_value.get_latest_transcript.return_value = None
            M.return_value.evaluate.return_value = {"score": 50, "confirmation_status": "PENDING", "reasons": []}
            V.return_value.evaluate.return_value = {"valuation_score": 50, "reasons": []}
            GR.return_value.evaluate_penalty.return_value = {
                "penalty": 30, "reason": "FORENSIC REJECTION", "rule": "MANUAL_BURIAL",
            }
            D.return_value.run_bear_layer.return_value = "BEAR"
            D.return_value.run_bull_layer.return_value = "BULL"

            result = AAEOrchestrator(self.symbol).run_full_scan()

        # 50 (weighted) - 30 (penalty) = 20
        self.assertEqual(result["master_score"], 20.0)

    def test_result_exposes_weights_dict(self):
        """Result['weights'] should expose the formula for the UI / Phase 5."""
        self.symbol = _make_test_symbol()
        result = self._run_scan(self.symbol, layer_score=50)

        self.assertIn("weights", result)
        self.assertEqual(set(result["weights"].keys()),
                         {"sector", "narrative", "market", "ownership", "valuation", "credibility"})
        self.assertAlmostEqual(result["weights"]["credibility"], 0.15, places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
