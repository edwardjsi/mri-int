# Amritkaal Alpha Engine PRD

## Product Overview

**Product name:** Amritkaal Alpha Engine (AAE)

AAE is an event-driven, multi-agent research and stock-selection platform for Indian listed equities. Its primary output is a ranked list of re-rating candidates, continuously updated company theses, and risk dashboards for professional investor review.

AAE extends the existing MRI platform:

- MRI provides market data, trend scores, regime context, watchlists, alerts, and deployment infrastructure.
- PRDE provides the fundamentals intelligence and financial fingerprint foundation.
- AAE adds event ingestion, document intelligence, structural signal detection, macro correlation, execution-risk monitoring, orchestration, thesis versioning, and analyst workflows.

## Goals

- Detect structural business inflections before consensus recognition.
- Map qualitative change to financial fingerprints and valuation re-rating probability.
- Maintain living theses with source evidence, score history, and risk state.
- Surface thesis breaks quickly through risk dashboards and alerts.
- Preserve human sign-off; AAE is an analyst decision-support system, not an execution engine.

## Target Users

- Buy-side analysts and portfolio managers focused on Indian equities.
- Family offices and HNIs running concentrated portfolios.
- Quant and hybrid funds that want machine-generated ideas with human review.

## Non-Goals for V1

- No automated order execution.
- No high-frequency or intraday trading.
- No global equities; V1 focuses on Indian NSE/BSE listed equities.
- No unsupported LLM-only investment conclusions. Every score and thesis must be traceable to source documents, financial data, or deterministic features.

## Primary Use Cases

### 1. Quarterly Result Event

Question: What changed structurally?

Trigger:

- New quarterly filing, annual filing, investor presentation, transcript, or announcement.

Output:

- Structural signals detected.
- Evidence snippets and source references.
- Matching financial fingerprints.
- Updated re-rating probability score.
- Updated thesis summary and risk state.

### 2. Universe Scan

Question: Show me re-rating candidates now.

Trigger:

- Weekly run or admin on-demand scan.

Output:

- Ranked companies by re-rating probability.
- Master Investor Checklist scores.
- Operating leverage, capital efficiency, FCF quality, and valuation context.
- Sector and macro context flags.

### 3. Company Deep Dive

Question: Why is this name interesting?

Input:

- Ticker or company name.

Output:

- Thesis object with structural signals, financial fingerprints, macro tailwinds, risks, and valuation context.
- Metric history for revenue, EBITDA, margins, ROCE, FCF/PAT, working capital days, and operating leverage.
- Comparable companies and sector context.

### 4. Risk Monitoring

Question: Is the thesis breaking?

Trigger:

- Financial update, price/volume event, filing, corporate action, news event, or macro/policy shock.

Output:

- Risk dashboard with green, amber, and red flags.
- Alert cause, severity, source, and suggested review action.

Review action labels:

- Watch
- Trim Review
- Exit Review
- Ignore Noise

These labels are for analyst review and must not be framed as automated trade instructions.

### 5. Sector Lens

Question: Where is the next wave?

Output:

- Sector heat map separating structural stories from cyclical stories.
- Top re-rating candidates per sector.
- Policy, macro, demand, flow, and valuation context.

## Logical Architecture

AAE is a hierarchical event-driven system.

### Event Bus and Scheduler

Responsibilities:

- Ingest new filings, presentations, transcripts, announcements, macro releases, policy events, flow data, news, and price/volume anomalies.
- Create normalized event objects.
- Dispatch events to relevant agents.
- Track job state and failures.

MVP implementation note:

- Start with manual and scheduled scripts in the existing monolith.
- Add a formal event queue only when manual scripts and database state are stable.

### Orchestrator Agent

Responsibilities:

- Route events to sub-agents.
- Maintain versioned company thesis state.
- Aggregate sub-agent outputs into a Re-rating Candidate Profile.
- Maintain score history and explainability.

### Core Agents

1. Sourcing and NLP Agent
2. Structural Signal Agent
3. Financial Fingerprint Agent
4. Macro Correlation Agent
5. Execution Monitoring Agent

### Data Layer

Required stores:

- Market and fundamentals tables in PostgreSQL.
- Document metadata and text chunks.
- Vector index for document retrieval.
- Feature snapshots for deterministic financial and structural features.
- Agent outputs, final scores, thesis versions, risk events, and analyst feedback.

MVP implementation note:

- Keep PostgreSQL as the source of truth.
- Add vector/document infrastructure only after fundamentals import and deterministic scoring are proven.

### User Layer

- Analyst console in the existing React/Vite frontend.
- FastAPI endpoints in the existing monolith.
- Email alerts first; Slack/Teams can be deferred.

## Agent Specifications

### Sourcing and NLP Agent

Goal:

- Convert unstructured text into structured finance-aware event objects.

Inputs:

- Regulatory filings.
- Quarterly and annual reports.
- Conference call transcripts.
- Investor presentations.
- News, sector reports, government notifications, and policy documents.

Responsibilities:

- Classify documents by company, sector, source, document type, and period.
- Extract entities such as companies, projects, capacities, geographies, products, capex plans, and subsidiaries.
- Detect semantic triggers such as:
  - Brownfield expansion
  - Backward integration
  - Forward integration
  - New product segment entry
  - Direct-to-consumer launch
  - Capacity addition
  - New geography
  - Joint venture
  - Subsidiary creation
  - Policy or tariff exposure
- Summarize key management claims with source references and confidence.

Outputs:

- Event objects containing event type, evidence snippets, timestamp, source document, company, confidence, and extracted metadata.

Requirements:

- Finance-specific prompts.
- Retrieval from historical company documents.
- Versioning by filing date.
- Multi-language support can be deferred until English document flow works end to end.

### Structural Signal Agent

Goal:

- Map qualitative events to six structural improvement signals and quantify conviction.

Six signals:

- Margin Quality
- TAM Expansion
- Backward Integration
- Forward Integration
- Moat Strengthening
- Geographic Expansion

Inputs:

- Event objects.
- Historical structural signal state.

Processing:

- Classify each event into one or more of the six signals.
- Assign signal strength from 0 to 1.
- Maintain rolling 3-5 year signal history.
- Generate a high-conviction structural alert when at least four of six signals are active above thresholds within a 12-18 month window.

Outputs:

- Six-signal vector.
- Structural conviction score from 0 to 100.
- Qualitative justifications with source references.

### Financial Fingerprint Agent

Goal:

- Validate qualitative claims against quantitative time series and compute investable metrics.

This is the current PRDE foundation.

Inputs:

- Structural signal vector.
- Annual and quarterly financials.
- Ratios and valuation data.
- Existing MRI market data, price history, trend score, and regime context.

Core computations:

- Sales CAGR over 3 and 5 years.
- EBITDA CAGR and PAT CAGR.
- EBITDA growth versus sales growth.
- Degree of Operating Leverage.
- Gross and EBITDA margin trend.
- ROCE and ROE trend.
- FCF/PAT and cash conversion.
- Working capital days, receivables days, inventory days, payables days, and cash conversion cycle.
- Capex intensity.
- Debt, interest coverage, and leverage.
- Current valuation versus history and peers.

Outputs:

- Time-series metrics.
- Master Investor Checklist scores.
- Green, amber, and red flags by dimension.
- Structural versus financial alignment score.

### Macro Correlation Agent

Goal:

- Align company and sector re-rating potential with macro, policy, valuation, and flows context.

Inputs:

- GDP, inflation, rates, fiscal data, sector data.
- Policy events such as PLI, tariffs, procurement, subsidy, or regulatory changes.
- FPI/DII flows and ownership data.
- Sector mapping and company exposure.

Outputs:

- Sector macro tailwind/headwind score.
- Market valuation regime estimate.
- Sector relative attractiveness.
- Company-level macro alignment score.

### Execution Monitoring Agent

Goal:

- Track thesis integrity and surface red flags.

Inputs:

- Quarterly financial updates.
- Price and volume data.
- News and corporate actions.
- Governance events.
- Macro and policy shocks.

Monitoring dimensions:

- Financial strain: EBIT/interest, net debt/EBITDA, covenant risk.
- Earnings quality: FCF/PAT deterioration and non-cash earnings.
- Working capital: receivables, inventory, payables, and cash conversion cycle.
- Governance: auditor resignations, pledges, related-party anomalies, tax or regulatory actions.
- Margin compression: guidance versus actual deterioration.

Outputs:

- Risk dashboard by category.
- Thesis-at-risk label when multiple persistent red flags fire.
- Alert stream with source evidence and severity.

## Re-Rating Candidate Profile

For each company and as-of date, AAE maintains:

- Structural signal vector.
- Structural conviction score.
- Financial fingerprint metrics.
- Master Investor Checklist score.
- Operating leverage classification.
- Capital efficiency metrics.
- Macro alignment score.
- Risk state.
- Current valuation versus historical and peer bands.
- Re-rating probability score from 0 to 100.
- Thesis object with evidence, risks, and version history.

## Scoring Logic

Start with the Master Investor Checklist as the base quality score.

Boost for:

- Multiple structural signals firing together.
- Demonstrated operating leverage.
- ROCE above required return thresholds.
- Strong FCF/PAT and cash conversion.
- Improving working capital.
- Macro or policy tailwinds.
- MRI trend and regime confirmation.

Penalize for:

- Governance red flags.
- Financial strain.
- Earnings quality deterioration.
- Working capital blow-ups.
- Macro headwinds.
- Extreme valuation without matching fundamentals.
- Crowded trade indicators when data becomes available.

## Data Requirements

### Market and Fundamental Data

- Daily price and volume history.
- Corporate actions.
- Annual and quarterly P&L, balance sheet, and cash flow.
- Ratios including ROE, ROCE, margins, leverage, working capital, and valuation.

### Documents and Text

- Filings.
- Annual reports.
- Transcripts.
- Investor presentations.
- Announcements.
- Press releases.
- Macro and policy documents.

### Macro and Flow Data

- GDP, inflation, RBI rates, fiscal metrics.
- Sector-level indicators.
- FPI/DII flows and ownership.
- Policy events and government notifications.

### Annotation and Feedback

- Human-labeled historical re-rating cases.
- Start date of structural change.
- Market recognition date.
- Financial metrics that moved.
- Language patterns from filings and transcripts.
- Analyst accept, reject, modify, and override actions.

## UX Requirements

### Analyst Console

Screens:

- Dashboard with top candidates, sector heat map, and structural alerts.
- Company page with score, thesis, risk state, signal timeline, financial fingerprints, macro context, and event log.
- Event view with filing/news/macro events and score impact.
- Watchlists and alerts with configurable severity.

### Human-in-the-Loop Workflow

For each high-conviction candidate, AAE generates a thesis breakdown:

- Structural driver summary.
- Financial corroboration.
- Macro context.
- Risk state.
- Valuation context.

Analyst actions:

- Accept thesis.
- Reject thesis.
- Modify thesis.
- Add notes.
- Override score with justification.

Every analyst action must be stored for audit and future calibration.

## Non-Functional Requirements

Latency:

- Event to initial analysis target: 5-15 minutes after filing availability.

Scalability:

- V1 starts with a curated universe.
- Long-term target is full NSE/BSE coverage.
- Backtesting should support 10+ years of historical events when data is available.

Reliability and Auditability:

- Every output references source documents or data points.
- Deterministic pipelines where possible.
- LLM randomness constrained.
- Score and thesis changes are versioned.

Security and Compliance:

- Read-only market data access.
- No trading capability in V1.
- Role-based access control.
- Tenant isolation if multi-client access expands.
- Output language must remain research and decision-support oriented.

## Implementation Phases

### Phase 0 - Foundations

Status: In progress through PRDE.

Deliverables:

- Fundamentals schema.
- Manual CSV import path.
- Import verification.
- Deterministic feature snapshots.
- Deterministic financial fingerprint scoring baseline.

### Phase 1 - Structural and Sourcing Agents

Deliverables:

- Document ingestion.
- Event object schema.
- Source document storage.
- Sourcing/NLP agent.
- Structural signal mapping.
- Six-signal score vector.

### Phase 2 - Macro and Risk Agents

Deliverables:

- Sector macro scoring.
- Policy and flow event ingestion.
- Execution risk dashboard.
- Thesis-at-risk alerts.

### Phase 3 - Orchestrator and UX

Deliverables:

- Re-rating Candidate Profile.
- Re-rating probability score.
- Thesis versioning.
- Analyst console.
- Watchlist and alert workflows.

### Phase 4 - Learning and Optimization

Deliverables:

- Historical re-rating case library.
- Analyst feedback loop.
- Threshold and weight calibration.
- Backtest framework for structural signals and score changes.

## Open Questions

- Sector-specific thresholds for DOL, ROCE, FCF/PAT, and growth.
- Handling lumpy sectors such as defense and EPC versus annuity sectors such as FMCG and software.
- Rule-based versus learned scoring boundaries.
- Whether later order-management integrations are needed after V1.

## Immediate Implementation Rule

Do not jump directly to event agents or document RAG.

AAE implementation begins by completing the PRDE financial fingerprint foundation:

1. Import real 5-10 year annual financial data for a seed universe.
2. Verify data quality and idempotency.
3. Generate deterministic feature snapshots.
4. Build a deterministic scoring baseline.
5. Only then add sourcing, structural, macro, risk, and orchestrator agents.
