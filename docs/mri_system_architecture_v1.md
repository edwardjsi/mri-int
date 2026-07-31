# MRI System Architecture v1.0

## 1. Executive Summary

MRI (Market Regime Intelligence) is a decision-support system engineered to operationalize automated, evidence-backed portfolio management. The primary architectural objective is to transform unstructured financial narratives into structured, evidence-backed knowledge objects through a deterministic processing pipeline. These nodes seamlessly feed a rules-based Decision Engine to execute portfolio actions without human emotional interference. 

### Principle: Knowledge is cumulative. Decisions are ephemeral.

Research compounds. Knowledge compounds. Understanding compounds. Decisions don't. A BUY today may become a HOLD next month. The knowledge that produced both decisions remains valuable. 

Therefore: **MRI optimizes for preserving and improving knowledge rather than preserving historical recommendations.** 

Historically, portfolio management tools have focused entirely on quantitative screener outputs. MRI differentiates itself by elevating **Knowledge** as a first-class primitive. By defining rigid boundaries between Document Ingestion, Knowledge Storage, and Decision Execution, MRI ensures that the system is entirely auditable. If a decision is made, the platform can recursively trace that decision back through the Decision Engine -> the Company Workspace -> the Knowledge Update Transaction -> and finally, the exact highlighted paragraph in the Source Document.

This v1.0 document establishes the foundational boundaries, aggregate roots, invariants, and event flows that govern the entire system.

---

## 2. Bounded Contexts & Aggregate Roots

The MRI ecosystem is partitioned into three strictly separated bounded contexts. This separation of concerns guarantees that changes in UI consumption do not corrupt knowledge ingestion, and that ML-driven insights do not bypass deterministic portfolio rules.

### 2.1 The Company Intelligence Workspace (CIW)
**Domain:** Knowledge Management & Entity State
**Aggregate Root:** `CompanyWorkspace`

The CIW is the canonical repository of truth for any given equity. It is entirely agnostic to *how* a decision is made and *where* a document came from. It strictly cares about maintaining a valid, evidence-backed state of understanding.

**Components:**
- **Identity (`CompanyIdentity`)**: The immutable core (e.g., Symbol, Name, Sector).
- **Workspace Version (`workspace_version`)**: A monotonic integer incremented upon every applied transaction. Ensures downstream consumers can precisely trace *which* version of a workspace produced a specific decision.
- **KnowledgeState (`KnowledgeState`)**: The living map of current understanding. It tracks exactly one active `Thesis` and `BusinessQuality` node, alongside a variable list of `Risks`, `Catalysts`, and `Monitoring` flags.
- **Timeline (`TimelineEvent`)**: An append-only chronological history. It unifies `RESEARCH`, `TRADE`, `EARNINGS`, and `DECISION` events so that a company's entire lifecycle is visible on a single timeline.
- **PortfolioContext (`PortfolioContext`)**: A localized, read-only projection of the system's ledger, allowing the CIW to know if a symbol is "Owned", "Watchlist", or "Archived" without directly coupling to the trading engine.

**Strict Invariants:**
1. **Single-Active Truth**: A workspace may only possess exactly one `ACTIVE` Thesis and one `ACTIVE` Business Quality node. When a new thesis is applied, the previous one MUST be transitioned to `ARCHIVED`.
2. **Evidence Mandate**: Every `KnowledgeNode` (Risk, Catalyst, Thesis) MUST maintain a lineage pointer (`evidence`) to a `SourceDocument` ID, ensuring zero hallucinated or untraceable knowledge.
3. **Mutation Sealing**: The `CompanyWorkspace` cannot be directly mutated by any external service. All state changes MUST be applied via a `WorkspaceUpdater` executing a `KnowledgeUpdateTransaction`.

---

### 2.2 Knowledge Ingestion Pipeline
**Domain:** Unstructured Data Processing & Intelligence Extraction
**Aggregate Root:** `KnowledgeUpdateTransaction`

The Ingestion Pipeline serves as the translation layer between the chaotic outside world (PDFs, raw text, broker reports) and the strictly-typed CIW. 

**Components:**
- **`SourceDocument`**: The raw asset (e.g., MOSI Report). Treated as an immutable blob of metadata and text.
- **`KnowledgeUpdateProcessor`**: The LLM-orchestration layer. It reads the `SourceDocument`, extracts insights, and formats them into a proposed list of `NodeUpdate` instructions (CREATE, UPDATE, ARCHIVE).
- **`KnowledgeUpdateTransaction`**: The formalized delta payload. It acts as a staging area. If approved, it is handed to the CIW.

**Strict Invariants:**
1. **Stateless Processing**: The `KnowledgeUpdateProcessor` has no database write access. It is a pure function: `f(document, prompt) -> transaction`.
2. **Audit Logging**: Every successful application of a transaction MUST generate a UUID-tagged log in the `ciw_update_transaction` table, mapping exactly which nodes were modified by which document.

---

### 2.3 The Decision Engine (Portfolio OS)
**Domain:** Trading Logic & Execution
**Aggregate Root:** `DecisionContext`

The Decision Engine is a deterministic, rule-based evaluator that decides whether to BUY, SELL, HOLD, or ADD based on the synthesized environment.

**Components:**
- **`StockSnapshot` / `IndicatorSnapshot`**: Pure technical facts (Trend scores, MRI scores, Moving Averages).
- **`DecisionContext`**: The ephemeral adapter object built at runtime. It blends the technical `StockSnapshot`, the `PortfolioPosition` (sizing, entry price), and the CIW abstract fields (`ciw_thesis`, `ciw_risks`) into one evaluation surface.
- **`RuleEngine`**: Evaluates the `DecisionContext` against a JSON-defined ruleset to compute a deterministic action (e.g., if price < stop_loss -> EXIT).
- **`CaiEngine`**: Wraps the deterministic action into an Explainable AI (XAI) recommendation tree, attaching CIW knowledge as `XaiEvidence`.

**Strict Invariants:**
1. **Graceful Degradation**: The Engine must successfully evaluate rules even if a symbol has zero CIW knowledge (a sparse context).
2. **Read-Only**: The Decision Engine NEVER writes to the CIW. It only consumes `DecisionContext`.

---

## 3. End-to-End Event Flow & Choreography

The architecture enforces a strictly unidirectional flow of data. Below is the lifecycle of a single piece of market intelligence, from raw document to executed trade.

### Phase A: Knowledge Accumulation
1. **Ingestion**: A raw MOSI report is uploaded and logged as a `SourceDocument`.
2. **Processing**: The `KnowledgeUpdateProcessor` reads the document and identifies that the company's margins are expanding due to a new CDMO unit.
3. **Staging**: The processor yields a `KnowledgeUpdateTransaction` containing a new `CATALYST` node and an instruction to `UPDATE` the primary `THESIS`.
4. **Commitment**: The `WorkspaceUpdater` receives the transaction. It opens a Postgres transaction, archives the old Thesis, inserts the new Thesis and Catalyst, logs the transaction ID, appends a Timeline Event, and commits. 

### Phase B: Decision Execution (Weekly Review)
5. **Context Assembly**: The `PortfolioOsReviewService` runs its weekly batch. For the target symbol, it fetches the `StockSnapshot` (technical data), the `PortfolioPosition` (ledger data), and queries the `CompanyWorkspaceRepository` for the CIW aggregate.
6. **Adapter Injection**: The repository returns the workspace. The service extracts the active Thesis and Catalysts and mounts them into the `DecisionContext`.
7. **Rule Evaluation**: The `RuleEngine` analyzes the `DecisionContext`. Seeing a strong trend and MRI score, it outputs an `ADD` action.
8. **Explanation Generation**: The `CaiEngine` formats the final `CaiRecommendation`. Because CIW data was present in the context, it overrides generic explanations with the actual CIW Thesis and appends the Catalysts as XAI Evidence points.
9. **UI Delivery**: The FastAPI router serializes the recommendation and delivers it to the React frontend, allowing the user to view the decision alongside a fully transparent evidence tree.

---

## 4. Physical Data Storage (Repositories)

The logical aggregates are persisted across a highly normalized PostgreSQL schema.

- **`ciw_company`**: Stores identity and denormalized portfolio states.
- **`ciw_knowledge_node`**: Stores the universe of all facts. Uses a `status` column to filter `ACTIVE` vs `ARCHIVED` knowledge.
- **`ciw_timeline_event`**: Unified chronological ledger.
- **`ciw_update_transaction`**: JSONB audit logs mapping node changes to documents.

**The Repository Pattern**:
The `CompanyWorkspaceRepository` is the sole gatekeeper for hydrating the CIW. It performs the necessary JOINs and routing logic (e.g., mapping a `NodeType.THESIS` row to `workspace.state.understanding['thesis']`) so that the application layer never deals with raw SQL rows.

---

## 5. API Boundaries & Read Models

The backend micro-architecture exposes its capabilities via distinct, modular FastAPI routers. The system is evolving toward a CQRS-style read model architecture, where the UI consumes optimized projections of the canonical workspace rather than the raw aggregate root.

- **`GET /api/ciw/{symbol}`**: Returns a `CompanySummaryView`, a hydrated projection of the `CompanyWorkspace` with dynamically injected `health` metrics.
- **`GET /api/review/weekly`**: The execution endpoint. Drives the Decision Engine batch process, returning an array of actionable `StockDecisionPayload` items (read models) for the frontend Dashboard.
- **`POST /api/ciw/ingest` (Future)**: The webhook entry point for the `KnowledgeUpdateProcessor`.

---

## 6. Ownership & Future Extensibility

### System Ownership
- **Knowledge Pipeline**: Owned by the Data/AI Engineering cell. They are responsible for prompt fidelity and extraction accuracy.
- **Decision Engine**: Owned by the Quant/Portfolio cell. They are responsible for indicator logic and ruleset tuning.
- **CIW Core**: Shared infrastructure. Modifying the CIW schema requires cross-team consensus, as it is the canonical bridge between Data and Quant.

### Domain Events (Future Event-Driven Architecture)
The system currently relies on transactions. As it scales, it will emit explicit Domain Events (`ThesisUpdated`, `RiskResolved`, `CatalystAdded`, `WorkspaceUpdated`). These events will serve as the nervous system driving workflows, real-time alerts, and LLM-generated summaries without tightly coupling services.

### Future Bounded Context: Learning & Calibration
As knowledge history accumulates, a fourth bounded context will emerge: **Learning & Calibration**. 
This module will query historical workspace versions and map them against resulting portfolio outcomes to answer:
- *Which catalysts proved reliable?*
- *Which risks mattered most?*
- *Which rules consistently underperformed?*
This context will not execute trades; it will generate feedback loops to improve future knowledge processing.

### Designing for Tomorrow
The most significant achievement of this v1.0 architecture is its resilience to decay. 
Because the UI is entirely decoupled from state mutation, the frontend can be rewritten entirely in a new framework without impacting intelligence accumulation.
Because the ruleset is JSON-driven and evaluating against a standardized adapter, the trading logic can be hot-swapped without touching the database.
Because every piece of knowledge is immutable and tagged with a transaction ID, the system inherently supports time-travel debugging. Six months from now, if an analyst asks, "Why did we buy this?", the system can precisely rebuild the exact `CompanyWorkspace` and `DecisionContext` that existed on that day.
