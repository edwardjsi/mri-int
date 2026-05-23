"""AAE Execution Monitoring Agent.

Tracks thesis integrity and surfaces red flags across five dimensions:
  Financial Strain, Earnings Quality, Working Capital, Governance, Margin Compression.

Usage:
    python engine_core/aae_execution_monitoring_agent.py --symbol RELIANCE
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from engine_core.db import fetch_df

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("aae_exec_monitor")

# Risk thresholds
HIGH_DEBT_EQUITY = 2.0
FCF_PAT_DETERIORATION = -0.3       # 30% decline in FCF/PAT ratio
WORKING_CAPITAL_DAYS_INCREASE = 15  # days increase = red flag
MARGIN_COMPRESSION = -0.03         # 3 percentage point margin decline


class ExecutionMonitoringAgent:
    """Monitors thesis integrity and generates risk dashboards."""

    def __init__(self, symbol: str):
        self.symbol = symbol.upper()

    def evaluate(self) -> dict[str, Any]:
        """Run all monitoring checks and return risk dashboard."""
        risks = {
            "financial_strain": self._check_financial_strain(),
            "earnings_quality": self._check_earnings_quality(),
            "working_capital": self._check_working_capital(),
            "governance": self._check_governance_events(),
            "margin_compression": self._check_margin_compression(),
        }

        # Aggregate risk state
        red_count = sum(1 for r in risks.values() if r["severity"] == "RED")
        amber_count = sum(1 for r in risks.values() if r["severity"] == "AMBER")
        green_count = sum(1 for r in risks.values() if r["severity"] == "GREEN")

        if red_count >= 2:
            overall = "THESIS_AT_RISK"
        elif red_count >= 1 or amber_count >= 3:
            overall = "WATCH_CLOSELY"
        elif amber_count >= 1:
            overall = "MONITOR"
        else:
            overall = "CLEAN"

        alerts = []
        for category, risk in risks.items():
            if risk["severity"] in ("RED", "AMBER"):
                alerts.append({
                    "category": category,
                    "severity": risk["severity"],
                    "detail": risk["detail"],
                    "suggested_action": self._suggested_action(category, risk["severity"]),
                })

        return {
            "symbol": self.symbol,
            "timestamp": str(date.today()),
            "overall_risk_state": overall,
            "risk_counts": {"RED": red_count, "AMBER": amber_count, "GREEN": green_count},
            "risks": risks,
            "alerts": alerts,
        }

    def _check_financial_strain(self) -> dict:
        """Check debt levels and leverage trends from PRDE data."""
        df = fetch_df(
            """
            SELECT debt_equity
            FROM public.prde_ratios_annual r
            JOIN public.prde_companies c ON c.id = r.company_id
            WHERE c.ticker = %s
            ORDER BY r.fiscal_year DESC
            LIMIT 2
            """,
            (self.symbol,),
        )

        if df is None or df.empty:
            return {"severity": "GREEN", "detail": "no debt data available", "data_available": False}

        latest = float(df.iloc[0]["debt_equity"]) if df.iloc[0]["debt_equity"] else None
        prev = float(df.iloc[1]["debt_equity"]) if len(df) > 1 and df.iloc[1]["debt_equity"] else None

        if latest is None:
            return {"severity": "GREEN", "detail": "no debt data", "data_available": False}

        if latest > HIGH_DEBT_EQUITY:
            if prev and latest > prev:
                return {"severity": "RED", "detail": f"High and rising D/E: {latest:.2f} (prev {prev:.2f})", "de_ratio": latest}
            return {"severity": "AMBER", "detail": f"High D/E: {latest:.2f}", "de_ratio": latest}

        if prev and latest < prev:
            return {"severity": "GREEN", "detail": f"Deleveraging: D/E {latest:.2f} ↓ from {prev:.2f}", "de_ratio": latest}

        return {"severity": "GREEN", "detail": f"Healthy D/E: {latest:.2f}", "de_ratio": latest}

    def _check_earnings_quality(self) -> dict:
        """Check PAT quality via growth consistency from PRDE features."""
        df = fetch_df(
            """
            SELECT features->'pat_cagr_3y' AS pat_cagr,
                   features->'revenue_cagr_3y' AS rev_cagr,
                   features->'ebitda_margin'->'trend_slope' AS margin_trend
            FROM public.prde_feature_snapshots s
            JOIN public.prde_companies c ON c.id = s.company_id
            WHERE c.ticker = %s
            ORDER BY s.created_at DESC
            LIMIT 1
            """,
            (self.symbol,),
        )

        if df is None or df.empty:
            return {"severity": "GREEN", "detail": "no earnings quality data", "data_available": False}

        import json as _json
        pat_cagr_str = df.iloc[0]["pat_cagr"]
        rev_cagr_str = df.iloc[0]["rev_cagr"]
        margin_trend_str = df.iloc[0]["margin_trend"]

        pat_cagr = float(pat_cagr_str) if pat_cagr_str else None
        rev_cagr = float(rev_cagr_str) if rev_cagr_str else None
        margin_trend = float(margin_trend_str) if margin_trend_str else None

        if pat_cagr is not None and rev_cagr is not None and pat_cagr < 0 and rev_cagr > 0:
            return {"severity": "RED", "detail": f"Revenue growing ({rev_cagr:.1%}) but PAT declining ({pat_cagr:.1%}) — earnings quality erosion"}

        if margin_trend is not None and margin_trend < MARGIN_COMPRESSION:
            return {"severity": "AMBER", "detail": f"Margin compression trend: {margin_trend:.3f}", "margin_trend": margin_trend}

        return {"severity": "GREEN", "detail": "earnings quality appears stable"}

    def _check_working_capital(self) -> dict:
        """Check working capital efficiency from PRDE data."""
        df = fetch_df(
            """
            SELECT features->'asset_turnover'->'trend_slope' AS at_trend,
                   features->'asset_turnover'->'latest' AS at_latest
            FROM public.prde_feature_snapshots s
            JOIN public.prde_companies c ON c.id = s.company_id
            WHERE c.ticker = %s
            ORDER BY s.created_at DESC
            LIMIT 1
            """,
            (self.symbol,),
        )

        if df is None or df.empty:
            return {"severity": "GREEN", "detail": "no working capital data", "data_available": False}

        import json as _json
        at_trend_str = df.iloc[0]["at_trend"]
        at_latest_str = df.iloc[0]["at_latest"]

        at_trend = float(at_trend_str) if at_trend_str else None
        at_latest = float(at_latest_str) if at_latest_str else None

        # Asset turnover decline = potential working capital inefficiency
        if at_trend is not None and at_trend < -0.05:
            return {"severity": "AMBER", "detail": f"Asset turnover declining ({at_trend:.3f}) — possible WC strain", "at_trend": at_trend}

        if at_latest is not None and at_latest < 0.3:
            return {"severity": "AMBER", "detail": f"Very low asset turnover: {at_latest:.2f}x (capital-intensive, watch WC)", "at_latest": at_latest}

        return {"severity": "GREEN", "detail": "working capital indicators stable"}

    def _check_governance_events(self) -> dict:
        """Check for recent governance red flag events."""
        df = fetch_df(
            """
            SELECT COUNT(*) AS red_flag_count
            FROM public.aae_events
            WHERE symbol = %s
              AND event_type = 'GOVERNANCE_RED_FLAG'
              AND event_date >= CURRENT_DATE - INTERVAL '12 months'
            """,
            (self.symbol,),
        )

        if df is not None and not df.empty:
            count = int(df.iloc[0]["red_flag_count"])
            if count >= 2:
                return {"severity": "RED", "detail": f"{count} governance red flags in last 12 months"}
            elif count == 1:
                return {"severity": "AMBER", "detail": f"1 governance red flag detected"}

        return {"severity": "GREEN", "detail": "no governance red flags"}

    def _check_margin_compression(self) -> dict:
        """Check for margin compression signals."""
        df = fetch_df(
            """
            SELECT features->'ebitda_margin'->'trend_slope' AS margin_trend,
                   features->'ebitda_margin'->'latest' AS margin_latest,
                   features->'ebitda_margin'->'stability' AS margin_stability
            FROM public.prde_feature_snapshots s
            JOIN public.prde_companies c ON c.id = s.company_id
            WHERE c.ticker = %s
            ORDER BY s.created_at DESC
            LIMIT 1
            """,
            (self.symbol,),
        )

        if df is None or df.empty:
            return {"severity": "GREEN", "detail": "no margin data", "data_available": False}

        import json as _json
        margin_trend = float(df.iloc[0]["margin_trend"]) if df.iloc[0]["margin_trend"] else None
        margin_stability = float(df.iloc[0]["margin_stability"]) if df.iloc[0]["margin_stability"] else None

        if margin_trend is not None and margin_trend < MARGIN_COMPRESSION:
            if margin_stability is not None and margin_stability > 0.06:
                return {"severity": "RED", "detail": f"Margin compression ({margin_trend:.3f}) with high volatility ({margin_stability:.3f})", "margin_trend": margin_trend}
            return {"severity": "AMBER", "detail": f"Margin compression trend: {margin_trend:.3f}", "margin_trend": margin_trend}

        return {"severity": "GREEN", "detail": "margins stable or expanding"}

    def _suggested_action(self, category: str, severity: str) -> str:
        """Suggest review action based on risk category and severity."""
        actions = {
            "financial_strain":    {"RED": "Exit Review", "AMBER": "Trim Review"},
            "earnings_quality":    {"RED": "Exit Review", "AMBER": "Watch"},
            "working_capital":     {"RED": "Trim Review", "AMBER": "Watch"},
            "governance":          {"RED": "Exit Review", "AMBER": "Watch"},
            "margin_compression":  {"RED": "Trim Review", "AMBER": "Watch"},
        }
        return actions.get(category, {}).get(severity, "Watch")


def main() -> None:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="AAE Execution Monitoring Agent")
    parser.add_argument("--symbol", required=True, help="Ticker symbol")
    args = parser.parse_args()

    agent = ExecutionMonitoringAgent(args.symbol)
    result = agent.evaluate()
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
