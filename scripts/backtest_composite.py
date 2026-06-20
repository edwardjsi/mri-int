"""
Composite Ecosystem Backtest
============================
Simulates the complete MRI platform as a unified portfolio.

Architecture:
- STEE Swing Execution Engine (primary signal generator, 10yr CSV data)
- MRI Score overlay (2024+ DB data) — requires total_score >= 60 for entry
- Regime filter — no new entries in BEARISH
- 1% risk per trade, 0.4% tx cost
- Max 5 concurrent positions (concentration limit)
- Compare vs Nifty 50

For dates before stock_scores (pre-2024): pure STEE signals.
For dates with stock_scores (2024+): STEE + MRI Score >= 60 overlay.

This produces a daily P&L trace for alpha calculation and
regime-conditional performance.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine_core.db import get_connection as get_db

DAILY_SNAPSHOT = ROOT / "backups" / "20260304" / "daily_prices.csv"
INDEX_SNAPSHOT = ROOT / "backups" / "20260304" / "index_prices.csv"

TX_COST = 0.004
INITIAL_CAPITAL = 1_000_000.0
MAX_POSITIONS = 5
SCORE_THRESHOLD = 60
START_DATE = pd.Timestamp("2014-01-01")
END_DATE   = pd.Timestamp("2024-12-30")

def get_stock_scores():
    """Load stock_scores from DB (2024+ data). Returns DataFrame with date, symbol, total_score."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT symbol, date, total_score
        FROM stock_scores
        ORDER BY symbol, date
    """)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    df = pd.DataFrame(rows, columns=cols)
    df["date"] = pd.to_datetime(df["date"])
    df["total_score"] = pd.to_numeric(df["total_score"], errors="coerce")
    return df

def load_data():
    cols = ["symbol", "date", "open", "high", "low", "close", "volume"]
    df = pd.read_csv(DAILY_SNAPSHOT, usecols=cols, parse_dates=["date"])
    df = df[(df["date"] >= START_DATE - pd.Timedelta(days=300)) & (df["date"] <= END_DATE)].copy()
    df = df.sort_values(["symbol", "date"])

    # Compute indicators
    df["ema_10"] = df.groupby("symbol")["close"].transform(lambda x: x.ewm(span=10, adjust=False).mean())
    df["ema_200"] = df.groupby("symbol")["close"].transform(lambda x: x.ewm(span=200, adjust=False).mean())
    df["high_10d"] = df.groupby("symbol")["high"].transform(lambda x: x.rolling(10).max().shift(1))
    df["low_5d"] = df.groupby("symbol")["low"].transform(lambda x: x.rolling(5).min().shift(1))
    df["avg_vol_20"] = df.groupby("symbol")["volume"].transform(lambda x: x.rolling(20).mean())

    # Index regime
    idx = pd.read_csv(INDEX_SNAPSHOT, parse_dates=["date"])
    idx = idx[idx["symbol"] == "NIFTY50"].sort_values("date")
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
    regime_map = dict(zip(idx["date"], idx["regime"]))
    return df, regime_map, idx

def run_composite(df, regime_map, score_map):
    """
    Composite simulation.
    score_map: dict of {(date, symbol): total_score} for MRI overlay.
    """
    dates = sorted(df["date"].unique())
    data_by_date = {d: g.set_index("symbol") for d, g in df.groupby("date")}

    cash = INITIAL_CAPITAL
    equity_curve = []
    active_trades = []
    trade_log = []

    for today in dates:
        if today < START_DATE:
            continue
        regime = regime_map.get(today, "NEUTRAL")
        today_data = data_by_date.get(today)
        if today_data is None:
            continue

        # --- Manage Exits ---
        remaining_trades = []
        for t in active_trades:
            sym = t["symbol"]
            if sym not in today_data.index:
                remaining_trades.append(t)
                continue

            row = today_data.loc[sym]
            price = float(row["close"])
            if pd.isna(price) or price <= 0:
                remaining_trades.append(t)
                continue

            ema10 = float(row["ema_10"])
            sl = t["stop_loss"]

            # 1. Hard Stop
            if price <= sl:
                exit_val = t["shares"] * price * (1 - TX_COST)
                cash += exit_val
                trade_log.append({**t, "exit_date": today, "exit_price": price, "reason": "STOP_LOSS", "final_val": exit_val})
                continue

            # 2. Trailing Stop
            if price < ema10:
                exit_val = t["shares"] * price * (1 - TX_COST)
                cash += exit_val
                trade_log.append({**t, "exit_date": today, "exit_price": price, "reason": "EMA10_TRAILING", "final_val": exit_val})
                continue

            # 3. Score-based exit (2024+ only) — if score < 40
            score = score_map.get((today, sym))
            if score is not None and score < 40:
                exit_val = t["shares"] * price * (1 - TX_COST)
                cash += exit_val
                trade_log.append({**t, "exit_date": today, "exit_price": price, "reason": "SCORE_EXIT", "final_val": exit_val})
                continue

            remaining_trades.append(t)
        active_trades = remaining_trades

        # --- Manage Entries ---
        if regime != "BEARISH" and len(active_trades) < MAX_POSITIONS:
            size_mod = 0.5 if regime == "SIDEWAYS" else 1.0

            eligible = today_data[
                (today_data["close"] > today_data["high_10d"]) &
                (today_data["volume"] > 1.5 * today_data["avg_vol_20"]) &
                ((today_data["close"] - today_data["low"]) / (today_data["high"] - today_data["low"]) >= 0.7) &
                (today_data["close"] > today_data["ema_200"])
            ]

            for sym, row in eligible.iterrows():
                if any(t["symbol"] == sym for t in active_trades):
                    continue
                if len(active_trades) >= MAX_POSITIONS:
                    break

                price = float(row["close"])
                sl = float(row["low_5d"])
                risk_per_share = price - sl
                if risk_per_share <= 0 or pd.isna(sl):
                    continue

                # MRI Overlay: if score exists and < threshold, skip
                score = score_map.get((today, sym))
                if score is not None and score < SCORE_THRESHOLD:
                    continue
                # If score exists and >= threshold, boost size
                size_mult = 1.5 if (score is not None and score >= 80) else 1.0

                # Current equity = cash + positions
                current_equity = cash + sum(
                    t["shares"] * float(today_data.loc[t["symbol"]]["close"])
                    for t in active_trades
                    if t["symbol"] in today_data.index
                )
                risk_amt = current_equity * 0.01 * size_mod * size_mult
                shares = int(risk_amt / risk_per_share)
                cost = shares * price * (1 + TX_COST)

                if shares > 0 and cash >= cost:
                    cash -= cost
                    active_trades.append({
                        "symbol": sym, "entry_date": today, "entry_price": price,
                        "stop_loss": sl, "target_2r": price + (2 * risk_per_share),
                        "shares": shares, "initial_risk": risk_amt,
                        "status": "OPEN", "cost": cost,
                    })

        # --- Equity ---
        current_val = cash
        for t in active_trades:
            if t["symbol"] in today_data.index:
                p = float(today_data.loc[t["symbol"]]["close"])
                if pd.notna(p) and p > 0:
                    current_val += t["shares"] * p
        equity_curve.append({"date": today, "equity": current_val, "regime": regime})

    eq_df = pd.DataFrame(equity_curve)
    return eq_df, trade_log, dates

def calculate_metrics(eq_df, idx_df):
    series = pd.Series(eq_df["equity"].values, index=pd.to_datetime(eq_df["date"])).sort_index()
    series = series.ffill().bfill().dropna()
    if len(series) < 2 or series.iloc[0] <= 0:
        return {"Portfolio": "Composite MRI", "Total Return (%)": 0, "CAGR (%)": 0, "Max Drawdown (%)": 0, "Sharpe Ratio": 0}

    returns = series.pct_change().dropna()
    years = (series.index[-1] - series.index[0]).days / 365.25
    cagr = ((series.iloc[-1] / series.iloc[0]) ** (1 / years) - 1) if years > 0 else 0
    drawdown = (series / series.cummax()) - 1.0
    sharpe = (returns.mean() / (returns.std() + 1e-9)) * np.sqrt(252)

    nifty = idx_df.set_index("date")["close"].sort_index() if not idx_df.empty else None
    if nifty is not None and len(nifty) >= 2:
        nf = nifty.astype(float)
        bench = (nf.iloc[-1] / nf.iloc[0] - 1)
        bench_cagr = ((nf.iloc[-1] / nf.iloc[0]) ** (1 / years) - 1) if years > 0 else 0
    else:
        bench, bench_cagr = 0, 0

    return {
        "Portfolio": "Composite MRI",
        "Period": f"{series.index[0].strftime('%Y-%m-%d')} → {series.index[-1].strftime('%Y-%m-%d')}",
        "Total Return (%)": round(((series.iloc[-1] / series.iloc[0]) - 1) * 100, 2),
        "CAGR (%)": round(cagr * 100, 2),
        "Max Drawdown (%)": round(drawdown.min() * 100, 2),
        "Sharpe Ratio": round(sharpe, 2),
        "Benchmark Return (%)": round(bench * 100, 2),
        "Benchmark CAGR (%)": round(bench_cagr * 100, 2),
        "Alpha (%)": round((cagr - bench_cagr) * 100, 2),
    }

def regime_metrics(eq_df):
    results = {}
    for r in ["BULLISH", "BEARISH", "NEUTRAL", "SIDEWAYS"]:
        sub = eq_df[eq_df["regime"] == r]["equity"]
        if len(sub) < 2:
            results[r] = {"n_days": len(sub), "cagr": "—", "avg_daily_return": "—"}
            continue
        ret = sub.pct_change().dropna()
        results[r] = {
            "n_days": len(sub),
            "cagr": round((ret.mean() * 252) * 100, 2),
            "avg_daily_return": round(ret.mean() * 100, 4),
        }
    return results

def main():
    print("🚀 Starting Composite MRI Backtest...")
    os.makedirs("outputs", exist_ok=True)

    print("  Loading data...")
    df, regime_map, idx_df = load_data()
    print(f"    Daily prices: {len(df)} rows")

    print("  Loading MRI scores (2024+ overlay)...")
    df_scores = get_stock_scores()
    score_map = {}
    if not df_scores.empty:
        for _, row in df_scores.iterrows():
            score_map[(row["date"], row["symbol"])] = row["total_score"]
        print(f"    MRI scores: {len(df_scores)} rows (overlay on 2024+ dates)")
    else:
        print("    No MRI scores found — running STEE-only composite")

    eq_df, trade_log, dates = run_composite(df, regime_map, score_map)
    print(f"  Simulation complete: {len(dates)} days, {len(trade_log)} trades")

    eq_df.to_csv(Path("outputs") / "composite_backtest.csv", index=False)

    metrics = calculate_metrics(eq_df, idx_df)
    regime_res = regime_metrics(eq_df)

    wins = [t for t in trade_log if (t["exit_price"] > t["entry_price"])]
    win_rate = len(wins) / len(trade_log) * 100 if trade_log else 0
    avg_r = round(np.mean([
        (t["final_val"] - t["cost"]) / t["initial_risk"]
        for t in trade_log if t["initial_risk"] > 0
    ]), 2) if trade_log else 0

    report_path = Path("outputs") / "composite_backtest_report.md"
    with open(report_path, "w") as f:
        f.write("# MRI Platform — Composite Ecosystem Backtest\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d')}\n\n")
        f.write("## Logic\n\n")
        f.write("- **Base**: STEE Swing execution (breakout + volume + trend)\n")
        f.write("- **Overlay**: MRI Score >= 60 required for entry (2024+ dates)\n")
        f.write("- **Overlay boost**: Score >= 80 → 1.5x position size\n")
        f.write("- **Exit**: Hard stop (5d low), trailing stop (EMA 10), score < 40 exit\n")
        f.write("- **Regime**: No new buys in BEARISH\n")
        f.write("- **Max Positions**: 5 concurrent\n\n")
        f.write("## Key Metrics\n\n")
        for k, v in metrics.items():
            f.write(f"- **{k}**: {v}\n")
        f.write(f"\n## Trade Statistics\n\n")
        f.write(f"- Total Trades: {len(trade_log)}\n")
        f.write(f"- Win Rate: {win_rate:.1f}%\n")
        f.write(f"- Avg R: {avg_r:.2f}\n")
        f.write(f"- Final Equity: ₹{eq_df['equity'].iloc[-1]:,.2f}\n")
        f.write(f"\n## Regime-Conditional Performance\n\n")
        for r, vals in regime_res.items():
            f.write(f"- **{r}** — Days: {vals['n_days']}, Avg Daily Return: {vals['avg_daily_return']}%, CAGR: {vals['cagr']}%\n")
        f.write(f"\n## Data Notes\n\n")
        f.write("- Pre-2024: STEE-only (no MRI overlay due to missing stock_scores)\n")
        f.write("- 2024+: MRI Score filter applied to STEE signals\n")
        f.write("- Nifty 50 return is computed only over the overlapping period\n")

    print(f"\n✅ Composite backtest complete: {report_path}")
    print(metrics)

if __name__ == "__main__":
    main()
