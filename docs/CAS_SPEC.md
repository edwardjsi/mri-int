# CAS Specification — Engineering Motto, Architecture, Lifecycle

> **"A recommendation is a scientific hypothesis.
> Calibration is the process of proving or disproving that hypothesis using observed outcomes."**

This document captures the philosophy, architecture, and lifecycle of the
Capital Allocation Score (CAS) engine. It is the architectural source of
truth that supplements the implementation plan
(`docs/CAPITAL_ALLOCATION_SCORE_PLAN_2026-07-06.md`) and the design decisions
log (`Decisions.md`).

---

## §0 — Engineering Motto

> **A recommendation is a scientific hypothesis.
> Calibration is the process of proving or disproving that hypothesis using observed outcomes.**

Every CAS score, every action tier, every confidence star is a HYPOTHESIS
about the future. We do not "know" that BROKEN_OUT + high QIF + bullish
regime leads to outperformance. We HYPOTHESIZE it. Calibration is what
turns hypotheses into either validated knowledge or invalidated noise.

**Implications:**

1. **Every parameter has a status.** `config/calibration_registry.yaml`
   tracks `hypothesis` vs `validated` for every tunable. New parameters
   start as `hypothesis`. After enough outcome data, they graduate to
   `validated` (or get deprecated).

2. **Calibration Debt is a living metric.** Debt = unvalidated assumptions.
   We accept growing debt in early days. We celebrate shrinking debt as
   we accumulate evidence. Stagnant debt (neither growing nor shrinking)
   means we are not learning.

3. **Document every change.** `Calibration.md` logs the Before/After,
   the Reason, the Expected Effect, and the Measured Effect. A change
   without a journal entry is technical debt.

4. **Action ≠ Truth.** A CAS of 85 means "I think this is worth deploying
   capital against," not "this will go up." The action verb is the
   confidence we have in the hypothesis, not a guarantee.

---

## §1.0 — Three-Layer Architecture

The CAS pipeline is structured as three sequential layers, each filtering
the candidate set before the next layer invests compute:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 0 — DATA                                                          │
│ daily_prices → indicators → BROKEN_OUT/CONSOLIDATING state              │
│ All Nifty 500 symbols (~961).                                           │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 1 — ELIGIBILITY GATES                                             │
│ Regime + EMA stack + Breakout state + Liquidity + Quality + 52w pos     │
│ Pass = eligible for scoring. Fail = ineligible (logged with reason).    │
│ Filters out ~95% of universe.                                           │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 2 — MARKET STRUCTURE SUB-GATES (HARD PASS/FAIL)                   │
│ Trend + Breakout freshness + Quality (stricter than eligibility)        │
│ Pass = Market Score computable. Fail = no numeric score.                │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 3 — MARKET SCORE (NUMERIC)                                        │
│ Weighted sum of 7 sub-scores: regime, weekly, breakout,                 │
│ overhead_supply, rs, volume, sector. Range [0, 100].                    │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 4 — CAS (Portfolio Allocation Score)                              │
│ CAS = Market Score × Winner Multiplier × Concentration Multiplier       │
│ Range [0, ~110]. Represents "conviction-weighted allocation score."     │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 5 — ACTION (DECISION LAYER)                                       │
│ CAS → Tier (NO_ACTION < WATCH < FIRST_TRANCHE < ADD_SECOND_TRANCHE)     │
│ Tier + hysteresis → Action (BUY/ADD/WATCH/NO_ACTION)                    │
│ Tier + stars → Confidence (model certainty, NOT stock quality)         │
└─────────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────────┐
│ Layer 6 — RECOMMENDATION + OUTCOME TRACKING                             │
│ cas_recommendations table (immutable, Event A)                          │
│ cas_recommendation_outcomes table (mutable, Event B — daily EOD)         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Why this layered design?

- **Each layer filters.** A stock that fails eligibility never reaches
  scoring (saves compute). A stock that fails structure never gets a
  numeric score (no partial credit for "good trend, bad breakout").
- **Each layer has clear pass/fail semantics.** No ambiguity about
  whether a stock is in the candidate set.
- **Each layer is independently testable.** `check_eligibility()`,
  `compute_market_structure()`, `compute_market_score()` are pure functions.

---

## §1.1 — Recommendation Lifecycle

Every recommendation flows through four states. The state is **derived
from dates + milestones**, not stored as a separate column — single
source of truth.

```
┌──────────┐    age > 0    ┌──────────┐   all milestones   ┌──────────┐
│   NEW    │ ────────────→ │  ACTIVE  │ ─────────────────→ │ MATURED  │
└──────────┘               └──────────┤                   └──────────┘
   created today             past creation,                all 5 milestones
                              milestones still              filled (w1/w2/w4/m3/m6)
                              being filled                  AND age <= 180 days
                                                          │
                                                          │ age > 180 days
                                                          ↓
                                                    ┌──────────┐
                                                    │ ARCHIVED │
                                                    └──────────┘
                                                    retained for
                                                    historical analysis
```

### State Definitions

| State | Trigger | Properties |
|-------|---------|-----------|
| **NEW** | `created_at == today` | Just recorded; no outcome movement yet |
| **ACTIVE** | `created_at < today` AND milestones incomplete | Outcome tracking in progress |
| **MATURED** | All 5 milestones filled AND `age <= 180 days` | All scheduled checkpoints completed |
| **ARCHIVED** | `MATURED` AND `age > 180 days` | Historical record; not in active queries |

### Why compute lifecycle from dates?

- **Single source of truth:** `created_at` and `milestones_reached` are
  authoritative. Lifecycle state is a derived view, not a separate
  mutable field. No risk of drift between "what the lifecycle says"
  and "what the data says."
- **Backfill safe:** If we backfill recommendations from historical
  data, lifecycle states are correct automatically.
- **Testable:** `compute_recommendation_lifecycle(rec, outcome, today)`
  is a pure function with no DB dependency.

### Lifecycle in the API/UI

| State | UI Treatment |
|-------|--------------|
| NEW | Highlight as "today's pick" with confidence emphasis |
| ACTIVE | Show next milestone countdown + current return |
| MATURED | Show full outcome table (m6 return, MFE/MAE, hit/miss) |
| ARCHIVED | Available only via historical query, not in default views |

---

## §2 — Cross-References

| Topic | Doc |
|-------|-----|
| Implementation plan (N+1, N+2a/b, V1.1) | `docs/CAPITAL_ALLOCATION_SCORE_PLAN_2026-07-06.md` |
| Decision 101 (V1.1 scope + expert feedback) | `Decisions.md` |
| Calibration journal (parameter history) | `Calibration.md` |
| Calibration status (current validation state) | `config/calibration_registry.yaml` |
| Calibration debt counter | `tools/calibration_debt.py` |
| Regression tolerance | `engine_core/cas_decision_layer.py` (assert_cas_within_tolerance) |
| Layer 5 decision logic | `engine_core/cas_decision_layer.py` (stabilize_action, should_return_no_action) |
