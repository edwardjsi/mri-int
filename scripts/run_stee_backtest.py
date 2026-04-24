#!/usr/bin/env python3
"""
STEE Momentum Swing Trading — 10-Year Canonical Backtest
=======================================================
Implements the full STEE PRD logic:
- 1% Risk-per-trade position sizing
- Breakout entry (10d high + 1.5x Volume)
- 2R Partial Profit booking (50%)
- EMA-10 Trailing Stop (Remaining 50%)
- 5d-Low Hard Stop
- Market Regime sizing (Full vs 50%)
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Paths & Settings
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DAILY_SNAPSHOT = ROOT / "backups" / "20260304" / "daily_prices.csv"
INDEX_SNAPSHOT = ROOT / "backups" / "20260304" / "index_prices.csv"
if not INDEX_SNAPSHOT.exists():
    INDEX_SNAPSHOT = Path("/home/edwar/index_prices.csv")

OUTPUT_DIR = ROOT / "outputs"
START_DATE = pd.Timestamp("2014-01-01") # 10 Year focus
END_DATE = pd.Timestamp("2024-12-30")
INITIAL_CAPITAL = 100_000.0
TX_COST = 0.002 # 0.2% per leg

def calculate_metrics(dates, values, name: str) -> dict:
    series = pd.Series(values, index=pd.to_datetime(dates)).sort_index()
    returns = series.pct_change().dropna()
    years = (series.index[-1] - series.index[0]).days / 365.25
    cagr = ((series.iloc[-1] / series.iloc[0]) ** (1 / years) - 1) if years > 0 else 0
    rolling_max = series.cummax()
    drawdown = (series / rolling_max) - 1.0
    std = returns.std()
    sharpe = (returns.mean() / (std + 1e-9)) * np.sqrt(252)
    
    return {
        "Portfolio": name,
        "Total Return (%)": round(((series.iloc[-1] / series.iloc[0]) - 1) * 100, 2),
        "CAGR (%)": round(cagr * 100, 2),
        "Max Drawdown (%)": round(drawdown.min() * 100, 2),
        "Sharpe Ratio": round(sharpe, 2),
        "Win Rate (%)": 0, # To be filled after trade analysis
        "Avg R": 0,        # To be filled after trade analysis
    }

def run_stee_backtest():
    print("🚀 Starting STEE 10-Year Backtest...")
    
    # 1. Load Data
    cols = ["symbol", "date", "open", "high", "low", "close", "volume"]
    df = pd.read_csv(DAILY_SNAPSHOT, usecols=cols, parse_dates=["date"])
    df = df[(df["date"] >= START_DATE - pd.Timedelta(days=300)) & (df["date"] <= END_DATE)].copy()
    df = df.sort_values(["symbol", "date"])

    idx = pd.read_csv(INDEX_SNAPSHOT, parse_dates=["date"])
    idx = idx[idx["symbol"] == "NIFTY50"].sort_values("date")
    
    # 2. Compute STEE Indicators
    print("  Computing indicators...")
    df["ema_10"] = df.groupby("symbol")["close"].transform(lambda x: x.ewm(span=10, adjust=False).mean())
    df["ema_50"] = df.groupby("symbol")["close"].transform(lambda x: x.ewm(span=50, adjust=False).mean())
    df["ema_200"] = df.groupby("symbol")["close"].transform(lambda x: x.ewm(span=200, adjust=False).mean())
    df["high_10d"] = df.groupby("symbol")["high"].transform(lambda x: x.rolling(10).max().shift(1))
    df["low_5d"] = df.groupby("symbol")["low"].transform(lambda x: x.rolling(5).min().shift(1))
    df["avg_vol_20"] = df.groupby("symbol")["volume"].transform(lambda x: x.rolling(20).mean())
    df["atr_14"] = df.groupby("symbol").apply(lambda x: (
        pd.concat([x["high"] - x["low"], (x["high"] - x["close"].shift(1)).abs(), (x["low"] - x["close"].shift(1)).abs()], axis=1).max(axis=1).rolling(14).mean()
    )).reset_index(level=0, drop=True)
    
    # Index Regime
    idx["ema_50"] = idx["close"].ewm(span=50, adjust=False).mean()
    idx["ema_200"] = idx["close"].ewm(span=200, adjust=False).mean()
    idx["regime"] = "NEUTRAL"
    idx.loc[(idx["close"] > idx["ema_200"]) & (idx["ema_50"] > idx["ema_200"]), "regime"] = "BULLISH"
    idx.loc[(idx["close"] < idx["ema_200"]) & (idx["ema_50"] < idx["ema_200"]), "regime"] = "BEARISH"
    idx.loc[(idx["regime"] == "NEUTRAL") & (abs(idx["close"] - idx["ema_200"]) / idx["ema_200"] <= 0.02), "regime"] = "SIDEWAYS"
    
    regime_map = dict(zip(idx["date"], idx["regime"]))
    dates = sorted(df["date"].unique())
    
    # 3. Backtest Loop
    cash = INITIAL_CAPITAL
    equity_curve = []
    active_trades = [] # List of dicts
    trade_log = []
    
    # Group data by date for speed
    data_by_date = {d: g.set_index("symbol") for d, g in df.groupby("date")}
    
    print("  Running simulation...")
    for today in dates:
        if today < START_DATE: continue
        
        regime = regime_map.get(today, "NEUTRAL")
        today_data = data_by_date.get(today)
        if today_data is None: continue
        
        # A. Manage Exits for active trades
        remaining_trades = []
        for t in active_trades:
            sym = t["symbol"]
            if sym not in today_data.index:
                remaining_trades.append(t)
                continue
            
            row = today_data.loc[sym]
            price = float(row["close"])
            ema10 = float(row["ema_10"])
            
            # 1. Hard Stop (5d Low or Breakout Low)
            if price <= t["stop_loss"]:
                exit_val = t["shares"] * price * (1 - TX_COST)
                cash += exit_val
                trade_log.append({**t, "exit_date": today, "exit_price": price, "reason": "STOP_LOSS", "final_val": exit_val})
                continue
            
            # 2. Partial Profit (2R)
            if t["status"] == "OPEN" and price >= t["target_2r"]:
                sell_shares = t["shares"] // 2
                exit_val = sell_shares * price * (1 - TX_COST)
                cash += exit_val
                t["shares"] -= sell_shares
                t["status"] = "PARTIAL"
                t["partial_exit_price"] = price
                # Don't log full trade yet
            
            # 3. Trailing Stop (Close < EMA 10)
            if price < ema10:
                exit_val = t["shares"] * price * (1 - TX_COST)
                cash += exit_val
                trade_log.append({**t, "exit_date": today, "exit_price": price, "reason": "EMA10_TRAILING", "final_val": exit_val})
                continue
                
            remaining_trades.append(t)
        active_trades = remaining_trades
        
        # B. Manage Entries
        if regime != "BEARISH":
            size_mod = 0.5 if regime == "SIDEWAYS" else 1.0
            eligible = today_data[
                (today_data["close"] > today_data["high_10d"]) & # Breakout
                (today_data["volume"] > 1.5 * today_data["avg_vol_20"]) & # Volume
                ((today_data["close"] - today_data["low"]) / (today_data["high"] - today_data["low"]) >= 0.7) & # Strength
                (today_data["close"] > today_data["ema_200"]) # Trend filter
            ]
            
            for sym, row in eligible.iterrows():
                if any(t["symbol"] == sym for t in active_trades): continue
                
                price = float(row["close"])
                sl = float(row["low_5d"])
                risk_per_share = price - sl
                if risk_per_share <= 0: continue
                
                # Risk 1% of CURRENT equity
                current_equity = cash + sum(t["shares"] * today_data.loc[t["symbol"]]["close"] for t in active_trades if t["symbol"] in today_data.index)
                risk_amt = current_equity * 0.01 * size_mod
                shares = int(risk_amt / risk_per_share)
                cost = shares * price * (1 + TX_COST)
                
                if shares > 0 and cash >= cost:
                    cash -= cost
                    active_trades.append({
                        "symbol": sym, "entry_date": today, "entry_price": price,
                        "stop_loss": sl, "target_2r": price + (2 * risk_per_share),
                        "shares": shares, "initial_risk": risk_amt, "status": "OPEN", "cost": cost
                    })

        # C. Equity Tracking
        current_val = cash + sum(t["shares"] * today_data.loc[t["symbol"]]["close"] for t in active_trades if t["symbol"] in today_data.index)
        equity_curve.append({"date": today, "equity": current_val})

    # 4. Results Generation
    eq_df = pd.DataFrame(equity_curve)
    metrics = calculate_metrics(eq_df["date"], eq_df["equity"], "STEE Momentum Swing")
    
    # Win Rate & R analysis
    if trade_log:
        wins = [t for t in trade_log if (t["exit_price"] > t["entry_price"])]
        metrics["Win Rate (%)"] = round(len(wins) / len(trade_log) * 100, 2)
        # Simplified R Calculation: (Profit) / (Initial Risk)
        rs = [(t["final_val"] - t["cost"]) / t["initial_risk"] for t in trade_log]
        metrics["Avg R"] = round(np.mean(rs), 2)

    # Write Report
    report_path = OUTPUT_DIR / "stee_backtest_report.md"
    with open(report_path, "w") as f:
        f.write("# STEE Momentum Swing Trading — Performance Report\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d')}\n\n")
        f.write("## Key Metrics\n\n")
        for k, v in metrics.items():
            f.write(f"- **{k}**: {v}\n")
        f.write("\n## Trade Statistics\n\n")
        f.write(f"- Total Trades: {len(trade_log)}\n")
        f.write(f"- Final Equity: ₹{eq_df['equity'].iloc[-1]:,.2f}\n")
    
    print(f"✅ Backtest Complete. Report saved to {report_path}")
    print(metrics)

if __name__ == "__main__":
    run_stee_backtest()
