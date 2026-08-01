# Decision Ladder Thresholds Specification

**Algorithm ID:** `DL-2.1-THRESHOLDS`
**Status:** Approved for Implementation

This document defines *how* the engine calculates the technical price thresholds. It does not dictate what the investor should do. For investor actions and state resolution, refer to `DECISION_LADDER_RESOLUTIONS.md`.

## Core Variables Required
The engine requires the following weekly technical data for each position:
* `current_price` (Weekly Close)
* `ema_20_w` (20-week Exponential Moving Average)
* `ema_50_w` (50-week Exponential Moving Average)
* `primary_swing_low` (Highest valid weekly higher-low in the current trend)
* `swing_high` (Most recent confirmed higher-high pivot)
* `atr_14_w` (14-Week Average True Range)

---

## Threshold Definitions (Derived Anchor Model)

The Decision Ladder uses a mathematically rigid **Derived Anchor Model**. This mathematically guarantees that the downside thresholds always geometrically obey: `Alert > Structure > Quit`.

### 1. Add Level
**Definition:** The mathematical breakout level above current price.
**Rule:** 
`add_level = breakout_level` (from MRI Breakout Engine)
*(If missing, no Add Level is computed).*

### 2. Structure Level (The Anchor)
**Definition:** The structural backbone of the chart.
**Rule:**
`structure_level = primary_swing_low`
**Fallback Order:** `Primary Swing Low -> EMA-50 -> EMA-20 -> NOT_COMPUTED`
*(Implementation logic: This serves as the absolute anchor for the entire downside ladder. It marks the last major structural pivot).*

### 3. Risk Alert Level
**Definition:** The earliest level where historical evidence shows structural failure becomes materially more probable.
**Rule:**
`alert_level = structure_level + (1 * atr_14_w)`
*(Implementation logic: Alert should mean "approaching failure". We initially approximate this boundary using 1 Average True Range above the structure level. In future iterations, this may evolve into a dynamic probability score without changing the core product philosophy.)*

### 4. Technical Exit Level (Quit)
**Definition:** A volatility-adjusted confirmation distance below the anchor.
**Rule:**
`quit_level = structure_level - (0.5 * atr_14_w)`
*(Implementation logic: A 0.5 ATR noise buffer to protect against intra-week fake-out wicks before confirming structural failure).*

---

## Edge Case Resolution

### 1. Missing Swing Lows (e.g., Parabolic Runs)
* **Rule:** If `primary_swing_low` is NULL, fallback sequentially to the 50-EMA, then the 20-EMA. 

### 2. Gaps and Friday Closes
* **Rule:** The engine evaluates thresholds using the *Friday Close*. Intraday gaps are ignored.

### 3. Rounding Convention
* **Rule:** All output thresholds must be mathematically rounded to the nearest two decimal places (`ROUND(value, 2)`).
