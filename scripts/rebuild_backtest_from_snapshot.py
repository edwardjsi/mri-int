#!/usr/bin/env python3
"""Rebuild the MRI backtest from frozen CSV snapshots.

This script is intentionally self-contained:
- reads the frozen daily price snapshot
- recomputes regime and score signals
- runs both same-day and next-day execution variants
- benchmarks each variant against the frozen NIFTY50 series
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DAILY_SNAPSHOT = ROOT / "backups" / "20260304" / "daily_prices.csv"
INDEX_SNAPSHOT = Path("/home/edwar/index_prices.csv")
START_DATE = pd.Timestamp("2007-09-17")
END_DATE = pd.Timestamp("2024-12-30")
INITIAL_CAPITAL = 100_000.0
TX_COST = 0.004
TOP_POSITIONS = 10


def calculate_metrics(dates, values, name):
    series = pd.Series(pd.to_numeric(pd.Series(values), errors="coerce").to_numpy(), index=pd.to_datetime(dates))
    series = series.replace([np.inf, -np.inf], np.nan).dropna().sort_index()
    if series.empty:
        return {
            "Portfolio": name,
            "Total Return (%)": np.nan,
            "CAGR (%)": np.nan,
            "Max Drawdown (%)": np.nan,
            "Ann. Volatility (%)": np.nan,
            "Sharpe Ratio": np.nan,
            "Sortino Ratio": np.nan,
            "Calmar Ratio": np.nan,
            "Years": np.nan,
        }
    returns = series.pct_change().dropna()
    years = (series.index[-1] - series.index[0]).days / 365.25
    cagr = ((series.iloc[-1] / series.iloc[0]) ** (1 / years)) - 1 if years else 0
    rolling_max = series.cummax()
    drawdown = (series / rolling_max) - 1.0
    excess_returns = returns - (0.05 / 252)
    sharpe = (excess_returns.mean() / returns.std()) * np.sqrt(252) if returns.std() else 0
    downside = returns[returns < 0]
    downside_std = downside.std() * np.sqrt(252)
    sortino = (excess_returns.mean() * 252) / downside_std if downside_std else 0
    calmar = cagr / abs(drawdown.min()) if drawdown.min() != 0 else 0
    return {
        "Portfolio": name,
        "Total Return (%)": round(((series.iloc[-1] / series.iloc[0]) - 1) * 100, 2),
        "CAGR (%)": round(cagr * 100, 2),
        "Max Drawdown (%)": round(drawdown.min() * 100, 2),
        "Ann. Volatility (%)": round(returns.std() * np.sqrt(252) * 100, 2),
        "Sharpe Ratio": round(sharpe, 2),
        "Sortino Ratio": round(sortino, 2),
        "Calmar Ratio": round(calmar, 2),
        "Years": round(years, 1),
    }


def load_snapshot():
    usecols = [
        "symbol",
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "ema_50",
        "ema_200",
        "ema_200_slope_20",
        "rolling_high_6m",
        "avg_volume_20d",
        "rs_90d",
    ]
    daily = pd.read_csv(
        DAILY_SNAPSHOT,
        usecols=usecols,
        parse_dates=["date"],
    )
    daily = daily[(daily["date"] >= START_DATE) & (daily["date"] <= END_DATE)].copy()
    for col in ["open", "high", "low", "close", "volume", "ema_50", "ema_200", "ema_200_slope_20", "rolling_high_6m", "avg_volume_20d", "rs_90d"]:
        daily[col] = pd.to_numeric(daily[col], errors="coerce")
    daily["symbol"] = daily["symbol"].astype(str)

    index_df = pd.read_csv(
        INDEX_SNAPSHOT,
        usecols=["symbol", "date", "close"],
        parse_dates=["date"],
    )
    index_df = index_df[(index_df["symbol"] == "NIFTY50") & (index_df["date"] >= START_DATE) & (index_df["date"] <= END_DATE)].copy()
    index_df["close"] = pd.to_numeric(index_df["close"], errors="coerce")
    return daily, index_df


def compute_regime(index_df):
    df = index_df.sort_values("date").copy()
    df["sma_200"] = df["close"].rolling(window=200, min_periods=1).mean()
    df["sma_200_slope_20"] = df["sma_200"].diff(20)
    df["classification"] = "NEUTRAL"
    bull = (df["close"] > df["sma_200"]) & (df["sma_200_slope_20"] > 0)
    bear = (df["close"] < df["sma_200"]) & (df["sma_200_slope_20"] < 0)
    df.loc[bull, "classification"] = "BULL"
    df.loc[bear, "classification"] = "BEAR"
    return df[["date", "classification"]]


def compute_scores(daily):
    df = daily.sort_values(["date", "symbol"]).copy()
    df["condition_ema_50_200"] = df["ema_50"] > df["ema_200"]
    df["condition_ema_200_slope"] = df["ema_200_slope_20"] > 0
    df["condition_6m_high"] = df["close"] >= df["rolling_high_6m"]
    df["condition_volume"] = df["volume"] > (1.5 * df["avg_volume_20d"])
    df["condition_rs"] = df["rs_90d"] > 0
    df["total_score"] = (
        df["condition_ema_50_200"].astype(int) * 25
        + df["condition_ema_200_slope"].astype(int) * 25
        + df["condition_rs"].astype(int) * 20
        + df["condition_6m_high"].astype(int) * 20
        + df["condition_volume"].astype(int) * 10
    )
    return df[
        [
            "date",
            "symbol",
            "open",
            "close",
            "total_score",
        ]
    ]


def backtest(daily, regime_df, same_day_close: bool):
    regime_by_date = dict(zip(regime_df["date"], regime_df["classification"]))
    dates = sorted(regime_df["date"].tolist())

    close_by_date = daily.groupby("date").apply(lambda x: dict(zip(x.symbol, x.close))).to_dict()
    open_by_date = daily.groupby("date").apply(lambda x: dict(zip(x.symbol, x.open))).to_dict()
    score_by_date = daily.groupby("date").apply(lambda x: dict(zip(x.symbol, x.total_score))).to_dict()

    cash = INITIAL_CAPITAL
    positions = {}
    trade_log = []
    equity_curve = []
    pending_exits = []
    pending_entries = []

    for i, current_date in enumerate(dates):
        regime = regime_by_date.get(current_date, "NEUTRAL")
        today_close = close_by_date.get(current_date, {})
        today_open = open_by_date.get(current_date, {})
        today_scores = score_by_date.get(current_date, {})
        if not today_close:
            continue

        if not same_day_close:
            for sym, reason in pending_exits:
                if sym in positions:
                    exec_price = today_open.get(sym)
                    if exec_price is None or exec_price <= 0:
                        exec_price = today_close.get(sym)
                    if exec_price is None:
                        continue
                    pos = positions.pop(sym)
                    shares = pos["shares"]
                    gross = shares * exec_price
                    fee = gross * TX_COST
                    cash += gross - fee
                    trade_log.append(
                        {
                            "symbol": sym,
                            "entry_date": pos["entry_date"],
                            "exit_date": current_date,
                            "entry_price": pos["entry_price"],
                            "exit_price": exec_price,
                            "shares": shares,
                            "pnl": (gross - fee) - (shares * pos["entry_price"]),
                            "exit_reason": reason,
                            "execution": "NEXT_DAY_OPEN",
                        }
                    )
            pending_exits = []
            for sym in pending_entries:
                if sym in positions or len(positions) >= TOP_POSITIONS:
                    continue
                buy_price = today_open.get(sym)
                if buy_price is None or buy_price <= 0:
                    buy_price = today_close.get(sym)
                if buy_price is None or buy_price <= 0 or cash <= 0:
                    continue
                equity = cash + sum(pos["shares"] * today_close.get(s, pos["entry_price"]) for s, pos in positions.items())
                alloc = equity * 0.10
                invest = min(alloc, cash)
                post_fee = invest / (1 + TX_COST)
                shares = int(post_fee // buy_price)
                cost = (shares * buy_price) * (1 + TX_COST)
                if shares > 0 and cash >= cost:
                    cash -= cost
                    positions[sym] = {
                        "shares": shares,
                        "entry_price": buy_price,
                        "highest_price": buy_price,
                        "entry_date": current_date,
                    }
            pending_entries = []

        for sym, pos in list(positions.items()):
            current_price = today_close.get(sym)
            if current_price is None:
                continue
            pos["highest_price"] = max(pos["highest_price"], current_price)
            current_score = today_scores.get(sym, 0)
            exit_reason = None
            if regime == "BEAR":
                exit_reason = "REGIME_BEAR"
            elif current_score <= 2:
                exit_reason = "SCORE_LOW"
            elif current_price <= pos["highest_price"] * 0.8:
                exit_reason = "TRAILING_STOP_20"
            if exit_reason:
                if same_day_close:
                    exit_price = current_price
                    gross = pos["shares"] * exit_price
                    fee = gross * TX_COST
                    cash += gross - fee
                    positions.pop(sym)
                    trade_log.append(
                        {
                            "symbol": sym,
                            "entry_date": pos["entry_date"],
                            "exit_date": current_date,
                            "entry_price": pos["entry_price"],
                            "exit_price": exit_price,
                            "shares": pos["shares"],
                            "pnl": (gross - fee) - (pos["shares"] * pos["entry_price"]),
                            "exit_reason": exit_reason,
                            "execution": "SAME_DAY_CLOSE",
                        }
                    )
                else:
                    pending_exits.append((sym, exit_reason))

        if regime == "BULL" and (len(positions) - len(pending_exits)) < TOP_POSITIONS:
            slots_available = TOP_POSITIONS - (len(positions) - len(pending_exits))
            eligible = [
                s
                for s, score in today_scores.items()
                if score >= 4 and s not in positions and s in today_close
            ]
            eligible.sort(key=lambda s: today_scores[s], reverse=True)
            chosen = eligible[:slots_available]
            if same_day_close:
                for sym in chosen:
                    if sym in positions or len(positions) >= TOP_POSITIONS:
                        continue
                    buy_price = today_close.get(sym)
                    if buy_price is None or buy_price <= 0 or cash <= 0:
                        continue
                    equity = cash + sum(pos["shares"] * today_close.get(s, pos["entry_price"]) for s, pos in positions.items())
                    alloc = equity * 0.10
                    invest = min(alloc, cash)
                    post_fee = invest / (1 + TX_COST)
                    shares = int(post_fee // buy_price)
                    cost = (shares * buy_price) * (1 + TX_COST)
                    if shares > 0 and cash >= cost:
                        cash -= cost
                        positions[sym] = {
                            "shares": shares,
                            "entry_price": buy_price,
                            "highest_price": buy_price,
                            "entry_date": current_date,
                        }
            else:
                pending_entries = chosen

        equity = cash + sum(pos["shares"] * today_close.get(sym, pos["entry_price"]) for sym, pos in positions.items())
        equity_curve.append({"date": current_date, "equity": equity, "cash": cash, "open_positions": len(positions)})

        if not same_day_close:
            # If entries/exits are pending, they are processed on the next day.
            pass

    eq_df = pd.DataFrame(equity_curve)
    return eq_df, pd.DataFrame(trade_log)


def run():
    daily, index_df = load_snapshot()
    regime_df = compute_regime(index_df)
    daily = daily.merge(regime_df, on="date", how="inner")
    daily = compute_scores(daily)

    same_eq, same_trades = backtest(daily, regime_df, same_day_close=True)
    next_eq, next_trades = backtest(daily, regime_df, same_day_close=False)

    bench = index_df[["date", "close"]].drop_duplicates().sort_values("date")
    bench = bench[(bench["date"] >= START_DATE) & (bench["date"] <= END_DATE)].copy()

    def report(label, eq_df):
        merged = pd.merge(eq_df, bench, on="date", how="inner")
        strat = calculate_metrics(merged["date"], merged["equity"], f"{label} Strategy")
        ref = calculate_metrics(merged["date"], merged["close"], "NIFTY 50 (Buy & Hold)")
        print(f"\n=== {label} ===")
        print(f"TRADES={len(same_trades) if label == 'SAME_DAY' else len(next_trades)}")
        print(f"FINAL_EQUITY={merged['equity'].iloc[-1]:.2f}")
        print(f"ALIGNED_DAYS={len(merged)}")
        print(
            f"STRATEGY_CAGR={strat['CAGR (%)']}% MAX_DD={strat['Max Drawdown (%)']}% "
            f"SHARPE={strat['Sharpe Ratio']}"
        )
        print(
            f"BENCH_CAGR={ref['CAGR (%)']}% MAX_DD={ref['Max Drawdown (%)']}% "
            f"SHARPE={ref['Sharpe Ratio']}"
        )
        return strat, ref, merged

    same_metrics, same_bench, same_merged = report("SAME_DAY", same_eq)
    next_metrics, next_bench, next_merged = report("NEXT_DAY", next_eq)

    out = ROOT / "outputs"
    out.mkdir(exist_ok=True)
    same_eq.to_csv(out / "rebuild_same_day_equity_curve.csv", index=False)
    same_trades.to_csv(out / "rebuild_same_day_trade_log.csv", index=False)
    next_eq.to_csv(out / "rebuild_next_day_equity_curve.csv", index=False)
    next_trades.to_csv(out / "rebuild_next_day_trade_log.csv", index=False)
    pd.DataFrame([same_metrics, same_bench]).to_csv(out / "rebuild_same_day_performance_summary.csv", index=False)
    pd.DataFrame([next_metrics, next_bench]).to_csv(out / "rebuild_next_day_performance_summary.csv", index=False)


if __name__ == "__main__":
    run()
