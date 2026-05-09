# PERX Implementation Plan
# Date: 08 May 26

## Product

PERX - Institutional Rerating Intelligence Engine

## Purpose

This document maps the PERX PRD onto the existing MRI platform and defines the smallest practical implementation path that preserves current production behavior.

PERX should be treated as a company-first orchestration layer inside the existing MRI monolith. It does not replace MRI, STEE, QIF, Risk Audit, Digital Twin, or the Debate Engine. It synthesizes their outputs into a unified institutional rerating report.

## Current System Architecture

The current system architecture remains:

- FastAPI monolith backend
- React/Vite frontend
- Neon PostgreSQL production database
- AWS SES transactional email delivery
- Existing daily pipeline for ingestion, indicators, regime, scoring, signals, STEE, and email

Existing engines already available:

- MRI technical scoring
- STEE breakout execution logic
- QIF fundamental scoring
- QIF trajectory and quality improver signals
- Debate engine for qualitative forensic review
- Watchlist, portfolio, risk audit, admin, and email infrastructure

## What Has Already Been Completed

- Nifty 500 price ingestion and indicator pipeline
- 7-step weighted MRI score and technical transparency
- QIF financial scoring and verdict persistence
- QIL/debate generation with branded HTML email delivery
- Watchlist and Digital Twin persistence
- Admin visibility, health checks, and SES-based notifications
- Schema auto-heal patterns in `api/schema.py`

## Known Constraints

- Do not redesign the architecture or split services
- Do not modify MRI/STEE/QIF signal logic
- Do not dilute signal scarcity
- Stay deterministic-first
- AI may synthesize narrative and contradictions, but may not invent metrics or issue trading advice
- PERX must fit the existing monolith, database, email, and route patterns

## Current Milestone Context

The current active delivery milestone in `Progress.md` remains:

- Debate Trigger Verification

PERX is the next planned product layer after that verification milestone, not a replacement for it.

## Existing Infrastructure We Can Reuse

### 1. Application Architecture

Reuse the current FastAPI monolith, React frontend, Railway deployment model, and shared database access.

PERX should follow the existing repo shape:

- new engine modules under `engine_perx/`
- new API router under `api/`
- schema bootstrap additions in `api/schema.py`
- optional email builder additions in `engine_core/email_service.py`
- later frontend surfaces in `frontend/src/`

### 2. Database

Reuse Neon PostgreSQL and existing intelligence tables.

Current useful data sources:

- `daily_prices`
- `stock_scores`
- `market_regime`
- `fundamental_financials`
- `quality_verdicts`
- `quality_verdicts_history`
- `qil_sources`
- `swing_trades`
- `client_watchlist`
- `client_external_holdings`
- `email_log`
- `system_audit_logs`

### 3. Email Delivery

Reuse `engine_core/email_service.py` and AWS SES.

Existing patterns already support:

- HTML report builders
- custom recipient routing
- email logging patterns
- debate-triggered delivery

PERX only needs a new builder and sender path, for example:

- `build_perx_report_email_html(...)`
- `send_perx_report_email(...)`

### 4. Existing Intelligence Layers

PERX should orchestrate, not duplicate:

- MRI answers: is the market recognizing leadership?
- STEE answers: is there a high-quality breakout structure?
- QIF answers: is business quality improving?
- Debate answers: what is the skeptical forensic read?

PERX should answer:

- is market perception changing in a way that could support sustained rerating?

## Data Readiness

### What We Already Have Enough Of

PERX V1 does not need more Yahoo Finance price downloads.

We already have enough data for:

- header and report timestamp
- MRI evidence block
- STEE evidence block
- QIF evidence block
- forensic review reuse
- first-pass executive summary
- first-pass PERX score
- first-pass lifecycle classification

### What Is Still Missing For Full PERX

The full PRD expects additional layers that are not yet modeled as first-class data:

- sector intelligence and sector breadth history
- explicit fragility snapshots
- lifecycle history persistence
- narrative transition history
- historical analog storage

These are not blockers for PERX V1, but they are blockers for the full PRD surface.

## MVP Scope

PERX V1 should be backend-first and single-symbol only.

### In Scope

- generate a unified PERX report for one symbol
- store the report JSON
- store a PERX score summary row
- expose scan and fetch endpoints
- optionally email the institutional report
- reuse the existing debate output as "Institutional Forensic Review"

### Out of Scope

- compare mode
- archive UI
- lifecycle history visualizations
- analog engine
- advanced sector intelligence
- PDF export

## Recommended Modules

```text
engine_perx/
├── orchestrator.py
├── scoring.py
├── lifecycle.py
├── narrative.py
├── fragility.py
├── sector.py
├── report_builder.py
└── schemas.py
```

### Minimal Phase 1 Reality

Only these must exist first:

- `engine_perx/orchestrator.py`
- `engine_perx/scoring.py`
- `engine_perx/report_builder.py`
- `engine_perx/schemas.py`

The other modules can start as thin helpers or placeholders until their inputs are real.

## Recommended Tables

For PERX V1, keep persistence minimal:

```text
perx_reports
perx_scores
```

Recommended later:

```text
lifecycle_history
narrative_transitions
fragility_snapshots
```

### Suggested V1 Table Intent

- `perx_reports`
  - one stored institutional report per generated scan
  - includes symbol, report JSON, summary text, created timestamp, and optional client linkage

- `perx_scores`
  - latest rerating score snapshot per symbol
  - includes score, lifecycle stage, narrative intensity, fragility level, generated timestamp

## API Plan

### Phase 1 Endpoints

- `POST /api/perx/scan/{symbol}`
  - generate and optionally persist a new PERX report

- `GET /api/perx/report/{report_id}`
  - fetch a stored report

### Phase 2 Endpoints

- `POST /api/perx/email/{report_id}`
  - send the institutional report by email

- `GET /api/perx/watchlist`
  - later watchlist intelligence view

- `POST /api/perx/compare`
  - later comparison mode

## Report Structure

PERX V1 unified JSON should contain:

- header
- executive_summary
- narrative_transition
- engine_outputs
- institutional_forensic_review
- lifecycle
- final_institutional_verdict

### Reuse Map

- `header`
  - symbol, timestamp, sector when available, computed PERX score

- `executive_summary`
  - synthesized from MRI + STEE + QIF + debate summary

- `narrative_transition`
  - initial AI synthesis based on financial trend + quality category + technical leadership

- `engine_outputs.mri`
  - latest `stock_scores`

- `engine_outputs.stee`
  - latest breakout and setup context derived from technical flags and swing logic

- `engine_outputs.qif`
  - `quality_verdicts` and supporting financial trends

- `institutional_forensic_review`
  - existing debate structure, renamed for PERX presentation

- `lifecycle`
  - deterministic classification from score mix and trend alignment

- `final_institutional_verdict`
  - constrained narrative conclusion with no buy/sell advice

## Suggested Deterministic Logic For V1

### PERX Score

Start with a weighted synthesis of existing outputs:

- MRI technical leadership
- STEE tactical quality
- QIF business quality
- trajectory or score-change support
- debate support or caution flags

This first score should be simple and explainable. Avoid overfitting or introducing opaque weighting before real validation.

### Lifecycle Classifier

Use rule-based stages:

- `Accumulation`
- `Early Rerating`
- `Institutional Expansion`
- `Euphoria`
- `Distribution`

Early versions can infer stage from:

- MRI score strength
- breakout/leadership confirmation
- QIF strength
- trajectory direction
- fragility penalty

### Fragility

PERX V1 can derive a basic fragility section from existing evidence:

- weak or absent profitability trend
- debt burden concerns
- deteriorating trajectory
- overheated technical extension
- skeptical debate flags

No new external data source is required for this first pass.

## Frontend Plan

Do not start with a full new dashboard.

### Phase 1

- backend-only or a thin route consumer
- generate report JSON and inspect in API/admin workflows

### Phase 2

- add `PERX Scan` entry to the sidebar
- company-first search UI
- single report page for `/perx/[symbol]`

### Phase 3

- compare mode
- research archive
- watchlist intelligence movements

## Delivery Sequence

### Phase 1

- schema for `perx_reports` and `perx_scores`
- `engine_perx` orchestration package
- single-symbol unified report JSON
- API route for scan and fetch

### Phase 2

- HTML email builder and email endpoint
- watchlist integration
- admin visibility for latest runs

### Phase 3

- compare mode
- lifecycle history
- archive surface
- richer sector and fragility engines

## Smallest Next Implementation Step

The next smallest logical implementation step is:

1. add `perx_reports` and `perx_scores` to `api/schema.py`
2. create `engine_perx/orchestrator.py`
3. create `api/perx.py`
4. return a stored unified report JSON for a single symbol with reused MRI/STEE/QIF/Debate evidence

This is the safest first cut because it proves the product shape without changing any existing production engine logic.
