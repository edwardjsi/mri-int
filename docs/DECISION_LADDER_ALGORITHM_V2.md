# Decision Ladder Algorithm Specification (Version 2.0)

**Algorithm ID:** `DL-2.0`
**Status:** Approved for Implementation

This document is the **single source of truth** for all CAI Decision Ladder calculations. The backend engine must implement these exact deterministic rules. No layer may redefine or reinterpret this algorithm.

## Core Variables Required
The engine requires the following weekly technical data for each position:
* `current_price` (Weekly Close)
* `ema_20_w` (20-week Exponential Moving Average)
* `ema_50_w` (50-week Exponential Moving Average)
* `swing_low` (Most recent confirmed higher-low pivot)
* `swing_high` (Most recent confirmed higher-high pivot)

---

## Threshold Definitions

### 1. Add Level
**Definition:** The price point at which the position demonstrates sufficient breakout strength to warrant additional capital.
**Rule:** 
`add_level` is defined as the lowest price that objectively confirms renewed strength after the current consolidation.
*(Implementation logic: The specific computation delegates to the approved MRI breakout or swing high rule, rather than a simplistic multiplier).*

### 2. Alert Level
**Definition:** The early warning boundary indicating momentum deceleration.
**Rule:**
`alert_level = ema_20_w`
*(Implementation logic: A break below the 20-week EMA triggers the first Alert, indicating short-term trend exhaustion).*

### 3. Structure Level
**Definition:** The critical support boundary where the primary trend is severely threatened.
**Rule:**
`structure_level = ema_50_w`
*(Implementation logic: The 50-week EMA serves as the structural backbone of the portfolio. Violating this level initiates risk mitigation).*

### 4. Quit Level
**Definition:** The absolute thesis invalidation point where the stock must be exited.
**Rule:**
`quit_level = swing_low`
*(Implementation logic: A lower-low structural break invalidates the uptrend thesis completely).*

---

## State Resolution Hierarchy

The backend must resolve the `decision_state` by evaluating conditions in this strict priority order. The highest priority condition that evaluates to TRUE becomes the active state.

**Priority 1: QUIT**
* `IF current_price < quit_level THEN decision_state = 'QUIT'`

**Priority 2: STRUCTURE**
* `IF current_price >= quit_level AND current_price < structure_level THEN decision_state = 'STRUCTURE'`

**Priority 3: ALERT**
* `IF current_price >= structure_level AND current_price < alert_level THEN decision_state = 'ALERT'`

**Priority 4: ADD**
* `IF current_price >= add_level THEN decision_state = 'ADD'`

**Priority 5: HOLD (Default)**
* `ELSE decision_state = 'HOLD'`

*Note: The system guarantees exactly one active state per position.*

---

## Edge Case Resolution & Determinism Rules

To guarantee mathematical determinism, the engine must execute the following fallback rules universally:

### 1. Missing Swing Lows / Highs (e.g., IPOs, Straight Parabolic Runs)
* **Rule:** If `swing_low` is NULL, fallback to `ema_50_w`. If `ema_50_w` is also NULL, the system must set `decision_state = 'NOT_COMPUTED'`. A deterministic engine must not manufacture technical levels from arbitrary percentages.
* **Rule:** If `swing_high` is NULL, `add_level` evaluates via the approved breakout rule if possible.

### 2. Missing EMAs (Recent IPOs < 50 weeks)
* **Rule:** If `ema_50_w` is NULL, the `structure_level` evaluates to the 20-week EMA (`ema_20_w`). If `ema_20_w` is also NULL, the `structure_level` evaluates to the recent `swing_low`.

### 3. Precedence in Disagreements (e.g., Swing Low > EMA50)
* **Rule:** The calculation formulas remain completely rigid. If the 50-EMA is mathematically higher than the Swing Low, then the Structure level is higher than the Quit level. If a gap down forces price below both simultaneously, the State Resolution Hierarchy (Priority 1: QUIT) naturally overrides Priority 2 (STRUCTURE).

### 4. Gaps and Friday Closes
* **Rule:** The engine only evaluates the *Friday Close*. Intraday gaps or mid-week wicks below thresholds are strictly ignored by this batch engine.

### 5. Stage 1 Bases (Sideways Compression)
* **Rule:** If the stock is moving sideways and the 20-EMA / 50-EMA / Swing Lows are completely compressed, the mathematical outputs remain as formulated. However, the engine evaluates an internal metadata flag `decision_quality = 'LOW'` to distinguish these mechanically correct but contextually weak ladders from high-quality trends (`decision_quality = 'NORMAL'`).

### 6. Rounding Convention
* **Rule:** All output thresholds must be mathematically rounded to the nearest two decimal places (`ROUND(value, 2)`) before insertion into the database to match PostgreSQL `DECIMAL(10,2)`.

### 7. Triggering `NOT_COMPUTED`
* **Rule:** The system sets `decision_state = 'NOT_COMPUTED'` under exactly two conditions:
  1. `current_price` (Weekly Close) is entirely missing from the upstream data feed.
  2. The asset lacks enough history to compute both the primary support (`swing_low`) and the fallback support (`ema_50_w`).
