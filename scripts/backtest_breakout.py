"""
Breakout Radar Individual Backtest
==================================
Buys when condition_breakout_10d + score >= 80.
Sells when score < 40 or hits 5-day low.
Compares vs Nifty 50.
Uses stock_scores and daily_prices from DB (2024-03 → 2026-06, 961 symbols).
"""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine_core.db import get_connection as get_db

TX_COST = 0.004
INITIAL_CAPITAL = 1_000_000.0
MAX_POSITIONS = 10

def get_stock_scores(min_date, max_date):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT symbol, date, total_score, condition_breakout_10d
        FROM stock_scores
        WHERE date BETWEEN %s AND %s
        ORDER BY symbol, date
    """, (min_date, max_date))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    df = pd.DataFrame(rows, columns=cols)
    df["date"] = pd.to_datetime(df["date"])
    for c in ["total_score", "condition_breakout_10d"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def get_daily_prices(symbols, min_date, max_date):
    conn = get_db()
    cur = conn.cursor()
    placeholders = ",".join("%s" for _ in symbols)
    q = f"""
        SELECT symbol, date, close, low
        FROM daily_prices
        WHERE symbol IN ({placeholders}) AND date BETWEEN %s AND %s
        ORDER BY symbol, date
    """
    cur.execute(q, tuple(symbols + [min_date, max_date]))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    df = pd.DataFrame(rows, columns=cols)
    df["date"] = pd.to_datetime(df["date"])
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["low"]  = pd.to_numeric(df["low"], errors="coerce")
    return df

def get_nifty_prices(min_date, max_date):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT date, close
        FROM index_prices
        WHERE symbol = 'NIFTY50' AND date BETWEEN %s AND %s
        ORDER BY date
    """, (min_date, max_date))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    df = pd.DataFrame(rows, columns=cols)
    df["date"] = pd.to_datetime(df["date"])
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    return df

def run_breakout_backtest(df_scores, df_prices, df_nifty):
    dates = sorted(df_scores["date"].unique())
    if not dates:
        print("No data")
        return None, None, None

    # Pivot prices
    price_pivot = df_prices.pivot(index="date", columns="symbol", values="close")
    low_pivot   = df_prices.pivot(index="date", columns="symbol", values="low")
    nifty = df_nifty.set_index("date")["close"].sort_index()

    # Compute 5-day rolling low
    low5_pivot = low_pivot.rolling(5).min()

    # Monthly rebalance (last score date of each month)
    reb_dates = []
    for d in dates:
        if not reb_dates or (d.year, d.month) != (reb_dates[-1].year, reb_dates[-1].month):
            reb_dates.append(d)
    if dates[-1] not in reb_dates:
        reb_dates.append(dates[-1])
    reb_dates = sorted(set(reb_dates))

    cash = INITIAL_CAPITAL
    holdings = {}
    equity_curve = []
    trade_log = []

    for i, reb in enumerate(reb_dates):
        # --- Exits ---
        sales = {}
        for sym, h in list(holdings.items()):
            price = price_pivot.get(sym, pd.Series()).get(reb)
            low5  = low5_pivot.get(sym, pd.Series()).get(reb)
            if pd.notna(price) and price > 0:
                today_score = df_scores[(df_scores["date"] == reb) & (df_scores["symbol"] == sym)]["total_score"]
                score_val = float(today_score.iloc[0]) if len(today_score) == 1 else None
                if score_val is not None and score_val < 40:
                    sales[sym] = (price, "SCORE_EXIT")
                    continue
                if pd.notna(low5) and price <= low5:
                    sales[sym] = (price, "5D_LOW")
                    continue

        if i == len(reb_dates) - 1:
            for sym, h in list(holdings.items()):
                price = price_pivot.get(sym, pd.Series()).get(reb)
                if pd.notna(price) and price > 0:
                    sales[sym] = (price, "FINAL_LIQUIDATE")

        for sym, (price, reason) in sales.items():
            h = holdings.pop(sym)
            proceeds = h["shares"] * price * (1 - TX_COST)
            cash += proceeds
            trade_log.append({
                "symbol": sym, "entry_date": h["entry_date"], "entry_price": h["entry_price"],
                "exit_date": reb, "exit_price": price, "reason": reason,
                "shares": h["shares"], "gain": h["shares"] * (price - h["entry_price"]),
            })

        # --- Entries ---
        today_scores = df_scores[df_scores["date"] == reb].copy()
        eligible = today_scores[
            (today_scores["condition_breakout_10d"] == True) &
            (today_scores["total_score"] >= 80)
        ].sort_values("total_score", ascending=False)

        target_cash = cash / MAX_POSITIONS
        for _, row in eligible.iterrows():
            sym = row["symbol"]
            if sym in holdings or len(holdings) >= MAX_POSITIONS:
                continue
            price = price_pivot.get(sym, pd.Series()).get(reb)
            if pd.notna(price) and price > 0 and cash >= price * (1 + TX_COST):
                shares = int(target_cash / (price * (1 + TX_COST)))
                if shares > 0:
                    cost = shares * price * (1 + TX_COST)
                    cash -= cost
                    holdings[sym] = {"shares": shares, "entry_date": reb, "entry_price": price, "cost": cost}

        # --- Equity ---
        val = cash
        for sym, h in holdings.items():
            price = price_pivot.get(sym, pd.Series()).get(reb)
            if pd.notna(price) and price > 0:
                val += h["shares"] * price
        equity_curve.append({"date": reb, "equity": val})

    eq_df = pd.DataFrame(equity_curve).set_index("date").sort_index()
    return eq_df, trade_log, nifty

def calculate_metrics(eq_df, nifty, name):
    series = eq_df["equity"].dropna()
    if len(series) < 2 or series.iloc[0] <= 0:
        return {"Portfolio": name, "Total Return (%)": 0, "CAGR (%)": 0, "Max Drawdown (%)": 0, "Sharpe Ratio": 0, "Benchmark Return (%)": 0, "Benchmark CAGR (%)": 0, "Alpha (%)": 0}
    returns = series.pct_change().dropna()
    years = (series.index[-1] - series.index[0]).days / 365.25
    cagr = ((series.iloc[-1] / series.iloc[0]) ** (1 / years) - 1) if years > 0 else 0
    drawdown = (series / series.cummax()) - 1.0
    sharpe = (returns.mean() / (returns.std() + 1e-9)) * np.sqrt(12)
    if nifty is not None and len(nifty) >= 2:
        nf = nifty.astype(float)
        bench = (nf.iloc[-1] / nf.iloc[0] - 1)
        bench_cagr = ((nf.iloc[-1] / nf.iloc[0]) ** (1 / years) - 1) if years > 0 else 0
    else:
        bench, bench_cagr = 0, 0
    return {
        "Portfolio": name,
        "Total Return (%)": round(((series.iloc[-1] / series.iloc[0]) - 1) * 100, 2),
        "CAGR (%)": round(cagr * 100, 2),
        "Max Drawdown (%)": round(drawdown.min() * 100, 2),
        "Sharpe Ratio": round(sharpe, 2),
        "Benchmark Return (%)": round(bench * 100, 2),
        "Benchmark CAGR (%)": round(bench_cagr * 100, 2),
        "Alpha (%)": round((cagr - bench_cagr) * 100, 2),
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="outputs")
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    df_scores = get_stock_scores("2020-01-01", "2026-12-31")
    df_scores = df_scores.dropna(subset=["date"])
    print(f"Loaded {len(df_scores)} score rows")
    symbols = df_scores["symbol"].unique().tolist()
    min_d = df_scores["date"].min().strftime("%Y-%m-%d")
    max_d = df_scores["date"].max().strftime("%Y-%m-%d")
    print(f"Range: {min_d} → {max_d}, symbols: {len(symbols)}")

    df_prices = get_daily_prices(symbols, min_d, max_d)
    df_nifty = get_nifty_prices(min_d, max_d)
    print(f"Prices: {len(df_prices)}  |  Nifty: {len(df_nifty)}")

    eq_df, trade_log, nifty = run_breakout_backtest(df_scores, df_prices, df_nifty)
    if eq_df is None:
        print("No results")
        return

    metrics = calculate_metrics(eq_df, nifty, "Breakout Radar")
    eq_df.reset_index().to_csv(Path(args.output_dir) / "breakout_backtest.csv", index=False)

    wins = [t for t in trade_log if t["gain"] > 0]
    win_rate = len(wins) / len(trade_log) * 100 if trade_log else 0
    total_gain = sum(max(t["gain"], 0) for t in trade_log)
    total_loss = sum(abs(min(t["gain"], 0)) for t in trade_log)
    pf = total_gain / (total_loss + 1e-9)

    report_path = Path(args.output_dir) / "breakout_backtest_report.md"
    with open(report_path, "w") as f:
        f.write("# Breakout Radar — Performance Backtest\n\n")
        f.write(f"Generated: 2026-06-20\n\n")
        f.write("## Key Metrics\n\n")
        for k, v in metrics.items():
            f.write(f"- **{k}**: {v}\n")
        f.write(f"\n## Trade Statistics\n\n")
        f.write(f"- Total Trades: {len(trade_log)}\n")
        f.write(f"- Win Rate: {win_rate:.1f}%\n")
        f.write(f"- Profit Factor: {pf:.2f}\n")
        f.write(f"- Final Equity: ₹{eq_df['equity'].iloc[-1]:,.2f}\n")
        f.write(f"\n## Data Limitations\n\n")
        f.write(f"- Only **{len(eq_df)} monthly checkpoints** ({min_d} → {max_d})\n")
        f.write(f"- Uses stock_scores.condition_breakout_10d + total_score >= 80 entry criteria\n")
    print(f"\n✅ Breakout backtest complete: {report_path}")
    print(metrics)

if __name__ == "__main__":
    main()
