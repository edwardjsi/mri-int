# AAE Milestone Implementation Plan

> **Created:** 2026-05-23
> **Status:** Living document — updated as milestones are completed.

---

## Layman's Introduction: What is AAE?

Imagine MRI as a **stock screening machine**. Every day, it scans 500+ Indian stocks, gives each one a 0–100 score based on price momentum, checks if the company is financially healthy (QIF), and sends alerts when a stock breaks out. It's like a fitness tracker for stocks.

### From "Good Stock" to "When Will The Market Notice?"

AAE — the **Active Alpha Engine** (also called the Amritkaal Alpha Engine) — goes one level deeper. MRI tells you *this stock is strong right now*. AAE tries to answer a harder question:

> *Which good companies is the market still underestimating, and why is that about to change?*

It's hunting for **re-rating candidates** — stocks whose PE ratio (how much investors are willing to pay for each rupee of profit) is about to expand because the company is improving in ways the market hasn't fully priced in yet.

### How It Works: Four Checks, One Verdict

AAE runs every stock through four gates:

| Gate | What It Asks |
|------|-------------|
| **1. Financial Health** | Are margins, cash flows, and returns on capital actually improving — or is this just a temporary upswing? |
| **2. Management Narrative** | Is the management's language evolving from vague promises to concrete execution? Or are they just talking? |
| **3. Smart Money** | Are FIIs, DIIs, and insiders quietly accumulating the stock? |
| **4. Valuation** | Even with all this improvement, is the stock still cheap versus its own history and its peers? |

A stock must clear all four gates to get a high score (80+ = "Institutional Re-Rating Candidate").

### Built-In Safety Nets

AAE is not a blind bull. It has several kill switches:
- **Governance filter**: Promoters pledging too many shares? Auditor resigned? CFO suddenly quit? Immediate rejection.
- **Narrative-vs-reality check**: If management says things are great but cash flows are worsening, the credibility score gets hammered.
- **False Positive Graveyard**: A database of past failures — the system learns from every wrong call.
- **Human-in-the-loop**: AAE is a research co-pilot, not a trading bot. Every thesis requires human sign-off.

### The One-Sentence Summary

> AAE is a **research co-pilot for stock pickers** — it doesn't tell you what to buy, it tells you *which improving companies the crowd hasn't noticed yet*, and backs every claim with data, documents, and historical evidence so you can make the final call yourself.

---

## Platform Architecture

### How AAE Fits Into MRI

```
MRI Platform
├── Technical Layer (MRI Score, Regime, STEE)
│   └── 7-step momentum scoring, swing trade execution, market regime
├── Fundamental Layer (QIF, PRDE)
│   ├── Quality Investor Framework — 7-agent fundamental scoring
│   └── PRDE — Financial fingerprint & deterministic feature engineering ← THIS DOCUMENT
├── Qualitative Layer (QIL)
│   └── GPT-powered narrative analysis, forensic debate
├── Institutional Layer (AAE, PERX)
│   ├── PERX — PE Re-Rating Discovery, lifecycle classification
│   └── AAE — Full event-driven multi-agent research platform ← THIS DOCUMENT
└── Frontend (React/Vite dashboard)
```

### AAE Relationship to PRDE

- **PRDE** (Platform for Re-rating Detection Engine) is the *deterministic financial fingerprint foundation*.
- **AAE** is the *full event-driven multi-agent research platform* built on top of MRI + PRDE.
- The roadmap rule: **Do not build LLM agents until PRDE data foundation is solid.**

---

## Current State (as of 2026-05-23)

### What's Already Built ✅

The AAE V3 forensic pipeline is **live and running**:

| Component | File | Status |
|-----------|------|--------|
| **Governance Kill Switch** | `engine_fundamental/governance_engine.py` | ✅ Live |
| **Sector Engine** | `engine_fundamental/sector_engine.py` | ✅ Live |
| **Ownership Engine** | `engine_fundamental/ownership_engine.py` | ✅ Live |
| **Valuation Engine** | `engine_fundamental/valuation_engine.py` | ✅ Live |
| **Narrative Engine** | `engine_fundamental/narrative_engine.py` | ✅ Live |
| **Market Confirmation** | `engine_fundamental/market_confirmation.py` | ✅ Live |
| **Graveyard Engine** | `engine_fundamental/graveyard_engine.py` | ✅ Live |
| **Forensic Debate (AI)** | `engine_fundamental/forensic_debate.py` | ✅ Live |
| **Master Orchestrator** | `engine_fundamental/aae_orchestrator.py` | ✅ Live (10-layer) |
| **API Endpoints** | `api/aae.py` | ✅ Live |
| **Frontend Console** | `frontend/src/AaeDashboard.tsx` | ✅ Live |
| **Email Reports** | `engine_core/email_service.py` | ✅ Live |
| **Database Tables** | `api/schema.py` (AAE section) | ✅ Live |
| **Bulk Scanning** | `scripts/aae_bulk_scan.py` | ✅ Live |
| **Narrative Bootstrap** | `scripts/aae_narrative_bootstrap.py` | ✅ Live |
| **Quarterly Backfill** | `scripts/aae_quarterly_backfill.py` | ✅ Live |

### What's Missing ❌

The **PRDE financial foundation** (Milestone 0) — the deterministic data pipeline that feeds verifiable numbers into the AAE engines:

| Missing Item | Description |
|-------------|-------------|
| `ensure_prde_tables()` | Function in `api/schema.py` to create PRDE tables |
| `prde_companies` table | Company registry for PRDE universe |
| `prde_financials_annual` table | Annual P&L data |
| `prde_ratios_annual` table | Annual valuation & efficiency ratios |
| `prde_feature_snapshots` table | Deterministic feature storage |
| Seed CSV | Real financial data for 10-20 Indian companies |
| Import script | `scripts/import_prde_financials.py` |
| Verify script | `scripts/verify_prde_import.py` |
| Scoring engine | `engine_core/prde_scoring_engine.py` (Milestone 1) |

> ⚠️ **Critical:** The PRDE feature engine (`engine_core/prde_feature_engine.py`, 392 lines) is already written but cannot run — it references 4 tables and a function that don't exist yet.

---

## The 7 Milestones

### Milestone 0 — PRDE Financial Foundation 🔴 IN PROGRESS

**Purpose:** Lay the concrete slab. Import real financial data, validate it, make it queryable. Everything else depends on this.

**Deliverables:**

1. `ensure_prde_tables()` function in `api/schema.py` creating:
   - `prde_companies` — ticker, name, sector, industry, country, is_active
   - `prde_financials_annual` — revenue, ebitda, pat, roce, capex, employee_cost, total_assets per fiscal year
   - `prde_ratios_annual` — PE, EV/EBITDA, PB, debt/equity per fiscal year
   - `prde_feature_snapshots` — immutable feature JSON with content-addressed hashes

2. Seed data pipeline:
   - `data/prde_financials_seed.csv` — template with all required columns
   - `scripts/fetch_prde_seed_data.py` — fetches real financials from yfinance for 10-20 Indian blue chips
   - `scripts/import_prde_financials.py` — idempotent upsert with `--dry-run` flag
   - `scripts/verify_prde_import.py` — row counts, null checks, year coverage validation

3. Integration test:
   - Dry-run import → validate CSV
   - Real import → verify row counts
   - Re-import → prove idempotency (no duplicates)
   - Generate feature snapshots → confirm stable hashes

**Done criteria:**
- [ ] 4 PRDE tables exist and are queryable
- [ ] 10-20 companies imported with 5+ years of annual data each
- [ ] Feature engine generates snapshots with reproducible hashes
- [ ] Re-running import on same CSV produces zero new rows

---

### Milestone 1 — Deterministic Financial Fingerprint Scoring

**Purpose:** Convert PRDE feature snapshots into transparent, inspectable numeric scores — no AI guesswork, just math.

**Deliverables:**

- `engine_core/prde_scoring_engine.py`

**Score Components (Master Investor Checklist):**

| Dimension | What It Measures | Weight |
|-----------|-----------------|--------|
| Operating Leverage | EBITDA growth vs revenue growth | 20% |
| Capital Efficiency | ROCE trend and level vs WACC | 20% |
| Margin Quality | EBITDA margin expansion + stability | 20% |
| Growth Quality | Revenue/EBITDA/PAT CAGR consistency | 15% |
| Cash Conversion | CFO/PAT, FCF generation | 10% |
| Balance Sheet Health | Debt reduction, leverage stability | 10% |
| Valuation Gap | Current PE vs historical band | 5% |

**Additional Layers:**
- Risk penalty (governance, financial strain, earnings quality flags)
- MRI trend/regime overlay (momentum confirmation)
- Sector-relative normalization

**Persistence:**
- `prde_final_scores` table — score per company per run, with component breakdown
- Score history for trend analysis

**Done criteria:**
- [ ] Seed universe can be ranked without any LLM calls
- [ ] Each score component is individually inspectable
- [ ] Re-running with unchanged input produces identical output
- [ ] Scores persist with run_id for audit trail

---

### Milestone 2 — AAE Event and Document Foundation

**Purpose:** Introduce event-driven inputs (filings, transcripts, presentations) without yet relying on AI agents for final conclusions.

**Deliverables:**

- Schema tables:
  - `aae_documents` — document metadata (type, source, date, company)
  - `aae_document_chunks` — text chunks for retrieval
  - `aae_events` — normalized event objects
  - `aae_event_evidence` — source references linking events to documents

- `scripts/ingest_aae_document.py` — manual document ingestion
- Source evidence storage with audit trail
- Event-to-company mapping

**Done criteria:**
- [ ] A filing or presentation can be ingested and linked to companies
- [ ] Extracted events retain source references (document, page, snippet)
- [ ] Events can be replayed or audited

---

### Milestone 3 — Sourcing and Structural Signal Agents

**Purpose:** Convert document events into the six AAE structural signals using a mix of NLP and AI (GPT-4o-mini).

**The Six Structural Signals:**

| Signal | What It Detects |
|--------|----------------|
| Margin Quality | Structural margin improvement vs cyclical uptick |
| TAM Expansion | New products, geographies, or segments expanding addressable market |
| Backward Integration | Moving upstream in the value chain |
| Forward Integration | Moving closer to end customers |
| Moat Strengthening | Brand, network effects, switching costs, patents |
| Geographic Expansion | New country/region entry with concrete timelines |

**Deliverables:**
- `engine_core/aae_sourcing_agent.py` — document classification, entity extraction, semantic trigger detection
- `engine_core/aae_structural_signal_agent.py` — six-signal vector, structural conviction score (0-100)
- Evidence-linked justifications with source references

**Done criteria:**
- [ ] A company can receive a versioned structural signal state
- [ ] High-conviction alerts fire only when 4+ signals are active above thresholds in a 12-18 month window
- [ ] Every signal is traceable to source documents

---

### Milestone 4 — Macro and Risk Agents

**Purpose:** Add sector/macro context and thesis-break monitoring.

**Deliverables:**

- `engine_core/aae_macro_agent.py`:
  - GDP, inflation, rates, fiscal context
  - Sector macro tailwind/headwind score
  - Market valuation regime estimate
  - Policy event correlation (PLI, tariffs, procurement)

- `engine_core/aae_execution_monitoring_agent.py`:
  - Financial strain detection (EBIT/interest, net debt/EBITDA)
  - Earnings quality monitoring (FCF/PAT deterioration)
  - Working capital blow-up alerts
  - Governance event monitoring
  - Margin compression detection

**Outputs:**
- Sector macro alignment score
- Risk dashboard state (green/amber/red by category)
- Thesis-at-risk alerts with severity and source evidence

**Done criteria:**
- [ ] Macro and risk outputs are stored separately from PRDE financial scores
- [ ] Risk alerts cite source data or source events
- [ ] Thesis-at-risk label fires when multiple persistent red flags accumulate

---

### Milestone 5 — Orchestrator and Re-Rating Candidate Profile

**Purpose:** Combine financial, structural, macro, risk, valuation, and MRI timing overlays into one investable research object. This upgrades the existing `AAEOrchestrator`.

**Deliverables:**

- Re-Rating Candidate Profile schema:
  ```json
  {
    "symbol": "RELIANCE",
    "as_of_date": "2026-05-23",
    "structural_signal_vector": {...},
    "structural_conviction_score": 72,
    "financial_fingerprint": {...},
    "master_checklist_score": 68,
    "operating_leverage_classification": "POSITIVE",
    "macro_alignment_score": 65,
    "risk_state": "GREEN",
    "valuation_context": {...},
    "rerating_probability_score": 74,
    "thesis": {
      "summary": "...",
      "evidence": [...],
      "risks": [...],
      "version": 3
    }
  }
  ```

- Thesis JSON with version history
- Score history table (track every score change)
- Re-rating probability score (0-100)

**Done criteria:**
- [ ] Every ranked candidate can be traced to: feature snapshot → structural evidence → macro/risk state → scoring version
- [ ] Thesis versions are immutable and time-stamped
- [ ] Score history preserves explainability

---

### Milestone 6 — Analyst Console

**Purpose:** Make AAE usable by human analysts with feedback loops.

**Deliverables:**

- Candidate dashboard (ranked list, sortable, filterable)
- Company deep-dive page with:
  - Structural signal timeline
  - Financial fingerprint charts
  - Risk dashboard
  - Valuation context
- Event view (chronological document/event feed per company)
- Analyst feedback workflow:
  - Accept / Reject / Modify thesis
  - Justification required
  - Stored with user, timestamp, and rationale

**Done criteria:**
- [ ] Analysts can review, modify, and audit machine-generated theses
- [ ] Analyst feedback is stored with full audit trail
- [ ] Dashboard loads in under 2 seconds for the seed universe

---

### Milestone 7 — Learning and Calibration

**Purpose:** Improve thresholds and weights using labeled historical re-rating cases. Close the feedback loop.

**Deliverables:**

- Historical case library:
  - Known re-rating successes (e.g., Trent, Varun Beverages, Dixon)
  - Known false positives (cyclical traps, governance implosions, narrative pumps)
  - Labeled with: pre-rerating score, post-event return, time to rerating

- Backtest framework:
  - Walk-forward scoring on historical data
  - Compare score changes against later re-rating outcomes
  - Threshold calibration reports

- Analyst feedback export and analysis
- `aae_false_positive_graveyard` enrichment (already has schema table)

**Done criteria:**
- [ ] Historical wins and misses are reviewable
- [ ] Score changes can be compared against later re-rating outcomes
- [ ] Threshold recommendations are data-backed, not guesswork

---

## Milestone Dependency Graph

```
Milestone 0 (PRDE Foundation)
    └── Milestone 1 (Scoring Engine)
            ├── Milestone 2 (Event/Doc Foundation)
            │       └── Milestone 3 (Structural Signal Agents)
            │               ├── Milestone 4 (Macro/Risk Agents)
            │               │       └── Milestone 5 (Orchestrator Upgrade)
            │               │               ├── Milestone 6 (Analyst Console)
            │               │               └── Milestone 7 (Calibration)
            │               │
            └── (Existing AAE V3 pipeline continues to operate independently)
```

> **Note:** The existing AAE V3 forensic pipeline (governance → sector → ownership → narrative → market → valuation → graveyard → debate) runs in parallel to this roadmap. Milestones 0-1 feed *deterministic financial fingerprints* into the pipeline, making scores more ground-truthed and less dependent on synthetic proxies.

---

## Immediate Next Step

Complete **Milestone 0** — the PRDE data foundation:

```bash
# 1. Schema bootstrap (add ensure_prde_tables to api/schema.py)
# 2. Fetch seed data
python scripts/fetch_prde_seed_data.py --companies 15 --output data/prde_financials_seed.csv

# 3. Validate the CSV
python scripts/import_prde_financials.py data/prde_financials_seed.csv --dry-run

# 4. Import
python scripts/import_prde_financials.py data/prde_financials_seed.csv

# 5. Verify
python scripts/verify_prde_import.py --min-companies 10 --min-years 5

# 6. Generate feature snapshots
python engine_core/prde_feature_engine.py --limit 20 --dry-run
python engine_core/prde_feature_engine.py --limit 20
```

---

## Key Design Principles

1. **Deterministic where possible, AI where necessary.** 80-90% of the scoring is rule-based math. AI is reserved for narrative delta detection, contradiction spotting, and debate synthesis.

2. **Every score is traceable.** From a re-rating probability of 74 → structural signal vector → financial fingerprint → source document → fiscal year row. No black boxes.

3. **Idempotency is non-negotiable.** Re-running any import, feature generation, or scoring step with the same input must produce the same output. All feature snapshots are content-addressed (SHA-256 hash).

4. **Human-in-the-loop.** AAE is an analyst decision-support system, not an execution engine. Every thesis requires human sign-off. AI never autonomously trades.

5. **Learn from failure.** The False Positive Graveyard is not an afterthought — it's a core engine. Every wrong call is categorized and fed back into scoring calibration.
