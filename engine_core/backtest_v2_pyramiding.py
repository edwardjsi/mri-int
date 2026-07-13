#!/usr/bin/env python3
"""Decision 103 P6 — V2 Pyramiding Discipline Backtest.

Walk every historical row in `cas_recommendations` and compare two signal
sets on the 6 §14.8 success metrics from docs/CAPITAL_ALLOCATION_SCORE_PLAN_2026-07-06.md:

  1. V1.1d baseline:  all rows where `action == 'ADD'` (CAS-only second tranche).
  2. V2 gated:        all rows where `factor_snapshot.final_state == 'ADD_SECOND_TRANCHE'`.

For each signal we compute forward 20/60/120-trading-day returns and compare
them to the NIFTY50 benchmark over the same windows.  The script also computes
the mean max drawdown within 60 trading days post-signal.

Exit points (consecutive closes below exit_ema is the existing live rule):
  - Return is measured as raw buy-and-hold over the horizon.
  - Drawdown is measured over the 60d window using daily closes.

Run:
    python engine_core/backtest_v2_pyramiding.py
    python engine_core/backtest_v2_pyramiding.py --start-date 2026-01-01 --end-date 2026-07-31

Output:
    JSON blob with sample sizes, per-metric values, pass/fail verdicts, and a
    human-readable table.  Writes nothing to the database by design.

Backward compatibility:
    Handles BOTH V1.1d snapshots (no `final_state` key) and V2 snapshots
    (have `final_state` / `gates`).  Pre-P3 rows naturally fall out of the
    V2 signal set because they lack `final_state`.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import mean
from typing import Any

# Add project root to path so this file can be imported / run directly.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from engine_core.db import fetch_df

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# §14.8 metric thresholds
THRESHOLDS = {
    "signals_per_month_max": 5,
    "outperform_20d_min": 0.60,
    "outperform_60d_min": 0.60,
    "outperform_120d_min": 0.55,
    # Win-rate vs CAS-only: V2 must be >= V1.1d (no fixed delta)
    "avg_max_drawdown_60d_min": -0.12,  # i.e. < -12% -> fail
}

FORWARD_WINDOWS = [20, 60, 120]


@dataclass
class Signal:
    """One historical ADD recommendation."""
    symbol: str
    rec_date: date
    entry_price: float
    action: str
    cas_score: float | None
    final_state: str | None
    gate_score_pct: float | None
    blocked_gates: list[str] = field(default_factory=list)
    is_v2: bool = False


@dataclass
class HorizonResult:
    """Forward return outcome for a single signal at one horizon."""
    signal: Signal
    horizon_days: int
    stock_return: float | None
    benchmark_return: float | None
    outperformed: bool | None
    positive_return: bool | None


@dataclass
class DrawdownResult:
    """Max drawdown outcome for a single signal over 60 trading days."""
    signal: Signal
    max_drawdown: float | None


@dataclass
class BacktestReport:
    """Aggregated backtest report."""
    label: str
    n_signals: int
    start_date: date | None
    end_date: date | None
    signals_per_month: float | None
    outperform_pct: dict[int, float | None]
    win_rate: float | None
    avg_max_drawdown: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "n_signals": self.n_signals,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "signals_per_month": _round_or_none(self.signals_per_month, 2),
            "outperform_pct": {f"{k}d": _round_or_none(v, 3) for k, v in self.outperform_pct.items()},
            "win_rate": _round_or_none(self.win_rate, 3),
            "avg_max_drawdown": _round_or_none(self.avg_max_drawdown, 3),
        }


def _round_or_none(value: float | None, ndigits: int) -> float | None:
    if value is None:
        return None
    return round(float(value), ndigits)


def load_cas_recommendations(start_date: date, end_date: date) -> list[Signal]:
    """Fetch eligible recommendations from the database."""
    query = """
        SELECT
            symbol,
            recommendation_date,
            action,
            cas,
            price_at_recommendation,
            factor_snapshot
        FROM cas_recommendations
        WHERE recommendation_date BETWEEN %(start)s AND %(end)s
        ORDER BY recommendation_date, symbol
    """
    df = fetch_df(query, {"start": start_date, "end": end_date})
    signals: list[Signal] = []
    for _, row in df.iterrows():
        snap = row["factor_snapshot"] or {}
        if isinstance(snap, str):
            snap = json.loads(snap)

        final_state = snap.get("final_state")
        gate_score_pct = snap.get("gate_score_pct")
        gates = snap.get("gates") or {}
        blocked = gates.get("blocked") or []

        signals.append(
            Signal(
                symbol=str(row["symbol"]),
                rec_date=_to_date(row["recommendation_date"]),
                entry_price=float(row["price_at_recommendation"] or 0),
                action=str(row["action"]),
                cas_score=_to_float_or_none(row.get("cas")),
                final_state=final_state,
                gate_score_pct=_to_float_or_none(gate_score_pct),
                blocked_gates=list(blocked),
                is_v2=final_state is not None,
            )
        )
    return signals


def _to_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError(f"Cannot convert {value!r} to date")


def _to_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_daily_prices(symbols: set[str]) -> pd.DataFrame:
    """Load daily close prices for the requested symbols."""
    if not symbols:
        return pd.DataFrame(columns=["symbol", "date", "close"])

    query = """
        SELECT symbol, date, close
        FROM daily_prices
        WHERE symbol = ANY(%(symbols)s)
        ORDER BY symbol, date
    """
    df = fetch_df(query, {"symbols": list(symbols)})
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    return df.dropna(subset=["close"])


def load_benchmark(start_date: date, end_date: date) -> pd.DataFrame:
    """Load NIFTY50 closes from market_index_prices."""
    query = """
        SELECT date, close
        FROM market_index_prices
        WHERE symbol = 'NIFTY50'
          AND date BETWEEN %(start)s AND %(end)s
        ORDER BY date
    """
    df = fetch_df(query, {"start": start_date, "end": end_date})
    if df.empty:
        # Fallback: try the older index_prices table if present.
        query = """
            SELECT date, close
            FROM index_prices
            WHERE symbol = 'NIFTY50'
              AND date BETWEEN %(start)s AND %(end)s
            ORDER BY date
        """
        df = fetch_df(query, {"start": start_date, "end": end_date})

    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    return df.dropna(subset=["close"])


def compute_forward_returns(
    signals: list[Signal],
    prices: pd.DataFrame,
    benchmark: pd.DataFrame,
) -> list[HorizonResult]:
    """Compute forward returns for every signal at every horizon."""
    price_index = prices.set_index(["symbol", "date"])["close"]
    bench_index = benchmark.set_index("date")["close"]
    results: list[HorizonResult] = []

    for sig in signals:
        try:
            entry_price = price_index.loc[(sig.symbol, sig.rec_date)]
        except KeyError:
            logger.debug("No entry price for %s on %s", sig.symbol, sig.rec_date)
            continue
        if entry_price <= 0:
            continue

        # Build ordered list of trading days for this symbol from rec_date onward.
        symbol_dates = prices.loc[prices["symbol"] == sig.symbol, "date"].unique()
        symbol_dates = sorted(d for d in symbol_dates if d >= sig.rec_date)

        for horizon in FORWARD_WINDOWS:
            if len(symbol_dates) <= horizon:
                stock_ret = None
            else:
                exit_date = symbol_dates[horizon]
                try:
                    exit_price = price_index.loc[(sig.symbol, exit_date)]
                    stock_ret = float(exit_price) / float(entry_price) - 1.0
                except KeyError:
                    stock_ret = None

            bench_ret = None
            try:
                bench_start = bench_index.loc[sig.rec_date]
                bench_dates = sorted(d for d in bench_index.index if d >= sig.rec_date)
                if len(bench_dates) > horizon:
                    bench_end = bench_index.loc[bench_dates[horizon]]
                    bench_ret = float(bench_end) / float(bench_start) - 1.0
            except KeyError:
                bench_ret = None

            outperf = None
            if stock_ret is not None and bench_ret is not None:
                outperf = stock_ret > bench_ret

            pos = None
            if stock_ret is not None:
                pos = stock_ret > 0

            results.append(
                HorizonResult(
                    signal=sig,
                    horizon_days=horizon,
                    stock_return=stock_ret,
                    benchmark_return=bench_ret,
                    outperformed=outperf,
                    positive_return=pos,
                )
            )

    return results


def compute_drawdowns(
    signals: list[Signal],
    prices: pd.DataFrame,
) -> list[DrawdownResult]:
    """Compute max drawdown over the first 60 trading days post-signal."""
    price_index = prices.set_index(["symbol", "date"])["close"]
    results: list[DrawdownResult] = []
    horizon = 60

    for sig in signals:
        symbol_dates = prices.loc[prices["symbol"] == sig.symbol, "date"].unique()
        symbol_dates = sorted(d for d in symbol_dates if d >= sig.rec_date)
        if len(symbol_dates) <= 1:
            results.append(DrawdownResult(signal=sig, max_drawdown=None))
            continue

        window = symbol_dates[: min(horizon + 1, len(symbol_dates))]
        closes = []
        for d in window:
            try:
                closes.append(float(price_index.loc[(sig.symbol, d)]))
            except KeyError:
                continue

        if len(closes) < 2:
            results.append(DrawdownResult(signal=sig, max_drawdown=None))
            continue

        series = pd.Series(closes)
        running_max = series.cummax()
        drawdown = (series / running_max) - 1.0
        results.append(DrawdownResult(signal=sig, max_drawdown=drawdown.min()))

    return results


def build_signal_set(signals: list[Signal], use_v2: bool) -> list[Signal]:
    """Return either the V1.1d ADD set or the V2 ADD_SECOND_TRANCHE set."""
    if use_v2:
        return [s for s in signals if s.final_state == "ADD_SECOND_TRANCHE"]
    return [s for s in signals if s.action == "ADD"]


def aggregate_report(
    label: str,
    signals: list[Signal],
    horizon_results: list[HorizonResult],
    drawdown_results: list[DrawdownResult],
) -> BacktestReport:
    """Aggregate per-signal outcomes into the §14.8 metrics."""
    if not signals:
        return BacktestReport(
            label=label,
            n_signals=0,
            start_date=None,
            end_date=None,
            signals_per_month=None,
            outperform_pct={h: None for h in FORWARD_WINDOWS},
            win_rate=None,
            avg_max_drawdown=None,
        )

    dates = sorted(s.rec_date for s in signals)
    start_date = dates[0]
    end_date = dates[-1]
    months = max(1, (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1)
    signals_per_month = len(signals) / months

    # Per-horizon % outperform benchmark
    outperform_pct: dict[int, float | None] = {}
    for horizon in FORWARD_WINDOWS:
        subset = [r for r in horizon_results if r.signal in signals and r.horizon_days == horizon]
        valid = [r for r in subset if r.outperformed is not None]
        if valid:
            outperform_pct[horizon] = mean(1 if r.outperformed else 0 for r in valid)
        else:
            outperform_pct[horizon] = None

    # Win rate = % of signals with positive return at any horizon we can measure.
    any_pos = [r for r in horizon_results if r.signal in signals and r.positive_return is not None]
    if any_pos:
        win_rate = mean(1 if r.positive_return else 0 for r in any_pos)
    else:
        win_rate = None

    # Average max drawdown
    dd_valid = [d.max_drawdown for d in drawdown_results if d.signal in signals and d.max_drawdown is not None]
    avg_max_dd = mean(dd_valid) if dd_valid else None

    return BacktestReport(
        label=label,
        n_signals=len(signals),
        start_date=start_date,
        end_date=end_date,
        signals_per_month=signals_per_month,
        outperform_pct=outperform_pct,
        win_rate=win_rate,
        avg_max_drawdown=avg_max_dd,
    )


def evaluate_verdicts(v1: BacktestReport, v2: BacktestReport) -> dict[str, dict[str, Any]]:
    """Compare V2 report against V1.1d and the §14.8 thresholds."""
    verdicts: dict[str, dict[str, Any]] = {}

    # 1. Signal density
    spm = v2.signals_per_month
    verdicts["signals_per_month"] = {
        "value": _round_or_none(spm, 2),
        "threshold": f"<= {THRESHOLDS['signals_per_month_max']}",
        "pass": spm is not None and spm <= THRESHOLDS["signals_per_month_max"],
    }

    # 2-4. Outperformance at 20/60/120d
    for horizon in FORWARD_WINDOWS:
        key = f"outperform_{horizon}d"
        val = v2.outperform_pct.get(horizon)
        thr = THRESHOLDS[f"{key}_min"]
        verdicts[key] = {
            "value": _round_or_none(val, 3),
            "threshold": f">= {thr:.0%}",
            "pass": val is not None and val >= thr,
        }

    # 5. Win rate vs CAS-only (V2 must be >= V1.1d)
    v2_wr = v2.win_rate
    v1_wr = v1.win_rate
    verdicts["win_rate_vs_cas_only"] = {
        "v2_win_rate": _round_or_none(v2_wr, 3),
        "v1_win_rate": _round_or_none(v1_wr, 3),
        "threshold": "V2 >= V1.1d",
        "pass": v2_wr is not None and v1_wr is not None and v2_wr >= v1_wr,
    }

    # 6. Avg max drawdown < -12%
    dd = v2.avg_max_drawdown
    verdicts["avg_max_drawdown_60d"] = {
        "value": _round_or_none(dd, 3),
        "threshold": f"> {THRESHOLDS['avg_max_drawdown_60d_min']:.0%}",
        "pass": dd is not None and dd > THRESHOLDS["avg_max_drawdown_60d_min"],
    }

    return verdicts


def print_report(v1: BacktestReport, v2: BacktestReport, verdicts: dict[str, dict[str, Any]]) -> None:
    """Human-readable console report."""
    print("\n" + "=" * 70)
    print("Decision 103 P6 — V2 Pyramiding Discipline Backtest")
    print("=" * 70)

    for rep in (v1, v2):
        print(f"\n{rep.label}: n={rep.n_signals}")
        if rep.start_date:
            print(f"  window: {rep.start_date} → {rep.end_date}")
        print(f"  signals/month: {_fmt(rep.signals_per_month)}")
        for horizon in FORWARD_WINDOWS:
            print(f"  % outperform NIFTY50 @ {horizon}d: {_fmt_pct(rep.outperform_pct.get(horizon))}")
        print(f"  win rate (any horizon): {_fmt_pct(rep.win_rate)}")
        print(f"  avg max drawdown (60d): {_fmt_pct(rep.avg_max_drawdown)}")

    print("\n" + "-" * 70)
    print("§14.8 Verdicts (V2 vs thresholds + V1.1d)")
    print("-" * 70)
    for name, v in verdicts.items():
        status = "PASS" if v["pass"] else "FAIL"
        print(f"  {name}: {status} (value={v.get('value', v.get('v2_win_rate'))}, threshold={v['threshold']})")

    all_pass = all(v["pass"] for v in verdicts.values())
    print("\n" + "=" * 70)
    if all_pass:
        print("OVERALL: ALL §14.8 METRICS PASS — calibration entries may be flipped to validated.")
    else:
        print("OVERALL: SOME METRICS FAIL — keep calibration entries as hypothesis; see Calibration.md journal.")
    print("=" * 70 + "\n")


def _fmt(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def main() -> int:
    parser = argparse.ArgumentParser(description="Decision 103 P6 V2 pyramiding backtest")
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=None,
        help="Backtest start date (ISO). Defaults to 6 months ago.",
    )
    parser.add_argument(
        "--end-date",
        type=date.fromisoformat,
        default=None,
        help="Backtest end date (ISO). Defaults to today.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional path to write a JSON report.",
    )
    args = parser.parse_args()

    end_date = args.end_date or date.today()
    start_date = args.start_date or (end_date - timedelta(days=180))

    logger.info("Loading CAS recommendations from %s to %s", start_date, end_date)
    signals = load_cas_recommendations(start_date, end_date)
    logger.info("Loaded %d recommendations", len(signals))

    if len(signals) < 5:
        logger.warning(
            "Very small sample (%d recommendations). "
            "Run scripts/daily_cas_scanner.py for more historical dates before trusting verdicts.",
            len(signals),
        )

    v1_signals = build_signal_set(signals, use_v2=False)
    v2_signals = build_signal_set(signals, use_v2=True)
    logger.info("V1.1d ADD signals: %d; V2 ADD_SECOND_TRANCHE signals: %d", len(v1_signals), len(v2_signals))

    symbols = {s.symbol for s in signals}
    logger.info("Loading daily prices for %d symbols", len(symbols))
    prices = load_daily_prices(symbols)

    logger.info("Loading NIFTY50 benchmark")
    benchmark = load_benchmark(start_date, end_date + timedelta(days=180))

    logger.info("Computing forward returns")
    horizon_results = compute_forward_returns(signals, prices, benchmark)

    logger.info("Computing drawdowns")
    drawdown_results = compute_drawdowns(signals, prices)

    logger.info("Aggregating reports")
    v1_report = aggregate_report("V1.1d CAS-only ADD", v1_signals, horizon_results, drawdown_results)
    v2_report = aggregate_report("V2 Gated ADD_SECOND_TRANCHE", v2_signals, horizon_results, drawdown_results)

    verdicts = evaluate_verdicts(v1_report, v2_report)

    print_report(v1_report, v2_report, verdicts)

    if args.json_out:
        payload = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "v1": v1_report.to_dict(),
            "v2": v2_report.to_dict(),
            "verdicts": verdicts,
            "all_pass": all(v["pass"] for v in verdicts.values()),
        }
        args.json_out.write_text(json.dumps(payload, indent=2, default=str))
        logger.info("Wrote JSON report to %s", args.json_out)

    return 0 if all(v["pass"] for v in verdicts.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
