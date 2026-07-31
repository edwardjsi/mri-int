# Engineering Specification: Capital Allocation Engine (formerly Decision Engine)

**Version:** 2.0  
**Priority:** P0  
**Owner:** Investment Logic Team  
**Depends on:** MRI System Architecture v1.0, MRI Data Dictionary v1.0, Knowledge Reconciliation Engine

---

## 1. Objective

The **Capital Allocation Engine (CAE)** is the pinnacle of the MRI Knowledge Pyramid. It answers the fundamental question of professional portfolio management: 

> *"Given all available evidence, all current opportunities, my existing portfolio, my cash, and my investing rules, where should the next rupee of capital go?"*

It rejects binary rule-engine logic (e.g., IF valid THEN buy). Instead, it implements a nuanced, scoring-based funnel that ranks opportunities and explicitly dictates capital tranches based on conviction, timing, and portfolio constraints.

---

## 2. Core Philosophy

- **No Extraction**: The CAE never reads `SourceDocument`s or raw text. It strictly consumes `CompanyKnowledge`.
- **Ranking over Binary Choice**: It does not just decide if a company is "buyable". It ranks all buyable companies to allocate limited capital optimally.
- **Spectrum over Binary Scoring**: Thesis and Timing are scored on a spectrum (e.g., 8.8 vs 9.2), allowing nuanced sizing and prioritization.
- **Structured Explainability**: Decisions contain reproducible, structured evidence objects, not raw markdown strings.
- **Feedback Loops**: Historical outcomes feed back into the system to refine thresholds and calibration.

---

## 3. The Capital Allocation Funnel

The engine evaluates candidates through a strict five-stage pipeline:

```text
               Company Knowledge
                      │
                      ▼
            Thesis Evaluation Engine
            (Scores 0-10 on Fundamentals)
                      │
                      ▼
            Market Structure Engine
         (Categorizes: Breakout, Pullback, etc.)
                      │
                      ▼
           Opportunity Ranking Engine
        (Ranks against all other opportunities)
                      │
                      ▼
          Portfolio Constraint Engine
        (Checks cash, max allocation, sector)
                      │
                      ▼
           Capital Allocation Engine
          (Determines Tranche & Size)
                      │
                      ▼
             Decision Generation
```

### Stage 1: Thesis Evaluation Engine
- **Input**: `CompanyKnowledge`.
- **Logic**: Aggregates continuous scores from underlying facts (e.g., Business Quality, Pricing Power).
- **Output**: `Thesis Strength Score` (0.0 to 10.0).

### Stage 2: Market Structure Engine
- **Input**: Daily Market Intelligence.
- **Logic**: Identifies precise structural states rather than binary "favorable/unfavorable".
- **States**: `Breakout`, `Healthy Pullback`, `Trend Continuation`, `Late Trend`, `Distribution`, `Structure Break`.
- **Output**: `Timing Score` (0.0 to 10.0) and `Market State`.

### Stage 3: Opportunity Ranking Engine
- **Input**: Combined Thesis + Timing scores for *all* eligible companies.
- **Logic**: Ranks the current company against the opportunity set.
- **Output**: `Opportunity Rank` (e.g., 2 of 186).

### Stage 4: Portfolio Constraint Engine
- **Input**: Current `Portfolio` (Cash, open positions, sector exposure).
- **Logic**: Applies risk limits (e.g., max 10% per sector, max 5% per position).
- **Output**: `Available Capacity` and `Portfolio Fit Score`.

### Stage 5: Capital Allocation Engine
- **Input**: Outputs of Stages 1-4.
- **Logic**: Maps the conviction and capacity to a specific tranche action (e.g., `BUY_TRANCHE_1` on a Healthy Pullback vs `WAIT` on a Late Trend despite high thesis score).

---

## 4. Domain Entities (Outputs)

### `CapitalAllocationDecision`

A rich object representing the generated decision and its reproducible rationale.

```yaml
Decision:
  action: BUY_TRANCHE_1
  priority: 2
  conviction: 91
  tranche_size: "₹20,000"
  
  scores:
    thesis_score: 8.9
    timing_score: 9.2
    portfolio_fit: 8.4
    opportunity_rank: 2
    
  blocking_conditions: []
  
  supporting_evidence:
    - variable: "pricing_power"
      value: "High"
      contribution: "+2.1"
    - variable: "weekly_trend"
      value: "Strong"
      contribution: "+1.5"
      
  next_review: "Weekly Close"
  next_expected_action: "Evaluate Tranche 2"
```

---

## 5. Execution Lifecycle

1. **Trigger**: The CAE runs globally (across all candidates) upon significant state changes:
   - A `KnowledgeUpdateTransaction` completes (Fundamental shift).
   - End-of-day market data is ingested (Structural shift).
   - Portfolio state changes (e.g., a position is closed, freeing cash).
2. **Snapshot**: Captures global `CompanyKnowledge`, Market Data, and Portfolio.
3. **Pipeline**: Routes the universe through the 5-stage funnel.
4. **Generation**: Creates a structured `CapitalAllocationDecision` for each evaluated candidate.
5. **Execution**: Dispatches actionable decisions (where `tranche_size > 0` or action is `EXIT`) to the execution layer.

---

## 6. Acceptance Criteria

1. The Engine executes as a 5-stage funnel, strictly separating thesis, timing, ranking, and sizing.
2. The Engine scores opportunities on a continuous scale rather than evaluating binary rules.
3. Ranking logic correctly suppresses "Buy" signals if cash is constrained and superior opportunities exist.
4. Output is a structured `CapitalAllocationDecision` object that natively supports programmatic explainability.
5. The Engine correctly navigates structural states (e.g., distinguishing between a `Healthy Pullback` entry and a `Late Trend` wait).
