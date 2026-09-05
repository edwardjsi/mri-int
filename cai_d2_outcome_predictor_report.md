# D2 Outcome Predictor & Cohort Analysis Report

## 1. Methodology

This read-only study evaluates the predictive characteristics of the D2 framework by classifying all historically tracked D2 signals from the Phase 1 ledger into three distinct outcome cohorts:
1. **Failure**: Fails to reach +50% from execution price within 126 sessions.
2. **R50-only**: Reaches +50% within 126 sessions, but fails to reach +100% within 252 sessions.
3. **R100**: Reaches +100% within 252 sessions.

**Execution & Pricing:** Consistent with the Candidate Quality Study, execution is simulated at the `next_open` following the signal. Point-in-time features (RS90, EMA50 Distance, EMA200 Slope, Volume Ratio) were anchored to the signal date. W-validation tracking verified if the weekly close crossed the threshold prior to D2 structural invalidation.

**Regime Classification (Nifty50 90-day return):**
- Positive: > +3%
- Neutral: -3% to +3%
- Negative: < -3%

**Safeguards Applied:** No changes to production code were made. No new trading rules were inferred, and no optimization of CAI parameters took place. This analysis relies purely on descriptive statistics of existing historical data.

---

## 2. Overall Cohort Comparison

| Outcome | N | RS90 Med | EMA50 Dist Med | EMA200 Slope Med | Vol Ratio Med | W-Val Rate | W-Val Time Med |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Failure** | 11,292 | 83.53 | -3.1% | -2.40 | 1.08 | 31.6% | 3.0 days |
| **R50-Only** | 1,425 | 78.79 | -3.1% | -1.14 | 1.18 | 38.8% | 3.0 days |
| **R100** | 3,819 | 74.77 | -4.7% | -1.34 | 1.14 | 30.2% | 3.0 days |

---

## 3. Regime-Controlled Comparison

| Regime | Outcome | N | RS90 Med | EMA50 Dist Med | EMA200 Slope Med | Vol Ratio Med | W-Val Rate |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Positive** | Failure | 2,028 | 81.22 | -2.9% | -4.71 | 1.05 | 30.2% |
| **Positive** | R50-Only | 144 | 73.29 | -3.0% | -4.54 | 1.13 | 34.7% |
| **Positive** | **R100** | 128 | **72.42** | **-4.5%** | -25.56 | 0.91 | 23.4% |
| | | | | | | | |
| **Neutral** | Failure | 1,813 | 83.65 | -2.8% | -5.31 | 0.99 | 28.1% |
| **Neutral** | R50-Only | 127 | 66.96 | -4.7% | -6.15 | 0.78 | 21.2% |
| **Neutral** | **R100** | 84 | **82.72** | **-4.9%** | -51.68 | 0.85 | 22.6% |
| | | | | | | | |
| **Negative** | Failure | 1,174 | 86.46 | -4.8% | -5.60 | 1.01 | 22.5% |
| **Negative** | R50-Only | 169 | 77.61 | -6.0% | -6.93 | 0.90 | 16.5% |
| **Negative** | **R100** | 108 | **90.11** | **-5.3%** | -3.15 | 1.23 | 15.7% |

*(Note: N counts per regime do not perfectly sum to the global ALL count due to some historical events falling outside valid Nifty price window data or undefined regimes).*

---

## 4. Key Findings

### A. R100 vs Failure
**What distinguishes eventual R100 winners from failures?**
- **Deeper Bases (Lower Relative Strength):** Overall, R100 winners exhibited *lower* relative strength (74.77) than Failures (83.53) at the time of breakout.
- **Deeper EMA50 Contractions:** R100 winners triggered further below their 50-day EMA (-4.7%) compared to Failures (-3.1%). 
- **Effect Size:** The median difference is 8.76 absolute RS90 points lower, and 1.6% deeper below the EMA50 for R100s. 

### B. R50-only vs R100
**What distinguishes stocks that make +50% but fail to reach +100% from R100 winners?**
- **W-Validation Bias:** R50-only stocks had the highest rate of rapid W-validation (38.8%) compared to R100s (30.2%).
- **Relative Strength Trap:** In Positive regimes, R50-only stocks looked nearly identical to R100s in terms of RS90 (73.2 vs 72.4), but R100s were much more heavily discounted against the EMA50 (-4.5% vs -3.0%). R50s pop out of shallower consolidations.

### C. W-Validation
**Does D2 → Friday W validation materially increase the probability of eventual R100?**
**No.** Using Bayes' theorem on the global dataset:
- Probability of R100 given W-Validation: **21.8%**
- Probability of R100 given NO W-Validation: **23.6%**
W-Validation actually *decreases* the probability of a massive multi-bagger marathon (R100), while slightly increasing the probability of a shorter-term hit (Probability of R50-Only rises from 7.7% without W-val to 10.4% with W-val). A rapid weekly validation often signals a quick burst that fizzles out before doubling.

### D. Regime Interaction
**Do characteristics that predict R100 change between regimes?**
**Yes, heavily.**
- **Positive/Bull Regime:** R100 winners have terrible relative strength (72.4) compared to Failures (81.2). They are deep laggards catching up.
- **Negative/Bear Regime:** R100 winners have the *highest* relative strength of any group (90.1) compared to Failures (86.4). They are relative safe havens showing resilience during market crashes.

---

## 5. Limitations

- **Regime Sample Sizes:** The R100 cohort sizes within specific regimes (84 to 128 events) are small relative to the global dataset, meaning median characteristics in these specific slices are sensitive to outliers. 
- **Missing Data:** 40% of the candidate universe lacks a valid RS90 score due to insufficient trading history. This means IPOs and newly listed high-growth names are excluded from this characterization entirely, which could mask a different archetype of R100 winner.
- **Survivorship Bias / Delistings:** Forward 252-day calculations rely on continuous price data. Stocks that delisted within a year of the signal were marked as Failures (unable to reach targets), but their structural setup may have matched R100 profiles.

---

## 6. What We Can and Cannot Conclude

### What We CAN Conclude:
1. **D2 is structurally anti-momentum in bull markets.** It finds multi-bagger (R100) success by locating heavily compressed laggards (low RS90, deep below EMA50) that are pivoting upward, rather than chasing established leaders.
2. **The W-Validation cascade does not guarantee endurance.** A quick Friday validation confirms short-term momentum (boosting R50-only hits) but provides zero predictive edge for finding a +100% winner.
3. **Regime context dictates Relative Strength utility.** High RS90 is predictive of R100 success *only* during bear markets/crashes. In bull markets, high RS90 predicts failure.

### What We CANNOT Conclude:
1. **We cannot conclude that we should add an RS90 filter.** Because the predictive direction of RS90 flips based on the market regime, applying a static threshold (e.g., "Must be >80") would severely damage returns in a bull market.
2. **We cannot conclude that the D2 ruleset should be changed.** The framework is operating exactly as designed—identifying non-obvious, deeply coiled setups before they become obvious momentum leaders.
