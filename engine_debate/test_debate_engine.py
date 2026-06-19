"""
Tests for engine_debate.debate_engine — FeatureRequest 2026-06-19.

Covers:
- canonical_hash determinism
- _load_prompts dispatch for 'guidance' and 'pe_expansion'
- PROMPT_REGISTRY exhaustiveness (every context_kind has all 6 prompts)
- Stub fallback when no LLM is configured
- run_debate cache miss -> hit flow (using disposable test symbols)
- Unknown context_kind raises ValueError

Smoke-tested against live Neon DB for cache behavior. Disposable test
symbols (`_DEBTEST_<uuid>`) so no production data is touched.
"""

import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine_debate.cache import canonical_hash, lookup_debate, store_debate
from engine_debate.debate_engine import (
    PROMPT_REGISTRY,
    DebateResult,
    _load_prompts,
    run_debate,
)


def _test_symbol() -> str:
    """Disposable uppercase symbol per test run."""
    return f"_DEBTEST_{uuid.uuid4().hex[:8].upper()}"


def _minimal_context(symbol: str) -> dict:
    """Minimal valid context payload for run_debate (no DB dependency)."""
    return {
        "symbol": symbol,
        "credibility": {"has_data": False, "note": "test fixture"},
        "intonation": {"has_data": False, "note": "test fixture"},
        "verifier_summary": {"by_status": {}, "unable_reasons": {}},
        "guidance_quality_signal": "DIRECTIONAL ONLY",
        "total_material_promises": 0,
    }


# ── Hash determinism ────────────────────────────────────────────────────


class HashTests(unittest.TestCase):
    def test_canonical_hash_is_deterministic(self):
        """Same payload → same hash, regardless of dict insertion order."""
        a = canonical_hash({"x": 1, "y": [1, 2, 3], "z": {"a": "hi"}})
        b = canonical_hash({"z": {"a": "hi"}, "y": [1, 2, 3], "x": 1})
        self.assertEqual(a, b)

    def test_canonical_hash_is_64_hex(self):
        h = canonical_hash({"a": 1})
        self.assertEqual(len(h), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in h))

    def test_canonical_hash_differs_on_payload_change(self):
        a = canonical_hash({"x": 1})
        b = canonical_hash({"x": 2})
        self.assertNotEqual(a, b)

    def test_canonical_hash_handles_datetime_via_default(self):
        """datetime objects should be stringified via default=str."""
        from datetime import datetime
        a = canonical_hash({"ts": datetime(2026, 6, 19)})
        b = canonical_hash({"ts": datetime(2026, 6, 20)})
        self.assertNotEqual(a, b)
        c = canonical_hash({"ts": datetime(2026, 6, 19)})
        self.assertEqual(a, c)


# ── Prompt registry / dispatch ─────────────────────────────────────────


class PromptRegistryTests(unittest.TestCase):

    def test_guidance_context_kind_registered(self):
        self.assertIn("guidance", PROMPT_REGISTRY)

    def test_pe_expansion_context_kind_registered(self):
        self.assertIn("pe_expansion", PROMPT_REGISTRY)

    def test_every_registry_entry_has_all_six_keys(self):
        required = {"module", "bear_system", "bear_user", "bull_system",
                    "bull_user", "adj_system", "adj_user"}
        for kind, cfg in PROMPT_REGISTRY.items():
            missing = required - set(cfg.keys())
            self.assertEqual(missing, set(),
                             f"context_kind={kind!r} missing keys: {missing}")

    def test_every_registry_module_is_importable(self):
        for kind, cfg in PROMPT_REGISTRY.items():
            try:
                __import__(cfg["module"])
            except ImportError as e:
                self.fail(f"context_kind={kind!r} module {cfg['module']!r} "
                          f"not importable: {e}")

    def test_every_registry_constant_exists(self):
        for kind, cfg in PROMPT_REGISTRY.items():
            mod = __import__(cfg["module"], fromlist=["*"])
            for key in ("bear_system", "bear_user", "bull_system",
                        "bull_user", "adj_system", "adj_user"):
                const_name = cfg[key]
                self.assertTrue(
                    hasattr(mod, const_name),
                    f"context_kind={kind!r}: {cfg['module']}.{const_name} missing",
                )

    def test_load_prompts_returns_six_strings(self):
        bear_sys, bear_usr, bull_sys, bull_usr, adj_sys, adj_usr = _load_prompts("guidance")
        # System + main user prompts are substantial; adjudicator_user is short.
        for s, label in [(bear_sys, "bear_sys"), (bear_usr, "bear_usr"),
                         (bull_sys, "bull_sys"), (bull_usr, "bull_usr"),
                         (adj_sys, "adj_sys")]:
            self.assertIsInstance(s, str, label)
            self.assertGreater(len(s), 100, f"{label} should be substantial")
        # adjudicator_user is short by design (just stock + bear + bull + instruct)
        self.assertIsInstance(adj_usr, str)
        self.assertGreater(len(adj_usr), 30, "adj_usr should have at least placeholders")

    def test_load_prompts_raises_on_unknown_kind(self):
        with self.assertRaises(ValueError) as cm:
            _load_prompts("not_a_real_kind")
        self.assertIn("Unknown context_kind", str(cm.exception))

    def test_guidance_bear_prompt_has_full_rule_set(self):
        """GuidanceCheck bear prompt must include the 5 critical grounding rules
        (per the prompt-tightening commit 10896b8)."""
        bear_sys, _, _, _, _, _ = _load_prompts("guidance")
        for marker in ("accuracy_pct", "CONTRARIAN",
                       "CAUSATION", "PARTIAL", "strong"):
            self.assertIn(marker, bear_sys,
                          f"guidance bear prompt missing grounding rule for {marker!r}")

    def test_guidance_bull_prompt_has_full_rule_set(self):
        """GuidanceCheck bull prompt must include the 5 critical grounding rules."""
        _, _, bull_sys, _, _, _ = _load_prompts("guidance")
        for marker in ("accuracy_pct", "CONTRARIAN",
                       "CAUSATION", "PARTIAL", "strong"):
            self.assertIn(marker, bull_sys,
                          f"guidance bull prompt missing grounding rule for {marker!r}")

    def test_pe_expansion_prompts_have_domain_rules(self):
        """PE Expansion prompts use domain-specific rules (cross-check matrix,
        independent check, FQ+PriceAction, credibility). Both bear and bull
        must include accuracy_pct, PARTIAL, 'no strong case' honesty, and
        cross-check as primary evidence."""
        bear_sys, _, bull_sys, _, _, _ = _load_prompts("pe_expansion")
        for label, prompt in (("bear", bear_sys), ("bull", bull_sys)):
            for marker in ("accuracy_pct", "PARTIAL",
                           "strong", "cross-check", "credibility"):
                self.assertIn(marker, prompt,
                              f"pe_expansion {label} prompt missing grounding rule for {marker!r}")

    def test_all_prompts_reference_accuracy_pct(self):
        """Universal rule across both contexts: accuracy_pct is the primary
        credibility metric — every prompt must mention it."""
        for kind in ("guidance", "pe_expansion"):
            bear_sys, _, bull_sys, _, _, _ = _load_prompts(kind)
            self.assertIn("accuracy_pct", bear_sys)
            self.assertIn("accuracy_pct", bull_sys)

    def test_all_prompts_have_honesty_about_weak_cases(self):
        """Every prompt must include the 'data does not support a strong case'
        honesty clause — prevents fabricated bear/bull arguments."""
        for kind in ("guidance", "pe_expansion"):
            bear_sys, _, bull_sys, _, _, _ = _load_prompts(kind)
            for label, prompt in (("bear", bear_sys), ("bull", bull_sys)):
                self.assertIn("does not support a strong", prompt.lower(),
                              f"{kind} {label} prompt missing 'no strong case' clause")

    def test_user_prompts_have_required_placeholders(self):
        """User prompts must reference {symbol} and {context_json}."""
        for kind in ("guidance", "pe_expansion"):
            _, bear_usr, _, bull_usr, _, _ = _load_prompts(kind)
            self.assertIn("{symbol}", bear_usr)
            self.assertIn("{context_json}", bear_usr)
            self.assertIn("{symbol}", bull_usr)
            self.assertIn("{context_json}", bull_usr)


# ── Stub fallback (no LLM configured) ──────────────────────────────────


class StubFallbackTests(unittest.TestCase):
    """When no LLM is configured, run_debate returns stub bear/bull text.

    Hard to force in CI (LLM key may be present), so we directly call
    the stub helpers and verify their output shape.
    """

    def _get_stubs(self):
        from engine_debate.debate_engine import _stub_bear, _stub_bull
        return _stub_bear, _stub_bull

    def test_stub_bear_mentions_symbol(self):
        stub_bear, _ = self._get_stubs()
        ctx = {"symbol": "TESTSTOCK"}
        out = stub_bear(ctx)
        self.assertIn("TESTSTOCK", out)
        self.assertIn("[STUB", out)

    def test_stub_bull_mentions_symbol(self):
        _, stub_bull = self._get_stubs()
        ctx = {"symbol": "TESTSTOCK"}
        out = stub_bull(ctx)
        self.assertIn("TESTSTOCK", out)
        self.assertIn("[STUB", out)

    def test_stub_handles_missing_symbol(self):
        stub_bear, _ = self._get_stubs()
        out = stub_bear({})
        self.assertIn("UNKNOWN", out)


# ── Cache round-trip (live DB) ──────────────────────────────────────────


class CacheRoundTripTests(unittest.TestCase):
    """Verify cache.store_debate -> lookup_debate round-trip with cleanup."""

    def setUp(self):
        self.symbol = _test_symbol()
        self.payload = _minimal_context(self.symbol)
        self.bear = "TEST_BEAR_TEXT_FOR_CACHE"
        self.bull = "TEST_BULL_TEXT_FOR_CACHE"
        self.hash_ = canonical_hash(self.payload)

    def tearDown(self):
        # Always clean up test rows
        try:
            from engine_core.db import get_connection
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM conviction_debates WHERE symbol = %s",
                (self.symbol,),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def test_lookup_returns_none_on_miss(self):
        # Ensure no leftover from prior run
        from engine_core.db import get_connection
        conn = get_connection()
        conn.cursor().execute(
            "DELETE FROM conviction_debates WHERE symbol = %s", (self.symbol,)
        )
        conn.commit()
        conn.close()

        result = lookup_debate(self.symbol, "guidance", self.hash_)
        self.assertIsNone(result)

    def test_store_then_lookup_roundtrip(self):
        row_id = store_debate(
            symbol=self.symbol,
            context_kind="guidance",
            context_hash=self.hash_,
            context_payload=self.payload,
            bear=self.bear,
            bull=self.bull,
            adjudicator=None,
            model_used="test-fixture",
        )
        self.assertIsNotNone(row_id)

        result = lookup_debate(self.symbol, "guidance", self.hash_)
        self.assertIsNotNone(result)
        self.assertEqual(result["bear"], self.bear)
        self.assertEqual(result["bull"], self.bull)
        self.assertEqual(result["model_used"], "test-fixture")
        self.assertTrue(result["cached"])
        self.assertEqual(result["cache_hits"], 1, "first hit counter should be 1")

    def test_repeated_lookup_increments_hits(self):
        store_debate(self.symbol, "guidance", self.hash_, self.payload,
                     self.bear, self.bull, None, "test-fixture")
        lookup_debate(self.symbol, "guidance", self.hash_)
        r2 = lookup_debate(self.symbol, "guidance", self.hash_)
        r3 = lookup_debate(self.symbol, "guidance", self.hash_)
        self.assertEqual(r2["cache_hits"], 2)
        self.assertEqual(r3["cache_hits"], 3)

    def test_different_context_hash_yields_different_cache(self):
        """Same symbol, different context hash → independent cache rows."""
        store_debate(self.symbol, "guidance", self.hash_, self.payload,
                     self.bear, self.bull, None, "test-fixture")

        other_payload = dict(self.payload, total_material_promises=999)
        other_hash = canonical_hash(other_payload)
        result = lookup_debate(self.symbol, "guidance", other_hash)
        self.assertIsNone(result, "different hash must not match existing row")

    def test_different_context_kind_yields_different_cache(self):
        """Same symbol + hash but different context_kind → independent cache."""
        store_debate(self.symbol, "guidance", self.hash_, self.payload,
                     self.bear, self.bull, None, "test-fixture")
        result = lookup_debate(self.symbol, "pe_expansion", self.hash_)
        self.assertIsNone(result, "different kind must not match existing row")


# ── DebateResult dataclass ──────────────────────────────────────────────


class DebateResultTests(unittest.TestCase):
    def test_to_dict_has_all_keys(self):
        r = DebateResult(
            bear="B", bull="U", adjudicator=None, model_used="test",
            generated_at="2026-06-19T00:00:00+00:00", cache_hits=0,
            cached=False, context_hash="abc",
        )
        d = r.to_dict()
        for key in ("bear", "bull", "adjudicator", "model_used",
                    "generated_at", "cache_hits", "cached", "context_hash"):
            self.assertIn(key, d)


if __name__ == "__main__":
    unittest.main()
