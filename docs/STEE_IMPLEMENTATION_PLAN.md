# Implementation Plan: Momentum Swing Trading Execution Engine (STEE)

## 1. Overview
This plan implements a rule-based swing trading engine for the Indian market, as specified in the `docs/SWING_TRADING_PRD.md`. It transitions the system from a score-based candidate pool to a fully automated execution logic with market regime filters, position sizing, and stop-loss management.

## 2. Phase 1: Database & Indicators (Hardening)
**Objective:** Prepare the data layer to support swing trading logic.

### 2.1 Schema Updates
- **File:** `api/schema.py` (or direct SQL if applicable)
- **Task:** Add indicator columns to `daily_prices`:
  - `ema_10` (NUMERIC)
  - `high_10d` (NUMERIC)
  - `low_5d` (NUMERIC)
  - `atr_14` (NUMERIC)
- **Task:** Create `swing_trades` table to track execution state.

### 2.2 Indicator Engine
- **File:** `engine_core/indicator_engine.py`
- **Task:** Update `INDICATOR_COLUMNS` constant.
- **Task:** Implement `ema_10`, `high_10d` (rolling max of previous 10 days), `low_5d` (rolling min of previous 5 days), and `atr_14`.

## 3. Phase 2: Market Regime Upgrade
**Objective:** Implement strict EMA-based regime logic for the Nifty 50.

### 3.1 Regime Logic
- **File:** `engine_core/regime_engine.py`
- **Rules:**
  - **BULLISH:** Nifty Close > EMA 200 AND EMA 50 > EMA 200.
  - **SIDEWAYS:** Nifty Close within +/- 2% of EMA 200.
  - **BEARISH:** Nifty Close < EMA 200 AND EMA 50 < EMA 200.
- **Constraint:** Trading is only permitted in BULLISH (Full size) and SIDEWAYS (50% size) regimes.

## 4. Phase 3: Signal Generation & Trigger Engine
**Objective:** Implement the breakout entry logic.

### 4.1 Entry Logic
- **File:** `engine_core/swing_execution_engine.py` [NEW]
- **Triggers:**
  - `Close > high_10d` (Breakout)
  - `Volume > 1.5 * avg_volume_20d` (Volume confirmation)
  - `(Close - Low) / (High - Low) >= 0.7` (Strong close)
- **Filters:**
  - Gap-up < 4%.
  - Candle range < 2 * ATR (Not overextended).

## 5. Phase 4: Risk & Trade Management
**Objective:** Automated exit and position sizing.

### 5.1 Position Sizing
- **Risk:** 1% of total capital per trade.
- **Formula:** `Quantity = (Capital * 0.01) / (Entry - StopLoss)`.
- **Stop Loss:** `low_5d` or `Breakout Candle Low`.

### 5.2 Exit Logic
- **Partial Profit:** Exit 50% at 2R.
- **Trailing Stop:** Exit remaining 50% when `Close < ema_10`.
- **Hard Stop:** Exit 100% if `Stop Loss` hit.

## 6. Phase 5: Verification & Deployment
**Objective:** Ensure correctness and integrate into the daily pipeline.

### 6.1 Backtesting
- **Script:** `scripts/run_canonical_backtest.py`
- **Metrics:** CAGR, Max Drawdown, Win Rate, Avg R.

### 6.2 Pipeline Integration
- **File:** `run_daily_pipeline.sh`
- **Action:** Add `python engine_core/swing_execution_engine.py` as Step 4b.
