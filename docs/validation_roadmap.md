# MRI Strategy Validation Roadmap

> **Purpose**: A systematic backtest validation plan derived from institutional quant research practices.
> Work through these tests sequentially. Failing earlier tests may make later tests irrelevant.

---

## Status Key
- ✅ **DONE** — Completed and results recorded
- 🔧 **BUILDABLE** — Can be implemented now using existing infrastructure
- 📋 **PLANNED** — Requires new data or significant new code

---

## Already Completed ✅

| # | Test | Result | File |
|---|------|--------|------|
| 1 | **Baseline Backtest (17yr)** | CAGR 29.46% (Full Nifty500) | `FINAL_REPORT.md` |
| 2 | **Next-Day Open Execution** | CAGR 26.39% (Full Nifty500) ✅ | `FINAL_REPORT.md` |
| 3 | **Walk-Forward Validation** | Train 31.44% → OOS 35.78% ✅ | `FINAL_REPORT.md` Scenario 5 |
| 4 | **2008 Crisis Stress Test** | MaxDD -3.65% vs Nifty -59.86% ✅ | `FINAL_REPORT.md` Scenario 2 |
| 5 | **2020 COVID Crash** | MaxDD -18% vs Nifty -38% ✅ | `FINAL_REPORT.md` Scenario 3 |
| 6 | **2010–2013 Sideways Market** | CAGR 21.56% (note: drawdown slightly worse) | `FINAL_REPORT.md` Scenario 4 |
| 7 | **High Friction / 2022 Vol** | CAGR 35.78% OOS period includes this | `outputs/high_friction_*` |
| 8 | **Transaction Cost Sensitivity (0.4%)** | Built into baseline engine | `portfolio_engine.py` |

---

## Phase 1 — Data Integrity (Run First) 🔧

These must be validated before trusting any backtest number.

### TEST-01: Survivorship Bias Check
**Goal**: Confirm the dataset includes stocks that were listed in 2005 but may have been delisted since.

**How to run:**
```bash
python3 - <<'EOF'
from src.db import get_connection
import pandas as pd

conn = get_connection()
df = pd.read_sql("""
    SELECT EXTRACT(YEAR FROM date) AS year, COUNT(DISTINCT symbol) AS stock_count
    FROM daily_prices
    GROUP BY year
    ORDER BY year
""", conn)
conn.close()
print(df.to_string())
EOF
```

**Pass condition**: Stock count varies across years (should grow from ~200 in 2005 to ~500+ in 2024).  
**Fail condition**: Count is flat (e.g., always 500) → dataset is survivorship-biased.

**Fix if failed**: Ingest historical NSE bhavcopy CM master files which include delisted symbols.

#### ✅ RESULT (2026-03-11)
| Metric | Value |
|--------|-------|
| Verdict | **PASS** |
| Variation | **757.6%** (59 → 506 symbols) |
| Earliest data | 2005-01-03 |
| Historical universe | 59 (2005) → 124 (2025) stocks/year |

**Key findings:**
1. **PASS on survivorship bias** — universe grows consistently year over year (59→115 over 2005–2024). Not a flat fixed list. ✅
2. **⚠️ IMPORTANT: Universe is much smaller than "Nifty500"** — The DB contains 59–124 stocks/year historically, NOT 500. The backtest ran on this smaller universe, not the full Nifty 500. The "1.64M rows" comes from depth of history, not breadth of stocks.
3. **2026 spike to 506 is artificial** — caused by our on-demand BSE ingestion (March 2026) which only has a few days of data per stock. This does NOT represent a real historical universe.

**Implication for CAGR claims:** The 33.84% CAGR was generated from a ~60–120 stock universe (likely Nifty 50/100, not Nifty 500). Rerunning on the full 500-stock universe may produce different results. This should be clarified in the FINAL_REPORT.


---

### TEST-02: Price Adjustment Check
**Goal**: Confirm OHLC is adjusted for splits and bonuses.

**How to run:** Spot-check a known stock split. e.g., Infosys 2018 split (1:1).  
Before split: price ~₹2,000. After split: price ~₹1,000. Check both sides are present and continuous.

**Pass condition**: Smooth adjusted price series with no artificial jumps.

---

## Phase 2 — Execution Realism 🔧

### TEST-03: Slippage Sensitivity
**Goal**: Test how sensitive the strategy is to transaction costs.

**How to run** (modify `portfolio_engine.py` TRANSACTION_COST):

| Cost per Trade | Expected CAGR |
|---|---|
| 0.2% (current/low) | ~26% |
| 0.4% (realistic) | ~25% |  
| 0.8% (high friction) | ~22–23% |
| 1.5% (worst case) | ~18–20% |

**Pass condition**: CAGR stays above Nifty (~10%) even at 1.5% transaction cost.

---

### TEST-04: Delayed Execution Test
**Goal**: Check if performance degrades gracefully with later entries.

**How to run** (add `entry_delay` param to `portfolio_engine.py`):

| Delay | Expected CAGR |
|---|---|
| 0 days (same-day) | 29.46% (baseline) |
| 1 day (next open) | 26.39% ✅ DONE |
| 2 days | ~21–23% |
| 3 days | ~18–20% |

**Pass condition**: Gradual degradation. A sudden collapse at 2 days would indicate timing overfitting.

---

## Phase 3 — Strategy Robustness 🔧

### TEST-05: Portfolio Size Sensitivity
**Goal**: Confirm the strategy isn't relying on exactly 10 stocks.

**How to run** (modify `TOP_N` in `portfolio_engine.py`):

| Top-N | Expected CAGR |
|---|---|
| 5 | ? |
| 10 | 25% (baseline) |
| 15 | ? |
| 20 | ? |
| 25 | ? |

**Pass condition**: Smooth, gradual degradation as N increases. Sharp changes = fragility.

---

### TEST-06: Parameter Perturbation
**Goal**: Verify EMA periods aren't overfit to history.

**Params to perturb** (in `indicator_engine.py`):

| EMA Fast | EMA Slow | Expected |
|---|---|---|
| 40 | 180 | similar |
| 50 | 200 | **baseline** |
| 60 | 220 | similar |
| 70 | 250 | similar |

**Pass condition**: CAGR stays in the 20–28% band across all variants.

---

### TEST-07: Liquidity Filter
**Goal**: Remove historically illiquid stocks to simulate realistic execution.

**How to run** (add `min_avg_volume_cr` filter before stock selection):

| Min Avg Daily Turnover | Expected Effect |
|---|---|
| No filter | baseline |
| ₹5 Cr | slight drop in universe |
| ₹10 Cr | moderate drop |
| ₹20 Cr | significant reduction |

**Pass condition**: Strategy remains viable (CAGR > 18%) at ₹10Cr filter.

---

### TEST-08: Market Cap Segmentation
**Goal**: Understand which market cap tier drives most of the alpha.

**How to run**: Tag each stock by market cap quartile. Run engine on each quartile separately.

| Segment | Expected |
|---|---|
| Large Cap only | lower CAGR, lower DD |
| Mid Cap only | higher CAGR, higher DD |
| Small Cap only | highest variance |
| All (mixed) | **baseline** |

---

## Phase 4 — Statistical Validation 🔧

### TEST-09: Randomization Test (Edge vs Luck)
**Goal**: Confirm the trend score ranking is adding real value vs random stock selection.

**How to run:**
```python
# Run 200 simulations of random stock selection (N=10)
# Keep regime filter active, replace ranking with random picks
import random
results = []
for i in range(200):
    # Replace score-based selection with random.sample(universe, 10)
    cagr = run_backtest(selection='random')
    results.append(cagr)

print(f"Random avg CAGR: {sum(results)/len(results):.1f}%")
print(f"MRI model CAGR: 25.3%")
```

**Pass condition**: MRI model CAGR clearly outside the top 5% of random distribution.

---

### TEST-10: Regime Removal Test
**Goal**: Prove the regime filter is the key source of alpha (not just momentum picking).

**How to run**: Disable regime filter. Always stay invested if score >= 4.

| Variant | Expected CAGR | Expected MaxDD |
|---|---|---|
| Full MRI (regime + score) | 25% | -31% |
| Score only (no regime) | ~20% | -45%? |
| Regime only (equal weight) | ~15%? | -20%? |

**Pass condition**: Full system clearly beats both components independently.

---

### TEST-11: Monte Carlo Simulation
**Goal**: Understand the distribution of possible outcomes by shuffling trade order.

**How to run:**
```python
# Load all historical trades
# Shuffle trade sequence 1,000 times
# Recompute equity curve each time
# Plot distribution of CAGR and MaxDD
```

**Output**: Confidence interval e.g., "90% of simulations yield CAGR between 18–32%"

---

## Phase 5 — Regime Engine Upgrades 📋

### TEST-12: Multi-Factor Regime Voting (Hedge Fund Upgrade)
**Goal**: Replace single-indicator regime with a composite voting system for greater robustness.

**Proposed factors:**

| Factor | Weight | Indicator |
|---|---|---|
| Trend | 35% | Nifty vs 200 EMA |
| Breadth | 25% | % of Nifty500 stocks above 200 DMA |
| Volatility | 20% | India VIX or realized vol |
| Momentum | 20% | 52-week high count vs low count |

**Implementation:** New function in `regime_engine.py` → `compute_composite_regime_score()`

---

### TEST-13: Regime Stability Check
**Goal**: Count regime flips. Too many = unstable, noisy signal.

**How to run:**
```sql
SELECT COUNT(*) as flips FROM (
  SELECT classification, LAG(classification) OVER (ORDER BY date) AS prev
  FROM market_regime
) t WHERE classification != prev;
```

**Pass condition**: < 15 regime flips per year on average.

---

## Phase 6 — Risk Control 📋

### TEST-14: Volatility Targeting
**Goal**: Scale position size inversely with realized volatility to stabilize Sharpe.

**Formula:**
```
target_vol = 15%  # annualized
realized_vol = rolling 20-day std of Nifty returns * sqrt(252)
vol_scale = min(max(target_vol / realized_vol, 0.3), 1.5)
capital_deployed = total_capital * vol_scale
```

**Expected improvement:**

| Metric | Before | After |
|---|---|---|
| Sharpe | 1.48 | ~1.6–1.8 |
| MaxDD | -31% | ~-20 to -25% |
| CAGR | 25% | ~23–25% |

---

## Recommended Run Order

```
Phase 1 (data integrity) → must pass before anything else
    TEST-01 Survivorship bias
    TEST-02 Price adjustment check

Phase 2 (execution) → week 2
    TEST-03 Slippage sensitivity
    TEST-04 Delayed execution

Phase 3 (robustness) → week 3
    TEST-05 Portfolio size
    TEST-06 Parameter perturbation
    TEST-07 Liquidity filter
    TEST-08 Market cap segmentation

Phase 4 (statistical) → week 4
    TEST-09 Randomization test
    TEST-10 Regime removal test
    TEST-11 Monte Carlo

Phase 5 + 6 (upgrades) → month 2
    TEST-12 Multi-factor regime
    TEST-13 Regime stability
    TEST-14 Volatility targeting
```

---

## Institutional Credibility Threshold

For MRI to be positioned as a serious quant platform (not just a backtest), the strategy must survive:

| Gate | Requirement |
|---|---|
| After slippage test | CAGR > 18% at 1% cost |
| After delay test | CAGR > 15% at 3-day delay |
| After randomization | Model in top 2% of random runs |
| After regime removal | Full system clearly beats components |
| After Monte Carlo | 80th percentile CAGR > 18% |

**If all 5 gates pass → strategy is institutionally publishable.**

---

*Last updated: 2026-03-11. Sources: FINAL_REPORT.md, Sessions.md, research conversation on CAGR/drawdown/regime architecture.*
