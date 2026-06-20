# MRI Backtest Plan

## 1. Original System: Quantified Fundamental Backtests (2020s, Never Live)

### 1.1 Deterministic AAE Core — `backtest/aae_quant_backtest_5y.py`

**What it does:** Screener for high-quality growth stocks using annual fundamental data, with technical confirmation.

**Inputs:**
- `fundamental_financials` (annual): revenue, ebitda, net_profit, debt, equity by symbol × year
- `daily_prices` (6 months lookback): close, ema_200, high_10d, low_5d, atr_14, avg_volume_20d
- `market_index_prices` (NIFTY50): for RS benchmark

**Scoring Logic (Deterministic):**
| Rule | Points | Condition |
|------|--------|-----------|
| Revenue Growth | +30 | YoY revenue growth > 10% |
| EBITDA Growth | +30 | YoY EBITDA growth > 10% |
| Debt/Equity | +20 | D/E < 0.8 |
| High Debt Penalty | -50 | D/E > 2.0 |

**Technical Confirmation Filters (post-score):**
1. EMA 200 trend: current_price > EMA_200
2. Relative Strength: stock 6M return > Nifty 6M return

**Trade Simulation:**
- Universe: top-10 stocks by composite score (sorted by score, then stock RS)
- Entry: First trading day of year (after annual results)
- Exit: Last trading day of year
- Stop Loss: 15% trailing stop (based on max price during year)
- Benchmark: Nifty 50 annual return

**Output:** Basket return, Nifty return, alpha per year (2021-2025)

**Status:** Research artifact. Never integrated into live pipeline. Never generated live signals.

---

### 1.2 Quality Momentum — `backtest/quality_backtest.py`

**What it does:** Simple momentum strategy on QIF quality score

**Inputs:**
- `daily_prices`: close by symbol × date
- `quality_verdicts_history`: score by symbol × date

**Trade Logic:**
- **Entry:** quality score > 70 AND score > previous score (improving)
- **Exit:** score < 60 OR holding period > 30 calendar days

**Status:** Research artifact. No evidence of live execution.

---

## 2. Current Signal Paths

### 2.1 MRI Score (Daily Technical Momentum)

**Source:** `engine_core/regime_engine.py` → `api/portfolio.py` scoring

**Inputs (from `daily_prices`):**
| Condition | Weight | Field |
|-----------|--------|-------|
| EMA 50 > EMA 200 | 25% | `ema_50`, `ema_200` |
| EMA 200 Slope > 0 | 25% | series of `ema_200` over 30 days |
| RS 90d > 0 (vs Nifty) | 20% | `close` vs Nifty 90-day return |
| Close ≥ 6-Month High | 20% | `close` vs `rolling_high_6m` |
| Volume ≥ 1.3× 20D Avg | 10% | `volume` vs `avg_volume_20d` |
| Breakout: Close > 10D High | booster | `close` vs `high_10d` |
| Price Quality ≥ 0.7 | gate | `(close - low) / (high - low)` |

**Output:** `stock_scores.total_score` (0-100) + 7 condition booleans

**Storage:** `public.stock_scores(score_date, symbol, total_score, condition_*)`

---

### 2.2 Breakout Radar

**Source:** `frontend/src/BreakoutRadar.tsx` + `api/breakout_status.py`

**Inputs:** `stock_scores` latest + `daily_prices` latest

**Gold Setup Detection:**
- `condition_breakout_10d = TRUE`
- `total_score >= 80`
- `close >= rolling_high_6m` (or within 15%)
- `volume >= 1.3 * avg_volume_20d`

**Output:** Breakout status: `READY_TO_BREAKOUT`, `BROKEN_OUT`, `CONSOLIDATING`

**Storage:** `public.daily_prices(breakout_state)`

---

### 2.3 AI Forensic Debate

**Source:** `engine_debate/debate_engine.py`

**Inputs:**
- Guidance debate: management promises vs actuals (`engine_debate/context_guidance.py`)
- PE expansion debate: MRI×QIF×STEE composite + expansion thesis (`engine_debate/context_pe_expansion.py`)

**Output:** bear_text, bull_text, optional adjudicator, model_used, cache_hits
**Storage:** `public.conviction_debates(symbol, context_kind, context_hash, bear_text, bull_text, ...)`

**Cost:** ~$0.002 per debate (2 LLM calls), ~$0.001 if adjudicator.

---

### 2.4 Signal Generator (Live Portfolio)

**Source:** `engine_core/signal_generator.py`

**Inputs:**
- `stock_scores` (latest date)
- `market_regime` (latest classification)
- `client_portfolio` (open positions per client)

**Constants:**
```python
MAX_POSITIONS = 10
MIN_BUY_SCORE = 75          # BULLISH regime
MIN_BUY_SCORE_SIDEWAYS = 85 # SIDEWAYS regime
MAX_SELL_SCORE = 40
MIN_ADTV = 100_000_000      # ₹10 Cr
MAX_SECTOR_STOCKS = 3
```

**Buy Logic (per client):**
1. Get latest regime
2. Filter stocks with `total_score >= threshold` (75 or 85)
3. Filter ADTV >= ₹10 Cr
4. Skip if client already has max positions
5. Skip if sector already has 3+ stocks
6. Rank by total_score DESC, then RS 90d DESC
7. Return top candidates as BUY signals

**Sell Logic:**
1. If regime == BEARISH → SELL all open positions
2. If score <= 40 → SELL

**Output:** `client_signals` table (action=BUY/SELL)

**Note:** This is SIGNAL generation, not trade execution. Trades are recorded separately in `client_actions`.

---

### 2.5 STEE Swing Execution

**Source:** `engine_core/swing_execution_engine.py`

**Inputs:**
- `stock_scores` latest
- `daily_prices` latest
- `clients` (active clients)
- `swing_trades` (open trades)

**Qualified Watchlist:**
```sql
condition_ema_50_200 = TRUE
AND condition_ema_200_slope = TRUE
AND condition_rs = TRUE
AND close >= rolling_high_6m * 0.85
AND avg_volume_20d * close >= 100_000_000
```

**Entry Rules (all must pass):**
1. Close > Highest High (last 10 days)
2. Volume > 1.5× 20-day Avg
3. Close in top 30% of day's range
4. Gap-up < 4%
5. Candle range < 2× ATR
6. Regime != BEARISH (SIDEWAYS → 50% position size)

**Stop Loss:**
```python
stop_loss = max(low_5d, close - 2 * ATR)
# Fallback: stop_loss = close * 0.95 if invalid
```

**Position Sizing:**
```python
risk_per_trade = capital * 0.01 * regime_modifier  # 1% default, 0.5% sideways
risk_per_share = max(close - stop_loss, 1.5 * ATR)
quantity = risk_per_trade / risk_per_share
```

**Exit Rules:**
1. Hard stop: Close < original stop loss
2. Partial profit: 50% at 2R
3. Trailing stop: After 1R profit, tighten to 0.5R below price
4. EMA 10 exit: Close < EMA 10 (remaining 50%)

**Output:** `swing_trades` table entries

---

### 2.6 PERX Composite Scoring

**Source:** `engine_perx/scoring.py` + `engine_perx/orchestrator.py`

**Formula:**
```
PERX = (MRI_Score × 0.35)
     + (QIF_Score × 0.40)
     + (STEE_Setup_Score × 0.15)
     + (Trajectory_Support × 0.10)
     + Debate_Adjustment
     - Fragility_Penalty
```

Where:
- `Debate_Adjustment = (debate_score - 5.0) × 2.0`  (range: -10 to +10)
- `Fragility_Penalty = fragility_score × 0.15`  (deducts up to 15 points)

**STEE Setup Score Logic:**
```python
def compute_stee_setup_score(mri_snapshot):
    score = 0.0
    if mri_snapshot.get('condition_breakout_10d'):
        score += 40  # Core breakout signal
    if mri_snapshot.get('condition_ema_50_200'):
        score += 30  # Trend support
    if mri_snapshot.get('condition_ema_200_slope'):
        score += 30  # Momentum support
    if technical_score >= 90 and not breakout_10d:
        score += 20  # Pre-breakout accumulation
    return score
```

**Lifecycle Classification:**
| Bucket | PERX Range | Description |
|--------|-----------|-------------|
| EXPLOSIVE_IMPROVER | 85+ | Strong momentum + improving fundamentals |
| STABLE_COMPOUNDER | 70-84 | Consistent quality + steady price action |
| TURNAROUND | 50-69 | Improving but fragile |
| VALUE_TRAP | < 50 | Low score + structural issues |

**Output:** `perx_pe_scores` table

---

## 3. Data Depth Audit

| Table | Earliest Date | Latest Date | Symbols/Rows | Notes |
|-------|-------------|-------------|---------|-------|
| `daily_prices` | 1996-01-01 | 2026-06-19 | 961 symbols | Full history but earliest years sparse |
| `stock_scores` | 2024-03-25 | 2026-06-19 | 961 symbols | Only 2+ years of scoring |
| `fundamental_financials` | 2021 | 2026 | 927 symbols | Annual only, not quarterly (D1.5 deferred) |
| `perx_pe_scores` | 2026-06-18 | 2026-06-18 | 149 symbols | **Single day** — very limited history |
| `conviction_debates` | 2026-06-20 | 2026-06-20 | 149 symbols | **All generated today** (A5 force re-run) |
| `quality_verdicts` | 2026-06-20 | 2026-06-20 | 927 symbols | **All updated today** (D3 re-run + A3 backfill) |
| `swing_trades` | — | — | **0 rows** | **STEE has NEVER executed a live trade** |
| `client_signals` | — | — | **0 rows** | **Signal generator has NEVER generated a live signal** |
| `market_regime` | 2007-09-17 | 2026-06-19 | 1 | Long regime history |
| `index_prices (NIFTY50)` | 2023-01-02 | 2026-04-06 | 1 | Only ~3 years of benchmark data |

**Data Gap:** `stock_scores` only exists from 2024-03-25 onward. Any backtest before that cannot rely on `stock_scores`. Options:
1. Reconstruct scores from `daily_prices` history (computationally feasible but expensive)
2. Limit backtest to 2024-03-25 onwards
3. Use reconstructed scores for pre-2024 and real scores for post-2024

**Recommendation:** Phase 2 backtests use real `stock_scores` from 2024-03-25. Phase 3 composite backtest also starts from 2024-03-25. For longer-term evidence, use `scripts/run_stee_backtest.py` which has 10-year data via backup CSVs.

### Critical Finding: Zero Live Signals Executed
- `swing_trades` table: **0 rows** — STEE engine has never executed a single live swing trade
- `client_signals` table: **0 rows** — Signal generator has never emitted a BUY/SELL signal
- This means the system has **zero live track record**. All performance evidence must come from backtests.
- For investors: emphasize the rigor of the backtest methodology rather than live alpha (which doesn't exist yet).

---

## 4. Dead/Stale Code Inventory

| Component | Location | Issue | Impact |
|-----------|----------|-------|--------|
| PerformancePage | `frontend/src/App.tsx:1406` | Expects CAGR/Sharpe/MDD — API returns raw equity | Page broken |
| `/portfolio/performance` | `api/portfolio.py:273` | Returns raw curves, doesn't compute metrics | No investor metrics |
| `page === 'unified'` | `frontend/src/App.tsx:2729` | Renders empty `<div />` in main layout | Dead route |
| `'conviction'` page | `frontend/src/App.tsx:2601` | Missing from union type | Type inconsistency |
| 0-5 Binary Model | `Decisions.md:068`, `Readme.md:238` | Replaced by 0-100 in March 2023 | Historical only |
| Old backtests | `backtest/*.py` | Standalone scripts, never wired to live pipeline | Research only |

---

## 5. Backtest Implementation Plan

### 5.1 Phase 2: Individual Subsystems

**A. MRI Score Backtest**
- Script: `scripts/backtest_mri_score.py`
- Logic: Buy top-5 stocks by `total_score >= 75`, sell when score < 40 or after 20 trading days
- Capital: Equal weight, ₹1Cr initial
- TC: 0.4% round-trip
- Benchmark: Nifty 50
- Start: 2024-03-25 (when stock_scores begins)

**B. STEE Backtest**
- Script: `scripts/run_stee_backtest.py` (already built, fix paths)
- Uses backup CSVs for 10-year data
- Entry/exit logic exactly matches `swing_execution_engine.py`
- Position sizing: 1% risk per trade
- Benchmark: Nifty 50
- Start: 2014-01-01 (10 years)

**C. Breakout Radar Backtest**
- Script: `scripts/backtest_breakout.py`
- Logic: Buy on `condition_breakout_10d = TRUE` AND `total_score >= 80`
- Exit: Sell when score < 40 OR 20 trading days
- Capital: Equal weight
- TC: 0.4%
- Benchmark: Nifty 50

**D. PERX Backtest**
- Script: `scripts/backtest_perx.py`
- Logic: Buy when `pe_score >= 78`, sell when `pe_score < 60` or after 30 days
- Capital: Equal weight
- TC: 0.4%
- Benchmark: Nifty 50
- Challenge: limited history (only ~2 years)

### 5.2 Phase 3: Composite Backtest

**Script:** `scripts/backtest_composite.py`

**Capital Allocation Priority:**
1. STEE signals (highest conviction): 40% of capital
2. PERX scores (medium conviction): 30%
3. Breakout Radar (short-term): 20%
4. MRI Score (trend following): 10%

**Regime Override:**
- BEARISH: No new entries, sell all open positions
- SIDEWAYS: 50% position size
- BULLISH: Full size

**Position Management:**
- Max 10 positions (enforced per day)
- Max 3 per sector
- ₹10 Cr ADTV minimum

**Output:**
- Daily P&L CSV
- Cumulative equity curve
- Monthly/annual metrics vs Nifty 50

### 5.3 Phase 4: Investor Report

**Report:** `docs/INVESTOR_PERFORMANCE_REPORT.md`

**Required Metrics:**
| Metric | Target |
|--------|--------|
| CAGR | > Nifty CAGR |
| Max Drawdown | < Nifty Max DD |
| Sharpe Ratio | ≥ 1.0 |
| Walk-Forward Sharpe | ≥ 0.8 |
| Regime Stability | Consistent across 3+ regimes |
| TC Stress Test | Survive 2× transaction costs |

**Sections:**
1. Executive Summary
2. Subsystem Performance (MRI, STEE, Breakout, PERX)
3. Composite System Performance
4. Risk Metrics (Drawdown, Volatility, Beta)
5. Regime-Conditional Performance
6. Sensitivity Analysis (TC stress)
7. Live Performance vs Backtest
8. Limitations & Data Gaps
9. Next Steps for Live Validation

---

*Plan drafted: 2026-06-20*
*Data cutoff: 2026-06-19*
