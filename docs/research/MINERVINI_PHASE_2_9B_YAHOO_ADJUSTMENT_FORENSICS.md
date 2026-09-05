# MINERVINI PHASE 2.9B: YAHOO ADJUSTMENT-FACTOR FORENSICS

## 1. Objective
Determine whether the existing Yahoo Finance dataset can be deterministically repaired using Yahoo-provided adjustment information (like `Adj Close`, dividends, and splits) without running the Minervini backtest.

## 2. Methodology & Findings
We conducted a targeted forensic analysis by directly downloading the unadjusted and adjusted OHLCV data, along with corporate actions, from `yfinance` for the specific anomaly symbols and dates.

### A. Can Yahoo's own adjustment information repair the historical OHLCV series deterministically?
**NO.** Our investigation shows that Yahoo Finance's `Adj Close` column does NOT contain the necessary adjustment factors to repair these massive discontinuities. The ratio of `Adj Close` to `Close` remains constant across the extreme price jumps/drops.

### B. Does it repair the known corporate-action discontinuities?
**NO.** For example, **CIPLA** experienced a permanent price jump from ~₹7.23 to ~₹95.80 on 2003-11-27 (a >1200% increase). Yahoo's `Adj Close` tracks this exact same >1200% jump without flattening the series. Furthermore, Yahoo's `stock splits` and `dividends` columns report `0.0` for this event, meaning Yahoo itself is completely missing the underlying corporate action data required to mathematically adjust it.

### C. Does it repair the MRF bad tick?
**NO.** While a fresh fetch from Yahoo for MRF around 2026-01-15 now entirely omits the date (treating it as missing/holiday instead of a bad tick), the other structural bad ticks remain completely unaddressed in the Yahoo source data.

### D. Are there residual >50% moves that require manual treatment?
**YES.** We found profound "bad ticks" (single-day price spikes that revert the next day) where `Adj Close` offers no repair. 
- **BAJFINANCE (2005-07-28):** Jumps from ₹2.66 to ₹291.47, then back to ₹2.67 the next day. The `Adj Close` mirrors this exactly (a +10,849% daily return).
- **BEL (2005-07-28):** Jumps from ₹7.48 to ₹250.96, then back to ₹7.62 (a +3,200% daily return). `Adj Close` mirrors this.
- **PATANJALI (2005-07-28):** Drops from ₹1666 to ₹50, then back to ₹1680. 
- **GLENMARK (2003-04-02):** Jumps from ₹1.02 to ₹20.67, then back to ₹1.07.

In all of these cases, Yahoo provides no adjustment factor to fix the data.

### E. Can the resulting series pass the Data Integrity Gate?
**NO.** Because Yahoo's own adjustment factors and corporate action tables are fundamentally blind to these events (both the unadjusted corporate actions and the transient bad ticks), it is impossible to deterministically repair the dataset using Yahoo's provided data. The resulting OHLCV series will still violently breach the Data Integrity Gate.

## 3. Final Decision

### C. NOT REPAIRABLE — another data source is required.

**Conclusion:** 
Yahoo Finance cannot be used to backtest this strategy. The dataset suffers from missing corporate action adjustments and severe transient bad ticks that are baked directly into both their raw `Close` and their `Adj Close` series. No deterministic mathematical transformation using Yahoo's data can repair this. A commercial, point-in-time, split-adjusted historical dataset is absolutely required to proceed with production validation.
