# CAI Rule Workshop – Session 1

**Objective:** Define the first 30 production-quality rules for the Minimum Viable Decision Platform.

**The Final Architectural Paradigm:**
```
Observation (Fact)
      ↓
Evidence (Classified Fact)
      ↓
Decision Engine (Deterministic Logic)
      ↓
Decision (Action)
      ↓
Explanation Service (Human Communication / Inference)
```

**Evidence Strengths:** `FATAL`, `STRONG_POSITIVE`, `POSITIVE`, `NEUTRAL`, `NEGATIVE`, `STRONG_NEGATIVE`.
*(Note: Interpretation and Inference are strictly banned from this document. They belong entirely to the downstream Explanation Service.)*

---

## Question 1: Should I ADD?

### CAI-101: Weekly Breakout Confirmed
* **Source:** Weekly Price DB
* **Observation:** `Weekly close > Highest High (20 weeks) AND Volume > 1.5× average`
* **Observation Reliability:** `VERY_HIGH`
* **Freshness:** Valid for 5 trading days
* **Evidence Produced:**
  * **Structure:** `BREAKOUT_CONFIRMED`
  * **Momentum:** `MOMENTUM_ACCELERATING`
  * **Volume:** `INSTITUTIONAL_PARTICIPATION`
* **Evidence Strength:** `STRONG_POSITIVE`

### CAI-601: Portfolio Capacity Available
* **Source:** Portfolio Engine
* **Observation:** `Current Asset Weight < Target Weight limit AND Cash > Minimum Reserve`
* **Observation Reliability:** `VERY_HIGH`
* **Freshness:** Valid until next execution
* **Evidence Produced:**
  * **Portfolio:** `CAPACITY_AVAILABLE`
* **Evidence Strength:** `POSITIVE`

---

## Question 2: Should I MAINTAIN?

### CAI-201: Higher High Higher Low
* **Source:** Daily Price DB
* **Observation:** `Current Swing Low > Previous Swing Low AND Current Swing High > Previous Swing High`
* **Observation Reliability:** `HIGH`
* **Freshness:** Valid until next swing point forms
* **Evidence Produced:**
  * **Trend:** `TREND_INTACT`
  * **Structure:** `HEALTHY_CONSOLIDATION`
* **Evidence Strength:** `POSITIVE`

---

## Question 3: Should I STRUCTURE (Warn)?

### CAI-401: Price Below 200 EMA Warning
* **Source:** Indicator Engine
* **Observation:** `Close below 200 EMA AND 200 EMA slope < 0`
* **Observation Reliability:** `VERY_HIGH`
* **Freshness:** Valid until Close > 200 EMA
* **Evidence Produced:**
  * **Trend:** `LONG_TERM_TREND_REVERSING`
  * **Structure:** `STRUCTURE_COMPROMISED`
* **Evidence Strength:** `STRONG_NEGATIVE`

---

## Question 4: Should I QUIT?

### CAI-501: Confirmed Weekly Trend Failure
* **Source:** Market Structure Engine
* **Observation:** `Confirmed lower-high/lower-low sequence AND Loss of primary support`
* **Observation Reliability:** `HIGH`
* **Freshness:** Valid until weekly close reclaims primary support
* **Evidence Produced:**
  * **Trend:** `TREND_FAILURE_CONFIRMED`
  * **Structure:** `PRIMARY_SUPPORT_LOST`
  * **Risk:** `CAPITAL_IMPAIRMENT_RISK_HIGH`
* **Evidence Strength:** `FATAL`

---

*Note: With the framework now fully frozen and devoid of subjective inference, we will proceed to expand these questions until we hit our MVDP target of 30 exceptional rules.*
