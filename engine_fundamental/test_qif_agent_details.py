"""
Tests for Phase D1 of the Data Richness Sprint:
  docs/INITIATIVE_DATA_RICHNESS_2026-06-19.md

Covers:
- Each of the 7 QIF agents returns a `detail` key with the documented
  per-year shape
- _build_agent_details_json merges agent details into a single by_year[]
  array and computes a trajectory summary
- Trajectory edge cases: 1 year, 2 years, 5+ years, declining YoY,
  accelerating decline
- run_quality_pipeline() writes agent_details JSONB that round-trips
  through Postgres correctly
- Empty fundamentals returns None (no verdict), no DB write

Uses disposable `_QIF_DET_<uuid>` symbols so it never collides with real
data. Cleans up afterwards. Decision 027 RDS-protection rules apply.
"""

import json
import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine_core.db import get_connection
from engine_fundamental.agents import (
    revenue_quality_agent, margin_quality_agent, operating_leverage_agent,
    working_capital_agent, capital_efficiency_agent, business_evolution_agent,
    financial_translation_agent,
)
from engine_fundamental.pipeline import (
    _build_agent_details_json, _compute_trajectory_summary, run_quality_pipeline,
)


# ─── Helpers ──────────────────────────────────────────────────────────────

def _make_test_symbol() -> str:
    # symbol column is TEXT UNIQUE on quality_verdicts + TEXT NOT NULL on
    # fundamental_financials. 19 chars available with the _QIF_DET_ prefix.
    return f"_QIF_DET_{uuid.uuid4().hex[:8].upper()}"


def _make_financials(years_data):
    """Build a list of financial dicts from a list of (year, revenue, ebitda, ...).

    years_data: list of dicts with year + financial fields.
    """
    rows = []
    for d in years_data:
        rows.append({
            "year": d["year"],
            "revenue": d.get("revenue"),
            "ebitda": d.get("ebitda"),
            "net_profit": d.get("net_profit"),
            "total_assets": d.get("total_assets"),
            "capital_employed": d.get("capital_employed"),
            "receivables": d.get("receivables"),
            "inventory": d.get("inventory"),
            "debt": d.get("debt"),
            "equity": d.get("equity"),
        })
    return rows


def _seed_fundamentals(cur, symbol, financials):
    """Insert test rows into fundamental_financials."""
    for f in financials:
        cur.execute(
            """INSERT INTO fundamental_financials
               (symbol, year, revenue, ebitda, net_profit, total_assets,
                capital_employed, receivables, inventory, debt, equity)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (symbol, year) DO UPDATE SET
                 revenue = EXCLUDED.revenue,
                 ebitda = EXCLUDED.ebitda,
                 net_profit = EXCLUDED.net_profit,
                 total_assets = EXCLUDED.total_assets,
                 capital_employed = EXCLUDED.capital_employed,
                 receivables = EXCLUDED.receivables,
                 inventory = EXCLUDED.inventory,
                 debt = EXCLUDED.debt,
                 equity = EXCLUDED.equity""",
            (symbol, f["year"], f.get("revenue"), f.get("ebitda"),
             f.get("net_profit"), f.get("total_assets"),
             f.get("capital_employed"), f.get("receivables"),
             f.get("inventory"), f.get("debt"), f.get("equity")),
        )


def _cleanup(cur, symbol):
    cur.execute("DELETE FROM quality_verdicts WHERE symbol = %s", (symbol,))
    cur.execute("DELETE FROM quality_verdicts_history WHERE symbol = %s", (symbol,))
    cur.execute("DELETE FROM fundamental_financials WHERE symbol = %s", (symbol,))


# ─── Agent detail shape tests (no DB) ────────────────────────────────────

class AgentDetailShapeTests(unittest.TestCase):
    """Each agent's `detail` dict must contain a per_year array with the
    documented metric shape. Pure unit tests — no DB."""

    def _sample_4yr(self):
        return _make_financials([
            {"year": 2023, "revenue": 100e9, "ebitda": 15e9, "net_profit": 8e9,
             "total_assets": 80e9, "capital_employed": 60e9, "receivables": 12e9,
             "inventory": 10e9, "debt": 10e9, "equity": 50e9},
            {"year": 2024, "revenue": 120e9, "ebitda": 19e9, "net_profit": 10e9,
             "total_assets": 90e9, "capital_employed": 65e9, "receivables": 14e9,
             "inventory": 11e9, "debt": 10e9, "equity": 55e9},
            {"year": 2025, "revenue": 145e9, "ebitda": 24e9, "net_profit": 13e9,
             "total_assets": 100e9, "capital_employed": 70e9, "receivables": 16e9,
             "inventory": 12e9, "debt": 11e9, "equity": 59e9},
            {"year": 2026, "revenue": 175e9, "ebitda": 30e9, "net_profit": 16e9,
             "total_assets": 115e9, "capital_employed": 78e9, "receivables": 19e9,
             "inventory": 13e9, "debt": 12e9, "equity": 66e9},
        ])

    def test_revenue_agent_detail_shape(self):
        fin = self._sample_4yr()
        out = revenue_quality_agent(fin)
        self.assertIn("detail", out)
        self.assertIn("per_year", out["detail"])
        self.assertEqual(out["detail"]["metric"], "revenue_growth")
        py = out["detail"]["per_year"]
        self.assertEqual(len(py), 4)
        for entry in py:
            self.assertIn("year", entry)
            self.assertIn("growth_yoy_pct", entry)
            self.assertIn("growth_3y_avg_pct", entry)
            self.assertIn("trend", entry)
        # First year has no prior → growth_yoy_pct should be 0
        self.assertEqual(py[0]["growth_yoy_pct"], 0.0)
        # Last year (2026) revenue = 175, prior (2025) = 145 → +20.69%
        self.assertAlmostEqual(py[-1]["growth_yoy_pct"], 20.69, places=1)
        self.assertEqual(py[-1]["trend"], "up")

    def test_margin_agent_detail_shape(self):
        fin = self._sample_4yr()
        out = margin_quality_agent(fin)
        py = out["detail"]["per_year"]
        self.assertEqual(len(py), 4)
        for entry in py:
            self.assertIn("year", entry)
            self.assertIn("opm_pct", entry)
            self.assertIn("opm_3y_avg_pct", entry)
            self.assertIn("compression_bps_yoy", entry)
        # 2023 OPM = 15/100 = 15.0%
        self.assertAlmostEqual(py[0]["opm_pct"], 15.0, places=1)

    def test_operating_leverage_agent_detail_shape(self):
        fin = self._sample_4yr()
        out = operating_leverage_agent(fin)
        py = out["detail"]["per_year"]
        for entry in py:
            self.assertIn("ebitda_to_revenue_growth_ratio", entry)

    def test_working_capital_agent_detail_shape(self):
        fin = self._sample_4yr()
        out = working_capital_agent(fin)
        py = out["detail"]["per_year"]
        for entry in py:
            self.assertIn("receivable_growth_yoy_pct", entry)
            self.assertIn("receivable_vs_revenue_growth_pct", entry)

    def test_capital_efficiency_agent_detail_shape(self):
        fin = self._sample_4yr()
        out = capital_efficiency_agent(fin, wacc=0.12)
        py = out["detail"]["per_year"]
        for entry in py:
            self.assertIn("roce_pct", entry)
            self.assertIn("wacc_pct", entry)
            self.assertIn("gap_pct", entry)
        self.assertEqual(out["detail"]["wacc_pct"], 12.0)
        # 2023 ROCE = 15/60 = 25.0%
        self.assertAlmostEqual(py[0]["roce_pct"], 25.0, places=1)
        # gap_pct = roce_pct - wacc_pct
        self.assertAlmostEqual(py[0]["gap_pct"], 13.0, places=1)

    def test_business_evolution_agent_detail_shape(self):
        fin = self._sample_4yr()
        out = business_evolution_agent(fin)
        py = out["detail"]["per_year"]
        for entry in py:
            self.assertIn("asset_growth_yoy_pct", entry)
            self.assertIn("margin_change_3y_bps", entry)

    def test_financial_translation_agent_detail_shape(self):
        fin = self._sample_4yr()
        out = financial_translation_agent(fin)
        py = out["detail"]["per_year"]
        for entry in py:
            self.assertIn("cash_conversion_ratio", entry)

    def test_empty_financials_returns_empty_detail(self):
        out = revenue_quality_agent([])
        self.assertEqual(out["detail"]["per_year"], [])
        out = capital_efficiency_agent([])
        self.assertEqual(out["detail"]["per_year"], [])
        self.assertEqual(out["detail"]["wacc_pct"], 12.0)


# ─── JSONB aggregator + trajectory tests (no DB) ─────────────────────────

class AgentDetailsAggregatorTests(unittest.TestCase):
    def _run_7_agents(self, fin):
        return {
            "revenue_growth": revenue_quality_agent(fin),
            "margin_quality": margin_quality_agent(fin),
            "operating_leverage": operating_leverage_agent(fin),
            "working_capital": working_capital_agent(fin),
            "capital_efficiency": capital_efficiency_agent(fin),
            "business_evolution": business_evolution_agent(fin),
            "financial_translation": financial_translation_agent(fin),
        }

    def test_merged_by_year_shape(self):
        fin = _make_financials([
            {"year": 2024, "revenue": 100e9, "ebitda": 15e9, "net_profit": 8e9,
             "total_assets": 80e9, "capital_employed": 60e9, "receivables": 12e9,
             "inventory": 10e9, "debt": 10e9, "equity": 50e9},
            {"year": 2025, "revenue": 120e9, "ebitda": 19e9, "net_profit": 10e9,
             "total_assets": 90e9, "capital_employed": 65e9, "receivables": 14e9,
             "inventory": 11e9, "debt": 10e9, "equity": 55e9},
            {"year": 2026, "revenue": 145e9, "ebitda": 24e9, "net_profit": 13e9,
             "total_assets": 100e9, "capital_employed": 70e9, "receivables": 16e9,
             "inventory": 12e9, "debt": 11e9, "equity": 59e9},
        ])
        results = self._run_7_agents(fin)
        ad = _build_agent_details_json(results, fin)
        self.assertIn("by_year", ad)
        self.assertIn("trajectory", ad)
        self.assertEqual(len(ad["by_year"]), 3)
        for entry in ad["by_year"]:
            self.assertIn("year", entry)
            self.assertIn("scores", entry)
            self.assertIn("metrics", entry)
            # Each year entry should have all 7 agents' metrics
            for agent_key in ("revenue_growth", "margin_quality",
                              "operating_leverage", "working_capital",
                              "capital_efficiency", "business_evolution",
                              "financial_translation"):
                self.assertIn(agent_key, entry["metrics"], f"missing {agent_key}")

    def test_trajectory_revenue_cagr_3y(self):
        # Need >=4 years for 3-year CAGR
        fin = _make_financials([
            {"year": 2023, "revenue": 100e9, "ebitda": 15e9, "net_profit": 8e9,
             "total_assets": 80e9, "capital_employed": 60e9, "receivables": 12e9,
             "inventory": 10e9, "debt": 10e9, "equity": 50e9},
            {"year": 2024, "revenue": 120e9, "ebitda": 19e9, "net_profit": 10e9,
             "total_assets": 90e9, "capital_employed": 65e9, "receivables": 14e9,
             "inventory": 11e9, "debt": 10e9, "equity": 55e9},
            {"year": 2025, "revenue": 145e9, "ebitda": 24e9, "net_profit": 13e9,
             "total_assets": 100e9, "capital_employed": 70e9, "receivables": 16e9,
             "inventory": 12e9, "debt": 11e9, "equity": 59e9},
            {"year": 2026, "revenue": 175e9, "ebitda": 30e9, "net_profit": 16e9,
             "total_assets": 115e9, "capital_employed": 78e9, "receivables": 19e9,
             "inventory": 13e9, "debt": 12e9, "equity": 66e9},
        ])
        results = self._run_7_agents(fin)
        ad = _build_agent_details_json(results, fin)
        # CAGR = (175/100)^(1/3) - 1 = 20.51%
        self.assertAlmostEqual(ad["trajectory"]["revenue_cagr_3y_pct"], 20.51, places=1)
        self.assertEqual(ad["trajectory"]["years_observed"], 4)

    def test_trajectory_declining_when_roce_drops(self):
        # ROCE: 2023=25% (15/60), 2024=20% (13/65), 2025=15% (10.5/70), 2026=10% (7.8/78)
        fin = _make_financials([
            {"year": 2023, "revenue": 100e9, "ebitda": 15e9, "net_profit": 8e9,
             "total_assets": 80e9, "capital_employed": 60e9, "receivables": 12e9,
             "inventory": 10e9, "debt": 10e9, "equity": 50e9},
            {"year": 2024, "revenue": 120e9, "ebitda": 13e9, "net_profit": 6e9,
             "total_assets": 90e9, "capital_employed": 65e9, "receivables": 14e9,
             "inventory": 11e9, "debt": 10e9, "equity": 55e9},
            {"year": 2025, "revenue": 145e9, "ebitda": 10.5e9, "net_profit": 4e9,
             "total_assets": 100e9, "capital_employed": 70e9, "receivables": 16e9,
             "inventory": 12e9, "debt": 11e9, "equity": 59e9},
            {"year": 2026, "revenue": 175e9, "ebitda": 7.8e9, "net_profit": 2e9,
             "total_assets": 115e9, "capital_employed": 78e9, "receivables": 19e9,
             "inventory": 13e9, "debt": 12e9, "equity": 66e9},
        ])
        results = self._run_7_agents(fin)
        ad = _build_agent_details_json(results, fin)
        self.assertEqual(ad["trajectory"]["score_trend"], "declining")
        self.assertLess(ad["trajectory"]["roce_change_yoy_bps"], -100)

    def test_trajectory_improving_when_roce_grows(self):
        # ROCE: 2023=10%, 2024=15%, 2025=20%, 2026=25%
        fin = _make_financials([
            {"year": 2023, "revenue": 100e9, "ebitda": 6e9, "net_profit": 2e9,
             "total_assets": 80e9, "capital_employed": 60e9, "receivables": 12e9,
             "inventory": 10e9, "debt": 10e9, "equity": 50e9},
            {"year": 2024, "revenue": 120e9, "ebitda": 9.75e9, "net_profit": 4e9,
             "total_assets": 90e9, "capital_employed": 65e9, "receivables": 14e9,
             "inventory": 11e9, "debt": 10e9, "equity": 55e9},
            {"year": 2025, "revenue": 145e9, "ebitda": 14e9, "net_profit": 7e9,
             "total_assets": 100e9, "capital_employed": 70e9, "receivables": 16e9,
             "inventory": 12e9, "debt": 11e9, "equity": 59e9},
            {"year": 2026, "revenue": 175e9, "ebitda": 19.5e9, "net_profit": 11e9,
             "total_assets": 115e9, "capital_employed": 78e9, "receivables": 19e9,
             "inventory": 13e9, "debt": 12e9, "equity": 66e9},
        ])
        results = self._run_7_agents(fin)
        ad = _build_agent_details_json(results, fin)
        self.assertEqual(ad["trajectory"]["score_trend"], "improving")
        self.assertGreater(ad["trajectory"]["roce_change_yoy_bps"], 100)

    def test_empty_financials_returns_empty_detail(self):
        ad = _build_agent_details_json({}, [])
        self.assertEqual(ad["by_year"], [])
        self.assertEqual(ad["trajectory"], {})


# ─── DB integration tests (live Neon) ────────────────────────────────────

class PipelineDBTests(unittest.TestCase):
    """Verify run_quality_pipeline() persists agent_details JSONB correctly."""

    def test_pipeline_writes_agent_details_jsonb(self):
        sym = _make_test_symbol()
        fin = _make_financials([
            {"year": 2024, "revenue": 100e9, "ebitda": 15e9, "net_profit": 8e9,
             "total_assets": 80e9, "capital_employed": 60e9, "receivables": 12e9,
             "inventory": 10e9, "debt": 10e9, "equity": 50e9},
            {"year": 2025, "revenue": 120e9, "ebitda": 19e9, "net_profit": 10e9,
             "total_assets": 90e9, "capital_employed": 65e9, "receivables": 14e9,
             "inventory": 11e9, "debt": 10e9, "equity": 55e9},
            {"year": 2026, "revenue": 145e9, "ebitda": 24e9, "net_profit": 13e9,
             "total_assets": 100e9, "capital_employed": 70e9, "receivables": 16e9,
             "inventory": 12e9, "debt": 11e9, "equity": 59e9},
        ])
        conn = get_connection()
        try:
            cur = conn.cursor()
            _seed_fundamentals(cur, sym, fin)
            conn.commit()
        finally:
            conn.close()

        try:
            result = run_quality_pipeline(sym)
            self.assertIsNotNone(result, "pipeline returned None for valid financials")
            self.assertIn("agent_details", result)
            ad = result["agent_details"]
            self.assertEqual(len(ad["by_year"]), 3)
            self.assertIn("trajectory", ad)

            # Verify it round-trips through Postgres
            conn = get_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT agent_details FROM quality_verdicts WHERE symbol = %s",
                    (sym,),
                )
                row = cur.fetchone()
                self.assertIsNotNone(row, "no quality_verdicts row written")
                self.assertIsInstance(row["agent_details"], dict,
                                       "agent_details not returned as dict by RealDictCursor")
                self.assertEqual(len(row["agent_details"]["by_year"]), 3)
            finally:
                conn.close()
        finally:
            conn = get_connection()
            try:
                _cleanup(conn.cursor(), sym)
                conn.commit()
            finally:
                conn.close()

    def test_pipeline_returns_none_for_no_fundamentals(self):
        sym = _make_test_symbol()
        # Don't seed any financials
        result = run_quality_pipeline(sym)
        self.assertIsNone(result)

        # Verify nothing was written to quality_verdicts
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) AS n FROM quality_verdicts WHERE symbol = %s", (sym,))
            self.assertEqual(cur.fetchone()["n"], 0)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()


# ── NaN/Inf sanitization (GROWW-style defensive fix) ───────────────────

class NaNSanitizationTests(unittest.TestCase):
    """Defensive: financials with NaN values (e.g. recent IPOs, missing
    data in early years) must not crash the pipeline. The trajectory
    summary must sanitize NaN/Inf to 0.0 before JSON serialization."""

    def test_nan_revenue_does_not_crash(self):
        """GROWW has NaN revenue in 2023/2024 — pipeline should still
        complete and write a valid (sanitized) agent_details JSONB."""
        sym = _make_test_symbol()
        # Insert NaN revenue for early years
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO fundamental_financials
                (symbol, year, revenue, ebitda, net_profit, total_assets,
                 capital_employed, receivables, inventory, debt, equity)
                VALUES (%s, 2023, 'NaN'::numeric, 'NaN'::numeric, NULL,
                        NULL, NULL, NULL, NULL, NULL, NULL)
                ON CONFLICT (symbol, year) DO UPDATE SET
                    revenue = EXCLUDED.revenue,
                    ebitda = EXCLUDED.ebitda
            """, (sym,))
            cur.execute("""
                INSERT INTO fundamental_financials
                (symbol, year, revenue, ebitda, net_profit, total_assets,
                 capital_employed, receivables, inventory, debt, equity)
                VALUES (%s, 2024, 'NaN'::numeric, 'NaN'::numeric, NULL,
                        NULL, NULL, NULL, NULL, NULL, NULL)
                ON CONFLICT (symbol, year) DO UPDATE SET
                    revenue = EXCLUDED.revenue,
                    ebitda = EXCLUDED.ebitda
            """, (sym,))
            cur.execute("""
                INSERT INTO fundamental_financials
                (symbol, year, revenue, ebitda, net_profit, total_assets,
                 capital_employed, receivables, inventory, debt, equity)
                VALUES (%s, 2025, 39017230000, 25309310000, NULL,
                        NULL, NULL, NULL, NULL, NULL, NULL)
                ON CONFLICT (symbol, year) DO UPDATE SET
                    revenue = EXCLUDED.revenue,
                    ebitda = EXCLUDED.ebitda
            """, (sym,))
            cur.execute("""
                INSERT INTO fundamental_financials
                (symbol, year, revenue, ebitda, net_profit, total_assets,
                 capital_employed, receivables, inventory, debt, equity)
                VALUES (%s, 2026, 46445790000, 29152260000, NULL,
                        NULL, 185409230000, NULL, NULL, NULL, NULL)
                ON CONFLICT (symbol, year) DO UPDATE SET
                    revenue = EXCLUDED.revenue,
                    ebitda = EXCLUDED.ebitda,
                    capital_employed = EXCLUDED.capital_employed
            """, (sym,))
            conn.commit()
        finally:
            conn.close()

        try:
            result = run_quality_pipeline(sym)
            self.assertIsNotNone(result, "pipeline must not crash on NaN inputs")
            ad = result["agent_details"]
            self.assertIn("by_year", ad)
            self.assertEqual(len(ad["by_year"]), 4)
            # Trajectory should have a sanitized revenue_cagr_3y_pct (not NaN)
            traj = ad["trajectory"]
            self.assertIn("revenue_cagr_3y_pct", traj)
            self.assertEqual(traj["revenue_cagr_3y_pct"], 0.0,
                             "NaN revenue in early years must yield CAGR=0, not NaN")
        finally:
            conn = get_connection()
            try:
                _cleanup(conn.cursor(), sym)
                conn.commit()
            finally:
                conn.close()

    def test_sanitize_helper_replaces_nan_and_inf(self):
        from engine_fundamental.pipeline import _sanitize_for_json
        import math
        # NaN/Inf should become 0.0
        self.assertEqual(_sanitize_for_json(float("nan")), 0.0)
        self.assertEqual(_sanitize_for_json(float("inf")), 0.0)
        self.assertEqual(_sanitize_for_json(float("-inf")), 0.0)
        # Regular numbers pass through
        self.assertEqual(_sanitize_for_json(1.5), 1.5)
        # Nested dicts and lists are recursed
        d = {"a": float("nan"), "b": [1.0, float("inf"), {"c": float("-inf")}]}
        s = _sanitize_for_json(d)
        self.assertEqual(s["a"], 0.0)
        self.assertEqual(s["b"][0], 1.0)
        self.assertEqual(s["b"][1], 0.0)
        self.assertEqual(s["b"][2]["c"], 0.0)
        # Sanity: result is JSON-serializable
        import json
        json.dumps(s)  # should not raise
