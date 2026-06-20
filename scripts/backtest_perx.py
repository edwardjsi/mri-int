"""
PERX Individual Backtest
========================
PE Re-rating subsystem. Buys when pe_score >= threshold.
Sells on re-rating completion or score drop below threshold.

IMPORTANT: perx_pe_scores table has ONLY 1 day of data (2026-06-18).
This script detects insufficient data and writes a diagnostic report
instead of a misleading backtest.

To run meaningfully, historical perx_pe_scores must be backfilled.
See docs/BACKTEST_PLAN.md for reconstruction proposal.
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

TX_COST = 0.004
INITIAL_CAPITAL = 1_000_000.0

def get_perx_scores():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT symbol, generated_at, pe_score
        FROM perx_pe_scores
        ORDER BY generated_at
    """)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    df = pd.DataFrame(rows, columns=cols)
    df["date"] = pd.to_datetime(df["generated_at"])
    for c in ["pe_score"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def get_daily_prices(symbols, min_date, max_date):
    conn = get_db()
    cur = conn.cursor()
    placeholders = ",".join("%s" for _ in symbols)
    q = f"""
        SELECT symbol, date, close
        FROM daily_prices
        WHERE symbol IN ({placeholders}) AND date BETWEEN %s AND %s
        ORDER BY symbol, date
    """
    cur.execute(q, tuple(symbols + [min_date, max_date]))
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    conn.close()
    df = pd.DataFrame(rows, columns=cols)
    df["date"] = pd.to_datetime(df["generated_at"])
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
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
    df["date"] = pd.to_datetime(df["generated_at"])
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    return df

def run_perx_backtest(df_scores, df_prices, df_nifty, threshold=60):
    dates = sorted(df_scores['generated_at'].unique())
    if not dates:
        return None, None, None

    price_pivot = df_prices.pivot(index="date", columns="symbol", values="close")
    nifty = df_nifty.set_index("date")["close"].sort_index()

    # For now, treat as single-day portfolio: buy on first date, sell on last
    buy_date = dates[0]
    sell_date = dates[-1] if len(dates) > 1 else buy_date
    eligible = df_scores[(df_scores['generated_at'] == buy_date) & (df_scores["pe_score"] >= threshold)]

    if eligible.empty:
        return None, None, None

    cash = INITIAL_CAPITAL
    trade_log = []
    target = cash / len(eligible)

    for _, row in eligible.iterrows():
        sym = row["symbol"]
        price = price_pivot.get(sym, pd.Series()).get(buy_date)
        exit_price = price_pivot.get(sym, pd.Series()).get(sell_date)
        if pd.notna(price) and pd.notna(exit_price) and price > 0:
            shares = int(target / (price * (1 + TX_COST)))
            if shares > 0:
                cost = shares * price * (1 + TX_COST)
                proceeds = shares * exit_price * (1 - TX_COST)
                cash = cash - cost + proceeds
                trade_log.append({
                    "symbol": sym, "entry_date": buy_date, "entry_price": price,
                    "exit_date": sell_date, "exit_price": exit_price,
                    "shares": shares,
                    "gain": proceeds - cost,
                })

    equity = [{"date": buy_date, "equity": INITIAL_CAPITAL}, {"date": sell_date, "equity": cash}]
    eq_df = pd.DataFrame(equity).set_index("date").sort_index()
    return eq_df, trade_log, nifty

def main():
    os.makedirs("outputs", exist_ok=True)
    df_scores = get_perx_scores()
    print(f"Loaded {len(df_scores)} PE score rows")
    unique_dates = df_scores['generated_at'].nunique()
    print(f"Unique dates: {unique_dates}")

    report_path = Path("outputs") / "perx_backtest_report.md"

    if unique_dates < 10:
        with open(report_path, "w") as f:
            f.write("# PERX Subsystem — Performance Backtest\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d')}\n\n")
            f.write("## Data Gap Alert\n\n")
            f.write(f"perx_pe_scores table contains only **{unique_dates} unique date(s)**.\n\n")
            f.write(f"Earliest: {df_scores['date'].min().strftime('%Y-%m-%d') if not df_scores.empty else 'N/A'}  ")
            f.write(f"Latest: {df_scores['date'].max().strftime('%Y-%m-%d') if not df_scores.empty else 'N/A'}\n")
            if not df_scores.empty:
                f.write(f"Symbols: {df_scores['symbol'].nunique()}\n\n")
            f.write("### Why This Matters\n\n")
            f.write("PERX (PE Re-rating) requires multi-year historical scores to compute CAGR, ")
            f.write("Sharpe, and drawdown. With a single day of data, any backtest would be ")
            f.write("statistically meaningless (effectively a 1-day forward test).\n\n")
            f.write("### Proposed Remediation\n\n")
            f.write("1. **Run PERX scoring pipeline retroactively** on historical data. The scoring engine ")
            f.write("   (`engine_perx/scoring.py`) accepts historical fundamental_financials rows.\n")
            f.write("2. **Backfill for 3+ years** to cover at least one full business cycle (bull + bear).\n")
            f.write("3. **Include regime slices** to validate that PERX alpha holds across market phases.\n")
            f.write("\n### Investor View\n\n")
            f.write("Until backfill is complete, PERX must be presented as a **forward-only strategy** ")
            f.write("with no historical track record. Investors should weight PERX allocations accordingly.\n")
        print(f"⚠️ PERX data insufficient ({unique_dates} dates). Diagnostic report written.")
        print(report_path)
        return

    symbols = df_scores["symbol"].unique().tolist()
    min_d = df_scores['generated_at'].min().strftime("%Y-%m-%d")
    max_d = df_scores['generated_at'].max().strftime("%Y-%m-%d")
    df_prices = get_daily_prices(symbols, min_d, max_d)
    df_nifty = get_nifty_prices(min_d, max_d)
    eq_df, trade_log, nifty = run_perx_backtest(df_scores, df_prices, df_nifty)

    if eq_df is None:
        print("No eligible trades.")
        return

    eq_df.reset_index().to_csv(Path("outputs") / "perx_backtest.csv", index=False)
    with open(report_path, "w") as f:
        f.write("# PERX — Performance Backtest\n\n")
        f.write(f"Dates: {min_d} → {max_d}  |  Trades: {len(trade_log)}\n")
        f.write(f"Final Equity: ₹{eq_df['equity'].iloc[-1]:,.2f}\n")
    print(f"✅ PERX backtest complete: {report_path}")

if __name__ == "__main__":
    main()
