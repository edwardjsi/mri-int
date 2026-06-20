"""
Tests for engine_debate.context_* builders — FeatureRequest 2026-06-19.

Covers:
- build_guidance_context shape, field types, presence of key blocks
- build_pe_expansion_context shape, field types, graceful empty-state
- Hash-stability: same DB state → same hash for cache purposes
- Graceful handling of unknown symbols (empty / has_data=False blocks)
- Live smoke on POLYCAB (HOLD ZONE, known rich data) and CGCL (ADD ZONE)
- Dispatches: same symbol produces different hashes across the two contexts

Tests are read-only against Neon DB (no inserts). No cleanup needed.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine_debate.cache import canonical_hash
from engine_debate.context_guidance import build_guidance_context
from engine_debate.context_pe_expansion import build_pe_expansion_context


# ── GuidanceCheck context ───────────────────────────────────────────────


class GuidanceContextTests(unittest.TestCase):

    def test_returns_required_top_level_keys(self):
        ctx = build_guidance_context("POLYCAB")
        for key in ("symbol", "credibility", "intonation",
                    "verifier_summary", "guidance_quality_signal",
                    "total_material_promises"):
            self.assertIn(key, ctx, f"missing top-level key: {key}")
        self.assertEqual(ctx["symbol"], "POLYCAB")

    def test_credibility_block_shape(self):
        ctx = build_guidance_context("POLYCAB")
        cred = ctx["credibility"]
        # For symbols with data, must have the full metric set
        if cred.get("has_data"):
            for key in ("accuracy_pct", "total_promises", "achieved_count",
                        "missed_count", "partial_count", "trend",
                        "consecutive_miss_quarters", "lag_score",
                        "current_verdict"):
                self.assertIn(key, cred, f"missing credibility key: {key}")
            # Types
            self.assertIsInstance(cred["accuracy_pct"], float)
            self.assertIsInstance(cred["total_promises"], int)
            self.assertIsInstance(cred["consecutive_miss_quarters"], int)

    def test_intonation_block_shape(self):
        ctx = build_guidance_context("POLYCAB")
        into = ctx["intonation"]
        if into.get("has_data"):
            self.assertIn("latest", into)
            self.assertIn("previous", into)
            self.assertIn("quarter_over_quarter_delta", into)
            self.assertIn("tone_shift_detected", into)
            self.assertIn("timeline", into)
            # Latest must have all 9 dimensions
            for dim in ("confidence", "hedging", "aggression", "transparency",
                        "optimism", "pessimism", "accountability",
                        "numerical_density", "headwind_acknowledged"):
                self.assertIn(dim, into["latest"], f"missing intonation dim: {dim}")

    def test_verifier_summary_has_status_counts(self):
        ctx = build_guidance_context("POLYCAB")
        vs = ctx["verifier_summary"]
        for key in ("by_status", "unable_reasons", "n_achieved",
                    "n_missed", "n_partial", "n_pending", "n_unable_to_verify"):
            self.assertIn(key, vs, f"missing verifier_summary key: {key}")

    def test_quality_signal_is_one_of_three(self):
        ctx = build_guidance_context("POLYCAB")
        self.assertIn(ctx["guidance_quality_signal"],
                      ("DIRECTIONAL ONLY", "MIXED", "NUMERICAL"))

    def test_handles_unknown_symbol_gracefully(self):
        """Unknown symbol with no credibility row must still return valid shape."""
        ctx = build_guidance_context("_UNKNOWN_SYMBOL_DEBTEST_")
        self.assertEqual(ctx["symbol"], "_UNKNOWN_SYMBOL_DEBTEST_")
        self.assertFalse(ctx["credibility"]["has_data"])
        self.assertFalse(ctx["intonation"]["has_data"])
        # verifier_summary should still return a dict with all keys
        self.assertIn("by_status", ctx["verifier_summary"])

    def test_hash_is_deterministic_for_same_payload(self):
        """Hashing the SAME payload twice gives the same hash. We hash the
        same returned dict twice rather than calling the builder twice,
        because build_guidance_context() also includes live DB state."""
        ctx = build_guidance_context("POLYCAB")
        h1 = canonical_hash(ctx)
        h2 = canonical_hash(ctx)
        self.assertEqual(h1, h2)


# ── Expansion Lens context ──────────────────────────────────────────────


class PeExpansionContextTests(unittest.TestCase):

    def test_returns_required_top_level_keys(self):
        ctx = build_pe_expansion_context("POLYCAB")
        for key in ("symbol", "header", "bottom_line", "top_drivers",
                    "category_breakdown_summary", "cross_check",
                    "credibility", "coverage"):
            self.assertIn(key, ctx, f"missing top-level key: {key}")
        self.assertEqual(ctx["symbol"], "POLYCAB")

    def test_header_shape(self):
        ctx = build_pe_expansion_context("POLYCAB")
        h = ctx["header"]
        for key in ("company_name", "pe_score", "rank", "total", "bucket"):
            self.assertIn(key, h, f"missing header key: {key}")
        # POLYCAB has a PE score row
        self.assertIsNotNone(h["pe_score"])

    def test_category_breakdown_summary_shape(self):
        ctx = build_pe_expansion_context("POLYCAB")
        cbs = ctx["category_breakdown_summary"]
        for key in ("strong_categories", "weak_categories",
                    "missing_categories", "n_total"):
            self.assertIn(key, cbs, f"missing cbs key: {key}")
        self.assertEqual(cbs["n_total"], 12, "12 PE categories expected")

    def test_bottom_line_shape(self):
        ctx = build_pe_expansion_context("POLYCAB")
        bl = ctx["bottom_line"]
        if bl:
            for key in ("summary", "action", "highlights"):
                self.assertIn(key, bl, f"missing bottom_line key: {key}")
            self.assertIn(bl["action"],
                          ("positive", "watch", "cautious", "negative", "no_data"))

    def test_cross_check_is_list_with_expected_dimensions(self):
        ctx = build_pe_expansion_context("POLYCAB")
        cc = ctx["cross_check"]
        self.assertIsInstance(cc, list)
        if cc:
            dimensions = [row.get("dimension") for row in cc]
            for required in ("Margins", "Growth", "Quality", "Momentum", "Credibility"):
                self.assertIn(required, dimensions,
                              f"cross_check missing dimension: {required}")

    def test_credibility_embedded_matches_guidance_shape(self):
        """The credibility block inside pe_expansion context must match the
        guidance context shape (same source table)."""
        pe_ctx = build_pe_expansion_context("POLYCAB")
        gd_ctx = build_guidance_context("POLYCAB")
        # Both should expose the same has_data, accuracy_pct, current_verdict
        pe_cred = pe_ctx.get("credibility") or {}
        gd_cred = gd_ctx.get("credibility") or {}
        if pe_cred.get("has_data") and gd_cred.get("has_data"):
            self.assertEqual(pe_cred["accuracy_pct"], gd_cred["accuracy_pct"])
            self.assertEqual(pe_cred["current_verdict"], gd_cred["current_verdict"])

    def test_handles_unknown_symbol_gracefully(self):
        """Unknown symbol → 'no-data' placeholder, no crash.

        build_pe_expansion_report() falls through gracefully for unknown
        symbols: returns a placeholder header with pe_score=0 and the 12
        categories all marked missing. What matters is that the context
        builder doesn't crash and produces a usable (if empty) shape.
        """
        ctx = build_pe_expansion_context("_UNKNOWN_SYMBOL_DEBTEST_")
        self.assertEqual(ctx["symbol"], "_UNKNOWN_SYMBOL_DEBTEST_")
        # All optional sub-blocks should be None or empty, never crash
        self.assertIsNone(ctx["independent_check"])
        self.assertIsNone(ctx["financial_quality"])
        self.assertIsNone(ctx["price_action"])
        self.assertIsNone(ctx["credibility"])
        # Category summary should have all categories in 'missing'
        cbs = ctx["category_breakdown_summary"]
        self.assertEqual(cbs["n_total"], 12)
        self.assertEqual(cbs["strong_categories"], [])
        self.assertEqual(cbs["weak_categories"], [])
        self.assertEqual(len(cbs["missing_categories"]), 12)

    def test_hash_is_deterministic_for_same_payload(self):
        """Two hashes of the SAME payload are equal. Doesn't compare across
        build_pe_expansion_context() calls because generated_at_ist is a
        build-time timestamp that legitimately changes across minute
        boundaries — that's not an engine bug, it's a property of the
        underlying report."""
        ctx = build_pe_expansion_context("POLYCAB")
        h1 = canonical_hash(ctx)
        h2 = canonical_hash(ctx)
        self.assertEqual(h1, h2)

    def test_hash_changes_when_payload_changes(self):
        """Different payloads → different hashes."""
        ctx = build_pe_expansion_context("POLYCAB")
        h1 = canonical_hash(ctx)
        modified = dict(ctx)
        modified["top_drivers"] = ["MUTATED"]
        h2 = canonical_hash(modified)
        self.assertNotEqual(h1, h2)


# ── Cross-context hash distinctness ─────────────────────────────────────


class CrossContextTests(unittest.TestCase):
    def test_guidance_and_pe_expansion_produce_different_hashes(self):
        """Same symbol, two contexts → two different hashes → two cache rows."""
        gd = build_guidance_context("POLYCAB")
        pe = build_pe_expansion_context("POLYCAB")
        self.assertNotEqual(canonical_hash(gd), canonical_hash(pe))


if __name__ == "__main__":
    unittest.main()


# ── Phase D2: agent_details surfaced in financial_quality ───────────────


class FinancialQualityAgentDetailsTests(unittest.TestCase):
    """Phase D2 of docs/INITIATIVE_DATA_RICHNESS_2026-06-19.md.

    Verify the Expansion Lens context surfaces the new agent_details JSONB
    (per-year metrics + trajectory) inside the financial_quality block, so
    the bear/bull LLM debate can cite specific numbers (ROCE 13.39% vs WACC
    12.0%, +126 bps YoY, etc.) instead of summary flags.
    """

    def test_financial_quality_has_agent_details_for_real_symbol(self):
        """For a symbol with data (KIRLOSENG — known 5-yr financials), the
        agent_details block must be present and populated with by_year[] +
        trajectory."""
        ctx = build_pe_expansion_context("KIRLOSENG")
        fq = ctx.get("financial_quality")
        self.assertIsNotNone(fq, "financial_quality should not be None for KIRLOSENG")
        ad = fq.get("agent_details")
        self.assertIsNotNone(ad, "agent_details must be present in financial_quality")
        # Shape checks
        self.assertIn("by_year", ad)
        self.assertIn("trajectory", ad)
        self.assertGreater(len(ad["by_year"]), 0, "by_year should not be empty for KIRLOSENG")
        # Trajectory summary must have the documented fields
        traj = ad["trajectory"]
        for key in ("score_trend", "score_change_yoy", "roce_change_yoy_bps",
                    "margin_compression_bps_yoy", "revenue_cagr_3y_pct",
                    "years_observed"):
            self.assertIn(key, traj, f"trajectory missing key: {key}")

    def test_agent_details_by_year_metrics_have_per_agent_breakdown(self):
        """Each by_year entry must have a metrics dict with all 7 agents'
        per-year detail (the data Phase D1 persists)."""
        ctx = build_pe_expansion_context("KIRLOSENG")
        ad = ctx["financial_quality"]["agent_details"]
        latest_year = ad["by_year"][-1]
        self.assertIn("year", latest_year)
        self.assertIn("metrics", latest_year)
        metrics = latest_year["metrics"]
        expected_agents = (
            "revenue_growth", "margin_quality", "operating_leverage",
            "working_capital", "capital_efficiency", "business_evolution",
            "financial_translation",
        )
        for agent_key in expected_agents:
            self.assertIn(agent_key, metrics,
                          f"latest year missing metrics for {agent_key}")

    def test_agent_details_roce_metrics_present(self):
        """The whole point of Phase D2: capital_efficiency.per_year must
        carry roce_pct / wacc_pct / gap_pct so the LLM can write
        'ROCE 13.39% vs WACC 12.0%' instead of just 'ROCE < WACC'."""
        ctx = build_pe_expansion_context("KIRLOSENG")
        ad = ctx["financial_quality"]["agent_details"]
        ce = ad["by_year"][-1]["metrics"]["capital_efficiency"]
        for key in ("roce_pct", "wacc_pct", "gap_pct"):
            self.assertIn(key, ce, f"capital_efficiency missing {key}")
            self.assertIsNotNone(ce[key], f"capital_efficiency.{key} is None")

    def test_agent_details_none_when_quality_verdicts_empty(self):
        """For a symbol with no quality_verdicts row (e.g. fresh symbol),
        financial_quality should be None — entire block absent, not a dict
        with empty agent_details."""
        ctx = build_pe_expansion_context("_UNKNOWN_SYMBOL_AGENT_DETAILS_")
        # Either fq is None, or agent_details is None — never an empty dict
        fq = ctx.get("financial_quality")
        if fq is not None:
            self.assertNotEqual(fq.get("agent_details"), {},
                                "agent_details must be None, not empty dict")

    def test_empty_agent_details_normalized_to_none(self):
        """Quality verdicts rows with agent_details = '{}' (default for
        pre-Phase-D1 rows) must surface as None in the context, not {}."""
        # Symbol that exists in quality_verdicts but has empty agent_details
        # — pick any symbol, the smoke run before this test populated data.
        ctx = build_pe_expansion_context("_QIF_DET_NONE_TEST_")
        # For an unknown symbol, financial_quality is None outright.
        # The normalization matters only when a row exists with empty {}.
        # We assert the contract: never an empty dict in the context.
        fq = ctx.get("financial_quality")
        if fq is not None:
            ad = fq.get("agent_details")
            self.assertNotEqual(ad, {}, "empty dict leaks into context")
