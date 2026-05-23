"""AAE Macro Correlation Agent.

Aligns company and sector re-rating potential with macro, policy,
valuation, and flows context.

Usage:
    python engine_core/aae_macro_agent.py --symbol RELIANCE
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from engine_core.db import fetch_df

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("aae_macro")

# ---------------------------------------------------------------------------
# Sector → Macro sensitivity mapping
# Higher sensitivity = sector more affected by macro/policy changes
# ---------------------------------------------------------------------------

SECTOR_MACRO_SENSITIVITY: dict[str, dict[str, float]] = {
    "BANKS":         {"rates": 0.9, "gdp": 0.8, "fiscal": 0.5, "policy": 0.6},
    "NBFC":          {"rates": 0.8, "gdp": 0.7, "fiscal": 0.4, "policy": 0.5},
    "IT":            {"rates": 0.2, "gdp": 0.6, "fiscal": 0.1, "policy": 0.3, "currency": 0.7},
    "PHARMA":        {"rates": 0.2, "gdp": 0.3, "fiscal": 0.2, "policy": 0.4, "currency": 0.3},
    "AUTO":          {"rates": 0.7, "gdp": 0.7, "fiscal": 0.5, "policy": 0.6},
    "CONSUMER":      {"rates": 0.4, "gdp": 0.8, "fiscal": 0.5, "policy": 0.4},
    "METALS":        {"rates": 0.5, "gdp": 0.8, "fiscal": 0.4, "policy": 0.5, "commodity": 0.8},
    "CEMENT":        {"rates": 0.6, "gdp": 0.8, "fiscal": 0.7, "policy": 0.7},
    "POWER":         {"rates": 0.5, "gdp": 0.6, "fiscal": 0.6, "policy": 0.8},
    "CONGLOMERATE":  {"rates": 0.5, "gdp": 0.7, "fiscal": 0.5, "policy": 0.5},
    "TELECOM":       {"rates": 0.6, "gdp": 0.4, "fiscal": 0.3, "policy": 0.9},
}

# Current macro regime scores (updated manually or via external data feed)
# These serve as sensible defaults; production would pull from RBI/Govt data
MACRO_REGIME_DEFAULTS: dict[str, float] = {
    "gdp":        0.65,   # India GDP growth ~6.5% = moderately positive
    "rates":      0.50,   # RBI neutral stance
    "fiscal":     0.55,   # Fiscal consolidation underway
    "policy":     0.60,   # PLI schemes, infra push = positive
    "currency":   0.45,   # INR depreciation headwind
    "commodity":  0.50,   # Mixed commodity outlook
}


class MacroCorrelationAgent:
    """Assesses macro alignment for a company and its sector."""

    def __init__(self, symbol: str):
        self.symbol = symbol.upper()

    def evaluate(self) -> dict[str, Any]:
        """Compute sector macro alignment score."""
        # Determine sector from PRDE or MRI data
        sector = self._get_sector()

        # Get sector sensitivities
        sensitivities = SECTOR_MACRO_SENSITIVITY.get(sector, {"gdp": 0.5, "rates": 0.5, "fiscal": 0.5, "policy": 0.5})

        # Compute weighted macro score
        macro_signals = {}
        weighted_sum = 0.0
        weight_sum = 0.0

        for factor, sensitivity in sensitivities.items():
            regime_score = MACRO_REGIME_DEFAULTS.get(factor, 0.5)
            macro_signals[factor] = {
                "regime_score": regime_score,
                "sensitivity": sensitivity,
                "contribution": round(regime_score * sensitivity, 2),
            }
            weighted_sum += regime_score * sensitivity
            weight_sum += sensitivity

        macro_alignment = round((weighted_sum / weight_sum) * 100, 1) if weight_sum > 0 else 50.0

        # Determine tailwind/headwind classification
        if macro_alignment >= 70:
            outlook = "STRONG TAILWIND"
        elif macro_alignment >= 55:
            outlook = "MODERATE TAILWIND"
        elif macro_alignment >= 45:
            outlook = "NEUTRAL"
        elif macro_alignment >= 30:
            outlook = "MODERATE HEADWIND"
        else:
            outlook = "STRONG HEADWIND"

        # Policy-specific notes for Indian context
        policy_notes = self._policy_context(sector)

        return {
            "symbol": self.symbol,
            "sector": sector,
            "macro_alignment_score": macro_alignment,
            "outlook": outlook,
            "macro_signals": macro_signals,
            "policy_notes": policy_notes,
            "timestamp": str(date.today()),
        }

    def _get_sector(self) -> str:
        """Get sector from PRDE companies table, falling back to MRI data."""
        df = fetch_df(
            "SELECT sector FROM public.prde_companies WHERE ticker = %s AND is_active = TRUE",
            (self.symbol,),
        )
        if df is not None and not df.empty:
            return df.iloc[0]["sector"] or "UNKNOWN"

        # Fallback: try stock_scores sector info
        df2 = fetch_df(
            "SELECT sector FROM public.aae_results_snapshot WHERE symbol = %s",
            (self.symbol,),
        )
        if df2 is not None and not df2.empty:
            return df2.iloc[0]["sector"] or "UNKNOWN"

        return "UNKNOWN"

    def _policy_context(self, sector: str) -> list[str]:
        """Return relevant Indian policy notes for the sector."""
        notes: dict[str, list[str]] = {
            "AUTO": ["PLI scheme for auto components", "EV adoption push", "BS-VI phase 2"],
            "IT":   ["Global IT spending cycle", "US H1-B visa policy risk", "AI/GenAI demand tailwind"],
            "PHARMA": ["PLI for APIs & KSMs", "US FDA regulatory risk", "China+1 sourcing shift"],
            "BANKS": ["Credit growth cycle", "RBI rate trajectory", "Asset quality improvement"],
            "METALS": ["Global commodity cycle", "China stimulus impact", "Infra spending boost"],
            "CEMENT": ["Government infra capex", "Housing demand cycle", "Input cost volatility"],
            "POWER": ["Renewable energy push", "Discom reform progress", "Thermal capacity addition"],
        }
        return notes.get(sector, ["No specific policy notes available"])


def main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="AAE Macro Correlation Agent")
    parser.add_argument("--symbol", required=True, help="Ticker symbol")
    args = parser.parse_args()

    agent = MacroCorrelationAgent(args.symbol)
    result = agent.evaluate()
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
