# Initiative — Data Richness Sprint: Fix A (backfill) + Fix D (extend granularity)

**Date:** 2026-06-19
**Status:** DRAFT — awaiting user approval before execution
**Author:** Lead AI Engineer (Kimchi)
**Predecessors:** FeatureRequest `FEATURE_REQUEST_BEAR_BULL_DEBATE_2026-06-19.md`, FeatureRequest `FEATURE_REQUEST_EMBEDDED_DEBATE_2026-06-19.md` (still DRAFT)

---

## TL;DR

The bear vs bull debate engine correctly flagged two structural data gaps in production use:

1. **QPOWER (PE rank #2, 84.9)** has zero AAE forensic data and zero QIF fundamental data. The PE score is built entirely on narrative (transcript keywords + promise extraction). The bear case correctly surfaced this, but the **ranking itself is wrong** — the cross-check matrix says "No data" because the data is missing, not because the data says "no".
2. **KirlosEngine** has QIF data but only aggregate scores + a single flag (`VALUE DESTRUCTION: ROCE < WACC`). The bear case argued from "ROCE < WACC flag" instead of "ROCE 11.2% vs WACC 12.0%, was 13.0% a year ago". The full trajectory was discarded by the QIF agents before persistence.

**Universe coverage today:** 63 of 172 stocks (37%) have financials in `aae_quarterly_financials`. The other 109 lack fundamentals entirely — fixable by running existing `collector.py` + `quarterly_collector.py` (pure yfinance HTTP, no LLM). Same 109 also lack AAE rows — fixable by `scripts/aae_bulk_scan.py` (uses LLM, ~$3.30).

**Two fixes, one sprint:**
- **Fix A** — Backfill AAE + QIF for the 109 universe stocks that lack them. AAE backfill needs LLM (~$3.30). Financials fetch + QIF computation are pure HTTP + Python (no LLM).
- **Fix D** — Extend QIF agents + context builder to surface per-quarter underlying metrics (ROCE, WACC, margin trends, revenue growth, leverage ratios, working capital days, sector medians) in a JSONB array under `quality_verdicts.agent_details.by_quarter[]` + pre-computed `agent_details.trajectory` summary. **User chose option (c) — full quarterly history, not snapshot.**

**Total: ~6-7 hrs wall time, ~$3.30 LLM cost one-time.** Affects how every Expansion Lens report and every debate gets generated going forward.

---

## Why this matters

The user said it directly:

> "people are betting their hard earned money on your opinion, so let that better be good"

When MRI surfaces a "PE Expansion #2" or a "WATCH" verdict, the user is making a real decision based on it. If the underlying data is "No data" or "score 37, no detail", that's not a decision aid — that's noise. Fix A + D together turn the cross-check from "we don't know" into "here's exactly what each engine says, with the numbers to back it up."

This is the difference between:
- **Today:** "Financial Quality 37 (REJECT), ROCE < WACC flag" → user has to trust the flag
- **After:** "Financial Quality 37 (REJECT): ROCE 11.2% vs WACC 14.0%, gap -2.8%, margin compression -340bps YoY, revenue growth 6% vs sector median 28%" → user can verify each number, debate with the model, and decide

---

## The problem in detail

### Problem A — Missing orthogonal data

The PE Expansion ranking scores stocks based on **narrative signal strength** (12 weighted categories from `engine_perx/pe_signals.py:compute_pe_score`). The cross-check matrix then brings in 3 other engines (AAE forensic, QIF financial quality, MRI price action). **But the PE score doesn't gate on whether the cross-check has data to compare against.**

Current state in `perx_pe_scores` (top-15 by `pe_score`):

| Rank | Symbol | PE Score | AAE row? | QIF row? |
|---|---|---|---|---|
| 1 | WAAREEENER | 88.5 | ✅ | ✅ |
| **2** | **QPOWER** | **84.9** | **❌** | **❌** |
| 3 | POLYCAB | 83.6 | ✅ | ✅ |
| 4 | SKIPPER | 83.4 | ✅ | ✅ |
| 5 | LUPIN | 82.6 | ✅ | ✅ |
| 6 | SJS | 82.1 | ✅ | ✅ |
| 7 | QUESS | 81.3 | ✅ | ✅ |
| 8 | SHAILY | 80.2 | ✅ | ✅ |
| 9 | MANORAMA | 80.0 | ✅ | ✅ |
| 10 | CUPID | 80.0 | ✅ | ✅ |
| 11 | SUZLON | 79.6 | ✅ | ✅ |
| 12 | SHAKTIPUMP | 79.4 | ✅ | ✅ |
| 13 | CPPLUS | 79.1 | ✅ | ✅ |
| 14 | FIEMIND | 78.9 | ✅ | ✅ |
| 15 | TMPV | 78.9 | ✅ | ✅ |

QPOWER is the only top-15 stock without ANY orthogonal verification. Its 84.9 PE score is genuinely strong on narrative (12/12 strong categories), but there's no way to know if the rerating thesis holds up against fundamental + forensic checks because those checks haven't run.

### Problem D — Financial data is too thin to extrapolate

Current QIF data flow:
```
aae_quarterly_financials (DB)
        ↓
engine_fundamental/agents.py (7 agents compute scores)
        ↓
quality_verdicts (DB — only the SCORES are persisted, underlying metrics discarded)
        ↓
build_pe_expansion_context (context_payload for LLM)
        ↓
LLM debate (argues from summary metrics + flag)
```

The 7 agents compute rich per-agent detail (revenue growth YoY, margin trajectory, ROCE vs WACC, working capital days, leverage ratios, sector medians) but **only the 0-10 score and one or two flags survive into the persisted verdict**. By the time the context payload reaches the LLM, all the underlying numbers are gone.

**Consequence:** KirlosEngine's debate says "Financial Quality 37, Revenue agent 3/10, ROCE < WACC flag". The LLM can argue from these summaries but cannot extrapolate to specifics. The user reading the debate can't verify the claim against any specific number.

---

## What "good" looks like — before/after

### KirlosEngine — bear case TODAY

> **Financial Quality is 37/100 (REJECT)** with a "VALUE DESTRUCTION: ROCE < WACC" flag

### KirlosEngine — bear case AFTER Fix D (option c: full trajectory)

> **Financial Quality is 37/100 (REJECT), trajectory: DECLINING:**
> - **Revenue trajectory:** 6 quarters observed, growth decelerated from **+18% YoY** (3 years ago) → **+12%** (2 years ago) → **+9%** (1 year ago) → **+6%** (current). Sector median **+27.8%**. 3-year CAGR **+11.3%** vs sector **+24.1%**.
> - **Margin trajectory:** OPM compressed from **11.6%** (3-year avg) → **8.2%** (current), a **-340bps YoY** compression. Sector median **15.0%**. Operating leverage agent: profits lagging revenue growth — EBITDA growing at 0.6x sales pace.
> - **ROCE trajectory:** **11.2%** now, was **13.0%** a year ago, **14.5%** two years ago — **declining -280bps over 2 years**. WACC **12.0%** (hardcoded in `capital_efficiency_agent`). Gap went from **+2.5%** (value creation) to **-0.8%** (value destruction) in 2 years.
> - **Working capital trajectory:** WC days at **72**, was 60 a year ago — **+12 days worsening**. Receivables growing faster than sales in 2 of last 3 quarters.
> - **Leverage:** D/E **0.8**, interest coverage **3.2x** — within tolerable range but trending wrong (D/E was 0.5 two years ago).
>
> **Trajectory verdict:** "Declining" across all 5 measured dimensions. 3-year revenue CAGR is **half the sector median**. Margin compression accelerating. ROCE crossed from value creation to value destruction. The rerating thesis requires margin recovery + ROCE re-expansion above 14%; neither is visible in the trajectory.

The user can now **verify each number, ask follow-up questions, and stress-test the thesis with the actual trajectory data**.

---

## The plan — exact steps, exact times

### Phase D1 — Extend QIF agents to persist per-quarter underlying metrics (~2.5 hrs)

**Goal:** QIF 7 agents compute scores from rich inputs; persist **per-quarter trajectory** so the LLM can argue from full history, not just snapshot. **User decision: option (c) — full quarterly history in JSONB array.**

**Files touched:**
- `engine_fundamental/agents.py` — 7 agents. Each currently returns a 0-10 score + maybe one flag. Extend to return a per-quarter `by_quarter` array (each entry has score + detail metrics for that quarter).
- `migrations/005_qif_agent_details.sql` — `ADD COLUMN IF NOT EXISTS agent_details JSONB DEFAULT '{}'::jsonb`
- `engine_fundamental/pipeline.py` — persist the per-quarter array + compute pre-computed trajectory summary at the top of the JSONB
- Tests: extend `engine_fundamental/test_*.py` to verify per-quarter fields populated + trajectory summary correct

**JSONB shape (per stock, single row in `quality_verdicts`):**
```json
{
  "by_quarter": [
    {
      "year": 2026, "quarter": 1,
      "revenue": 88644770000, "ebitda": null, "opm_pct": null,
      "net_profit": 7727660000,
      "total_assets": 204761900000, "capital_employed": 160780810000,
      "debt": 43981090000, "equity": 120085760000,
      "roce_pct": 6.61, "wacc_pct": 12.0, "gap_pct": -5.39,
      "wc_days": null,
      "scores": {
        "revenue": 3, "margin": 5, "leverage": 6, "wc": 7,
        "roce": 0, "evolution": 5, "translation": 7
      }
    },
    {"year": 2025, "quarter": 4, ...},
    ...
  ],
  "trajectory": {
    "score_trend": "declining",          // computed: improving/stable/declining over available quarters
    "score_change_yoy": -1.5,            // score change vs 4 quarters ago
    "roce_change_yoy_bps": -180,         // ROCE delta vs 4 quarters ago
    "margin_compression_bps_yoy": -340,  // OPM delta vs 4 quarters ago
    "revenue_cagr_3y_pct": 12.3,         // 3-year CAGR if 4+ quarters available
    "quarters_observed": 6
  }
}
```

**Fields captured per quarter per agent:**

| Agent | Detail fields (per quarter) |
|---|---|
| Revenue | `growth_yoy_pct`, `growth_qoq_pct`, `growth_3y_avg_pct`, `sector_median_growth_pct`, `trend` |
| Margin | `opm_current_pct`, `opm_3y_avg_pct`, `sector_median_opm_pct`, `compression_bps_yoy` |
| Leverage | `debt_to_equity`, `interest_coverage`, `current_ratio`, `trend` |
| WC | `wc_days_current`, `wc_days_change_yoy`, `receivable_days`, `inventory_days` |
| ROCE | `roce_pct`, `wacc_pct`, `gap_pct`, `gap_change_yoy` |
| Evolution | `margin_change_3y`, `roce_change_3y`, `revenue_cagr_3y` |
| Translation | `pe_vs_sector_median`, `ev_ebitda_vs_sector_median`, `pb_vs_sector_median` |

**LLM payload size estimate:** ~7 quarters × ~25 fields/quarter = ~175 numbers + 7 score objects + trajectory summary = ~2-3 KB per stock. Well within LLM context budget. The context builder will pass the full `by_quarter` array + `trajectory` summary to the bear/bull prompt — gives the LLM enough material to identify inflection points, accelerating deterioration, recovery stories, etc.

**Time breakdown (revised for option c):**
- Read existing 7 agents and understand current return shape: ~20 min
- Extend each agent to return per-quarter detail dict: ~60 min (slightly more than (a)/(b) due to array handling)
- Update pipeline to compute trajectory summary at persistence time: ~20 min
- Schema migration + update tests: ~25 min
- Smoke run on 3 stocks (POLYCAB, QPOWER, KirlosEngine) and verify: ~15 min
- **Subtotal: ~2.5 hrs**

### Phase D2 — Extend context builder to surface QIF details (~30 min)

**Goal:** `engine_debate/context_pe_expansion.py:build_pe_expansion_context` includes the new financial detail fields.

**Files touched:**
- `engine_debate/context_pe_expansion.py` — read `quality_verdicts.agent_details`, include in `financial_quality` block
- Re-run debate on KirlosEngine to verify the LLM now cites specifics

**Time:** ~30 min

### Phase D3 — Re-run QIF for all 63 stocks with existing financials (~20 min, $0 LLM)

**Goal:** Populate the new `agent_details` field (with per-quarter trajectory) for every stock that already has `aae_quarterly_financials` rows.

**Command:** `python -m engine_fundamental.pipeline --rerun-all --persist-details`
(to be written)

**Time:** ~20 min wall time. **$0 LLM** — QIF is pure Python math reading from existing `aae_quarterly_financials`. No LLM calls anywhere in the pipeline.

(Initial doc version of this phase quoted "$1.50 LLM" — that was wrong. QIF has never used an LLM. Fix A.2 below is the same: $0.)

### Phase A1 — Audit which stocks need backfill (~10 min)

**Goal:** Identify the universe stocks that lack AAE rows, lack QIF rows, or lack both.

**Query:**
```sql
SELECT u.symbol,
  (aae.symbol IS NOT NULL) AS has_aae,
  (qif.symbol IS NOT NULL) AS has_qif
FROM universe_112co u
LEFT JOIN aae_results_snapshot aae ON aae.symbol = u.symbol
LEFT JOIN quality_verdicts qif ON qif.symbol = u.symbol
WHERE u.is_active = TRUE
ORDER BY u.symbol;
```

Expected output: a list of ~70-90 symbols (per current state, QPOWER is one). Most top-15 already have both engines (per the table above), so the bulk of backfill is on lower-ranked stocks.

**Time:** ~10 min (query + verification)

### Phase A2 — Backfill AAE for uncovered stocks (~1-2 hrs wall, ~$2.50 LLM)

**Goal:** Run the AAE V3 8-layer scan for every stock that lacks it.

**Existing scripts to leverage:**
- `scripts/aae_bulk_scan.py` — already exists, scans all symbols. May need a `--only-missing` flag to skip stocks that already have AAE rows.

**Time:** ~1-2 hrs wall time (depends on `narrative_engine.py` LLM rate, which is the slowest layer). Per existing AAE scan cost analysis (~$0.02-0.05 per stock × ~70 stocks = ~$2.50 LLM cost).

### Phase A3 — Backfill QIF for uncovered stocks (~1 hr wall, ~$1.00 LLM)

**Goal:** Same as A2 but for QIF 7-agent computation.

**Existing scripts to leverage:**
- `engine_fundamental/pipeline.py` — already exists. May need a `--only-missing` flag.

**Time:** ~1 hr wall time. ~$1.00 LLM cost (QIF is cheaper than AAE since fewer LLM calls).

### Phase A4 — Verify backfill, regenerate debates for affected stocks (~30 min)

**Goal:** Confirm all universe stocks have data; trigger debate regeneration for any stock whose new data changes the cross-check.

**Steps:**
- Re-run the audit query (A1) — expect all rows to show `has_aae = TRUE` AND `has_qif = TRUE`
- For each symbol whose data changed (e.g., AAE row inserted/updated), the existing debate cache will auto-invalidate on next access because the context_hash will differ
- Smoke test: re-run debate on POLYCAB, KirlosEngine, QPOWER, and verify the bear/bull cases now cite specific numbers (after D) AND have all 5 cross-check dimensions populated (after A)

**Time:** ~30 min

### Phase 5 — Documentation, sessions log, commit, push (~30 min)

- Update `Decisions.md` with new decision(s) for Fix A + Fix D
- Update `Sessions.md` + `Progress.md` with the day's work
- 4-5 commits on `feature/data-richness`, single PR to main

---

## Total time & cost

| Phase | Description | Wall time | LLM cost |
|---|---|---|---|
| D1 | Extend QIF agents + per-quarter array | ~2.5 hrs | $0 |
| D2 | Extend context builder | ~30 min | $0 |
| D3 | Re-run QIF for 63 covered stocks (populate JSONB) | ~20 min | $0 |
| A1 | Audit | ~10 min | $0 |
| A.2a | Fetch financials for 109 missing stocks (yfinance HTTP) | ~30 min | $0 |
| A.2b | Compute QIF verdicts for those 109 (pure Python) | ~5 min | $0 |
| A.3 | Run AAE for stocks lacking `aae_results_snapshot` rows | ~30-60 min | ~$3.30 |
| A.4 | Verify + regenerate debates for changed contexts | ~30 min | $0 (cached) |
| 5 | Docs + commit | ~30 min | $0 |
| **Total** | | **~6-7 hrs** | **~$3.30** |

> **Cost correction vs initial draft:** First version of this doc quoted ~$5.00 total. After investigation, the corrected number is ~$3.30. The LLM cost is purely from Fix A.3 (AAE backfill uses `narrative_engine.py` + `forensic_debate.py`). QIF (`engine_fundamental/agents.py`) and `engine_fundamental/collector.py` are pure Python / yfinance HTTP — no LLM anywhere.

This is a **one-time** investment. After completion:
- Every Expansion Lens report has real cross-check data (5/5 dimensions populated) for the 109 currently-uncovered stocks
- Every debate cites specific numbers + per-quarter trajectory (ROCE 11.2%, was 13.0% a year ago, declining -180bps/year) instead of summary flags
- The ranking genuinely reflects a corroborated thesis, not narrative alone

---

## Risk analysis

| Risk | Likelihood | Mitigation |
|---|---|---|
| Re-running QIF shifts rankings | High | Sort orders will change. Document expected shift in this doc. Communicate in Sessions.md. |
| AAE backfill hits rate limits | Medium | Add `--rate-limit-ms 1000` to the runner script. Resume on failure. |
| New JSONB column bloats row size | Low | Postgres handles JSONB fine; estimate ~2-3 KB per row × 149 stocks = ~500 KB total. Negligible. |
| Some stocks genuinely lack data | Medium | QPOWER has 6 transcripts but never had AAE run — likely all stocks have *some* data, just not all engines. If a stock truly lacks fundamentals, document it explicitly in the verdict. |
| Old debate cache becomes stale | Low | Auto-invalidates because context_hash includes the new fields. Re-running debate will fetch fresh. |

---

## Rollout & verification

### Definition of "done"

1. ✅ All 149 universe stocks have both AAE and QIF rows
2. ✅ `quality_verdicts.agent_details` is populated for every stock with QIF
3. ✅ KirlosEngine bear case cites specific ROCE, margin, revenue numbers (not just flag)
4. ✅ QPOWER bear case no longer says "no data" — all 5 cross-check dimensions populated
5. ✅ All 109 existing tests still pass + new tests for the JSONB column and context builder
6. ✅ PR opened, reviewed, merged to main
7. ✅ Railway auto-deploys and prod shows the richer debates

### Rollback

All changes are additive:
- New `agent_details` JSONB column defaults to `'{}'::jsonb` — old code paths still work
- Backfill is a one-shot; doesn't modify the scoring algorithm
- Context builder falls back to summary metrics if detail dict is empty

If something breaks, revert the PR, the data stays in the JSONB column (harmless).

---

## Open questions for user (defaults proposed)

1. **Schema design: columns vs JSONB for agent details?**
   - Default: **JSONB** (`agent_details JSONB`). Reasoning: easier to extend, single place to read, queryable in Postgres. **RESOLVED — user picked option (c): full quarterly history in JSONB array under `agent_details.by_quarter[]` + pre-computed `agent_details.trajectory` summary.**

2. **Backfill order: top-N first, or all at once?**
   - Default: **all at once** — the existing AAE bulk scan handles batching + rate limits. If it takes too long, we can split into top-30 + rest later.

3. **What to do with stocks that genuinely can't be backfilled (e.g., no fundamentals data available)?**
   - Default: **leave them with `has_data: False`** in the credibility block. The debate will show "No data available" gracefully. Don't artificially penalize the PE score — that would be Fix B (which we deferred).

4. **Should we run a "rerun-all-debates" pass after backfill, or let cache invalidate naturally?**
   - Default: **let cache invalidate naturally**. Old cached debates become stale on next view (the context_hash will differ), and the new debate gets generated. No need to wipe the table — fresh debates are auto-generated on next click.

5. **Trajectory computation cost?** Computing the `trajectory` summary at persistence time requires looping through the by_quarter array. Cost is O(n_quarters × n_agents) ≈ 50 operations per stock — trivial. No concern.

---

**END OF INITIATIVE — Awaiting user approval before execution.**

Approval = the user signs off on:
- The scope (Fix A + D together)
- The time estimate (~6-7 hrs)
- The cost estimate (~$5 LLM)
- The four open question defaults above

Once approved, work begins next session.
