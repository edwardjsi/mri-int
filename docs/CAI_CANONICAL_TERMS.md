# CAI Canonical Terms & Glossary

This document serves as the immutable source of truth for terminology across the entire CAI architecture. To prevent terminology drift and ensure alignment across engineering and product teams, these definitions must be used consistently in all code, documentation, and user interfaces.

| Term | Canonical Meaning |
|------|-------------------|
| **Threshold** | A mathematically computed price boundary. Never contains business logic. |
| **Decision** | The final, deterministic recommendation produced after evaluating thresholds, evidence, and portfolio policy. |
| **Evidence** | Structured, objective information derived from one or more observations by deterministic rules. |
| **Rule** | A deterministic function that produces evidence. |
| **Policy** | Portfolio-level governance that constrains decisions. |
| **Structure** | The current technical integrity of the trend. |
| **Opportunity** | Conditions under which additional capital may be deployed. |
| **Risk** | Conditions under which capital protection becomes increasingly important. |
| **Observation** | An objective fact detected from data before any interpretation. |
| **Inference** | A conclusion drawn from one or more pieces of evidence. |
| **Decision Engine** | The orchestration layer that combines evidence, thresholds, rules, and policies into a single decision. |
| **Decision State** | The current lifecycle state of a position (`ADD`, `HOLD`, `ALERT`, `STRUCTURE`, `QUIT`). |
| **MOSI** | Management, Operations, Strategy, and Industry. The fundamental intelligence engine evaluating structured and unstructured corporate data. |
| **Threshold Engine** | Pure mathematical engine that computes technical price boundaries. |
| **Evidence Engine** | The collection of Rule Engines that transform observations into structured evidence consumed by the Decision Engine. |

---

## 2. Engine Hierarchy

This diagram defines how the core concepts and engines interact sequentially:

```text
Observation
        │
        ▼
Rule
        │
produces
        ▼
Evidence
        │
combined by
        ▼
Decision Engine
        │
constrained by
        ▼
Policy
        │
produces
        ▼
Decision
        │
represented by
        ▼
Decision State
        │
displayed as
        ▼
Decision Ladder
```

---

## 3. CAI Engine Responsibilities

This is the single responsibility contract for the platform:

| Engine                  | Responsibility                                     | Never Does                |
| ----------------------- | -------------------------------------------------- | ------------------------- |
| Indicator Engine        | Calculates indicators (EMA, RSI, ATR)              | Makes decisions           |
| Market Structure Engine | Identifies trend, swings, support, resistance      | Generates recommendations |
| Threshold Engine        | Calculates technical price levels                  | Applies business rules    |
| Rule Engine             | Produces evidence from observations                | Makes final decisions     |
| Policy Engine           | Applies portfolio constraints                      | Calculates indicators     |
| Resolution Engine       | Resolves thresholds and evidence into one decision | Changes portfolio         |
| Decision Engine         | Orchestrates the complete decision process         | Performs UI rendering     |

---

## 4. CAI Layering Principles

The information flow through the platform must remain strictly unidirectional:

```text
Data
  ↓
Observations
  ↓
Evidence
  ↓
Inference
  ↓
Decision
  ↓
Investor Action
```

**Core Architectural Rule:** Each layer may consume outputs from the layer immediately below it but must never bypass the architecture to read from lower layers directly.
