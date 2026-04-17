# MRI Platform — Session Briefing

**Date:** 2026-04-17
**Author:** Antigravity (AI Assistant)
**Session Start:** 03:30 IST
**Project:** Market Regime Intelligence (MRI) — `mri-int`

---

## 🧠 What I Learned About This Project

### What MRI Is

A quantitative decision-support platform for the Indian equity market (Nifty 500 universe).
It runs a daily pipeline that:

1. Ingests EOD price data from `yfinance` (NSE/BSE symbols)
2. Computes technical indicators per stock (EMA-50, EMA-200, 200d slope, 90d RS, 6m momentum, volume surge)
3. Classifies the overall market into a regime score (0–100, Risk-On vs Risk-Off)
4. Scores each stock 0–100 using a weighted model
5. Builds a model portfolio (top-10 stocks, equal weight, entry on Score ≥ 75 in Risk-On regime)

The goal is to become a retail SaaS product at ₹1,499–₹2,999/month, with a target of Advisor and Signal API tiers later.

---

### What the Stack Looks Like

| Layer              | Technology                          |
|--------------------|-------------------------------------|
| Quant Engine       | Python (pandas, numpy, scipy)       |
| Backend API        | FastAPI (Monolith Mode)             |
| Frontend           | React + Vite + Tailwind             |
| Database           | Neon.tech (Serverless PostgreSQL)   |
| Deployment         | Railway.app (Unified Service)       |
| Data Source        | yfinance (NSE/BSE EOD)              |

---

### History of Problems Encountered

1. **Schema instability** — `index_prices` table missing `created_at`, causing ingestion crashes. Fixed with idempotent `DO` blocks.
2. **Stale runner cache (ghost modules)** — WSL/GitHub Actions caching caused old code to run. Fixed by migrating to `engine_core` package structure.
3. **EMA-50 NULL epidemic** — 94% of 514 symbols had NULL EMA-50 values (Decision 080, April 15). Reduced to ~0.2% after patching the indicator engine with verification + resumable batch limits.
4. **Stale `stock_scores` booleans** — Upsert path only refreshed `total_score`, leaving boolean condition columns stale after recomputes. Fixed in this session.
5. **Brittle backtest data access** — `pandas.read_sql` + `RealDictCursor` was inconsistent and hid type errors (Decimal fields, shape issues).
6. **Live DB does not reproduce the headline CAGR** — After fixing all of the above, the live DB rerun did NOT reproduce the 20%+ CAGR story. The original result was derived from a frozen historical snapshot.

---

### The Critical Finding (from `docs/backtest_reality_check_2026-04-17.md`)

There are **two separate realities** in this project right now:

| Reality | Source | CAGR | Max DD | Sharpe | Status |
|---------|--------|------|--------|--------|--------|
| Frozen snapshot | `backups/20260304/daily_prices.csv` + `index_prices.csv` | **26.8%** (same-day) / **26.36%** (next-day) | -25.25% / -27.17% | **1.04** / **1.01** | ✅ Real, reproducible |
| Live DB rerun | Current `market_index_prices` + `stock_scores` | Unknown | Unknown | Unknown | ❌ Does not reproduce headline |
| Nifty benchmark | `^NSEI` 2007–2024 | 10.08% | -59.86% | 0.34 | Reference |

The snapshot covers **4,237 trading days**, **501 symbols**, from ~2005 to 2024.

**The strategy concept is real.** The frozen snapshot supports a genuine edge over Nifty buy-and-hold. The live implementation is not currently trustworthy enough to quote.

---

### Current State of the Codebase

**Active modules (in `src/`):**
- `src/db.py` — Schema v12.1, uses `market_index_prices` table (BIGSERIAL, TIMESTAMPTZ)
- `src/ingestion_engine.py` — Fetches NIFTY50 via yfinance, inserts into `market_index_prices`
- `src/config.py` — DB credential loader

**Dead / archived code:**
- `db.py` (root, v9.0) — References old `index_prices` table. Not used.
- `db_fixed.py` (root) — Older full-schema reference. Not used.
- `check_db_state.py` — Queries `index_prices` (wrong table). Broken against current schema.

**Key docs:**
- `Readme.md` — Full architecture, strategy rules, pipeline flow
- `Progress.md` — Issue history, phase tracking, current status
- `Tasks.md` — Day-by-day task log (Day 1 through Day 28+)
- `Decisions.md` — Architectural decision log (up to Decision 080)
- `docs/backtest_reality_check_2026-04-17.md` — The canonical honesty document
- `SaaS_Blueprint.md` — Product and monetization plan

---

## 📋 What I Am Going to Do This Session

### Primary Goal
**Lock the frozen snapshot backtest as the canonical, reproducible source of truth.**

This implements the recommendation in `docs/backtest_reality_check_2026-04-17.md`.

---

### Deliverable: `backtest/run_snapshot.py`

A single, self-contained script that:

1. **Loads the frozen CSVs** — reads `backups/20260304/daily_prices.csv` and the index prices CSV. No database connection. No live data. No yfinance calls.

2. **Recomputes all indicators from scratch** using only pandas:
   - EMA-50, EMA-200 (per symbol, sorted by date)
   - 200d EMA slope (20-day regression)
   - 90-day Relative Strength vs NIFTY50
   - 6-month price momentum (% change)
   - 20-day average volume ratio (volume surge indicator)

3. **Runs the regime engine** — computes daily regime score (0–100) from breadth metrics across the universe, classifies as Risk-On (>60), Neutral, or Risk-Off (<40)

4. **Runs the portfolio engine** in two modes:
   - **Same-day**: Signal computed and executed on the same row's price
   - **Next-day**: Signal computed on day T, executed on day T+1 open

5. **Produces a locked report** (`outputs/snapshot_canonical.md`) with:
   - All performance metrics (CAGR, Max DD, Sharpe, Sortino, Exposure)
   - A clear header marking it as the canonical frozen-snapshot result
   - A checksum or record count of the input data (to prove it wasn't tampered)
   - Timestamp of when the run was executed

6. **Produces period stress test results** across:
   - 2008 crash
   - 2010–2013 sideways
   - 2020 COVID crash
   - Walk-forward: train (2005–2015) vs test (2016–2024)

---

### Secondary Goal (if time allows)
Update `check_db_state.py` to use `market_index_prices` (the correct current table name).

---

### Files to Create

| File | Purpose |
|------|---------|
| `scripts/run_canonical_backtest.py` | The canonical frozen-snapshot backtest runner |
| `scripts/__init__.py` | Makes it a proper package |
| `outputs/snapshot_canonical.md` | Locked output report (generated by the script) |

### Files to NOT Touch
- `src/db.py`, `src/ingestion_engine.py` — Live pipeline, leave stable
- The frozen CSVs in `backups/` — Read-only inputs
- `docs/backtest_reality_check_2026-04-17.md` — Source of truth document

---

## ⚠️ Risks and Constraints

1. **I cannot read `.md` files directly** — There is a WSL path mapping issue. The `view_file` tool only works for files that exist on the Linux filesystem side, and `.md` files appear to have a Windows-side lock. The user needs to paste contents manually. Python files work fine.

2. **I cannot run commands directly** — `run_command` tool also has a workspace path validation issue. All commands must be proposed for user approval.

3. **I have not seen `engine_core/`** — The find output was truncated. I need to know if existing backtest engines are already there before building from scratch.

4. **The frozen CSVs path needs confirmation** — I have seen `backups/20260304/daily_prices.csv` referenced in docs, but need to confirm it physically exists before writing code that depends on it.

---

## 🔑 Principles This Session Follows

1. **Do not touch the live pipeline** — `src/` stays intact
2. **Read-only on frozen data** — CSVs are inputs, not outputs
3. **Zero DB dependency in the snapshot runner** — pure pandas, pure CSV
4. **Reproducibility over performance** — the script must produce the same numbers on every run, on any machine
5. **Document everything** — the output report must be self-describing

---

*Antigravity — Session opened 2026-04-17 03:30 IST*
