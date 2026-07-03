#!/usr/bin/env python3
"""
papertrader_seed.py :: 90-Day Historical Paper Trading Seed
Simulates STEE + MRI overlay entry/exit over the last 90 trading days
(2026-02-13 → 2026-06-19) using existing stock_scores and daily_prices.

Writes trades to swing_trades with sentinel client_id for PAPER_TRADER.
Generates outputs/paper_trading_90day.md with equity curve and trade log.
"""

import argparse
import os
import sys
import math
import uuid
from datetime import date
from collections import defaultdict

import psycopg2
import pandas as pd
from psycopg2.extras import RealDictCursor

PAPER_CLIENT = "a1111111-1111-1111-1111-111111111111"
START_EQUITY = 1_000_000.0
BASE_ALLOC = 20_000.0
SCORE_THRESHOLD = 50
VOLUME_MULT = 1.0


def get_conn():
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        conn = psycopg2.connect(db_url)
    else:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "mri"),
            user=os.getenv("DB_USER", "mri_user"),
            password=os.getenv("DB_PASSWORD", "mri_password"),
            port=os.getenv("DB_PORT", "5432"),
            cursor_factory=RealDictCursor,
        )
    conn.cursor_factory = RealDictCursor
    return conn


def fetch_nifty_regime(conn, end_date):
    """Compute Nifty 50 EMA 50/200 regime for each date up to end_date."""
    cur = conn.cursor()
    cur.execute(
        "SELECT date, close FROM index_prices WHERE symbol = 'NIFTY50' AND date <= %s ORDER BY date",
        (end_date,),
    )
    rows = cur.fetchall()
    if not rows:
        return {}
    df = pd.DataFrame(rows)
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean()
    # 2% transition band to reduce whipsaws
    df["band"] = (df["close"] * 0.02).rolling(20).mean()

    def regime(r):
        if pd.isna(r["ema_50"]) or pd.isna(r["ema_200"]):
            return "NEUTRAL"
        diff = r["ema_50"] - r["ema_200"]
        band = r["band"] if pd.notna(r["band"]) else 0
        if diff > band:
            return "BULLISH"
        elif diff < -band:
            return "BEARISH"
        return "NEUTRAL"

    df["regime"] = df.apply(regime, axis=1).tolist()
    return {d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d): r for d, r in zip(df["date"], df["regime"])}


def fetch_scores_and_prices(conn, start_date, end_date):
    """Pull merged stock_scores + daily_prices for the simulation window."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            ss.date, ss.symbol, ss.total_score,
            dp.close, dp.high, dp.low,
            dp.ema_200, dp.avg_volume_20d, dp.volume,
            dp.condition_price_quality,
            dp.condition_breakout_10d,
            dp.low_5d, dp.ema_10
        FROM stock_scores ss
        JOIN daily_prices dp
            ON ss.symbol = dp.symbol AND ss.date = dp.date
        WHERE ss.date BETWEEN %s AND %s
        ORDER BY ss.date, ss.symbol
        """,
        (start_date, end_date),
    )
    rows = cur.fetchall()
    return pd.DataFrame(rows)


def signal_entry(row, regime, score_thresh=None, vol_mult=None):
    """STEE + MRI overlay entry criteria."""
    sc = score_thresh if score_thresh is not None else SCORE_THRESHOLD
    vm = vol_mult if vol_mult is not None else VOLUME_MULT
    if regime == "BEARISH":
        return False
    if not row["condition_breakout_10d"]:
        return False
    score = int(row["total_score"] or 0)
    if score < sc:
        return False
    close = float(row["close"])
    ema200 = float(row["ema_200"]) if pd.notna(row["ema_200"]) else None
    if ema200 is None or close <= ema200:
        return False
    avg_vol = float(row["avg_volume_20d"]) if pd.notna(row["avg_volume_20d"]) else 0
    vol = float(row["volume"]) if pd.notna(row["volume"]) else 0
    if avg_vol <= 0 or vol <= vm * avg_vol:
        return False
    pq = float(row["condition_price_quality"]) if pd.notna(row["condition_price_quality"]) else 0
    if pq < 0.7:
        return False
    return True


def size_position(row):
    """Compute quantity, SL, target and risk for a qualifying entry."""
    close = float(row["close"])
    sl = float(row["low_5d"]) if pd.notna(row["low_5d"]) else close * 0.95
    score = int(row["total_score"] or 0)
    allocated = BASE_ALLOC * (1.5 if score >= 80 else 1.0)
    qty = max(1, math.floor(allocated / close))
    risk = (close - sl) * qty
    target = close + 2 * (close - sl)
    return qty, close, sl, target, risk


def check_exit(trade, row):
    """Evaluate exit conditions for an open trade. Returns updated trade dict or None."""
    if row is None:
        return None
    close = float(row["close"]) if pd.notna(row["close"]) else None
    high = float(row["high"]) if pd.notna(row["high"]) else None
    low = float(row["low"]) if pd.notna(row["low"]) else None
    ema10 = float(row["ema_10"]) if pd.notna(row["ema_10"]) else None
    score = int(row["total_score"]) if pd.notna(row["total_score"]) else None

    if close is None or high is None or low is None:
        return None

    # 1. Hard stop loss
    if low <= trade["stop_loss"]:
        return {**trade, "exit_price": trade["stop_loss"], "exit_reason": "SL",
                "exit_date": row["date"], "status": "CLOSED"}

    # 2. Target (2R)
    if high >= trade["take_profit_2r"]:
        return {**trade, "exit_price": trade["take_profit_2r"], "exit_reason": "TARGET",
                "exit_date": row["date"], "status": "CLOSED"}

    # 3. Trailing stop (EMA10)
    if ema10 is not None and close < ema10:
        return {**trade, "exit_price": close, "exit_reason": "TRAILING_STOP",
                "exit_date": row["date"], "status": "CLOSED"}

    # 4. Score exit (< 40)
    if score is not None and score < 40:
        return {**trade, "exit_price": close, "exit_reason": "SCORE_EXIT",
                "exit_date": row["date"], "status": "CLOSED"}

    return None


def simulate(conn, start_date, end_date):
    """Run day-by-day paper trading simulation."""
    regime_map = fetch_nifty_regime(conn, end_date)
    df = fetch_scores_and_prices(conn, start_date, end_date)
    if df.empty:
        print("No stock data found for period.")
        return [], []

    dates = sorted(df["date"].unique())
    open_trades = []
    trade_log = {}
    equity_curve = []
    cash = START_EQUITY

    for trade_date in dates:
        date_str = trade_date.strftime("%Y-%m-%d") if hasattr(trade_date, "strftime") else str(trade_date)
        regime = regime_map.get(date_str, "NEUTRAL")
        day_df = df[df["date"] == trade_date].set_index("symbol")

        # --- Process exits ---
        survivors = []
        for trade in open_trades:
            sym = trade["symbol"]
            if sym in day_df.index:
                exited = check_exit(trade, day_df.loc[sym])
                if exited:
                    cash += exited["exit_price"] * exited["quantity"]
                    trade_log[exited["id"]] = exited
                else:
                    survivors.append(trade)
            else:
                survivors.append(trade)
        open_trades = survivors

        # --- Process entries ---
        if regime != "BEARISH":
            for sym, row in day_df.iterrows():
                if any(t["symbol"] == sym and t["status"] == "OPEN" for t in open_trades):
                    continue
                if signal_entry(row, regime):
                    qty, close, sl, target, risk = size_position(row)
                    if qty <= 0 or risk <= 0:
                        continue
                    cost = close * qty
                    if cash < cost:
                        continue
                    cash -= cost
                    trade = {
                        "id": str(uuid.uuid4()),
                        "symbol": sym,
                        "entry_date": date_str,
                        "entry_price": close,
                        "stop_loss": sl,
                        "take_profit_2r": target,
                        "quantity": qty,
                        "risk_amount": risk,
                        "score_at_entry": int(row["total_score"]),
                        "status": "OPEN",
                        "exit_date": None,
                        "exit_price": None,
                        "exit_reason": None,
                        "client_id": PAPER_CLIENT,
                    }
                    open_trades.append(trade)
                    trade_log[trade["id"]] = trade

        # --- Mark-to-market equity ---
        mtm = 0.0
        for trade in open_trades:
            sym = trade["symbol"]
            if sym in day_df.index:
                mtm += float(day_df.loc[sym, "close"]) * trade["quantity"]
            else:
                mtm += trade["entry_price"] * trade["quantity"]
        total_equity = cash + mtm
        equity_curve.append({"date": date_str, "regime": regime, "equity": total_equity, "cash": cash})

    # Close any remaining open trades at final close
    final_day = df[df["date"] == dates[-1]].set_index("symbol")
    for trade in open_trades:
        sym = trade["symbol"]
        if sym in final_day.index:
            trade["exit_price"] = float(final_day.loc[sym, "close"])
        else:
            trade["exit_price"] = trade["entry_price"]
        trade["exit_date"] = str(dates[-1])
        trade["exit_reason"] = "MANUAL"
        trade["status"] = "CLOSED"
        trade_log[trade["id"]] = trade

    return list(trade_log.values()), equity_curve


def insert_trades(conn, trades, dry=False):
    """Insert all trades into swing_trades."""
    fields = [
        "id", "client_id", "symbol", "entry_date", "entry_price",
        "stop_loss", "take_profit_2r", "quantity", "risk_amount",
        "status", "exit_date", "exit_price", "exit_reason",
    ]
    placeholders = ",".join(["%s"] * len(fields))
    sql = f"INSERT INTO swing_trades ({','.join(fields)}) VALUES ({placeholders})"
    cur = conn.cursor()
    inserted = 0
    for t in trades:
        row = (
            t["id"], t["client_id"], t["symbol"], t["entry_date"],
            t["entry_price"], t["stop_loss"], t["take_profit_2r"],
            t["quantity"], t["risk_amount"], t["status"],
            t["exit_date"], t["exit_price"], t["exit_reason"],
        )
        if not dry:
            try:
                cur.execute(sql, row)
                inserted += 1
            except Exception as e:
                conn.rollback()
                print(f"WARN: insert failed for {t['symbol']}: {e}")
                continue
        else:
            print(f"[DRY] Would insert trade for {t['symbol']} {t['entry_date']} → {t['status']}")
    if not dry:
        conn.commit()
    print(f"Inserted {inserted} trades (dry={dry})")


def generate_report(trades, equity, path):
    """Write honest markdown report with equity curve and trade log."""
    closed = [t for t in trades if t["status"] == "CLOSED" and t["entry_date"] != t.get("exit_date")]
    wins = sum(1 for t in closed if t["exit_price"] > t["entry_price"])
    losses = len(closed) - wins
    total_pnl = sum((t["exit_price"] - t["entry_price"]) * t["quantity"] for t in closed)
    win_rate = (wins / len(closed) * 100) if closed else 0

    peak = START_EQUITY
    mdd = 0.0
    for point in equity:
        val = point["equity"]
        if val > peak:
            peak = val
        dd = (peak - val) / peak
        if dd > mdd:
            mdd = dd

    start = equity[0]["date"] if equity else ""
    end = equity[-1]["date"] if equity else ""

    lines = [
        "# Paper Trading 90-Day Report\n",
        f"**Period:** {start} → {end}\n",
        f"**Starting Equity:** ₹{START_EQUITY:,.0f}\n",
        f"**Trades:** {len(closed)}\n",
        f"**Wins:** {wins} | **Losses:** {losses}\n",
        f"**Win Rate:** {win_rate:.1f}%\n",
        f"**Total P&L:** ₹{total_pnl:,.0f}\n",
        f"**Max Drawdown:** {mdd * 100:.2f}%\n",
        f"**Final Equity:** ₹{equity[-1]['equity']:,.0f}\n" if equity else "",
        "\n## Equity Curve\n",
        "| Date | Regime | Equity ₹ |\n",
        "|------|--------|----------|\n",
    ]
    for point in equity:
        lines.append(f"| {point['date']} | {point['regime']} | {point['equity']:,.0f} |\n")

    lines.extend([
        "\n## Trade Log\n",
        "| Symbol | Entry | Exit | Qty | Entry ₹ | Exit ₹ | P&L ₹ | Reason |\n",
        "|--------|-------|------|-----|---------|--------|-------|--------|\n",
    ])
    for t in closed:
        pnl = (t["exit_price"] - t["entry_price"]) * t["quantity"]
        lines.append(
            f"| {t['symbol']} | {t['entry_date']} | {t.get('exit_date', '--') or '--'} | "
            f"{t['quantity']} | {t['entry_price']:.2f} | {t['exit_price']:.2f} | "
            f"{pnl:,.0f} | {t.get('exit_reason') or ''} |\n"
        )

    with open(path, "w") as f:
        f.writelines(lines)
    print(f"Report written to {path}")


def main():
    parser = argparse.ArgumentParser(description="Paper trading 90-day seed")
    parser.add_argument("--dry-run", action="store_true", help="Simulate but do not write DB")
    parser.add_argument("--start", default="2026-02-13", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2026-06-19", help="End date (YYYY-MM-DD)")
    parser.add_argument("--score-threshold", type=int, default=50, help="Min total_score for entry")
    parser.add_argument("--volume-mult", type=float, default=1.0, help="Volume multiplier over avg")
    args = parser.parse_args()
    # Update module-level constants for this run
    global SCORE_THRESHOLD, VOLUME_MULT
    SCORE_THRESHOLD = args.score_threshold
    VOLUME_MULT = args.volume_mult

    conn = get_conn()
    trades, equity = simulate(conn, args.start, args.end)
    insert_trades(conn, trades, dry=args.dry_run)
    conn.close()

    report_path = os.path.join(os.path.dirname(__file__), "..", "outputs", "paper_trading_90day.md")
    generate_report(trades, equity, report_path)

    if args.dry_run:
        print("\nDRY RUN COMPLETE. No DB rows written.")
    else:
        print(f"\nSeed complete. {len(trades)} trades recorded.")


if __name__ == "__main__":
    main()
