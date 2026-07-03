# MOSI Automation & Data Richness — Implementation Discussion

**Date:** 23 June 2026
**Session type:** Planning & scoping
**Branch:** `feature/data-richness`
**Status:** DRAFT — awaiting user approval before execution

---

## Executive Summary

This document captures all planning discussions from the 23 June 2026 session between the Lead AI Engineer and the project owner. Three workstreams were scoped:

1. **Data Richness Sprint** — Fix A (backfill missing AAE/QIF for ~109 universe stocks) + Fix D (extend QIF agents to persist per-quarter underlying metrics in JSONB)
2. **MOSI Prompt Cost Analysis** — LLM cost for running the 14-step institutional MOSI framework across the 149-symbol universe
3. **MOSI Automation Feature** — End-to-end "give me a symbol, get a report" automation with document gathering + email delivery

---

## 1. Data Richness Sprint — Current Status

### Context
The Expansion Lens (PE Expansion scorer) surfaced two structural data gaps when the bear/bull debate engine ran on real symbols:

- **QPOWER** (PE rank #2, 84.9) — zero AAE forensic rows, zero QIF fundamental rows. The PE score is built entirely on narrative. The cross-check matrix shows "No data" because the data is missing, not because the data says "no."
- **KirlosEngine** — QIF data exists but only aggregate scores + flags (e.g., "ROCE < WACC"). The underlying numbers (ROCE %, margin trends, sector medians) are discarded after scoring. The bear case argues from a flag instead of specifics.

### Universe Coverage Today
- **63 of 172 stocks** (37%) have financials in `aae_quarterly_financials`
- **109 stocks lack fundamentals entirely** — fixable by running existing `collector.py` + `quarterly_collector.py` (pure yfinance HTTP, no LLM)
- Same 109 also lack AAE rows — fixable by `scripts/aae_bulk_scan.py` (uses LLM, ~$3.30)

### Approved Design Decision
- **Option (c)** — Full quarterly history in JSONB array under `quality_verdicts.agent_details.by_quarter[]` + pre-computed `agent_details.trajectory` summary.
- All changes additive (JSONB column defaults to `'{}'::jsonb`). Old code paths still work.

### Phase Breakdown

| Phase | Description | Time | LLM Cost |
|-------|-------------|------|----------|
| **D1** | Extend QIF 7 agents to return per-quarter detail dicts; update pipeline to compute trajectory summary; schema migration; tests | **~2.5 hrs** | **$0** |
| D2 | Extend `engine_debate/context_pe_expansion.py` to surface new QIF detail fields | ~30 min | $0 |
| D3 | Re-run QIF for 63 covered stocks (populate new JSONB field) | ~20 min | $0 |
| A1 | Audit which universe stocks lack AAE / QIF rows | ~10 min | $0 |
| A.2a | Fetch financials for 109 missing stocks (yfinance HTTP) | ~30 min | $0 |
| A.2b | Compute QIF verdicts for those 109 (pure Python) | ~5 min | $0 |
| A.3 | Run AAE V3 scan for stocks lacking `aae_results_snapshot` rows | ~30–60 min | **~$3.30** |
| A.4 | Verify backfill + regenerate debates for affected stocks | ~30 min | $0 (cached) |
| 5 | Documentation (`Decisions.md`, `Sessions.md`, `Progress.md`) + git commit + push | ~30 min | $0 |
| **Total** | | **~6–7 hrs** | **~$3.30** |

### Cost Correction Notes
- Initial draft of the initiative doc quoted ~$5.00 total. After investigation, the corrected number is **~$3.30**.
- The LLM cost is purely from **Fix A.3** (AAE backfill uses `narrative_engine.py` + `forensic_debate.py` LLM calls).
- QIF (`engine_fundamental/agents.py`) and `engine_fundamental/collector.py` are **pure Python / yfinance HTTP** — no LLM anywhere in the QIF pipeline.

### Phases Remaining (if D1 starts now)
After D1 completes, **8 phases remain**: D2, D3, A1, A2a, A2b, A3, A4, Phase 5.

### Rollout & Verification (Definition of Done)
1. All 149 universe stocks have both AAE and QIF rows
2. `quality_verdicts.agent_details` populated for every stock with QIF
3. KirlosEngine bear case cites specific ROCE, margin, revenue numbers (not just flag)
4. QPOWER bear case no longer says "no data" — all 5 cross-check dimensions populated
5. All 109 existing tests still pass + new tests for JSONB column and context builder
6. PR opened, reviewed, merged to `main`
7. Railway auto-deploys and prod shows the richer debates

---

## 2. MOSI Prompt — Cost Analysis for 149-Symbol Universe

### The MOSI Prompt (Version 2.0)
A 14-step institutional equity analysis framework covering:
1. Company Stage & Growth Cycle
2. Global Trend & Historical Precedent
3. India Macro & Policy Alignment
4. Segment-Level Growth Analysis
5. Quarterly Growth Acceleration Test
6. Margin Expansion: Structural or Cyclical?
7. Operating Leverage Quantification
8A/8B. Financial Health: Quantitative + Qualitative Checks
9. CapEx → ROCE Cycle & Re-Rating Signal
10. Moat, TAM & Competitive Position
11. Narrative vs Financial Reality
12. Valuation Context
13. Risk Matrix
14. Final PE Expansion Verdict

### LLM Cost Per Company (Full Document Upload)

Assuming **GPT-4o-mini** (current project standard for extraction/analysis):

| Input source | Estimated tokens |
|-------------|------------------|
| Prompt template (~14 steps + instructions) | ~3,500 |
| Annual Report (full text) | ~50,000–80,000 |
| 3 Quarterly Earnings Transcripts | ~20,000–40,000 |
| 3 Investor Presentations | ~10,000–20,000 |
| Latest Quarterly Results / Press Release | ~5,000–10,000 |
| **Total input per company** | **~90,000–150,000** |
| **Estimated output per company** | **~15,000–25,000** |

| Model | Per Company | 149 Companies |
|-------|-------------|---------------|
| **GPT-4o-mini** | ~$0.015–0.025 | **~$2.20–$3.70** |
| GPT-4o | ~$0.25–0.40 | **~$37–$60** |
| DeepSeek V3 | ~$0.015–0.025 | **~$2.20–$3.70** |

**Conclusion:** At GPT-4o-mini pricing, the LLM cost for the full 149-symbol universe is **negligible (~$3–4)**. The real constraint is data acquisition and context-window management, not API spend.

### Do We Need Annual Reports and Presentations?

**Short answer: No — for ~70-80% of the MOSI steps.**

#### Steps Already Covered by Existing DB (Zero LLM Cost)

| MOSI Step | What it asks | Existing source | Cost |
|-----------|-------------|-----------------|------|
| 5 — Quarterly acceleration | 6 quarters Rev/EBITDA/PAT growth | `aae_quarterly_financials` | $0 |
| 6 — Margin expansion | 8 quarters OPM/EBITDA margin | `aae_quarterly_financials` + `quality_verdicts` | $0 |
| 7 — Operating leverage | EBITDA Growth % ÷ Revenue Growth % | Computable from quarterly DB | $0 |
| 8A — Financial health (quant) | Revenue CAGR, ROCE, ROE, D/E, FCF | `quality_verdicts` + `aae_quarterly_financials` | $0 |
| 11 — Narrative vs reality | Management claims vs actual numbers | `management_narrative_timeline` + `guidance_verification` + `aae_narrative_intelligence` | Already paid |
| 12 — Valuation | PE, EV/EBITDA, price target | Live price + TTM EPS in `aae_quarterly_financials` | $0 |

#### Where Annual Reports / Presentations Are Actually Needed

| MOSI Step | Why docs help | Can transcripts substitute? |
|-----------|-------------|----------------------------|
| 4 — Segment data | Detailed segment-wise P&L breakdown | Partially — transcripts discuss segments but rarely give exact P&L splits |
| 9 — CapEx plans with timelines | Annual reports have detailed CapEx schedules; presentations have roadmaps | Partially — transcripts mention CapEx but not exact timelines |
| 10 — TAM quantification | Presentations have TAM / SAM / SOM slides | Rarely — transcripts almost never quantify TAM |

**Transcripts are BETTER than annual reports for:**
- Step 11 (narrative vs reality) — Q&A is more candid than prepared disclosures
- Forward guidance, risk acknowledgment, demand outlook

**Investor presentations are BETTER than transcripts for:**
- Step 10 (TAM, competitive position) — presentations have TAM slides
- Strategic roadmap visuals, unit economics, margin target bridges

#### Optimized "MOSI Lite" Using Only Existing Data
- Uses `aae_quarterly_financials`, `quality_verdicts`, `management_narrative_timeline`, `aae_narrative_intelligence`, live prices
- LLM only for Steps 1-3 (macro/policy inference), 9-10 (synthesis from name/sector/transcript), 13-14 (risk matrix + verdict)
- **Cost per company: ~$0.01** (single short GPT-4o-mini call)
- **Cost for 149: ~$1.50**

---

## 3. MOSI Automation Feature — Build Estimate

### User Requirement
> "I give you the company name and you gather all the materials from the web and run and create/email the MOSI report to me"

### Full Automation (Tier 2)
End-to-end: symbol input → web document gathering → text extraction → MOSI LLM run → HTML report → SES email

| Component | What it does | Time |
|-----------|-------------|------|
| `engine_mosi/document_fetcher.py` | Search NSE/BSE for annual reports, investor presentations, earnings releases; download PDFs; extract text; fallback to company IR website | ~2–3 hrs |
| `engine_mosi/orchestrator.py` | Orchestrate fetch → extract → build context → LLM call → parse JSON → build report; handle missing docs gracefully | ~2 hrs |
| `engine_mosi/prompt.py` | Compress 14-step MOSI prompt to use gathered docs + existing DB data | ~1 hr |
| `engine_mosi/report_builder.py` | Convert MOSI JSON into branded HTML email (reuses PERX/AAE patterns) | ~1 hr |
| `api/mosi.py` | `POST /api/mosi/scan/{symbol}` with `BackgroundTasks`; status tracking; SES send | ~1 hr |
| `frontend/src/MosiPage.tsx` | Company name input, progress bar, report preview | ~1 hr |
| Testing & hardening | 5-company smoke test; OCR edge cases; rate limit backoff; graceful "not found" states | ~2 hrs |
| **Total** | | **~10–12 hrs** |

### Existing Modules Reused (No Build Time)
- `engine_guidance/bse_concall_finder.py` — transcript discovery
- `engine_fundamental/quarterly_collector.py` — quarterly financials from yfinance
- `engine_core/email_service.py` — AWS SES delivery
- `engine_perx/report_builder.py` — HTML formatting patterns
- `api/schema.py` — idempotent table creation

### Real Risks (Not Time, But Reliability)

| Risk | Why it matters | Mitigation |
|------|---------------|------------|
| Annual reports are scanned images | ~30-40% of BSE/NSE annual report PDFs are image-based. `pdftotext` returns garbage. | Add Tesseract OCR or cloud Vision API fallback |
| Investor presentations not on NSE | Many mid-caps only publish on IR websites or share with brokerages | Fallback to company IR website scraper |
| NSE/BSE rate limits | Aggressive scraping gets IP-blocked | `requests.Session` with exponential backoff + rotate user-agents |
| Document availability is spotty | Small caps often have no presentation and no transcript | MOSI prompt handles `null` gracefully; falls back to DB-only analysis |

### Pragmatic Recommendation: Tier 1 First, Tier 2 Later

#### Tier 1: "MOSI Lite" — ~3–4 hours
- **No web scraping** for annual reports/presentations
- Uses **existing DB only**: `aae_quarterly_financials`, `quality_verdicts`, `management_narrative_timeline`, `aae_narrative_intelligence`, live prices, governance metrics
- LLM fills Steps 1-4 (macro/policy), 9-10 (TAM/moat inference from name/sector), 13-14 (synthesis)
- Emails a rich report with a note: *"Annual report and investor presentation were not analyzed; upload them via the attach button to upgrade."*
- **Cost per report: ~$0.01** (single GPT-4o-mini call on existing DB text)
- **Reliability: 95%+** because no external scraping

#### Tier 2: "MOSI Deep" — +6 hours on top of Tier 1
- Add annual report + investor presentation fetcher
- OCR for scanned PDFs
- Hybrid prompt merging uploaded docs + DB data
- Auto-falls back to Tier 1 when documents are missing

---

## 4. Decision Points & Next Actions

### Awaiting User Approval

| # | Decision | Options |
|---|----------|---------|
| 1 | **Start Data Richness Sprint?** | Approve → begin Phase D1 immediately |
| 2 | **MOSI automation scope?** | (a) Build Tier 1 only (~3-4 hrs) / (b) Build Tier 1+2 (~10-12 hrs) / (c) Defer |
| 3 | **MOSI model choice?** | GPT-4o-mini (~$0.01/report) vs GPT-4o (~$0.30/report) vs DeepSeek V3 (~$0.01/report) |

### Proposed Next Session Flow
1. **Approve Data Richness Sprint** → Begin Phase D1 (extend QIF agents, ~2.5 hrs)
2. **Approve MOSI Tier 1** → Draft `docs/MOSI_IMPLEMENTATION_PLAN_2026-06-23.md` → build in parallel after D1
3. **Push day's work** → Commit to `feature/data-richness`, open PR, Railway auto-deploy

---

## 5. Notes & References

- Initiative doc: `docs/INITIATIVE_DATA_RICHNESS_2026-06-19.md`
- Embedded Debate FR (deferred): `docs/FEATURE_REQUEST_EMBEDDED_DEBATE_2026-06-19.md`
- Expansion Lens plan: `docs/EXPANSION_LENS_PLAN_2026-06-18.md`
- AAE Integration plan: `docs/AAE_INTEGRATION_PLAN_2026-06-17.md`
- PERX PRD: `docs/Perx PRD.md`
- Current branch: `feature/data-richness`
- Current milestone: Data Richness Sprint (Fix A + Fix D)
- LLM model standard in project: GPT-4o-mini for extraction/analysis, DeepSeek for debate

---

*End of document — awaiting user approval on decision points above.*
