# PRODUCT REQUIREMENTS DOCUMENT (PRD)

## Project: Momentum Swing Trading Execution Engine (India Focus)

---

## 1. Objective

Build a **fully rule-based trading engine** that:

* Identifies high-probability swing trades
* Filters trades based on **market regime (Nifty context)**
* Generates **actionable signals**:

  * Entry
  * Position size
  * Stop loss
  * Exit
* Requires **zero discretionary intervention**

---

## 2. System Philosophy

* No charts
* No human interpretation
* No prediction
* Only **rules + probabilities + risk control**

---

## 3. Data Inputs

### 3.1 Stock Data (Daily OHLCV)

* Open
* High
* Low
* Close
* Volume

### 3.2 Index Data (for regime filter)

* NIFTY 50 OHLCV

### 3.3 Derived Indicators

System must compute:

* EMA 50
* EMA 200
* 200 EMA slope
* 10-day high / low
* 20-day average volume
* 90-day Relative Strength (vs Nifty)
* 6-month high proximity
* ATR (optional but recommended)

---

## 4. System Architecture

### Modules:

1. **Universe Scanner**
2. **Market Regime Engine**
3. **Stock Scoring Engine**
4. **Entry Trigger Engine**
5. **Risk & Position Sizing Engine**
6. **Trade Management Engine**
7. **Execution Output Engine (Email/API)**

---

## 5. Market Regime Filter (Critical Layer)

### Purpose:

Avoid trading in low-probability environments

---

### Regime Logic:

#### Bullish Regime:

```
IF
    Nifty Close > EMA 200
AND EMA 50 > EMA 200
THEN
    Regime = BULLISH
```

#### Neutral Regime:

```
IF
    Price around EMA 200 (+/- 2%)
THEN
    Regime = SIDEWAYS
```

#### Bearish Regime:

```
IF
    Nifty Close < EMA 200
AND EMA 50 < EMA 200
THEN
    Regime = BEARISH
```

---

### Trading Rules by Regime:

| Regime   | Action                      |
| -------- | --------------------------- |
| Bullish  | Full system active          |
| Sideways | Reduce position size by 50% |
| Bearish  | No new trades               |

---

## 6. Stock Selection Engine (Existing – Refined)

Each stock must pass:

```
EMA 50 > EMA 200
200 EMA slope > 0
RS (90d) > 0
Close within 15% of 6M high
```

👉 Output: **Qualified Watchlist**

---

## 7. Entry Trigger Engine (Core Upgrade)

### Entry Conditions:

```
IF
    Stock in Watchlist
AND Regime != BEARISH
AND Close > Highest High (last 10 days)
AND Volume > 1.5 × 20-day Avg Volume
AND Close near Day High (Top 30% of candle range)
THEN
    Generate BUY Signal
```

---

## 8. Position Sizing Engine

### Fixed Risk Model:

```
Risk per trade = 1% of total capital
```

### Calculation:

```
Position Size = Risk Amount / (Entry Price - Stop Loss)
```

---

## 9. Stop Loss Engine

### Rule:

```
Stop Loss = Lowest Low of last 5 candles
```

OR

```
Stop Loss = Breakout Candle Low
```

(Choose one globally, not both)

---

## 10. Trade Management Engine

### Exit Logic (Hybrid Model)

#### Partial Profit Booking:

```
At 2R → Exit 50%
```

#### Trailing Exit:

```
Exit remaining when Close < EMA 10
```

---

### Hard Exit Condition:

```
If Close hits Stop Loss → Exit 100%
```

---

## 11. No-Trade Filters

Reject trade if:

* Gap-up > 4% on breakout day
* Volume spike without price breakout
* Candle range > 2× ATR (overextended move)

---

## 12. Output Specification

System should generate:

### Daily Output (Post Market)

For each signal:

* Stock Name
* Entry Price
* Stop Loss
* Position Size
* Risk Amount
* Regime Status
* Signal Strength Score

---

### Delivery Mode:

* Email (Primary)
* Optional: API / Dashboard

---

## 13. Backtesting Requirements

System must support:

* Minimum 10 years historical testing
* Metrics:

  * Win Rate
  * Avg R per trade
  * Max Drawdown
  * CAGR
  * Sharpe Ratio

---

## 14. Logging & Audit

Every trade must store:

* Entry reason
* Exit reason
* R-multiple outcome
* Regime at entry

---

## 15. Future Enhancements (Phase 2)

* Sector rotation filter
* Earnings event filter
* Volatility regime filter
* Pyramiding logic

---

# Final System Summary (for your architect)

> “This is a rule-based momentum swing trading engine that selects strong stocks, filters them through market regime, enters on breakout with volume, manages risk via fixed position sizing, and exits using a hybrid profit + trend-following model.”
