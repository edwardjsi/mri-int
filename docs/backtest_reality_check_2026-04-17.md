# Backtest Reality Check

**Date:** 2026-04-17  
**Purpose:** Record why we reran the MRI backtest from scratch, what we doubted, what mistakes we found, and what the final frozen-snapshot result actually shows.

## Why We Redid the Test

We did not rerun the backtest to prove a thesis.
We reran it because the project's live state and its documentation were no longer in agreement:

- the live indicator pipeline had a serious EMA-50 null-rate problem
- the score recompute path had been silently writing stale condition columns
- the live backtest engines were not reproducing the historical CAGR claim
- the README still implied the old performance story without a fresh, reproducible rerun

That made the strategy claim too important to leave on trust alone.

## The Doubts

The main concern was simple: if the backtest could not be rebuilt cleanly from the actual data, then the performance story might be misleading.

Specific doubts we had:

- the live database may have drifted from the snapshot used in the original report
- `pandas.read_sql` with the project's DB cursor setup may have been hiding data-shape problems
- the backtest could have been depending on stale `stock_scores` booleans instead of freshly recomputed values
- the reported CAGR could have been a result of a narrower or cleaner historical universe than the prose suggested

## Mistakes Found in the Code

### 1. Backtest data access was brittle

Both portfolio engines were reading from the database with `pandas.read_sql` against a `RealDictCursor` connection.
That worked inconsistently and obscured type issues.

### 2. Numeric values were not normalized

Price and score fields were coming back as `Decimal` in some paths.
That caused execution bugs and type errors during floor division and percentage calculations.

### 3. `stock_scores` conflict handling was incomplete

The upsert path was only refreshing `total_score`.
The boolean condition columns could remain stale even after a recompute, which made the strategy state inconsistent.

### 4. The live regime / score story did not match the README claim

When we reran the corrected engines on the live database, the strategy did not support the advertised CAGR edge.

## What We Unravelled Today

We rebuilt the backtest from the frozen snapshot data:

- `backups/20260304/daily_prices.csv`
- `/home/edwar/index_prices.csv`

That snapshot covers:

- `4,237` trading days
- `501` symbols in the daily price snapshot
- `NIFTY50` benchmark history from `2007-09-17` to `2024-12-30`

The frozen-snapshot rerun produced:

- same-day execution: `26.8% CAGR`, `-25.25% max drawdown`, `1.04 Sharpe`
- next-day execution: `26.36% CAGR`, `-27.17% max drawdown`, `1.01 Sharpe`
- benchmark: `10.08% CAGR`, `-59.86% max drawdown`, `0.34 Sharpe`

## Final Finding

The strategy is a serious concept.
It is not a toy idea, and the frozen historical snapshot still shows a real edge.

But the important distinction is this:

- the **frozen snapshot** supports the original CAGR story
- the **current live repo state** does **not** reliably reproduce that story

So the correct posture is not "the strategy is fake."
The correct posture is:

1. the concept is real and deserves respect
2. the live implementation was not trustworthy enough to continue quoting without a frozen reproducible rebuild
3. the rebuilt snapshot run is the source of truth for any future discussion

## Recommendation

If this project is continued, the next step should be to lock the snapshot backtest as the canonical benchmark and separate it from any live evolving data path.

