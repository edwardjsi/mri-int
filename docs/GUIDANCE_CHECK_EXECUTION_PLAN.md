# GuidanceCheck — Execution Plan
## Feature Branch: `feature/guidance-check`
## Date: 2026-05-28

---

## What We're Building

**GuidanceCheck** — Management Credibility Tracking Engine for top 100 NSE stocks.

A wedge product inside MRI that:
1. Finds concall PDFs from BSE corporate filings (via screener.in)
2. Extracts forward-looking management statements via GPT-4o-mini
3. Verifies promises against quarterly financial results
4. Computes aggregate management credibility scores

---

## Why This Approach

- **No new ingestion infrastructure** — reuses `aae_transcripts`, `aae_quarterly_financials`, `TranscriptCollector`
- **No pipeline disruption** — all new code in `engine_guidance/`, isolated module
- **No API registration until ready** — `api/main.py` untouched
- **Idempotent schema** — `CREATE TABLE IF NOT EXISTS`
- **Feature branch** — GitHub Actions only triggers on `main` push

---

## Files Created

| # | File | Purpose | Status |
|---|------|---------|--------|
| 1 | `engine_guidance/__init__.py` | Package init | done |
| 2 | `engine_guidance/bse_concall_finder.py` | Screener.in -> BSE PDF -> text -> aae_transcripts | done |
| 3 | `engine_guidance/guidance_extractor.py` | GPT-4o-mini extracts forward-looking statements | done |
| 4 | `engine_guidance/guidance_verifier.py` | Check promises vs aae_quarterly_financials | done |
| 5 | `engine_guidance/credibility_scorer.py` | Aggregate credibility per management team | done |
| 6 | `scripts/test_guidance_check.py` | Standalone dry-run test | pending |
| 7 | `scripts/show_guidance.py` | Display extracted guidance for a symbol | done |
| 8 | `scripts/show_verification.py` | Display verification results | done |
| 9 | `scripts/sync_guidance_schema.py` | One-shot schema sync | done |

## Files Modified

| # | File | Change | Status |
|---|------|--------|--------|
| 10 | `api/schema.py` | Added `ensure_guidance_tables()` with 4 new tables | done |

## New DB Tables

| Table | Purpose |
|-------|---------|
| `management_guidance` | Forward-looking statements extracted from transcripts |
| `guidance_verification` | Actual outcomes vs guidance promises |
| `management_credibility_scores` | Aggregate credibility per company |
| `user_thesis` | Why user bought, key assumptions, thesis break conditions |

---

## Test Results (May 28, 2026)

### Phase 1: Concall Discovery
- Screener.in -> BSE PDF -> pdftotext pipeline verified
- TCS: 20 transcripts found, 68K chars extracted per transcript
- RELIANCE: 45 transcripts found
- Speed: ~1.7s per transcript

### Phase 2: GPT Extraction
- GPT-4o-mini prompt tuned: extracts forward-looking statements, skips current-state
- TCS: 3 statements from 2 transcripts
- RELIANCE: 6 statements from 2 transcripts

### Phase 3: Verification
- MAPPING table maps guidance types to quarterly financial columns
- Verifiable types: MARGIN, CAPEX, DEBT_REDUCTION, WORKING_CAPITAL
- TCS/RELIANCE: mostly qualitative — correct result for large-caps

### Key Finding
Most top Indian companies give directional, not specific guidance.
The credibility score becomes meaningful after 4+ quarters of data
on companies that make specific numeric promises (common in mid-caps).

---

## Next Steps

1. Expanded coverage: Run pipeline on mid-caps with quarterly data
2. Verification expansion: Add dividend verification
3. API layer: `api/guidance.py` FastAPI router
4. Frontend: `GuidanceCheck.tsx` single-screen dashboard
5. Thesis tracking: User thesis registration and conviction scoring (v2)

---

## Branch Strategy
- Work on `feature/guidance-check`
- Merge to `main` only after API + frontend complete
- Schema changes are idempotent — safe to deploy anytime

---

## Cost

| Item | Cost |
|------|------|
| GPT-4o-mini extraction | ~$0.00015 per transcript |
| 100 stocks x 4 quarters | ~$0.06 total |
| Quarterly ongoing | ~$0.015/quarter |
