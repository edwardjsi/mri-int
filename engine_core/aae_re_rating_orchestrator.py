"""AAE Re-Rating Candidate Profile Orchestrator.

Upgraded orchestrator that combines the existing 10-layer forensic pipeline
with the new PRDE scoring engine, structural signal agent, macro agent,
and execution monitoring agent to produce a full Re-Rating Candidate Profile.

This is Milestone 5: the master synthesis layer.

Usage:
    python engine_core/aae_re_rating_orchestrator.py --symbol RELIANCE
    python engine_core/aae_re_rating_orchestrator.py --limit 20
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date
from typing import Any
from uuid import uuid4

from engine_core.db import get_connection
from engine_fundamental.aae_orchestrator import AAEOrchestrator  # legacy 10-layer
from engine_core.prde_scoring_engine import compute_master_score  # PRDE scoring
from engine_core.aae_structural_signal_agent import StructuralSignalAgent
from engine_core.aae_macro_agent import MacroCorrelationAgent
from engine_core.aae_execution_monitoring_agent import ExecutionMonitoringAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("aae_re_rating")


def thesis_hash(thesis: dict) -> str:
    payload = json.dumps(thesis, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class ReRatingOrchestrator:
    """Produces a full Re-Rating Candidate Profile by synthesizing all AAE layers."""

    def __init__(self, symbol: str):
        self.symbol = symbol.upper()

    def build_profile(self) -> dict[str, Any]:
        """Build a complete Re-Rating Candidate Profile.

        Returns a dict ready for persistence and display.
        """
        profile: dict[str, Any] = {
            "symbol": self.symbol,
            "as_of_date": str(date.today()),
        }

        # ── Layer A: Governance Kill Switch ──
        gov_result = self._run_governance_check()
        profile["governance"] = gov_result
        if gov_result.get("rejected"):
            profile["status"] = "REJECTED"
            profile["rejection_reason"] = gov_result["reason"]
            profile["rerating_probability_score"] = 0.0
            return profile

        # ── Layer B: PRDE Financial Fingerprint ──
        prde_result = self._run_prde_scoring()
        profile["financial_fingerprint"] = prde_result
        profile["master_checklist_score"] = prde_result.get("master_score", 50.0)

        # ── Layer C: AAE Legacy 10-Layer Scan ──
        try:
            legacy = AAEOrchestrator(self.symbol).run_full_scan()
            profile["legacy_forensic"] = {
                "master_score": legacy.get("master_score"),
                "status": legacy.get("status"),
                "layers": legacy.get("layers", {}),
            }
            profile["forensic_score"] = legacy.get("master_score", 50.0)
        except Exception as e:
            logger.warning(f"Legacy forensic scan failed for {self.symbol}: {e}")
            profile["legacy_forensic"] = {"error": str(e)}
            profile["forensic_score"] = 50.0

        # ── Layer D: Structural Signals ──
        structural_result = self._run_structural_signals()
        profile["structural_signals"] = structural_result
        profile["structural_conviction_score"] = structural_result.get("conviction_score", 0)

        # ── Layer E: Macro Alignment ──
        macro_result = self._run_macro()
        profile["macro_alignment"] = macro_result
        profile["macro_alignment_score"] = macro_result.get("macro_alignment_score", 50.0)

        # ── Layer F: Risk Monitoring ──
        risk_result = self._run_risk_monitor()
        profile["risk_state"] = risk_result
        profile["risk_level"] = risk_result.get("overall_risk_state", "CLEAN")

        # ── Re-Rating Probability Score ──
        # Weighted synthesis of all layers
        prde_score = profile.get("master_checklist_score", 50.0)
        forensic_score = profile.get("forensic_score", 50.0)
        structural_score = profile.get("structural_conviction_score", 0)
        macro_score = profile.get("macro_alignment_score", 50.0)

        rerating_probability = (
            prde_score * 0.30 +
            forensic_score * 0.30 +
            structural_score * 0.25 +
            macro_score * 0.15
        )

        # Risk penalty
        risk_level = profile["risk_level"]
        if risk_level == "THESIS_AT_RISK":
            rerating_probability -= 25
        elif risk_level == "WATCH_CLOSELY":
            rerating_probability -= 10
        elif risk_level == "MONITOR":
            rerating_probability -= 5

        profile["rerating_probability_score"] = round(max(0, min(100, rerating_probability)), 1)

        # ── Thesis Construction ──
        thesis = self._build_thesis(profile)
        profile["thesis"] = thesis
        profile["thesis_version"] = 1  # initial version; incremented on change

        # ── Score classification ──
        profile["score_interpretation"] = self._classify_score(profile["rerating_probability_score"])

        profile["status"] = "ACTIVE"
        return profile

    def _run_governance_check(self) -> dict:
        """Run governance kill switch check."""
        try:
            from engine_fundamental.governance_engine import GovernanceEngine
            gov = GovernanceEngine(self.symbol)
            data = gov.fetch_governance_data()
            killed, reason = gov.evaluate_kill_switch(data)
            return {"rejected": killed, "reason": reason, "data": data}
        except Exception as e:
            return {"rejected": False, "reason": f"governance check unavailable: {e}", "data": None}

    def _run_prde_scoring(self) -> dict:
        """Run PRDE deterministic scoring."""
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.features
                    FROM public.prde_feature_snapshots s
                    JOIN public.prde_companies c ON c.id = s.company_id
                    WHERE c.ticker = %s
                    ORDER BY s.created_at DESC
                    LIMIT 1
                    """,
                    (self.symbol,),
                )
                row = cur.fetchone()
                if not row:
                    return {"master_score": 50.0, "error": "no PRDE feature snapshot"}

                features = row["features"]
                if isinstance(features, str):
                    features = json.loads(features)

                # Get MRI score for overlay
                cur.execute(
                    "SELECT total_score FROM public.stock_scores WHERE symbol = %s ORDER BY date DESC LIMIT 1",
                    (self.symbol,),
                )
                mri_row = cur.fetchone()
                mri_score = float(mri_row["total_score"]) if mri_row else None

                return compute_master_score(features, mri_score)
        finally:
            conn.close()

    def _run_structural_signals(self) -> dict:
        """Run structural signal agent."""
        try:
            agent = StructuralSignalAgent(self.symbol)
            return agent.evaluate()
        except Exception as e:
            return {"conviction_score": 0, "error": str(e)}

    def _run_macro(self) -> dict:
        """Run macro correlation agent."""
        try:
            agent = MacroCorrelationAgent(self.symbol)
            return agent.evaluate()
        except Exception as e:
            return {"macro_alignment_score": 50.0, "error": str(e)}

    def _run_risk_monitor(self) -> dict:
        """Run execution monitoring agent."""
        try:
            agent = ExecutionMonitoringAgent(self.symbol)
            return agent.evaluate()
        except Exception as e:
            return {"overall_risk_state": "CLEAN", "error": str(e)}

    def _build_thesis(self, profile: dict) -> dict:
        """Build investment thesis from all layers."""
        reasons = []
        risks = []

        # Financial strength
        prde = profile.get("financial_fingerprint", {})
        if prde.get("master_score", 0) >= 70:
            reasons.append(f"Strong financial fingerprint: Master Checklist score {prde['master_score']:.0f}/100")
        elif prde.get("master_score", 0) >= 50:
            reasons.append(f"Adequate financial foundation: Master Checklist score {prde['master_score']:.0f}/100")
        else:
            risks.append(f"Weak financial metrics: Master Checklist score {prde['master_score']:.0f}/100")

        # Structural signals
        structural = profile.get("structural_signals", {})
        if structural.get("high_conviction"):
            reasons.append(f"Structural conviction: {structural['active_count']}/6 signals active — {', '.join(structural['active_signals'])}")
        elif structural.get("active_count", 0) > 0:
            reasons.append(f"Emerging structural signals: {structural['active_count']}/6 active — {', '.join(structural.get('active_signals', []))}")
        else:
            risks.append("No active structural signals detected")

        # Macro
        macro = profile.get("macro_alignment", {})
        if macro.get("outlook", "").startswith("STRONG TAILWIND"):
            reasons.append(f"Strong macro tailwind: {macro.get('sector', 'Unknown')} sector ({macro['macro_alignment_score']:.0f}/100)")
        elif macro.get("outlook", "").startswith("MODERATE HEADWIND") or macro.get("outlook", "").startswith("STRONG HEADWIND"):
            risks.append(f"Macro headwind: {macro.get('outlook', 'Neutral')} for {macro.get('sector', 'Unknown')} sector")
        else:
            reasons.append(f"Macro context: {macro.get('outlook', 'Neutral')} for {macro.get('sector', 'Unknown')} sector")

        # Risk state
        risk = profile.get("risk_state", {})
        if risk.get("alerts"):
            for alert in risk["alerts"]:
                risks.append(f"[{alert['severity']}] {alert['category']}: {alert['detail']} → {alert.get('suggested_action', 'Watch')}")

        # Score summary
        score = profile["rerating_probability_score"]
        if score >= 80:
            verdict = "HIGH CONVICTION — institutional rerating candidate"
        elif score >= 65:
            verdict = "EMERGING — rerating setup forming, monitor for confirmation"
        elif score >= 50:
            verdict = "NEUTRAL — insufficient evidence for rerating thesis"
        else:
            verdict = "AVOID — insufficient convergence or active risk flags"

        return {
            "summary": verdict,
            "score": score,
            "reasons": reasons,
            "risks": risks,
            "generated_at": str(date.today()),
        }

    def _classify_score(self, score: float) -> str:
        if score >= 80:
            return "Institutional rerating candidate"
        elif score >= 65:
            return "Emerging rerating setup"
        elif score >= 50:
            return "Monitor closely"
        else:
            return "Noise / insufficient convergence"

    def persist_profile(self, profile: dict) -> str:
        """Persist the Re-Rating Candidate Profile to database."""
        from psycopg2.extras import Json

        conn = get_connection()
        try:
            with conn.cursor() as cur:
                # Ensure the profile table exists
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS public.aae_re_rating_profiles (
                        symbol          VARCHAR(20) PRIMARY KEY,
                        profile         JSONB NOT NULL,
                        thesis_version  INT DEFAULT 1,
                        thesis_hash     VARCHAR(32),
                        updated_at      TIMESTAMPTZ DEFAULT NOW()
                    );
                    """
                )

                thesis_hash_val = thesis_hash(profile.get("thesis", {}))

                cur.execute(
                    """
                    INSERT INTO public.aae_re_rating_profiles (symbol, profile, thesis_version, thesis_hash)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (symbol) DO UPDATE SET
                        profile         = EXCLUDED.profile,
                        thesis_version  = public.aae_re_rating_profiles.thesis_version + 1,
                        thesis_hash     = EXCLUDED.thesis_hash,
                        updated_at      = NOW()
                    RETURNING thesis_version
                    """,
                    (self.symbol, Json(profile), 1, thesis_hash_val),
                )
                version = cur.fetchone()["thesis_version"]
                conn.commit()

                logger.info(f"Persisted Re-Rating Profile for {self.symbol} (v{version})")
                return str(version)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def batch_scan(limit: int = 20, persist: bool = True) -> list[dict]:
    """Run Re-Rating Profile generation across the PRDE universe."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.ticker
                FROM public.prde_companies c
                WHERE c.is_active = TRUE
                  AND EXISTS (
                      SELECT 1 FROM public.prde_feature_snapshots s WHERE s.company_id = c.id
                  )
                ORDER BY c.ticker
                LIMIT %s
                """,
                (limit,),
            )
            tickers = [row[0] for row in cur.fetchall()]
    finally:
        conn.close()

    results = []
    for ticker in tickers:
        logger.info(f"Building Re-Rating Profile for {ticker}...")
        orchestrator = ReRatingOrchestrator(ticker)
        profile = orchestrator.build_profile()

        if persist:
            orchestrator.persist_profile(profile)

        results.append({
            "symbol": ticker,
            "rerating_score": profile["rerating_probability_score"],
            "master_checklist": profile.get("master_checklist_score"),
            "risk_level": profile.get("risk_level"),
            "thesis": profile.get("thesis", {}).get("summary", ""),
        })

    return sorted(results, key=lambda x: x["rerating_score"], reverse=True)


def main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="AAE Re-Rating Candidate Profile Orchestrator")
    parser.add_argument("--symbol", help="Build profile for a single ticker")
    parser.add_argument("--limit", type=int, default=0, help="Batch scan N companies")
    parser.add_argument("--no-persist", action="store_true", help="Skip persistence")
    args = parser.parse_args()

    if args.limit:
        results = batch_scan(limit=args.limit, persist=not args.no_persist)
        print(f"\n{'Rank':>4}  {'Symbol':<12} {'Re-Rating':>10}  {'PRDE':>7}  {'Risk':<16}  {'Thesis'}")
        print("-" * 90)
        for rank, r in enumerate(results, 1):
            print(f"{rank:>4}  {r['symbol']:<12} {r['rerating_score']:>10.1f}  {r['master_checklist']:>7.1f}  {r['risk_level']:<16}  {r['thesis'][:50]}")
    elif args.symbol:
        orchestrator = ReRatingOrchestrator(args.symbol)
        profile = orchestrator.build_profile()
        print(json.dumps(profile, indent=2, default=str))
        if not args.no_persist:
            version = orchestrator.persist_profile(profile)
            print(f"\nPersisted as version {version}")
    else:
        print("Specify --symbol or --limit N")
        sys.exit(1)


if __name__ == "__main__":
    main()
