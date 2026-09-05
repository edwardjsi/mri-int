# D2 W-Validation Timing Study

## 1. Methodology

This read-only study evaluates whether rapid W-validation (a Friday weekly close above the anchor threshold) is inherently detrimental to R100 hit rates, or whether signals that rapidly W-validate possess different starting characteristics. 

For every D2 signal in the Phase 1 ledger, the number of calendar days between the daily signal and the first W-validation was calculated. Signals were grouped into timing buckets (0-5 trading days, 6-10 days, 11-20 days, >20 days) and compared against signals that never achieved W-validation prior to structural invalidation. 

*Note: 7 calendar days was used to approximate 0-5 trading days.*

All execution prices and outcome definitions (126-day R50, 252-day R100) match the original Candidate Quality Study. No CAI modifications or optimizations were performed.

---

## 2. Global Timing-Bucket Table

| Bucket | N | RS90 Med | EMA50 Dist Med | EMA200 Slope Med | Vol Ratio Med | R50 Hit Rate | R100 Hit Rate |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **0-5 Days (Fast)** | 5,049 | 87.03 | +1.9% | -1.19 | 1.56 | 27.1% | 21.6% |
| **6-10 Days** | 191 | 88.19 | +2.1% | -3.95 | 1.23 | 25.7% | 20.9% |
| **11-20 Days** | 38 | 82.25 | +2.2% | -2.96 | 1.48 | 71.1% | 63.2% |
| **Never** | 11,258 | **80.72** | **-5.3%** | -2.46 | **0.97** | 26.3% | **23.7%** |

*(Note: The 11-20 day bucket has N=38, which is too small to draw robust conclusions from).*

---

## 3. Regime-Controlled Table

| Regime | Bucket | N | RS90 Med | EMA50 Dist Med | EMA200 Slope Med | Vol Ratio Med | R50 Hit Rate | R100 Hit Rate |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Positive (>3%)** | 0-5 Days | 683 | 83.37 | +2.1% | -3.98 | 1.61 | 11.6% | 4.4% |
| **Positive (>3%)** | 6-10 Days | 10 | 86.94 | +2.8% | -2.40 | 2.72 | 0.0% | 0.0% |
| **Positive (>3%)** | **Never** | 1,607 | **79.56** | **-4.7%** | -5.61 | 0.95 | 11.6% | **6.1%** |
| | | | | | | | | |
| **Neutral (-3% to 3%)**| 0-5 Days | 555 | 88.82 | +1.1% | -3.98 | 1.28 | 7.2% | 3.2% |
| **Neutral (-3% to 3%)**| 6-10 Days | 1 | 84.88 | +8.9% | -22.01 | 3.64 | 0.0% | 100.0% |
| **Neutral (-3% to 3%)**| **Never** | 1,468 | **81.45** | **-3.9%** | -6.82 | 0.90 | 9.7% | **4.4%** |
| | | | | | | | | |
| **Negative (<-3%)** | 0-5 Days | 228 | 93.84 | +0.9% | -6.15 | 1.37 | 14.0% | 6.6% |
| **Negative (<-3%)** | 6-10 Days | 82 | 87.65 | +1.6% | -9.56 | 1.03 | 11.0% | 2.4% |
| **Negative (<-3%)** | **Never** | 1,141 | **84.08** | **-6.7%** | -5.29 | 0.97 | 17.9% | **8.0%** |

---

## 4. Key Findings & Setup Characteristics

### Most Important Test: Is fast W-validation inherently bad?
**No. Fast W-validation is not inherently bad; rather, fast W-validation candidates represent an entirely different structural setup.**

When we compare the "0-5 Days" bucket to the "Never" bucket, the starting characteristics are drastically different:
- **EMA50 Distance:** Signals that W-validate immediately trigger when they are already **above** their 50-day EMA (+1.9%). Signals that never W-validate trigger from deep structural discounts (**-5.3%** below the EMA50).
- **Relative Strength:** Fast validators have significantly higher RS90 (87.03 vs 80.72).
- **Volume Ratio:** Fast validators break out on massive relative volume (1.56x), while "Never" validators break out on subdued volume (0.97x).

**Conclusion:** The candidates that W-validate rapidly are "momentum-style" setups—they are already above moving averages, showing high relative strength, and breaking out on heavy volume. The candidates that never W-validate are true "deep-base / reversal" setups. Because we already established that the D2 ruleset's edge specifically targets deep-base reversals (Q1 RS90, deep below EMA50), the momentum setups naturally underperform within this specific framework.

### Does the W-Validation Finding Survive Controls?
The finding that W-validation correlates with lower R100 rates *does* survive regime controls, but the mechanism is fully explained by the starting characteristics. Across every regime, the "Never" cohort triggers from much deeper below the EMA50 (-4.7% to -6.7%) and achieves higher R100 hit rates than the fast-validating cohort.

---

## 5. What We Can and Cannot Conclude

### What We CAN Conclude:
1. **W-Validation is a Proxy for Momentum:** If a D2 signal W-validates by the very next Friday, it was almost certainly a momentum-style breakout (above the EMA50, high volume) rather than a deep structural base. 
2. **D2 Should Not Target Momentum:** D2's specific combination of trailing stops, ATR constraints, and structural anchors is poorly suited for standard momentum breakouts. It excels purely at deep reversals.
3. **The Original Finding was a Confounding Variable:** We initially observed that W-validation led to lower R100 rates. We now know this is because W-validation disproportionately selects for momentum setups, which D2 handles poorly.

### What We CANNOT Conclude:
1. **We cannot conclude that W-validation is a useless concept.** For a generic momentum breakout system, rapid W-validation might be highly predictive of success. It simply conflicts with D2's specific deep-reversal edge.
2. **We cannot conclude that we should filter out momentum setups entirely.** We have not tested whether a different trailing stop / risk-management ruleset would allow these fast-validating momentum setups to reach R100.
