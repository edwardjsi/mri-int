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

### MRI/STEE Platform
- Nifty 500 price ingestion and indicator pipeline
- 7-step weighted MRI score and technical transparency
- QIF financial scoring and verdict persistence
- QIL/debate generation with branded HTML email delivery
- Watchlist and Digital Twin persistence
- Admin visibility, health checks, and SES-based notifications
- Schema auto-heal patterns in `api/schema.py`
- `system_audit_logs` table for execution audit trail
- Pipeline auto-triggers on push to `main` (GitHub Actions)
- Market holiday gate preventing weekend runs
- EMA-50/EMA-200 regime (not SMA) — reflected in UI and API

### PERX V1 (Shipped May 08, 2026)
- `perx_reports` and `perx_scores` schema in `api/schema.py`
- `engine_perx/` package: orchestrator, scoring, report_builder
- `api/perx.py`: scan, fetch, search, recent, email endpoints
- `PerxPage` in `frontend/src/App.tsx` with company autocomplete dropdown
- On-demand QIF compute (missing quality/fundamental data fetched automatically)
- Email delivery via existing SES path
- Debate/Forensic Review integration (optional via toggle)
- Docker: `engine_perx/` copied into Railway container

## Known Constraints

- Do not redesign the architecture or split services
- Do not modify MRI/STEE/QIF signal logic
- Do not dilute signal scarcity
- Stay deterministic-first
- AI may synthesize narrative and contradictions, but may not invent metrics or issue trading advice
- PERX must fit the existing monolith, database, email, and route patterns

## Current Milestone Context

**V1 Delivery Status (May 08, 2026):** ✅ COMPLETE

All V1 items shipped to production (Railway):
- `perx_reports` and `perx_scores` schema in `api/schema.py`
- `engine_perx/` orchestration package with on-demand QIF compute
- `api/perx.py` with scan, fetch, search, recent, and email endpoints
- `PerxPage` in frontend with company autocomplete dropdown
- Email delivery via existing SES path
- Debate/Forensic Review integration

**V2 is now the active delivery milestone.**

## Data Readiness

### What We Already Have Enough Of (V2)

V2 can be built entirely from existing data and infrastructure, with these additions to enable:

- **Compare Mode**: `perx_scores` already snapshots every scan; needs history endpoint + UI
- **Research Archive**: `perx_reports` already stores all scans; needs filter/search API + UI
- **Lifecycle History**: `perx_scores` already tracks latest; needs full history query

### What Is Still Missing For Full PERX (Phase 3)

The full PRD expects additional layers that are not yet modeled as first-class data:

- sector intelligence and sector breadth history
- explicit fragility snapshots persistence
- lifecycle history persistence (full timeline, not just latest)
- narrative transition history
- historical analog storage

These are Phase 3 blockers, not V2 blockers.

---

## V2 Scope: Compare Mode + Research Archive + Lifecycle History

### In Scope (V2)

#### Compare Mode
- `POST /api/perx/compare` — generate side-by-side comparison of 2 symbols
- Comparison UI in `PerxPage`: pick 2 companies, view diff across MRI, STEE, QIF, PERX score, lifecycle, fragility
- Shared context: same regime backdrop, same sector if available

#### Research Archive
- `GET /api/perx/archive` — list all scans with filters (symbol, date range, score range, lifecycle stage)
- Archive view in `PerxPage`: table of all past scans for the client, sortable/filterable

#### Lifecycle History
- `GET /api/perx/history/{symbol}` — PERX score trajectory over all scans for a symbol
- Small sparkline/score chart in the single-company report view

#### On-Demand Quality Improvements
- PERX already computes missing QIF data on-demand; continue to improve coverage and speed

### Out of Scope (V2)
- Compare mode for more than 2 companies
- Sector intelligence layer
- Analog detection
- PDF export
- Lifecycle history persistence for symbols not scanned via PERX

### Recommended V2 Tables

```text
# No new tables required for V2
# perx_reports  — already has all scan history
# perx_scores   — already has latest per symbol
# Consider adding perx_score_history in Phase 3 if lifetime trajectory is needed beyond scans
```

## V2 API Plan

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/perx/compare` | POST | Compare 2 symbols side-by-side |
| `/api/perx/archive` | GET | List all scans with filters |
| `/api/perx/history/{symbol}` | GET | Score trajectory for a symbol |
| `/api/perx/search` | GET | Company autocomplete (already in V1) |

## V2 Report Structure

### Compare Report JSON
```json
{
  "left": { ...same as single report... },
  "right": { ...same as single report... },
  "comparison": {
    "winner": {
      "perx_score": "left",
      "mri": "left",
      "qif": "left",
      "fragility": "right",
      "lifecycle": "left"
    },
    "score_delta": 8.5,
    "key_differentials": [
      "QIF score: left leads by 15 points on ROCE trajectory",
      "Fragility: right is MODERATE vs left LOW"
    ]
  }
}
```

## V2 Frontend Plan

### Compare Mode UI
- Add a second company search alongside the existing one
- When both are selected, show side-by-side report panels
- Comparison summary banner at top

### Archive UI
- New tab/section in `PerxPage` below the scan + recent reports
- Filter bar: symbol search, date range, score range, lifecycle stage
- Sortable table of all scans for the client

### Lifecycle History UI
- Small line chart or score badge list within the single-company report
- Shows all past PERX scores for that symbol with timestamps

## Delivery Sequence

### V2 Step 1: Lifecycle History
- Add `GET /api/perx/history/{symbol}` endpoint
- Show score trajectory in single-company report view
- *Rationale*: smallest scope, proves the history query pattern

### V2 Step 2: Research Archive
- Add `GET /api/perx/archive` endpoint with filters
- Add archive tab to `PerxPage` with filter bar and results table
- *Rationale*: easy backend query, useful standalone

### V2 Step 3: Compare Mode
- Add `POST /api/perx/compare` endpoint generating side-by-side report
- Add second company search in `PerxPage`
- Show comparison summary + diff panels
- *Rationale*: highest user-value V2 feature, most complex

## Smallest Next Implementation Step (V2)

The next smallest logical step is **Lifecycle History**:

1. Add `GET /api/perx/history/{symbol}` in `api/perx.py`
2. Add `get_perx_score_history(...)` in `engine_perx/orchestrator.py`
3. Add history sparkline/list to the single-company report in `PerxPage`

This proves the history query pattern and provides immediate value (seeing score trajectory).

---

## V1 Completed Deliverables (Reference)

- ✅ `perx_reports` and `perx_scores` schema
- ✅ `engine_perx/` orchestration package
- ✅ Single-symbol unified report JSON
- ✅ API routes: scan, fetch, recent, search, email
- ✅ On-demand QIF compute (missing data fetched automatically)
- ✅ Company autocomplete dropdown
- ✅ Email delivery via existing SES path
- ✅ Debate/Forensic Review integration (optional)
- ✅ PERX sidebar navigation (desktop + mobile)
- ✅ Frontend build: `npm run build` → `api/static/`

---

## V3+ Roadmap (Future Phases)

| Feature | Description |
|---------|-------------|
| Sector Intelligence | Sector RS, breadth, institutional attention derived layers |
| Analog Detection | Historical rerating pattern matching |
| Lifecycle History Persistence | Full timeline for all tracked symbols |
| PDF Export | Branded institutional report as downloadable PDF |
| Watchlist PERX Intelligence | PERX scores surfaced in watchlist table |

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
- `market_regime` (EMA-based: ema_50, ema_200, classification)
- `fundamental_financials`
- `quality_verdicts`
- `quality_verdicts_history`
- `qil_sources`
- `swing_trades`
- `client_watchlist`
- `client_external_holdings`
- `email_log`
- `system_audit_logs`
- `perx_reports` (all scan history, V1+)
- `perx_scores` (latest PERX snapshot per symbol, V1+)

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
