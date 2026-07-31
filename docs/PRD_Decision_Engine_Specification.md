# Engineering Specification: Decision Engine

**Version:** 1.0  
**Priority:** P0  
**Owner:** Investment Logic Team  
**Depends on:** MRI System Architecture v1.0, MRI Data Dictionary v1.0, Knowledge Reconciliation Engine

---

## 1. Objective

The **Decision Engine** is the pinnacle of the MRI Knowledge Pyramid. It consumes `CompanyKnowledge` (the output of the Knowledge Reconciliation Engine) combined with Daily Market Intelligence and Portfolio Rules to deterministically output **Investment Decisions** (e.g. BUY, HOLD, ADD, EXIT).

The core objective is to specify exactly how the engine translates structured facts into actionable portfolio tranches.

---

## 2. Core Philosophy

- **No Extraction**: The Decision Engine never reads `SourceDocument`s or raw text.
- **No Ambiguity**: Given a specific snapshot of `CompanyKnowledge` and Market Data, the Decision Engine will always produce the exact same `Decision`.
- **Explainability**: Every `Decision` must point to the specific `CompanyKnowledge` entities that triggered it.

---

## 3. Decision Funnel Architecture

The Decision Engine operates as a strict multi-stage funnel.

### Stage 1: Thesis Validation (Knowledge Layer)
Evaluates if the company's fundamentals currently justify investment.
- Reads: `CompanyKnowledge` (e.g., Pricing Power, Customer Concentration).
- Output: `THESIS_VALID` or `THESIS_INVALID`.

### Stage 2: Market Timing (Intelligence Layer)
Evaluates if the current market conditions are favorable for entry/exit.
- Reads: Daily Market Intelligence (Moving Averages, Relative Strength).
- Output: `TIMING_FAVORABLE` or `TIMING_UNFAVORABLE`.

### Stage 3: Portfolio Sizing (Rules Layer)
Evaluates how much capital to deploy based on current exposure.
- Reads: `Portfolio` (Current Allocation, Max Allocation Rules).
- Output: `Tranche Size` (e.g., 2%, 5%, 0%).

---

## 4. The Tranche Decision Matrix

Decisions are broken down into **Tranches**. A standard position is built in two tranches.

### First Tranche Decision (Entry)
**Conditions:**
- Thesis Validation == `THESIS_VALID`
- Market Timing == `TIMING_FAVORABLE`
- Current Allocation == 0%
**Action**: `BUY_TRANCHE_1` (Allocates initial capital)

### Second Tranche Decision (Add)
**Conditions:**
- Thesis Validation == `THESIS_VALID`
- Market Timing == `TIMING_FAVORABLE` (e.g., stock price > Tranche 1 cost basis)
- Current Allocation == Tranche 1 size
**Action**: `BUY_TRANCHE_2` (Completes full position)

### Hold / Exit Decisions
**Conditions:**
- Thesis Validation == `THESIS_INVALID` (Fundamental deterioration)
**Action**: `EXIT` (Sell all tranches immediately)

**Conditions:**
- Thesis Validation == `THESIS_VALID`
- Current Allocation == Max Allocation
**Action**: `HOLD`

---

## 5. Domain Entities (Outputs)

### `DecisionContext`
A snapshot of the exact parameters used during execution.
- `company_id`: UUID
- `knowledge_snapshot_ids`: List[UUID]
- `market_data_snapshot`: JSONB
- `portfolio_snapshot`: JSONB

### `Decision`
The final generated output.
- `decision_id`: UUID
- `company_id`: UUID
- `context_id`: UUID
- `action`: ENUM (BUY_TRANCHE_1, BUY_TRANCHE_2, HOLD, EXIT, WATCH)
- `confidence`: Float
- `explanation`: Markdown text detailing exactly which Knowledge variables triggered the action.
- `created_at`: Timestamp

---

## 6. Execution Lifecycle

1. **Trigger**: The Decision Engine is triggered asynchronously. Triggers can be:
   - Completion of a `KnowledgeUpdateTransaction` (Fundamentals changed).
   - End-of-day market data ingestion (Prices changed).
2. **Snapshot**: Engine takes a snapshot of `CompanyKnowledge`, Market Data, and Portfolio.
3. **Funnel Evaluation**: Passes the snapshot through Stages 1, 2, and 3.
4. **Generation**: Creates `Decision` and `DecisionContext` records.
5. **Dispatch**: Sends the `Decision` to the Portfolio Engine for capital execution.

---

## 7. Acceptance Criteria

1. The Engine executes solely on `CompanyKnowledge` and external market/portfolio state.
2. Given a fixed `DecisionContext`, the Engine produces a deterministic `Decision`.
3. The Engine correctly navigates the Tranche Matrix (will not BUY_TRANCHE_2 if THESIS_INVALID).
4. Every `Decision` record persists its full context for historical auditing.
