# CAI Canonical Terms & Glossary

This document serves as the immutable source of truth for terminology across the entire CAI architecture. To prevent terminology drift and ensure alignment across engineering and product teams, these definitions must be used consistently in all code, documentation, and user interfaces.

| Term | Canonical Meaning |
|------|-------------------|
| **Threshold** | A mathematically computed price boundary. Never contains business logic. |
| **Decision** | The final portfolio recommendation produced after resolving technical, fundamental, portfolio, market, and policy evidence. |
| **Evidence** | One or more validated observations that support or weaken an investment hypothesis. |
| **Hypothesis** | A testable proposition about a stock's future trajectory, combining multiple inferences (e.g. "Growth story intact"). |
| **Rule** | A deterministic function that produces evidence. |
| **Policy** | Portfolio-level governance that constrains decisions. |
| **Structure** | The current technical integrity of the trend. |
| **Opportunity** | Conditions under which additional capital may be deployed. |
| **Risk** | Conditions under which capital protection becomes increasingly important. |
| **Observation** | A raw, deterministic fact extracted directly from technical, fundamental, portfolio, or market data before any interpretation. |
| **Inference** | An intermediate conclusion derived from one or more pieces of evidence. Inferences are inputs to portfolio decisions but are not themselves recommendations. |
| **Decision State** | The current lifecycle state of a position (`ADD`, `HOLD`, `ALERT`, `STRUCTURE`, `QUIT`). |
| **MOSI** | Management, Operations, Strategy, and Industry. The fundamental intelligence engine evaluating structured and unstructured corporate data. |
| **Threshold Engine** | Pure mathematical engine that computes technical price boundaries. |
| **Evidence Engine** | The collection of Rule Engines that transform observations into structured evidence. |
| **Inference Engine** | Aggregates evidence into intermediate hypotheses about the stock. |
| **Policy Engine** | Applies portfolio-level constraints (e.g., maximum allocation, regime locks) to filter permissible inferences. |
| **Resolution Engine** | Orchestrates the complete decision process by resolving thresholds, inferences, and policies into a single decision. |

---

## 2. Engine Hierarchy

This diagram defines how the core concepts and engines interact sequentially:

```text
                 DATA
                   │
                   ▼
        Observation Engines
                   │
                   ▼
             Rule Engines
                   │
                   ▼
          Evidence Engine
                   │
                   ▼
          Inference Engine
                   │
                   ▼
           Policy Engine
                   │
                   ▼
        Resolution Engine
                   │
                   ▼
              Decision
                   │
                   ▼
          Decision State
                   │
                   ▼
         Decision Ladder UI
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
| Inference Engine        | Generates hypotheses from evidence                 | Recommends buys or sells  |
| Policy Engine           | Applies portfolio constraints                      | Calculates indicators     |
| Resolution Engine       | Resolves thresholds, inferences, and policies into one decision | Changes portfolio directly |

---

## 4. CAI Layering Principles

The information flow through the platform must remain strictly unidirectional:

```text
Raw Data
      ↓
Observations
      ↓
Evidence
      ↓
Inferences
      ↓
Policies
      ↓
Decision
      ↓
Decision State
      ↓
Investor Action
```

**Core Architectural Rule:** Each layer may consume outputs from the layer immediately below it but must never bypass the architecture to read from lower layers directly.
