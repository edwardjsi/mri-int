# Breakout & Ready-To-Breakout Identification Engine
## Implementation Plan & Architecture
**Date: May 21, 2026**

### 1. Objective
To implement an automated technical analysis layer inside the MRI platform that classifies stocks into specific breakout stages (`BROKEN_OUT`, `READY_TO_BREAKOUT`, `CONSOLIDATING`). This helps swing traders and momentum investors discover active breakouts with institutional volume support, as well as high-probability consolidation patterns (VCP - Volatility Contraction Pattern) that are primed to break out.

---

### 2. Core Concepts & Mathematical Rules

#### State A: `BROKEN_OUT` (Momentum Active)
A stock is classified as `BROKEN_OUT` on a given date if it satisfies:
1.  **Price Breakout**: Current close is equal to or exceeds the 10-day high or 6-month high:
    $$\text{close} \ge \text{high\_10d} \quad \text{OR} \quad \text{close} \ge \text{rolling\_high\_6m} \times 0.99$$
2.  **Volume Confirmation**: Current daily volume shows a surge:
    $$\text{volume} \ge \text{avg\_volume\_20d} \times 1.30$$
3.  **Trend Alignment**: Aligned above its moving averages:
    $$\text{close} > \text{ema\_50} \quad \text{AND} \quad \text{ema\_50} \ge \text{ema\_200}$$

#### State B: `READY_TO_BREAKOUT` (Volatility Contraction & Proximity)
A stock is classified as `READY_TO_BREAKOUT` if it is consolidating tightly near its key resistance levels and waiting for a volume trigger:
1.  **Proximity**: Close is extremely close to its 6-month high or 10-day high but has *not* broken out:
    $$0.97 \times \text{rolling\_high\_6m} \le \text{close} < \text{rolling\_high\_6m} \quad \text{AND} \quad \text{close} < \text{high\_10d}$$
2.  **Volatility Contraction (VCP)**: The price range over the last 5 days has contracted. We measure this using the high-to-low daily spread:
    $$\text{Average}\left(\frac{\text{high} - \text{low}}{\text{close}}\right) \text{ over last 5 days} \le 2.5\%$$
3.  **Volume Dry-up**: Volume is lower than average, representing exhaustion of sellers:
    $$\text{volume} \le \text{avg\_volume\_20d} \times 0.85$$
4.  **Trend Alignment**: Structured in an uptrend:
    $$\text{close} > \text{ema\_50} \quad \text{AND} \quad \text{ema\_50} \ge \text{ema\_200}$$

#### State C: `CONSOLIDATING`
All other active stocks in the universe that do not meet the breakout or pre-breakout definitions.

---

### 3. Execution Phases

#### Phase 1: Database Migration
- Add a new nullable `breakout_state` column to the `stock_scores` and `daily_prices` tables:
  ```sql
  ALTER TABLE daily_prices ADD COLUMN breakout_state VARCHAR(30) DEFAULT 'CONSOLIDATING';
  ALTER TABLE stock_scores ADD COLUMN breakout_state VARCHAR(30) DEFAULT 'CONSOLIDATING';
  ```
- Register the new column and default logic inside `api/schema.py:ensure_required_tables`.

#### Phase 2: Engine Integration (`engine_core/indicator_engine.py`)
- Refactor the indicator calculation logic to:
  1.  Compute the 5-day rolling average of daily price spreads: `(high - low) / close`.
  2.  Apply the formulas to label each symbol-date row as `BROKEN_OUT`, `READY_TO_BREAKOUT`, or `CONSOLIDATING`.
  3.  Persist the state in `daily_prices` and propagate it to `stock_scores` during scoring runs.

#### Phase 3: API Endpoints (`api/signals.py`)
- Create a new API route `/api/signals/breakouts` that returns a structured JSON list of all symbols flagged as `BROKEN_OUT` or `READY_TO_BREAKOUT` on the latest trading day.
- Output schema:
  ```json
  [
    {
      "symbol": "POLYCAB",
      "breakout_state": "BROKEN_OUT",
      "close": 7120.5,
      "volume_multiplier": 1.45,
      "proximity_to_6m_high": 0.0,
      "latest_mri_score": 85
    }
  ]
  ```

#### Phase 4: Frontend UI Badge Addition
- Update `AaeDashboard.tsx` and `App.tsx` (Global Explorer):
  - Add visual badges to candidate listings:
    - `[Breakout 🚀]` in bright green text or badge for `BROKEN_OUT`.
    - `[Ready ⚡]` in amber/teal text or badge for `READY_TO_BREAKOUT`.
  - Add a filter toggle on the UI to only display breakout candidates.

---

### 4. Done Criteria & Validation
1.  **Unit Verification**: Write a python script to test the indicator engine against historical breakout patterns.
2.  **Pipeline Run**: Run `compute_indicators.py` and verify database values populate correctly.
3.  **Endpoint Health**: Confirm `/api/signals/breakouts` works and returns the correct payload structure.
4.  **UI Verification**: Badges render correctly on the dashboard.
