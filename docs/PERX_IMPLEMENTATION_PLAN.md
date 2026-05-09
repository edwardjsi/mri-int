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
- ✅ `perx_reports` and `perx_scores` schema in `api/schema.py`
- ✅ `engine_perx/` package: orchestrator, scoring, report_builder
- ✅ `api/perx.py`: scan, fetch, search, recent, email endpoints
- ✅ `PerxPage` in `frontend/src/App.tsx` with company autocomplete dropdown
- ✅ On-demand QIF compute (missing quality/fundamental data fetched automatically)
- ✅ Email delivery via existing SES path
- ✅ Debate/Forensic Review integration (optional via toggle)
- ✅ Docker: `engine_perx/` copied into Railway container

### PERX V2 (Shipped May 08, 2026)
- ✅ `GET /api/perx/history/{symbol}` for score trajectory
- ✅ `GET /api/perx/archive` with advanced filtering
- ✅ `POST /api/perx/compare` for side-by-side analysis
- ✅ Tabbed UI (Scan, Compare, Archive) in `PerxPage`
- ✅ Portfolio quick-select chips for one-click scans
- ✅ Institutional Baseline awareness (prior report context)

## Known Constraints

- Do not redesign the architecture or split services
- Do not modify MRI/STEE/QIF signal logic
- Do not dilute signal scarcity
- Stay deterministic-first
- AI may synthesize narrative and contradictions, but may not invent metrics or issue trading advice
- PERX must fit the existing monolith, database, email, and route patterns

## Current Milestone Context

**V3 is now the active delivery milestone.**

---

## V3 Scope: Institutional Depth & Integration

### In Scope (V3)

#### 1. Sector Intelligence Layer
- **Real Sector Metrics**: Replace V1 placeholders with actual `stock_sectors` data.
- **Sector RS**: Relative Strength calculation for the company against its specific industry peers.
- **Peer Context**: Automatically identify and display the PERX scores of the 2 closest competitors during a scan.
- **Industry Breadth**: Metric showing if the sector as a whole is in accumulation or distribution.

#### 2. Watchlist Intelligence
- **Score Surfacing**: Add `PERX Score` and `Lifecycle Stage` columns to the main Watchlist table.
- **Rerating Alerts**: Automate notifications if a watchlisted stock's PERX score improves by >5 points during a daily pipeline run.

#### 3. Branded Institutional Memo (PDF)
- **Export Feature**: Add an "Export PDF" button to the report view.
- **Professional Layout**: Generate a clean, branded PDF summary including MRI checklist, QIF trajectory, and Forensic Review.
- **Backend**: Implement PDF generation via `ReportLab` or similar library in `engine_perx`.

#### 4. Analog Detection (Early Pattern Match)
- **Historical Analogs**: Identify 1-2 historical Indian stocks that exhibited similar PERX/MRI trajectories before a major rerating.
- **Semantic Matching**: Match current "Narrative Transition" patterns against historical winners (e.g., "Setup mirrors HAL in early 2022").

### V3 API Plan

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/perx/sector/{symbol}` | GET | Fetch detailed sector breadth and peer context |
| `/api/perx/report/{id}/pdf` | GET | Generate and download branded PDF report |
| `/api/perx/alerts` | GET | List recent PERX score upgrades for watchlist stocks |

## Delivery Sequence (V3)

### V3 Step 1: Sector Intelligence & Peers
- Implement `engine_perx/sector.py` to calculate industry RS and peer ranks.
- Update `engine_outputs` to include real sector data instead of placeholders.
- *Rationale*: Low risk, high analytical value.

### V3 Step 2: Watchlist Score Surfacing
- Update `api/watchlist.py` to join with `perx_scores`.
- Update `WatchlistPage` UI to show PERX metrics.
- *Rationale*: Drives daily engagement and surfaces rerating candidates.

### V3 Step 3: PDF Export
- Implement backend PDF generation.
- Add "Export Memo" button to `PerxPage`.
- *Rationale*: Makes the product feel "Premium" and "Institutional."

### V3 Step 4: Analog Detection
- Create semantic pattern matching for historical reratings.
- Add "Historical Analogs" section to the report.
- *Rationale*: Most complex; requires historical score mapping.

## Smallest Next Implementation Step (V3)

The next smallest logical step is **Sector Intelligence**:

1. Implement `get_sector_context(symbol)` in `engine_perx/orchestrator.py`.
2. Fetch top 3 peers by market cap/score in the same industry.
3. Replace the "Sector" placeholder in the UI with real peer ranking data.

---

## V1 Implementation Plan (Archive)

### MVP Scope
PERX V1 should be backend-first and single-symbol only.

#### In Scope
- generate a unified PERX report for one symbol
- store the report JSON
- store a PERX score summary row
- expose scan and fetch endpoints
- optionally email the institutional report
- reuse the existing debate output as "Institutional Forensic Review"

#### Recommended Modules
```text
engine_perx/
├── orchestrator.py
├── scoring.py
├── report_builder.py
└── schemas.py
```

#### API Plan
- `POST /api/perx/scan/{symbol}`
- `GET /api/perx/report/{report_id}`

---

## V2 Implementation Plan (Archive)

### V2 Scope: Compare Mode + Research Archive + Lifecycle History

#### In Scope (V2)
- **Compare Mode**: `POST /api/perx/compare` — side-by-side analysis of 2 symbols.
- **Research Archive**: `GET /api/perx/archive` — list all scans with filters.
- **Lifecycle History**: `GET /api/perx/history/{symbol}` — score trajectory over time.

#### API Plan
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/perx/compare` | POST | Compare 2 symbols side-by-side |
| `/api/perx/archive` | GET | List all scans with filters |
| `/api/perx/history/{symbol}` | GET | Score trajectory for a symbol |

#### Delivery Sequence
1. Lifecycle History
2. Research Archive
3. Compare Mode
