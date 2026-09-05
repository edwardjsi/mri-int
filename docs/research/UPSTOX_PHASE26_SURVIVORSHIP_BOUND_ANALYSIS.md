# UPSTOX PHASE 2.6 — SURVIVORSHIP SENSITIVITY / BOUND ANALYSIS

## 1. Actual Coverage
**EXPLICIT STATEMENT:** The historical constituent file `IndexInclExcl.xls` obtained from the NSE archives **does not permit this calculation**.
The free NSE archive file only tracks inclusion/exclusion dates for the **Nifty 50**, not the Nifty 500. Without a point-in-time snapshot dataset of the Nifty 500, it is impossible to calculate the actual, unestimated number of missing securities for 2005, 2010, 2015, 2020, and 2025.

## 2. Classify Missing Securities
**EXPLICIT STATEMENT:** Because the actual point-in-time constituent lists cannot be derived, we cannot classify the missing historical constituents.
- A. Bankruptcy/failure: Cannot be counted.
- B. Delisted: Cannot be counted.
- C. Merger: Cannot be counted.
- D. Acquisition: Cannot be counted.
- E. Name/identity change: Cannot be counted.
- F. Other: Cannot be counted.
- G. Unknown: 100% of the missing population is currently unknown without a commercial Nifty 500 historical dataset.

## 3. Available-Data Signal Baseline
**EXPLICIT STATEMENT:** We have not performed a 500+ stock download from Upstox (prohibited in Phase 1) and we do not have the Nifty 500 historical constituents. Therefore, we cannot calculate the actual Stage-2 candidate count, VCP candidate count, or Breakout-proxy count on the available Upstox data.
The observed qualifying setups (S) is currently UNKNOWN.

## 4. Missing-Data Bound
Because actual data is unavailable, we express the bounds as a mathematical ratio. Let $S$ = observed qualifying setups, and $N$ = number of missing historical constituent-security periods.
To change the signal population by a target percentage, the missing population would need to contain the following number of additional qualifying setups ($S_{missing}$):
- **5% change**: $S_{missing} = 0.05 \times S$
- **10% change**: $S_{missing} = 0.10 \times S$
- **25% change**: $S_{missing} = 0.25 \times S$
- **50% change**: $S_{missing} = 0.50 \times S$

## 5. Failure-Bias Stress Test (Hypothetical Sensitivity Scenarios)
*Note: These are strictly hypothetical sensitivity scenarios. They are NOT measured historical results.*
Let $R_{obs}$ = Observed setup rate = $S / N_{obs}$
Let $S_{missing}$ = Setups produced by missing securities

**Scenario A:** Missing securities produce ZERO qualifying setups.
- $S_{missing} = 0$
- Impact on signal population: 0% change.

**Scenario B:** Missing securities produce the same setup rate as observed securities.
- $S_{missing} = N \times R_{obs}$
- Impact on signal population: increases proportionally by $N / N_{obs}$.

**Scenario C:** Missing securities produce 2x the observed setup rate.
- $S_{missing} = N \times (2 \times R_{obs})$
- Impact on signal population: increases by $2 \times (N / N_{obs})$.

**Scenario D:** Missing securities produce 5x the observed setup rate.
- $S_{missing} = N \times (5 \times R_{obs})$
- Impact on signal population: increases by $5 \times (N / N_{obs})$.

## 6. Merger/Acquisition Bias
**EXPLICIT STATEMENT:** Because we cannot identify the missing securities from the NSE Nifty 50 file, we cannot determine how many observations belong to the merger, acquisition, delisting, or bankruptcy/failure categories.

## 7. FINAL RECOMMENDATION
**D. DATA INSUFFICIENT**

Without commercial data providing the true historical Nifty 500 constituents, and without downloading the full active universe from Upstox, we possess neither the baseline signal count ($S$) nor the missing constituent count ($N$). Therefore, calculating actual bounds or drawing a measured conclusion on survivorship impact is mathematically impossible.