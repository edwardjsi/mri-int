This is the final, frozen Architecture PRD. By introducing the Configuration Layer, elevating Market Regime to a core service, and separating the Explanation generation from the Decision Engine, the system transitions from a robust feature into a true, multi-strategy institutional platform.

Here is the final specification, ready for engineering implementation.

---

# PRD-018: CAI Decision Framework & Decision Ladder

**System Context:** Core Platform Service (Foundation for CAI, MRI, Risk Optimizer, and AI Assistants)
**Version:** 4.0 (Frozen for Implementation) | **Priority:** P0 | **Status:** Approved

## 1. Executive Summary & Architectural Intent

This PRD defines a deterministic, rule-based portfolio lifecycle management platform. Internally, the architecture is referred to as the **Decision Framework**; it calculates states, thresholds, and actions. Externally, the UI visualizes this as the **Decision Ladder**.

This architecture acts as a pure business-logic layer. It completely decouples data aggregation, market context, fact evaluation, rule execution, portfolio policy, and human-readable explanations. Crucially, it supports multiple trading strategies simultaneously via a Configuration Layer and guarantees 100% deterministic replayability.

### Dependencies (Strictly Read-Only)

* `Daily Price Database`
* `Indicator Engine`
* `MRI Engine`
* `Portfolio Engine`

---

## 2. System Architecture & Data Pipeline

The pipeline strictly prohibits downstream engines from calculating their own indicators or formatting their own text. Data flows sequentially through highly specialized, decoupled platform services:

**The Platform Pipeline:**
`Market Regime Service` *(System-wide context)*
↓
`Indicator Engine` *(Calculates EMAs, RSI, ATR)*
↓
`Market Structure Engine` *(Derives Support/Resistance, Trend Phase)*
↓
`Position Evaluation Engine` *(Synthesizes Facts)*
↓
`Decision Threshold Engine` *(Calculates Price Levels)*
↓
`Decision Rule Engine` *(Evaluates based on Strategy Configuration)*
↓
`Portfolio Policy Engine` *(Applies Contextual Constraints & Overrides)*
↓
`CAI Decision Engine` *(Assembles Executable State)*
↓
`Explanation Service` *(Translates Facts to Human Language)*
↓
`Decision Ledger` $\rightarrow$ `Notification Engine` $\rightarrow$ `UI Presentation`

---

## 3. Core Service Specifications

### 3.1 Market Regime Service (New First-Class Service)

**Purpose:** Provides global market context consumed by every downstream engine. Market regime is a system-wide input, not a discrete rule.

* **Outputs:** `Bull`, `Bear`, `Sideways`, `High Volatility`, `Low Volatility`, `Risk-On`, `Risk-Off`.

### 3.2 Decision Configuration Layer

**Purpose:** Maps objective rules to specific investment philosophies, allowing the platform to support multiple strategies simultaneously without changing code.

* **Profiles:** `Momentum`, `Growth`, `Conservative`, `Bear Market`, `Custom`.
* *Mapping Example:*
* `CAI-101 (Weekly Breakout)` $\rightarrow$ Enabled for: `Momentum`, `Growth`. Disabled for: `Conservative`.



### 3.3 Decision Rule Engine & Portfolio Policy Engine

* **Decision Rule Engine:** Evaluates objective technical reality against the configured Strategy Profile.
* **Portfolio Policy Engine:** The Governance layer. Overrides technical rules based on portfolio constraints (e.g., Max Sector Exposure, Cash Available) and shifts the final output (e.g., overriding an `ADD` to a `HOLD`).

### 3.4 CAI Decision Engine

**Purpose:** Assembles evaluated rules, policy constraints, and threshold comparisons into a final structured state. It does *not* generate human-readable text or execution timing.

* **Calculates:**
1. `Evidence Strength`: Objective strength of the asset's data (e.g., 95%).
2. `Decision Quality`: Recommendation viability given current portfolio context and market regime (e.g., 41%).


* **Outputs:** Pure structured facts (Action, State, Passed/Failed Rules).

### 3.5 Explanation Service (The Translation Layer)

**Purpose:** Consumes the structured output of the Decision Engine and formats it into the *Why, Why Now, What Next* narrative for the user interface.

* **Benefit:** Enables multi-language support and AI-driven narrative generation without touching core deterministic decision logic.

---

## 4. State & Transition Logic

### 4.1 Decision Priority (Evaluation Order)

Evaluations occur top-down. A holding possesses exactly one active state.

1. **QUIT** (Highest)
2. **STRUCTURE**
3. **ALERT**
4. **ADD**
5. **HOLD** (Default base state)

### 4.2 Allowed State Transitions

The state machine enforces valid transitions while accommodating real-world market shocks.

**Normal Transitions (Progression):**

* `HOLD` $\rightarrow$ `ADD`  |  `ADD` $\rightarrow$ `HOLD`
* `HOLD` $\rightarrow$ `ALERT`  |  `ALERT` $\rightarrow$ `STRUCTURE`
* `STRUCTURE` $\rightarrow$ `QUIT`
* `QUIT` $\rightarrow$ `STRUCTURE`  |  `STRUCTURE` $\rightarrow$ `ALERT`

**Emergency Transitions (Catastrophic Events / Black Swans):**

* `ADD` $\rightarrow$ `QUIT` (e.g., severe gap-down)
* `HOLD` $\rightarrow$ `QUIT`
* `ALERT` $\rightarrow$ `QUIT`

---

## 5. Output Schema & Ledger Specification

### 5.1 Executable Output Schema (Post-Explanation Service)

```json
{
  "state": "ADD",
  "evidence_strength": 92,
  "decision_quality": 88,
  "action_payload": {
    "recommended_action": "Deploy ₹30,000",
    "target_weight": 5.0
  },
  "narrative": {
    "why": "Fresh breakout with volume expansion.",
    "why_now": "Weekly breakout confirmed on Friday close.",
    "what_next": "Add ₹30,000 to reach target weight."
  }
}

```

*(Note: Execution timing is deferred to a separate Execution Planner).*

### 5.2 Database Schema (Append-Only Ledger)

**Table: `decision_history**`

* `evaluation_id` (PK)
* `holding_id` (FK)
* `strategy_profile` (String, e.g., 'Momentum')
* `decision` (Enum)
* `evidence_strength` (Decimal)
* `decision_quality` (Decimal)
* `engine_version_data` (JSONB)
* `rule_traceability` (JSONB)
* `timestamp` (Datetime)

---

## 6. UI/UX Interface Requirements

### 6.1 Portfolio Dashboard

* **Portfolio Health Widget:** Aggregate counters (`ADD`: 5, `HOLD`: 11).
* **Holdings Table:** Append columns for `Decision`, `Decision Quality`, and dynamically calculated Thresholds.

### 6.2 Holding Detail Page

* **Decision Ladder Panel:** Vertical UI hierarchy mapping current price against Add, Alert, Structure, and Quit threshold levels.
* **Assistant Panel:** Renders the narrative *Why?*, *Why Now?*, and *What Next?* provided by the Explanation Service.
* **Traceability Modal:** Exposes the exact rules and policies that passed/failed for transparent debugging.

---

## 7. Developer Acceptance Criteria (DoR/DoD)

1. **Strict Pipeline Compliance:** The Decision Engine reads zero OHLC/price data directly and generates zero text.
2. **Configuration-Driven Logic:** All rules must be mapped to Strategy Profiles in the Configuration Layer.
3. **Transition Guardrails:** Unit tests must prove normal transitions are enforced and emergency transitions only trigger under defined volatility thresholds.
4. **100% Traceability & Versioning:** Every ledger entry must include explicit arrays of passed/failed rules, policy overrides, and engine version hashes.
5. **Deterministic Replay (Critical):** Re-running the engine with the exact same inputs (market data, portfolio context) and the same versioned rule/policy sets **must** reproduce an identical decision, thresholds, evidence scores, and rule traceability.