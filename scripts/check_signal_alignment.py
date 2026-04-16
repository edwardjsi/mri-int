#!/usr/bin/env python3
"""Inspect backtest signal alignment and entry eligibility."""

from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine_core.config import get_connection_string
from engine_core.db import get_connection


def main() -> int:
    os.environ["DATABASE_URL"] = get_connection_string()
    conn = get_connection()
    try:
        regime_df = pd.read_sql(
            "SELECT date, classification FROM market_regime WHERE classification IS NOT NULL ORDER BY date",
            conn,
        )
        scores_df = pd.read_sql(
            "SELECT date, symbol, total_score FROM stock_scores WHERE total_score IS NOT NULL",
            conn,
        )
        prices_df = pd.read_sql(
            "SELECT date, symbol, open, close FROM daily_prices",
            conn,
        )

        print(f"REGIME_ROWS={len(regime_df)}")
        print(f"SCORE_ROWS={len(scores_df)}")
        print(f"PRICE_ROWS={len(prices_df)}")
        print(f"REGIME_DATE_TYPE={type(regime_df['date'].iloc[0]).__name__}")
        print(f"SCORE_DATE_TYPE={type(scores_df['date'].iloc[0]).__name__}")
        print(f"PRICE_DATE_TYPE={type(prices_df['date'].iloc[0]).__name__}")
        print(f"REGIME_CLASSIFICATIONS={sorted(regime_df['classification'].astype(str).unique().tolist())}")
        print("REGIME_HEAD")
        print(regime_df.head(5).to_string(index=False))

        regime_dict = dict(zip(regime_df["date"], regime_df["classification"]))
        dates = sorted(regime_df["date"].tolist())
        prices_close_nested = prices_df.groupby("date").apply(
            lambda x: dict(zip(x.symbol, x.close))
        ).to_dict()
        scores_nested = scores_df.groupby("date").apply(
            lambda x: dict(zip(x.symbol, x.total_score))
        ).to_dict()

        bull_dates = [d for d, c in regime_dict.items() if c == "BULL"]
        print(f"BULL_DAYS={len(bull_dates)}")
        if not bull_dates:
            print("NO_BULL_REGIME")
            return 2

        for label, d in [
            ("FIRST", dates[0]),
            ("MIDDLE", dates[len(dates) // 2]),
            ("LAST", dates[-1]),
            ("LATEST_BULL", bull_dates[-1]),
        ]:
            close_map = prices_close_nested.get(d, {})
            score_map = scores_nested.get(d, {})
            eligible = [s for s, score in score_map.items() if score >= 4 and s in close_map]
            print(
                f"{label}_DATE={d} REGIME={regime_dict.get(d)} "
                f"CLOSES={len(close_map)} SCORES={len(score_map)} "
                f"ELIGIBLE={len(eligible)} MAX_SCORE={max(score_map.values()) if score_map else None}"
            )

        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
