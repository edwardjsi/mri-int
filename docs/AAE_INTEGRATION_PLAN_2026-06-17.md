# AAE × Management Integrity Integration — Execution Plan
**Date:** 2026-06-17
**Owner:** Kimchi (with Immanuel's approval)
**Source:** User request from 2026-06-16 — "marry these results into [AAE] so the report goes with numbers + managerial integrity verified thru transcripts"

## Goal
Combine the existing AAE V3 10-layer numerical engine with the new
narrative-tracer credibility engine so a single symbol report shows:
- **Numbers** (sector delta, ownership, valuation, market confirmation, etc.)
- **Managerial integrity** (cross-transcript promise tracking with verdict flip detection)

## Background — what's broken today

**AAE Layer 4 (Narrative):** Sends ONE latest transcript to GPT-4o-mini asking
for sentiment/themes/divergence. The AI has **zero context** about what
management said in prior quarters. So a bullishly-written transcript from
a manager who has missed 3 of their last 5 promises scores the same as
one from a manager with a perfect track record.

**AAE Layer 7 (Graveyard):** Purely reactive. Only penalizes symbols someone
*manually* added to the graveyard table. No pattern detection.

**AAE Layers 9-10 (Bear/Bull Debate):** AI agents debate with: symbol, master
score, sector, financial delta, narrative summary, valuation, market
confirmation. **No management track record.** The bear case can argue
"valuations are stretched" but can't say "management has missed 3 of 5
promises" because that data isn't piped in.

## Phase 1 — Layer 4 enhancement (~1 hr)

**File:** `engine_fundamental/narrative_engine.py`

**Change:** Before calling OpenAI, fetch credibility context from
`management_credibility_scores` + recent timeline. Inject into the prompt.

**New prompt structure:**
```
Analyze the following earnings call transcript for {symbol}.
Financial Inflections Detected: {financial_deltas}

Management Track Record (verified across 4 transcripts):
  Credibility: 80.4/100 (ADD ZONE)
  Promise timeline: 5 FULFILLED, 7 ON_TRACK, 1 REVISED_UP, 0 MISSED
  Trend: STABLE
  Verdict flips: 0 in last 4 quarters
  Recent specific promises (verbatim from transcripts):
    • "AUM target INR55,000 cr by FY28" — REVISED_UP (upgraded from INR50,000)
    • "100 branches by FY27" — ON_TRACK (98 added in latest quarter)
    • "NIM 6.5-7%" — ON_TRACK (currently 6.9%)

Extract: sentiment, themes, divergence, ceo_confidence, narrative_delta,
summary + management_credibility_assessment (TRUSTED | NEUTRAL | DISTRUSTED)
```

**Cost:** $0 extra (same prompt size, just structured).
**Value:** HIGH. AI gets multi-quarter context for free.
**Risk:** Low. If `management_credibility_scores` is empty for a symbol, fall back to current behavior.

**Done when:**
- [ ] `narrative_engine.py` fetches credibility + recent timeline
- [ ] Prompt includes track-record section
- [ ] `narrative_summary` is passed to AAE orchestrator with the new assessment
- [ ] Tested on CGCL (high credibility) and EIHAHOTELS (THESIS BROKEN)

## Phase 2 — Layer 7 enhancement (~30 min)

**File:** `engine_fundamental/graveyard_engine.py`

**Change:** Auto-detect credibility collapse. Currently only penalizes
manually-buried symbols.

**New logic:**
```python
def evaluate_penalty(self):
    # NEW: Read credibility data
    cred = fetch_credibility(self.symbol)

    # Rule 1: Auto-bury trigger (4+ consecutive misses + score < 40)
    if cred and cred['consecutive_miss_quarters'] >= 4 and cred['score'] < 40:
        # Also write to aae_graveyard so the burial is permanent
        self.bury_symbol(self.symbol,
            reason=f"Auto-buried: {cred['consecutive_miss_quarters']}Q miss streak + {cred['score']:.0f}/100 credibility",
            score=cred['score'])
        return {"penalty": 30, "reason": f"AUTO-BURIED: {cred['consecutive_miss_quarters']} consecutive missed quarters, credibility {cred['score']:.0f}/100"}

    # Rule 2: Soft penalty for lag streaks (2-3 consecutive misses)
    if cred and cred['consecutive_miss_quarters'] >= 2:
        return {"penalty": 10, "reason":
                f"Credibility warning: {cred['consecutive_miss_quarters']} consecutive missed quarters (lag score {cred['lag_score']:.0f})"}

    # Rule 3: Manual burial override (existing behavior)
    burial = self.check_burial_status()
    if burial is not None:
        return {"penalty": 30, "reason": f"Manually buried: {burial['reason_for_death']}"}

    return {"penalty": 0, "reason": None}
```

**Value:** HIGH. Proactive risk detection. EIHAHOTELS would auto-flag with THESIS BROKEN penalty; ASHOKA with 4Q lag gets -10 soft penalty.

**Done when:**
- [ ] Auto-bury rule implemented
- [ ] Soft-penalty rule implemented
- [ ] Manual burial rule still works (backward compat)
- [ ] Tested on EIHAHOTELS (should auto-flag)

## Phase 3 — Layers 9-10 enhancement (~30 min)

**File:** `engine_fundamental/aae_orchestrator.py`

**Change:** Add `management_integrity` to the `ai_context` dict passed to
bear/bull debate agents.

**New ai_context structure:**
```python
cred = fetch_credibility_summary(self.symbol)  # lightweight summary
ai_context = {
    "symbol": ..., "master_score": ..., "sector": ...,
    "financial_delta": ..., "narrative_summary": ...,
    "valuation": ..., "market_confirmation": ...,
    # NEW
    "management_integrity": {
        "credibility_score": cred['score'],
        "verdict": cred['current_verdict'],
        "trend": cred['trend'],
        "promise_summary": cred['counts'],   # FULFILLED/ON_TRACK/etc
        "consecutive_miss_quarters": cred['consecutive_miss_quarters'],
        "verdict_flipped_recently": cred['verdict_flipped'],
        "credibility_assessment": narrative_result['credibility_assessment']  # from Phase 1
    }
}
```

**Value:** MEDIUM. Bear case becomes: *"Numbers look good but management has
missed 3 of 5 promises and credibility is THESIS BROKEN"* — concrete risk,
not generic hand-waving.

**Done when:**
- [ ] `ai_context` includes `management_integrity`
- [ ] Debate prompts include the integrity section
- [ ] Tested on CGCL (clean record → bull case leans on stability) and ASHOKA (lag streak → bear case focuses on credibility)

## Phase 4 — Master score weighting (~30 min)

**File:** `engine_fundamental/aae_orchestrator.py`

**Change:** Currently master_score = (sector × 0.30) + (narrative × 0.25) + (market × 0.25) + (own × 0.10) + (val × 0.10). Sum = 100%.

Rebalance to include credibility:
- Sector: 0.25
- Narrative: 0.20 (down from 0.25, since narrative now incorporates credibility)
- Market: 0.20 (down from 0.25)
- Ownership: 0.10
- Valuation: 0.10
- **Credibility: 0.15 (NEW)**

Or simpler: keep current weights, add credibility as a penalty:
```python
master_score = (
    (sector * 0.30) + (narrative * 0.25) +
    (market * 0.25) + (own * 0.10) + (val * 0.10)
)
# New: credibility penalty
if cred and cred['consecutive_miss_quarters'] >= 2:
    master_score -= (cred['consecutive_miss_quarters'] - 1) * 5  # -5 per consecutive miss
master_score -= divergence_penalty
master_score -= forensic['penalty']
```

**Value:** MEDIUM. Numbers + integrity now blended in master score.
**Decision:** Phases 1-3 are highest value. Phase 4 is optional polish.

**Done when:**
- [ ] Decision made on rebalance vs penalty approach
- [ ] Implemented and tested

## Phase 5 — Frontend surface (~30 min)

**File:** `frontend/src/AaeDashboard.tsx`

**Change:** When AAE scan returns, surface the credibility subscore as a
new panel in the layer breakdown:
- Layer panel: "🛡️ Management Integrity — 80/100 (ADD ZONE)"
- Below: "5 of 13 actionable promises fulfilled, 7 on track, 1 revised up, 0 missed, 4Q clean streak"

**Done when:**
- [ ] AaeDashboard renders a new layer card for Management Integrity
- [ ] Includes the timeline evidence (mini sparkline of credibility over time)
- [ ] User can click into the timeline cards

## Phase 6 — ConvictionEngine update (~15 min)

**File:** `frontend/src/ConvictionEngine.tsx`

**Context:** Today, clicking a row in ConvictionEngine opens
StockDetailsModal which fetches AAE data. After Phase 1-3, AAE data will
include credibility. So this gap closes *for free* once AAE is updated.

**Optional polish:** Add a "📊" badge or tooltip on rows showing "5 FULFILLED,
7 ON_TRACK, 1 REVISED" — using data already in the row.

**Done when:**
- [ ] If AAE integration goes well, this might not need changes
- [ ] Otherwise: add inline promise count badges to rows

## Phase 7 — Tests + commit (~30 min)

- [ ] Run existing AAE scan on CGCL → verify Layer 4 prompt includes credibility
- [ ] Run AAE on EIHAHOTELS → verify Layer 7 auto-burial triggers
- [ ] Run AAE on ASHOKA → verify soft penalty for 4Q lag
- [ ] Run AAE on CGCL → verify bear/bull debate uses integrity context
- [ ] Snapshot test: master_score for CGCL shouldn't crash, EIHAHOTELS should get auto-penalty

## Total estimated effort

| Phase | Effort | Value |
|---|---|---|
| 1 — Layer 4 prompt enrichment | 1 hr | HIGH |
| 2 — Layer 7 auto-burial | 30 min | HIGH |
| 3 — Layers 9-10 debate context | 30 min | MEDIUM |
| 4 — Master score weighting | 30 min | MEDIUM |
| 5 — Frontend AAE panel | 30 min | MEDIUM |
| 6 — ConvictionEngine polish | 15 min | LOW |
| 7 — Tests + commit | 30 min | REQUIRED |

**Total: ~4 hours of focused work.**

## Out of scope (deferred)

- Re-running AAE V3 for all 140 companies to populate `management_integrity` in `aae_results_snapshot`
- Frontend CredibilityHero on GuidanceCheck linking to AAE layer view
- Alerting system for verdict flips (email/Slack)
- Backfilling credibility data for symbols that haven't been scored yet

## Risk assessment

- **API cost:** $0 extra (Layer 4 prompt is same length, just structured differently)
- **Breaking change:** Low — narrative_summary still has the same shape; just richer
- **Data quality:** Medium — narrative_engine depends on `aae_transcripts` table; if empty, falls back to current behavior
- **Layer 7 false-positive risk:** Medium — auto-burying is aggressive. Mitigation: only auto-bury when consecutive_miss_quarters >= 4 AND score < 40 (conservative threshold)

## Acceptance criteria

- AAE scan on **EIHAHOTELS** returns master_score that reflects its THESIS BROKEN credibility (lower than current)
- AAE scan on **CGCL** shows narrative_summary with credibility_assessment=TRUSTED
- AAE scan on **ASHOKA** shows master_score with -10 lag-streak penalty applied
- AI debate on **ASHOKA** bear case mentions missed quarters specifically
- ConvictionEngine row click on any company shows management integrity (via the AAE panel from Phase 5)

## Open questions for user

1. **Auto-burial threshold:** Is 4 consecutive misses + score < 40 the right cutoff?
   Or should it be more aggressive (3Q + <50)?
2. **Master score weighting:** Rebalance (credibility gets 15%) or penalty-based
   (-5 per consecutive miss quarter)?
3. **Scope:** Do all 7 phases today, or just 1-3 (highest value)?

---

## Pre-flight checklist (start of day 2026-06-17)

- [ ] `git status` clean on main
- [ ] Railway showing latest deploy as active
- [ ] Local `git pull` to ensure latest code
- [ ] Re-confirm: `DEEPSEEK_API_KEY` and `OPENAI_API_KEY` set in `.env`
- [ ] DB connection working (run `venv/bin/python3 -c "from engine_core.db import get_connection; print(get_connection())"`)
