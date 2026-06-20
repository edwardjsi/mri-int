"""
MRI Score Individual Backtest
=============================
Simulates a portfolio that holds the top-N stocks by total_score each month,
with regime-filtered entry. Compares against Nifty 50 benchmark per README
Go/No-Go criteria.

Constraints & Assumptions:
- Uses stock_scores table from the DB (limited to ~14 months as of 2024-03).
- For older periods, falls back to interim CSV or notes the gap.
- Transaction cost: 0.4% round-trip per README.
- Equal-weight allocation, monthly rebalance.
- Regime filter: No new buys in BEARISH.

To run:
  python scripts/backtest_mri_score.py --top-n 5 --threshold 75 --hold-days 20
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Ensure project root on path for engine_core imports
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine_core.db import get_connection as get_db

TX_COST = 0.004  # 0.4% round-trip
INITIAL_CAPITAL = 1_000_000.0

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--top-n", type=int, default=5, help="Number of top-scoring stocks to hold")
    p.add_argument("--threshold", type=int, default=75, help="Minimum total_score to qualify")
    p.add_argument("--hold-days", type=int, default=20, help="Trading days to hold before rebalance")
    p.add_argument("--csv-scores", type=str, default=None, help="Optional CSV of stock_scores to backfill gaps")
    p.add_argument("--output-dir", type=str, default="outputs")
    return p.parse_args()

def get_stock_scores(min_date: str, max_date: str):
    conn = get_db()
    q = """
        SELECT symbol, date, total_score
        FROM stock_scores
        WHERE date BETWEEN %s AND %s
        ORDER BY symbol, date
    """
    cur = conn.cursor()
    cur.execute(q, (min_date, max_date))
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    conn.close()
    df = pd.DataFrame(rows, columns=cols)
    df["date"] = pd.to_datetime(df["date"])
    return df

def get_regime_map(min_date, max_date):
    """Compute regime from Nifty 50 EMA cross per signal_generator.py logic."""
    conn = get_db()
    q = """
        SELECT date, close
        FROM index_prices
        WHERE symbol = 'NIFTY50' AND date BETWEEN %s AND %s
        ORDER BY date
    """
    cur = conn.cursor()
    cur.execute(q, (min_date, max_date))
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    conn.close()
    idx = pd.DataFrame(rows, columns=cols)
    idx["date"] = pd.to_datetime(idx["date"])
    if idx.empty:
        return {}
    idx["close"] = idx["close"].astype(float)
    idx["ema50"] = idx["close"].ewm(span=50, adjust=False).mean()
    idx["ema200"] = idx["close"].ewm(span=200, adjust=False).mean()
    def classify(row):
        c, e50, e200 = row["close"], row["ema50"], row["ema200"]
        if c > e200 and e50 > e200:
            return "BULLISH"
        if c < e200 and e50 < e200:
            return "BEARISH"
        if abs((c - e200) / e200) <= 0.02:
            return "SIDEWAYS"
        return "NEUTRAL"
    idx["regime"] = idx.apply(classify, axis=1)
    return dict(zip(idx["date"], idx["regime"]))

def get_daily_prices(symbols, min_date, max_date):
    conn = get_db()
    placeholders = ",".join("%s" for _ in symbols)
    q = f"""
        SELECT symbol, date, close
        FROM daily_prices
        WHERE symbol IN ({placeholders}) AND date BETWEEN %s AND %s
        ORDER BY symbol, date
    """
    cur = conn.cursor()
    cur.execute(q, tuple(symbols + [min_date, max_date]))
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    conn.close()
    df = pd.DataFrame(rows, columns=cols)
    df["date"] = pd.to_datetime(df["date"])
    return df

def get_nifty_prices(min_date, max_date):
    conn = get_db()
    q = """
        SELECT date, close
        FROM index_prices
        WHERE symbol = 'NIFTY50' AND date BETWEEN %s AND %s
        ORDER BY date
    """
    cur = conn.cursor()
    cur.execute(q, (min_date, max_date))
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    conn.close()
    df = pd.DataFrame(rows, columns=cols)
    df["date"] = pd.to_datetime(df["date"])
    return df

def run_mri_backtest(df_scores, df_prices, df_nifty, args, regime_info=None):
    """
    df_scores: stock_scores DataFrame from DB
    df_prices: daily_prices DataFrame for close prices
    df_nifty: Nifty 50 index prices DataFrame
    args: parsed args
    regime_info: dict date -> regime (optional)
    """
    top_n = args.top_n
    threshold = args.threshold
    hold_days = args.hold_days

    dates = sorted(df_scores["date"].unique())
    if not dates:
        print("No stock_scores dates found.")
        return None, None, None

    # Pivot prices
    price_pivot = df_prices.pivot(index="date", columns="symbol", values="close")
    nifty = df_nifty.set_index("date")["close"].sort_index()

    # Resample to monthly rebalance (last trading day of each month)
    rebalance_dates = []
    for d in dates:
        if not rebalance_dates or (d.year, d.month) != (rebalance_dates[-1].year, rebalance_dates[-1].month):
            rebalance_dates.append(d)
    # Ensure final date is included
    if dates[-1] not in rebalance_dates:
        rebalance_dates.append(dates[-1])
    rebalance_dates = sorted(set(rebalance_dates))

    cash = INITIAL_CAPITAL
    holdings = {}  # symbol -> {"shares": int, "entry_price": float, "entry_date": date}
    equity_curve = []
    trade_log = []

    for i, reb_date in enumerate(rebalance_dates):
        # Get regime for this date
        regime = "NEUTRAL"
        if regime_info and reb_date in regime_info:
            regime = regime_info[reb_date]

        # --- Manage Exits ---
        sales = []
        for sym, h in list(holdings.items()):
            price = float(price_pivot.get(sym, pd.Series()).get(reb_date))
            if pd.notna(price) and price > 0:
                days_held = (reb_date - h["entry_date"]).days
                # Exit if hold period expired (>= hold_days)
                if days_held >= hold_days:
                    sales.append((sym, price, "HOLD_EXPIRED"))
                    continue
                # Exit if price drops below 90% of entry (hard stop @ 10%)
                if price <= h["entry_price"] * 0.90:
                    sales.append((sym, price, "HARD_STOP"))
                    continue
            else:
                # No price today — carry forward
                pass

        # If this is the final rebalance, liquidate everything
        if i == len(rebalance_dates) - 1:
            for sym, h in list(holdings.items()):
                price = float(price_pivot.get(sym, pd.Series()).get(reb_date))
                if pd.notna(price) and price > 0:
                    sales.append((sym, price, "FINAL_LIQUIDATE"))

        for sym, price, reason in sales:
            h = holdings.pop(sym)
            proceeds = h["shares"] * price * (1 - TX_COST)
            cash += proceeds
            trade_log.append({
                "symbol": sym,
                "entry_date": h["entry_date"],
                "entry_price": h["entry_price"],
                "exit_date": reb_date,
                "exit_price": price,
                "reason": reason,
                "shares": h["shares"],
                "gain": h["shares"] * (price - h["entry_price"]),
            })

        # --- Manage Entries ---
        if regime != "BEARISH":
            today_scores = df_scores[df_scores["date"] == reb_date].copy()
            today_scores = today_scores[today_scores["total_score"] >= threshold]
            today_scores = today_scores.sort_values("total_score", ascending=False).head(top_n)

            # Size = equal weight of available capital / N
            target_per_stock = cash / top_n if cash > 0 else 0

            for _, row in today_scores.iterrows():
                sym = row["symbol"]
                if sym in holdings:
                    continue
                price = float(price_pivot.get(sym, pd.Series()).get(reb_date))
                if pd.notna(price) and price > 0 and cash >= price * (1 + TX_COST):
                    shares = int(target_per_stock / (price * (1 + TX_COST)))
                    if shares > 0:
                        cost = shares * price * (1 + TX_COST)
                        cash -= cost
                        holdings[sym] = {
                            "shares": shares,
                            "entry_price": price,
                            "entry_date": reb_date,
                        }

        # --- Equity Tracking ---
        portfolio_value = cash
        for sym, h in holdings.items():
            price = float(price_pivot.get(sym, pd.Series()).get(reb_date))
            if pd.notna(price) and price > 0:
                portfolio_value += h["shares"] * price
            else:
                # Carry last known price / skip
                pass

        equity_curve.append({"date": reb_date, "equity": portfolio_value, "regime": regime})

    eq_df = pd.DataFrame(equity_curve).set_index("date").sort_index()
    return eq_df, trade_log, nifty

def calculate_metrics(eq_df, nifty, name: str):
    series = eq_df["equity"].dropna()
    if len(series) < 2 or series.iloc[0] <= 0:
        return {
            "Portfolio": name, "Period": None,
            "Total Return (%)": 0, "CAGR (%)": 0,
            "Max Drawdown (%)": 0, "Sharpe Ratio": 0,
            "Win Rate (%)": 0, "Profit Factor": 0,
            "Benchmark Return (%)": 0,
            "Alpha (%)": 0,
        }

    returns = series.pct_change().dropna()
    years = (series.index[-1] - series.index[0]).days / 365.25
    cagr = ((series.iloc[-1] / series.iloc[0]) ** (1 / years) - 1) if years > 0 else 0
    rolling_max = series.cummax()
    drawdown = (series / rolling_max) - 1.0
    std = returns.std()
    sharpe = (returns.mean() / (std + 1e-9)) * np.sqrt(12)  # Monthly rebalance => sqrt(12)

    # Benchmark
    if nifty is not None and len(nifty) >= 2:
        nifty_f = nifty.astype(float)
        bench_return = (nifty_f.iloc[-1] / nifty_f.iloc[0] - 1)
        bench_cagr = ((nifty_f.iloc[-1] / nifty_f.iloc[0]) ** (1 / years) - 1) if years > 0 else 0
    else:
        bench_return, bench_cagr = 0, 0

    return {
        "Portfolio": name,
        "Period": f"{series.index[0].strftime('%Y-%m-%d')} → {series.index[-1].strftime('%Y-%m-%d')}",
        "Total Return (%)": round(((series.iloc[-1] / series.iloc[0]) - 1) * 100, 2),
        "CAGR (%)": round(cagr * 100, 2),
        "Max Drawdown (%)": round(drawdown.min() * 100, 2),
        "Sharpe Ratio": round(sharpe, 2),
        "Benchmark Return (%)": round(bench_return * 100, 2),
        "Benchmark CAGR (%)": round(bench_cagr * 100, 2),
        "Alpha (%)": round((cagr - bench_cagr) * 100, 2),
    }

def regime_metrics(eq_df, trade_log):
    """Compute metrics split by regime — simplistic monthly snapshot."""
    results = {}
    for regime in ["BULLISH", "BEARISH", "NEUTRAL", "SIDEWAYS"]:
        sub = eq_df[eq_df["regime"] == regime]["equity"]
        if len(sub) < 2:
            results[regime] = {"trades": "—", "cagr": "—", "avg_return_month": "—"}
            continue
        returns = sub.pct_change().dropna()
        results[regime] = {
            "trades": len([t for t in trade_log if t.get("entry_regime") == regime]),
            "cagr": round((returns.mean() * 12) * 100, 2),
            "avg_return_month": round(returns.mean() * 100, 2),
        }
    return results

def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    # Load data
    print("Loading stock_scores...")
    df_scores = get_stock_scores("2020-01-01", "2026-12-31")
    df_scores = df_scores.dropna(subset=["date"])  # Drop any NaT entries
    print(f"  Loaded {len(df_scores)} score rows")

    if args.csv_scores and Path(args.csv_scores).exists():
        df_csv = pd.read_csv(args.csv_scores, parse_dates=["date"])
        df_csv = df_csv.dropna(subset=["date"])
        df_scores = pd.concat([df_scores, df_csv]).drop_duplicates(subset=["symbol", "date"]).sort_values(["symbol", "date"])
        print(f"  Merged CSV, total {len(df_scores)} rows")

    if df_scores.empty:
        print("ERROR: No stock_scores data found. Run signal generation pipeline first.")
        sys.exit(1)

    all_symbols = df_scores["symbol"].unique().tolist()
    min_date = df_scores["date"].min().strftime("%Y-%m-%d")
    max_date = df_scores["date"].max().strftime("%Y-%m-%d")

    print(f"Score date range: {min_date} → {max_date}, symbols: {len(all_symbols)}")

    print("Loading daily prices...")
    df_prices = get_daily_prices(all_symbols, min_date, max_date)
    print(f"  Loaded {len(df_prices)} price rows")

    print("Loading Nifty 50...")
    df_nifty = get_nifty_prices(min_date, max_date)
    print(f"  Loaded {len(df_nifty)} nifty rows")

    # Regime info
    print("Computing regime map from Nifty 50...")
    regime_info = get_regime_map(min_date, max_date)
    print(f"  Regime map built: {len(regime_info)} dates")

    eq_df, trade_log, nifty = run_mri_backtest(df_scores, df_prices, df_nifty, args, regime_info)
    if eq_df is None:
        print("No results — exiting.")
        return

    metrics = calculate_metrics(eq_df, nifty, "MRI Score Top-N")
    regime_res = regime_metrics(eq_df, trade_log)

    # Write outputs
    eq_df.reset_index().to_csv(Path(args.output_dir) / "mri_score_backtest.csv", index=False)

    win_rate = 0
    profit_factor = 0
    if trade_log:
        wins = [t for t in trade_log if t["gain"] > 0]
        win_rate = len(wins) / len(trade_log) * 100
        total_gain = sum(max(t["gain"], 0) for t in trade_log)
        total_loss = sum(abs(min(t["gain"], 0)) for t in trade_log)
        profit_factor = total_gain / (total_loss + 1e-9)

    report_path = Path(args.output_dir) / "mri_score_backtest_report.md"
    with open(report_path, "w") as f:
        f.write("# MRI Score Subsystem — Performance Backtest\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d')}\n\n")
        f.write("## Parameters\n\n")
        f.write(f"- Top-N: **{args.top_n}**\n")
        f.write(f"- Threshold: **{args.threshold}**\n")
        f.write(f"- Hold Days: **{args.hold_days}**\n")
        f.write(f"- Tx Cost: **{TX_COST * 100:.1f}%** round-trip\n\n")
        f.write("## Key Metrics\n\n")
        for k, v in metrics.items():
            f.write(f"- **{k}**: {v}\n")
        f.write("\n## Trade Statistics\n\n")
        f.write(f"- Total Trades: {len(trade_log)}\n")
        f.write(f"- Win Rate: {win_rate:.1f}%\n")
        f.write(f"- Profit Factor: {profit_factor:.2f}\n")
        f.write(f"- Final Equity: ₹{eq_df['equity'].iloc[-1]:,.2f}\n")
        f.write("\n## Regime-Conditional Performance\n\n")
        for regime, vals in regime_res.items():
            f.write(f"- **{regime}** — Avg Mo Return: {vals['avg_return_month']}%, CAGR(ann): {vals['cagr']}%\n")
        f.write("\n## Data Limitations\n\n")
        f.write(f"- stock_scores history spans only **{len(eq_df)} monthly checkpoints** ({metrics.get('Period', 'N/A')})\n")
        f.write("- For a full 10-year backtest, run `scripts/run_stee_backtest.py` (uses 1996-2024 daily_prices CSV)\n")
        f.write("- steel_scores reconstruction from `daily_prices` historical EMA signals is planned for Phase D1.5\n")

    print("\n✅ MRI Score backtest complete.")
    print(f"Report: {report_path}")
    print(metrics)

if __name__ == "__main__":
    main()
