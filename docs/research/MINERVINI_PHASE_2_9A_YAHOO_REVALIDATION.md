# MINERVINI PHASE 2.9A: RESTORED YAHOO DATA REVALIDATION

## 1. Objective
Determine whether the Minervini edge observed in Phase 2B survives after the Yahoo Finance historical price pipeline has been restored and the known data-quality problems have been addressed.

This is a strict evaluation of the existing Phase 2B methodology against the restored Yahoo Finance data, subject to a stringent Data Integrity Gate.

## 2. Phase 2B Baseline
The previously reported Phase 2B baseline was recovered from the Phase 2B artifacts (`validation_candidates.pkl` and `validation_mtm_results.pkl`).
- **Unique Setups:** 760 unique setups
- **Trades:** 47 (Variant A) / 48 (Variant B)
- **Win Rate:** 29.78% (Variant A) / 29.16% (Variant B)
- **Average R / Expectancy:** (Not explicitly available in MTM output, but implicitly driven by positive final equity)
- **Profit Factor:** 4.92 (Variant A) / 4.91 (Variant B)
- **CAGR:** 17.74%
- **Max Drawdown:** -75.14%
- **Average Market Exposure:** 78.54%

## 3. Restored Yahoo Dataset
The restored data was exported directly from the PostgreSQL `daily_prices` table to `scratch/yahoo_restored.pkl` without any modifications.
- **Row count:** 2,181,121
- **Symbol count:** 994
- **Minimum date:** 1996-01-01
- **Maximum date:** 2026-08-21
- **Duplicate symbol/date pairs:** 0

## 4. Data-Integrity Audit
**OBSERVED RESULT**
Before proceeding to any signal generation, a comprehensive data-integrity audit (`scratch/phase29a_data_audit.py`) was conducted:
- **Duplicate Symbol/Date:** 0
- **Missing OHLC:** 0
- **Negative Volume:** 0
- **Invalid OHLC Relationships (High < Open/Close/Low):** 787 instances
- **Invalid OHLC Relationships (Low > Open/Close/High):** 884 instances
- **Extreme Daily Returns (>50% or <-50%):** 463 instances
- **Abnormal Zero-Volume Days:** 37,450 instances

## 5. Corporate-Action / Bad-Tick Audit
**OBSERVED RESULT**
The specific discontinuities identified during previous phases remain unadjusted and persist in the restored Yahoo dataset:
- **BAJFINANCE:** Max Drop: -99.09% on 2005-07-29 | Max Jump: 10849.35% on 2005-07-28
- **HINDZINC:** Max Drop: -12.49% on 2008-01-21 | Max Jump: 5574.79% on 2006-11-21
- **GVT&D:** Max Drop: -7.64% on 2026-06-01 | Max Jump: 10.00% on 2025-05-26
- **BEL:** Max Drop: -97.06% on 2005-07-29 | Max Jump: 3200.00% on 2005-07-28
- **PATANJALI:** Max Drop: -97.00% on 2005-07-28 | Max Jump: 3149.85% on 2005-07-29
- **GLENMARK:** Max Drop: -94.89% on 2003-04-03 | Max Jump: 1900.00% on 2003-04-02
- **NUVAMA:** Max Drop: -94.50% on 2026-01-15 | Max Jump: 1766.93% on 2026-01-16
- **AIAENG:** Max Drop: -94.37% on 2026-01-15 | Max Jump: 1681.79% on 2026-01-16
- **CIPLA:** Max Drop: -92.00% on 2003-04-14 | Max Jump: 1224.16% on 2003-11-27

## 6. MRF Investigation
**OBSERVED RESULT**
The known critical bad tick for MRF remains present in the dataset:
- **2026-01-15:** Close drops to 1,037.49 (-99.29% daily return) with 0 volume.
- **2026-01-16:** Close jumps back to 142,837.17 (+13667.56% daily return).

## 7-15. Backtest Execution (SKIPPED)
**INFERENCE**
Because the restored Yahoo dataset failed the Data Integrity Gate (material unadjusted corporate-action discontinuities and bad ticks persist), no further signal generation, trade simulation, or portfolio backtesting was executed. Sections 7 through 15 are skipped per the strict rules of this validation.

## 16. Final Decision

### A. FAIL DATA INTEGRITY

**LIMITATION**
Material Yahoo data problems remain. The unadjusted corporate actions and massive price discontinuities (e.g., 99% drops) render the historical dataset structurally invalid for evaluating any momentum or breakout edge. Running the Phase 2B methodology over this data would produce mathematically distorted risk sizing and returns, identical to the failure condition identified previously. Production validation is impossible with this dataset.
