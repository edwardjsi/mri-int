# Expansion Lens Cross-Check — Execution Plan (User-Friendly Labels)

**Date:** 2026-06-18
**Owner:** Immanuel Santosh
**Status:** Approved
**Predecessor:** `docs/EXPANSION_LENS_PLAN_2026-06-18.md`, commit `104a0ba`
**Scope choice:** Full — three independent checks + an agreement summary

> **User-facing language note:** this plan deliberately uses plain-English labels everywhere instead of internal engine names (AAE / QIF / MRI / etc.). The backend still queries the same DB tables; only the labels the reader sees change. After implementation, when you click "Expansion Lens" the report will say **"Independent Check"** and **"Financial Quality"** and **"Price Action"** — not the internal names.

---

## Goal

Surface **what management said vs what the data shows**, across three independent checks, in one report. Turns the report from a transcript-derived narrative score into a verifiable institutional audit — but written for humans, not for a research desk.

The three checks we already have data for:

| Reader sees this in the report | What it actually is (internal name) | Source data |
|---|---|---|
| **Independent Check** — 47/100, with a list of the cross-checker's concerns in plain English | The 8-layer forensic audit (AAE) — cross-references management narrative against the financials, sector, ownership, valuation | `aae_results_snapshot` |
| **Financial Quality** — Strong / Mixed / Weak, with 7 sub-scores (revenue, margins, etc.) | The 7-agent fundamental quality verdict (QIF) — revenue, margin, leverage, working capital, ROCE, business evolution, financial translation | `quality_verdicts` |
| **Price Action** — Strong / Mixed / Weak, with the 7 technical conditions | The 7-step MRI technical momentum score — EMA cross, slope, 6-month high, volume, relative strength, breakout, price quality | `stock_scores` |

Plus a **"Where the Signals Agree"** summary at the bottom that compares all three against each other and against the PE Expansion score, on these 5 dimensions:

1. **Margins** — PE narrative says strong vs Financial Quality says margin = X/10
2. **Growth** — PE narrative says revenue/capacity story vs Financial Quality says revenue = X/10
3. **Overall Quality** — PE score vs Independent Check vs Financial Quality (all 0-100)
4. **Momentum** — PE score vs Price Action score
5. **Management Credibility** — PE credibility vs Independent Check's verdict

Each dimension ends with a plain-English verdict: **"All three agree"** / **"Two out of three say yes"** / **"Split"** / **"Mixed"** / **"No data"**.

### What this gives you (POLYCAB, current data)

The user will see something like:

> **INDEPENDENT CHECK** — 47/100 — Mixed signals
> The cross-checker flags: "Master Checklist score 50/100", "Moderate tailwind for Electrical Infrastructure sector"
>
> **FINANCIAL QUALITY** — Strong (89/100) — HIGH_QUALITY
> Revenue 10/10 · Margins 10/10 · Leverage 3/10 · Working capital 8/10 · ROCE 10/10 · Evolution 8/10
>
> **PRICE ACTION** — Holding up (80/100)
> 5 of 7 momentum signals on. Trend positive but no fresh breakout. CONSOLIDATING.
>
> **WHERE THE SIGNALS AGREE**
> - Margins: Narrative + Financial Quality agree (both strong)
> - Quality: Split — Financial Quality is high (89), PE is high (84), but Independent Check is low (47)
> - Momentum: Narrative and Price Action agree (both ~80)
> - Credibility: Mixed — PE credibility at 73%, Independent Check notes weak fundamentals check

That's the story: **"Management is talking a big game, the financials back it up, but the independent cross-check is cautious, and price hasn't broken out yet."** Institutional thesis in one paragraph.

## Verified data availability

| Reader-facing label | POLYCAB example | Source table |
|---|---|---|
| **PE Expansion** (this report, current) | 83.6 / Strong | `perx_pe_scores` |
| **Independent Check** | 47/100 · "Master Checklist 50/100" · "MODERATE TAILWIND" | `aae_results_snapshot` |
| **Financial Quality** | 89/100 · HIGH_QUALITY · revenue=10 margin=10 leverage=3 wc=8 roce=10 evolution=8 | `quality_verdicts` |
| **Price Action** | 80/100 · 5/7 conditions pass · CONSOLIDATING | `stock_scores` |

The story: **narrative hot, fundamentals strong, independent check cautious, technicals mixed** → "high quality but momentum slowing" thesis.

## Constraints

1. **No new schema, no new dependencies.** Reuse existing tables. Reuse existing `boto3`, `psycopg2`, React.
2. **Read-only on the other engines.** Expansion Lens must NOT mutate Independent Check / Financial Quality / Price Action data — only read it.
3. **Graceful when data missing.** If a symbol has no row in any of the three, render "no data" placeholder, don't crash.
4. **Email size budget.** Current email is ~60 KB after the credibility strip. Stay under 100 KB to avoid Gmail preview truncation.
5. **Same data shape on web and email.** Both render from the same `PeReport` dict. Backend is the single source of truth.
6. **No new tests in this round.** Pure additive feature; existing 77/77 tests must still pass.
7. **User-facing language.** No "AAE" / "QIF" / "MRI" labels in the rendered output. Use the plain-English labels from the goal section. Internal comments and field names in code can keep their internal names.

## Chunks (4 ordered units)

### Chunk 1 — Backend data fetchers (engine_perx/pe_signals.py)

**Scope:**

Three new helpers, all defensive (no crash on missing data, return None on empty):

- `_fetch_independent_check(symbol)` — read `aae_results_snapshot` most-recent row for the symbol. Returns `{master_score, sector, reasons: [...], updated_at}` or None.
- `_fetch_financial_quality(symbol)` — read `quality_verdicts` most-recent row. Returns `{score, category, agents: {revenue, margin, leverage, wc, roce, evolution, translation}, flags: [...]}` or None.
- `_fetch_price_action(symbol)` — read `stock_scores` most-recent row. Returns `{total_score, conditions: {ema_50_200, ema_200_slope, six_m_high, volume, rs, breakout_10d, price_quality}, breakout_state}` or None.

One helper for the cross-check logic:

- `_build_cross_check(pe_breakdown, pe_score, pe_credibility, indep, fin, price)` — returns a list of `{dimension, pe_view, indep_view, fin_view, price_view, alignment: 'all_agree' | 'mostly_agree' | 'split' | 'no_data'}` rows. Dimensions covered:
  - **Margins**: PE `MARGIN_EXPANSION` strength ≥ 3 vs Financial Quality `margin_score` ≥ 7
  - **Growth**: PE `REVENUE_VISIBILITY` + `CAPACITY_EXPANSION` avg ≥ 3 vs Financial Quality `revenue_score` ≥ 7
  - **Quality**: PE overall score vs Financial Quality `score` vs Independent Check `master_score`
  - **Momentum**: PE overall score vs Price Action `total_score`
  - **Credibility**: PE credibility vs Independent Check notes

Wire all four into `build_pe_expansion_report()` as new top-level fields.

**Depends On:** nothing.

**Accept When:** Build report for POLYCAB returns all 3 dicts + cross_check list of 5 dimensions; unknown symbol returns None + empty cross_check; `ast.parse` clean.

### Chunk 2 — Email renderer (api/pe_expansion.py)

Five new email sections, all plain-English labels. See "Goal" section above for shape. `curl /pe-expansion/email/preview/POLYCAB` returns HTML containing all 5 sections; size under 100 KB; no "AAE"/"QIF"/"MRI" strings.

### Chunk 3 — Web UI (frontend/src/PeExpansionReport.tsx)

Type updates + matching render of all 5 sections inside the IIFE, between existing sections. `npx tsc -b` + `npm run build` clean; no regressions; no jargon labels in rendered DOM.

### Chunk 4 — Verify + commit + push

`pytest` 77/77; live curl greps for new section names + greps that jargon is absent; commit + push.

## Verification Strategy

| Check | Expected |
|---|---|
| `python3 -c "import ast; ast.parse(...)"` | exit 0 |
| `npx tsc -b` | "No errors found" |
| `npm run build` | 0 errors |
| `pytest` | 77/77 pass |
| Email contains "Independent Check" / "Financial Quality" / "Price Action" / "Where the Signals Agree" | all True |
| Email contains "AAE" / "QIF" / "MRI" | all False |
| Live API contains "Where the Signals Agree" | ≥ 1 |

## Decision Log

| # | Decision | Rationale |
|---|---|---|
| 1 | Read-only on the three checks | Expansion Lens is a presentation surface, not an analysis engine |
| 2 | Graceful "no data" placeholders | 149-symbol universe — some won't have all 3 populated |
| 3 | Single cross-check helper | DRY — same alignment logic across all renderers |
| 4 | Pre-defined thresholds (≥7 green, etc.) | Avoid making the user guess "agreement" |
| 5 | Email size budget: 100 KB | Gmail truncates previews above 102 KB |
| 6 | New plan doc per feature, dated | Matches existing convention |
| 7 | No new tests in this round | Pure additive; test additions can follow |
| 8 | Internal naming in code unchanged | DB tables keep their names; only rendered labels change |
| 9 | Plain-English `alignment` values | "all_agree" / "mostly_agree" / "split" / "mixed" / "no_data" — UI translates to readable strings |

## Risks

| Risk | Mitigation |
|---|---|
| `aae_results_snapshot` row missing | Graceful placeholder |
| `quality_verdicts` row missing | Graceful placeholder |
| Email exceeds 100 KB | Move AAE reasons to web-only if over budget |
| `quality_verdicts.translation_score` may not exist | Helper reads what exists; missing agents render as "—" |
| Cross-check thresholds don't match user intuition | Class-level constants, easy to tune |

## Out of Scope (deferred)

- "Recompute other engines" button — read-only constraint
- Real-time cross-check updates as scores change — page rebuilds on load anyway
- Sector-level cross-check (company vs sector median)
- Detailed 8-layer Independent Check breakdown — headline + reasons only
- Historical cross-check trajectory

## Estimated effort

| Chunk | Time |
|---|---|
| Chunk 1 — Backend | 45 min |
| Chunk 2 — Email | 60 min |
| Chunk 3 — Web UI | 75 min |
| Chunk 4 — Verify + commit + push | 15 min |
| **Total** | **~3.25 hrs** |

## Sign-off

Approved and executing.
