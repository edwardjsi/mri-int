# Product Requirements Document (PRD)

# MRI Explainable AI (XAI) Framework v1.0

**Project:** MRI – Market & Capital Intelligence Platform
**Module:** Explainable Decision Engine (XAI)
**Version:** 1.0
**Status:** Approved for Development
**Priority:** P0 (Core Platform Capability)

---

# Vision

MRI should never behave like a black-box AI.

Every recommendation made by the platform must be explainable, auditable, drillable, and reproducible.

The goal is to make every investment decision transparent enough that an investor can understand exactly **why** a recommendation was made and challenge it if necessary.

The user should be able to drill from a portfolio recommendation all the way down to the raw market data used to produce that recommendation.

This capability is called the **MRI Explainability Framework (XAI).**

---

# Product Philosophy

The platform should answer five progressively deeper questions:

1. **What should I do?**
2. **Why should I do it?**
3. **Which rules led to this decision?**
4. **What evidence supports those rules?**
5. **How was that evidence calculated?**

Every recommendation must answer all five.

---

# Design Principles

## Principle 1 — Glass Box AI

Every recommendation must be fully transparent.

No hidden logic.

No unexplained scores.

---

## Principle 2 — Progressive Disclosure

Users should not see everything at once.

Instead they progressively drill deeper.

```
Decision

↓

Reason

↓

Evidence

↓

Rules

↓

Indicators

↓

Calculations

↓

Raw Data
```

Each level should answer the user's curiosity without overwhelming them.

---

## Principle 3 — One Source of Truth

Every UI component (Dashboard, Email, Mobile App, AI Chat, Decision Ledger) must consume the exact same explanation object.

The explanation should never be regenerated differently in different interfaces.

---

# User Stories

### Investor

"I want to know exactly why MRI told me to HOLD Welcorp."

---

### Advanced Investor

"I disagree with the recommendation.

Show me every rule that fired."

---

### Portfolio Manager

"Why didn't MRI recommend adding another tranche?"

---

### Developer

"I need to reproduce this recommendation six months later."

---

### Auditor

"I need proof that this recommendation came from deterministic rules."

---

# Explainability Levels

---

# Level 1 – Recommendation

Purpose:

Answer:

> What should I do?

Example

```
Welcorp

🟢 HOLD

Continue letting the winner compound.
```

Maximum reading time:

5 seconds.

---

# Level 2 – Reason

Purpose:

Explain the recommendation.

Example

```
Recommendation

HOLD

Primary Reason

Weekly trend remains intact.

Supporting Reasons

✓ Above 30-week EMA

✓ Higher highs maintained

✓ Position profitable

✓ No hard rules triggered

✓ No superior replacement opportunity
```

Maximum reading time:

20 seconds.

---

# Level 3 – Decision Flow

Purpose

Show how MRI reached the decision.

Example

```
Hard Rules

PASS

↓

Review Required

NO

↓

Next Tranche Eligible

NO

↓

Reduce Required

NO

↓

Final Decision

HOLD
```

---

# Level 4 – Rule Evaluation

Purpose

Expose every evaluated rule.

Example

```
Weekly Structure Broken

FALSE

-------------------

Maximum Allocation

FALSE

-------------------

Earnings Risk

FALSE

-------------------

Next Tranche Earned

FALSE

-------------------

Replacement Candidate Exists

FALSE
```

Every rule should include:

* Rule Name
* Rule ID
* Result
* Threshold
* Actual Value

---

# Level 5 – Indicator Evidence

Purpose

Show factual evidence supporting each rule.

Example

```
Trend

PASS

30W EMA

PASS

Higher High

TRUE

Higher Low

TRUE

Relative Strength

92

Volume Expansion

PASS
```

These are objective market facts.

---

# Level 6 – Calculation Layer

Purpose

Explain how every indicator was produced.

Example

```
30 Week EMA

Formula

EMA(30)

Input

Weekly closing prices

Current Value

₹1,472

Current Price

₹1,736

Distance

+17.9%
```

Every calculated metric should expose:

* Formula
* Inputs
* Calculation Date
* Output

---

# Level 7 – Raw Market Data

Purpose

Provide complete auditability.

Example

```
Weekly OHLC

Volume

Corporate Actions

Adjusted Prices

Trading Calendar

Source Timestamp
```

Nothing below this layer should exist.

---

# Decision Explainability Tree

Every engine must return an Explanation Tree.

Example

```
Decision

HOLD

├── Trend
│   ├── 30W EMA
│   ├── Higher High
│   ├── Higher Low
│   └── Relative Strength
│
├── Risk
│   ├── Position Size
│   ├── Market Regime
│   └── Portfolio Exposure
│
└── Rules
    ├── Hard Rules
    ├── Review Rules
    └── Allocation Rules
```

The UI should simply expand and collapse nodes.

---

# Decision Object

Every recommendation must return an explanation object.

Example

```typescript
Decision {
    id
    stock
    action
    confidence
    summary

    explanation_tree

    rules[]

    evidence[]

    calculations[]

    raw_data_reference
}
```

This object becomes the platform-wide contract.

---

# Why Not?

Every recommendation must expose rejected alternatives.

Example

```
Current Recommendation

HOLD
```

User clicks

```
Why not ADD?
```

Response

```
ADD rejected because:

• Position already near allocation limit.

• Better opportunity available.

• Next tranche conditions not satisfied.
```

---

User clicks

```
Why not EXIT?
```

Response

```
EXIT rejected because:

• Weekly trend intact.

• No structure break.

• Thesis remains valid.

• Hard stop not triggered.
```

This feature dramatically increases trust.

---

# Evidence Metadata

Every indicator must expose metadata.

Example

```
Relative Strength

92

Source

Daily Price Database

Lookback

52 Weeks

Updated

26 Jul 2026

Formula

Price Performance vs Nifty 500
```

Every number should answer:

> Where did this come from?

---

# Decision Trace

Every recommendation receives a permanent Decision ID.

Example

```
Decision ID

CAI-20260729-WELCORP-001
```

Decision trace:

```
Market Snapshot

↓

Indicator Engine

↓

MRI Engine

↓

CAI Engine

↓

Rule Engine

↓

Decision

↓

Dashboard

↓

Weekly Email

↓

Decision Ledger
```

Every step should be reproducible.

---

# Decision Ledger Integration

Store the complete explanation.

Not just:

```
HOLD
```

Store:

* Recommendation
* Rules Fired
* Rules Rejected
* Indicators Used
* Market Snapshot
* Portfolio Snapshot
* Explanation Tree
* Confidence
* User Action
* Future Outcome

This allows future backtesting of decision quality.

---

# AI Chat Integration

The explanation tree becomes the knowledge source for the AI assistant.

Supported prompts include:

* Why am I holding Welcorp?
* Why didn't MRI recommend adding?
* Which rule prevented the trade?
* Show me the evidence.
* Compare Welcorp and Neuland.
* What changed since last Saturday?
* Which indicator weakened this week?
* Explain this recommendation like I'm a beginner.

The AI should answer exclusively from the explanation tree, not by inventing reasoning.

---

# UI Requirements

Every decision card must support progressive drill-down.

```
Welcorp

▼ HOLD
```

Expand

```
Reason
```

Expand

```
Rules
```

Expand

```
Indicators
```

Expand

```
Calculations
```

Expand

```
Raw Market Data
```

No navigation away from the page should be required.

---

# Engineering Architecture

Each engine must return two outputs:

```
Result
```

and

```
ExplanationNode
```

Example

```
Indicator Engine

↓

Indicator Result
Indicator Explanation

↓

MRI Engine

↓

MRI Result
MRI Explanation

↓

CAI Engine

↓

CAI Result
CAI Explanation
```

The final explanation tree is composed by combining child nodes from every engine.

This prevents duplicated explanation logic.

---

# Non-Functional Requirements

* Explanation generation must be deterministic.
* All explanations must be generated from actual rule evaluations.
* No fabricated or LLM-invented reasoning.
* Drill-down latency should remain under 300 ms.
* Explanation objects should be immutable once stored in the Decision Ledger.
* All recommendations must be reproducible from the stored market snapshot.

---

# Acceptance Criteria

The feature is complete when:

* Every recommendation includes a complete explanation tree.
* Every displayed score is drillable to its underlying evidence.
* Every rule displays its evaluation result and supporting data.
* Every calculated indicator exposes its formula, inputs, and calculation metadata.
* Users can ask "Why?" and "Why not?" for any recommendation.
* A historical recommendation can be reconstructed exactly from the Decision Ledger.
* Dashboard, AI chat, weekly email, and future mobile clients all render explanations from the same explanation tree without implementing separate business logic.

---

# Strategic Outcome

This feature transforms MRI from a stock screener into an **Explainable Investment Decision Platform**.

Most investment software tells users **what** to do. Some attempt to explain **why**. MRI should uniquely provide a complete chain of evidence:

**Recommendation → Reason → Rule → Evidence → Calculation → Raw Data**

That architecture creates a system that investors can understand, developers can debug, auditors can verify, and users can trust over years of portfolio management. I would recommend treating the Explainability Framework as a foundational capability of the platform rather than a UI enhancement, because every future feature—AI chat, alerts, emails, decision history, and analytics—can be built on top of this single, consistent explanation model.
