# CAI Rule Book v1.0 (Decision Constitution)

This document is the "Constitution" of CAI. It translates our investing philosophy into deterministic logic and defines the exact rules, policies, conditions, and outputs used by the Decision Rule Engine.

> **Development Rule: Do not implement more than 30 rules in Version 1.** Focus entirely on Technical, Capital Allocation, and Portfolio Policy rules. Validate and calibrate these first before expanding.

---

## Part 1A – Investment Principles
This section never changes. It acts as the timeless, immutable foundation of the platform:
* Evidence overrides opinion.
* Every rupee must earn the next rupee.
* Weekly structure matters more than daily noise.
* Decisions must be reproducible.
* Capital preservation precedes capital appreciation.

## Part 1B – Investment Policies
These are implementation constraints that can be adjusted over time as strategy evolves:
* Never average down.
* Maximum position size is strictly capped.
* Maximum sector allocation is strictly capped.
* No adding in a Bear regime.
* Maximum five tranches per position.
* Minimum cash reserve must be maintained.

---

## Part 2 – Decision Pipeline
The engine strictly evaluates in this sequential order:
```
Market Structure
      ↓
Position Evaluation
      ↓
Thresholds
      ↓
Rules
      ↓
Policy
      ↓
Decision
```

---

## Part 3 – Decision Groups
Rules are organized by the decisions they produce, categorized by ID ranges:
* **CAI-100–199**: ADD Rules
* **CAI-200–299**: MAINTAIN (Hold) Rules
* **CAI-300–399**: ALERT Rules
* **CAI-400–499**: STRUCTURE Rules
* **CAI-500–599**: QUIT Rules
* **CAI-600–699**: Capital Allocation Rules
* **CAI-700–799**: Portfolio Policy Rules

---

# ADD Rules (CAI-100–199)

### CAI-101
* **Name:** Weekly Breakout Confirmed
* **Category:** Technical
* **Priority:** Major
* **Severity:** Medium
* **Enabled:** Yes
* **Version:** 1.0
* **Expected Frequency:** 1-3% of stocks
* **Produces:** `ADD`
* **Never Produces:** `QUIT`
* **Owner:** Technical Rules

#### Dependencies
* Market Structure Engine
* CAI-601 (Portfolio Capacity)
* CAI-703 (Market Policy)

#### Preconditions
* Market Regime != Bear
* Position already owned
* Current State = MAINTAIN
* Cash Available > Minimum
* Portfolio Weight < Maximum

#### Condition
`Close > Highest High (20 weeks) AND Volume > 1.5× average`

#### Conflicts & Resolution
* **Conflict:** CAI-401 produces `STRUCTURE`.
* **Resolution:** `STRUCTURE` takes precedence over `ADD`.

#### Explanation Template
"Fresh weekly breakout confirmed with volume expansion."

#### Counterexamples (Should NOT Fire When)
* Gap-up above resistance with weak volume
* Bear market override active
* Portfolio already full

#### Unit Tests: 12

---

# MAINTAIN Rules (CAI-200–299)

### CAI-201
* **Name:** Higher High Higher Low
* **Category:** Technical
* **Priority:** Normal
* **Severity:** Low
* **Enabled:** Yes
* **Version:** 1.0
* **Expected Frequency:** 40-60% of stocks
* **Produces:** `MAINTAIN`
* **Never Produces:** `QUIT`

#### Dependencies
* Position Evaluation Engine

#### Preconditions
* Position owned

#### Condition
`Current Swing Low > Previous Swing Low AND Current Swing High > Previous Swing High`

#### Conflicts & Resolution
* **Conflict:** CAI-301 produces `ALERT`.
* **Resolution:** `ALERT` takes precedence over `MAINTAIN`.

#### Explanation Template
"Trend is intact. Making higher highs and higher lows."

#### Counterexamples
* Trend is sideways

---

# ALERT Rules (CAI-300–399)
*(To be populated...)*

---

# STRUCTURE Rules (CAI-400–499)

### CAI-401
* **Name:** Price Below 200 EMA Warning
* **Category:** Technical
* **Priority:** Major
* **Severity:** Medium
* **Enabled:** Yes
* **Version:** 1.0
* **Expected Frequency:** 5-10% of stocks
* **Produces:** `STRUCTURE`
* **Never Produces:** `QUIT`

#### Dependencies
* Indicator Engine (200 EMA)
* Position Evaluation Engine (Weekly Trend Score)

#### Preconditions
* Position owned
* Weekly Trend Score < Threshold

#### Condition
`Close below 200 EMA AND 200 EMA slope < 0`

#### Conflicts & Resolution
* **Conflict:** CAI-101 produces `ADD`.
* **Resolution:** `STRUCTURE` overrides `ADD`.

#### Explanation Template
"Price has fallen below a declining 200 EMA with weak weekly trend. Trend structure compromised."

#### Counterexamples
* Price dips below 200 EMA but 200 EMA is rising and weekly trend is strong.

---

# QUIT Rules (CAI-500–599)

### CAI-501
* **Name:** Confirmed Weekly Trend Failure
* **Category:** Technical
* **Priority:** Fatal
* **Severity:** High
* **Enabled:** Yes
* **Version:** 1.0
* **Expected Frequency:** <2% of stocks
* **Produces:** `QUIT`

#### Dependencies
* Market Structure Engine
* Threshold Engine (Primary Support)

#### Preconditions
* Position owned

#### Condition
`Confirmed lower-high/lower-low sequence AND Loss of primary support`

#### Conflicts & Resolution
* **Conflict:** Rule naturally overrides all lower states.

#### Explanation Template
"Weekly structure failure confirmed. Primary support lost."

#### Counterexamples
* Flash crash wick that recovers above primary support by end-of-week.

---

## Capital Allocation Rules (CAI-600–699)
*(To be populated...)*

---

## Portfolio Policy Rules (CAI-700–799)
*(To be populated...)*
