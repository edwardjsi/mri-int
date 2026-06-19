# Initiative — Data Richness Sprint: Fix A (backfill) + Fix D (extend granularity)

**Date:** 2026-06-19
**Status:** DRAFT — awaiting user approval before execution
**Author:** Lead AI Engineer (Kimchi)
**Predecessors:** FeatureRequest `FEATURE_REQUEST_BEAR_BULL_DEBATE_2026-06-19.md`, FeatureRequest `FEATURE_REQUEST_EMBEDDED_DEBATE_2026-06-19.md` (still DRAFT)

---

## TL;DR

The bear vs bull debate engine correctly flagged two structural data gaps in production use:

1. **QPOWER (PE rank #2, 84.9)** has zero AAE forensic data and zero QIF fundamental data. The PE score is built entirely on narrative (transcript keywords + promise extraction). The bear case correctly surfaced this, but the **ranking itself is wrong** — the cross-check matrix says "No data" because the data is missing, not because the data says "no".
2. **KirlosEngine** has QIF data but only aggregate scores + a single flag (`VALUE DESTRUCTION: ROCE < WACC`). The bear case argued from "ROCE < WACC flag" instead of "ROCE 11.2% vs WACC 14.0%, gap widened from -0.8% to -2.8% over 6 quarters". Not extrapolable.

**Two fixes, one sprint:**
- **Fix A** — Backfill AAE + QIF for universe stocks that lack them (~149 stocks × 2 engines)
- **Fix D** — Extend QIF agents + context builder to surface underlying financial metrics (ROCE, WACC, margin trends, revenue growth, leverage ratios, working capital days, sector medians)

**Total: ~6 hours wall time, ~$5 LLM cost one-time.** Affects how every Expansion Lens report and every debate gets generated going forward.

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

### KirlosEngine — bear case AFTER Fix D

> **Financial Quality is 37/100 (REJECT):**
> - Revenue agent 3/10: revenue grew **6.1% YoY** vs sector median **27.8%**, decelerating for **4 consecutive quarters**
> - Margin agent 5/10: OPM compressed **340bps YoY** to **8.2%**, vs sector median **15.0%** and 3-year company average **11.6%**
> - ROCE agent 2/10: ROCE **11.2%** vs WACC **14.0%**, gap **-2.8%** (widened from **-0.8%** one year ago)
> - Working capital: WC days at **72** (up from 60 one year ago)
> - Leverage: D/E **0.8**, interest coverage **3.2x** — within tolerable range but trending wrong

The conclusion is the same. The user can now **verify each number, ask follow-up questions, and stress-test the thesis**.

---

## The plan — exact steps, exact times

### Phase D1 — Extend QIF agents to persist underlying metrics (~2 hrs)

**Goal:** QIF 7 agents compute scores from rich inputs; persist both the score AND the inputs that drove it.

**Files touched:**
- `engine_fundamental/agents.py` — 7 agents (Revenue, Margin, Leverage, WC, ROCE, Evolution, Translation). Each currently returns a 0-10 score + maybe one flag. Extend to also return a `detail` dict of underlying numbers.
- `migrations/005_qif_agent_details.sql` — ADD columns to `quality_verdicts` (or use a single JSONB `agent_details` column for cleanliness)
- `engine_fundamental/pipeline.py` — pass through the detail dict when persisting
- Tests: extend `engine_fundamental/test_*.py` to verify detail fields are populated

**Per-agent fields to capture:**

| Agent | Detail fields |
|---|---|
| Revenue | `growth_yoy_pct`, `growth_qoq_pct`, `growth_3y_avg_pct`, `sector_median_growth_pct`, `trend` (accelerating/decelerating/stable) |
| Margin | `opm_current_pct`, `opm_3y_avg_pct`, `sector_median_opm_pct`, `compression_bps_yoy` |
| Leverage | `debt_to_equity`, `interest_coverage`, `current_ratio`, `trend` |
| WC | `wc_days_current`, `wc_days_change_yoy`, `receivable_days`, `inventory_days` |
| ROCE | `roce_pct`, `wacc_pct`, `gap_pct`, `gap_change_yoy` |
| Evolution | `margin_change_3y`, `roce_change_3y`, `revenue_cagr_3y` |
| Translation | `pe_vs_sector_median`, `ev_ebitda_vs_sector_median`, `pb_vs_sector_median` |

**Decision: columns vs JSONB.** Recommendation: **single `agent_details JSONB` column**. Reasoning:
- Easier to extend (add fields without migrations)
- Easier to read (one place for all 7 agents' details)
- Postgres-native, queryable
- Schema migration is `ADD COLUMN IF NOT EXISTS agent_details JSONB DEFAULT '{}'::jsonb`

**Time breakdown:**
- Read existing 7 agents and understand current return shape: ~20 min
- Extend each agent to return detail dict: ~45 min
- Update pipeline to persist + add migration: ~20 min
- Update tests: ~20 min
- Smoke run on 3 stocks (POLYCAB, QPOWER, KirlosEngine) and verify: ~15 min
- **Subtotal: ~2 hrs**

### Phase D2 — Extend context builder to surface QIF details (~30 min)

**Goal:** `engine_debate/context_pe_expansion.py:build_pe_expansion_context` includes the new financial detail fields.

**Files touched:**
- `engine_debate/context_pe_expansion.py` — read `quality_verdicts.agent_details`, include in `financial_quality` block
- Re-run debate on KirlosEngine to verify the LLM now cites specifics

**Time:** ~30 min

### Phase D3 — Re-run QIF for all 149 universe stocks (~1 hr wall, ~$1.50 LLM)

**Goal:** Populate the new `agent_details` field for every stock that already has QIF data.

**Command:** `python -m engine_fundamental.pipeline --rerun-all --persist-details`
(to be written)

**Time:** ~1 hr wall time (depends on Yahoo Finance rate limits), ~$1.50 in DeepSeek/OpenAI cost

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
| D1 | Extend QIF agents | ~2 hrs | $0 |
| D2 | Extend context builder | ~30 min | $0 |
| D3 | Re-run QIF for 149 stocks | ~1 hr | ~$1.50 |
| A1 | Audit | ~10 min | $0 |
| A2 | Backfill AAE | ~1-2 hrs | ~$2.50 |
| A3 | Backfill QIF | ~1 hr | ~$1.00 |
| A4 | Verify + regenerate debates | ~30 min | $0 (cached) |
| 5 | Docs + commit | ~30 min | $0 |
| **Total** | | **~6-7 hrs** | **~$5.00** |

This is a **one-time** investment. After completion:
- Every Expansion Lens report has real cross-check data (5/5 dimensions populated)
- Every debate cites specific numbers (ROCE, margin trends, revenue growth) instead of summary flags
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
   - Default: **JSONB** (`agent_details JSONB`). Reasoning: easier to extend, single place to read, queryable in Postgres.

2. **Backfill order: top-N first, or all at once?**
   - Default: **all at once** — the existing AAE bulk scan handles batching + rate limits. If it takes too long, we can split into top-30 + rest later.

3. **What to do with stocks that genuinely can't be backfilled (e.g., no fundamentals data available)?**
   - Default: **leave them with `has_data: False`** in the credibility block. The debate will show "No data available" gracefully. Don't artificially penalize the PE score — that would be Fix B (which we deferred).

4. **Should we run a "rerun-all-debates" pass after backfill, or let cache invalidate naturally?**
   - Default: **let cache invalidate naturally**. Old cached debates become stale on next view (the context_hash will differ), and the new debate gets generated. No need to wipe the table — fresh debates are auto-generated on next click.

---

**END OF INITIATIVE — Awaiting user approval before execution.**

Approval = the user signs off on:
- The scope (Fix A + D together)
- The time estimate (~6-7 hrs)
- The cost estimate (~$5 LLM)
- The four open question defaults above

Once approved, work begins next session.
