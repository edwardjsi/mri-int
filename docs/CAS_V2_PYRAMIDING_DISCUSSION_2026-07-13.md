# CAS V2 Pyramiding Discipline Gates — Design Discussion Record

> **Decision:** 103  
> **Branch:** `feature/capital-allocation-v1`  
> **Date:** 2026-07-13  
> **Status:** Approved (pending doc save)

## 0 · Purpose

This document captures the multi-round design discussion between the
implementer (AI) and the domain expert (owner) that produced the V2
pyramiding discipline gates for `ADD_SECOND_TRANCHE`. It is the
institutional record of *why* the design is what it is, including the
alternatives considered and the rationale for each choice.

If you are an agent resuming work on this branch, read this file BEFORE
reading CAS_SPEC.md — it explains the design intent that the spec assumes.

---

## 1 · Round 1 — Initial Proposal

### 1.1 Owner's brief

> "You've built an excellent BreakoutRadar. Rather than adding purely
> because an alert fires, make your second tranche conditional on these
> three checks:
>
> 1. BreakoutRadar score remains ≥ 85
> 2. Capital Allocation Score (CAS) ≥ 80
> 3. Weekly breakout closes above resistance with higher-than-average
>    volume
>
> Only when all three align does the stock truly earn the second ₹20k.
> That keeps your pyramiding disciplined and consistent with the process
> you've been refining."

### 1.2 AI's plan v1

Proposed the following foundational choices (later refined):

- **5-gate ADD model** instead of 3, separating:
  - G1 `decision_score ≥ 85` (capital allocation quality)
  - G2 `mri_technical_score ≥ 80` (technical structure)
  - G3 weekly close > resistance
  - G4 breakout-day volume ≥ 1.3 × 20d avg
  - G5 breakout_age ≤ 15 trading days
- **Single-responsibility scoring** — each score answers one question:
  - `radar_priority` → radar ranking
  - `decision_score` → capital allocation
  - `mri_technical_score` → technical confirmation
- **3-layer UI state model** — `OBSERVE / APPROACHING_ADD / READY_FOR_ADD / ADD_SECOND_TRANCHE`
- **Per-gate diagnostics** in `factor_snapshot.gates`
- **7-phase rollout** — P1 docs → P2 indicators → P3 engine → P4 API → P5 frontend → P6 backtest → P7 wrap-up

### 1.3 Owner's structural feedback (became C1–C4)

Three architectural refinements requested before approval:

#### C1 · Thin-history fallback for G3
> "I would not silently fail them. Instead:
> IF history >= 52 weeks → resistance = prior_52w_high
> ELSE → resistance = all_time_high_before_current_week"

**Rationale:** The system already favours emerging rerating candidates.
A stock listed 8–10 months ago shouldn't be permanently excluded because
it lacks a full year of price history. Both branches preserve the
"price discovery" intent of the gate.

#### C2 · G4 must be versioned, not boolean
> "Store `breakout_day_volume_ratio`, `breakout_day_avg20_volume`,
> `breakout_day_volume`, `breakout_date`, AND `volume_threshold_used`.
> Otherwise six months from now, if you change the calibration from
> 1.3× to 1.5×, you won't know which historical recommendations were
> generated under which rule."

**Rationale:** Auditability + future backtesting under different
calibration regimes.

#### C3 · No hardcoded thresholds (HIGHEST PRIORITY)
> "Every gate should come from the calibration registry:
> `add_gate: { decision_score_min, mri_technical_min, breakout_age_max,
> breakout_volume_ratio, weekly_breakout_mode }`
> Then `evaluate_add_gates()` simply reads the configuration."

**Rationale:** Future calibration is far easier when the engine is
data-driven. Decision thresholds belong in YAML, not Python.

#### C4 · Cap the "Approaching ADD" surface
> CAS 80–84, top 20 by radar_priority, no notifications, radar page only.

**Rationale:** Avoid alert fatigue while still surfacing worthwhile
candidates for active watch.

### 1.4 Risk responses (owner)

- **R3** (`decision_score` × `mri_technical_score` overlap):  
  > "Keep both — `decision_score` = 'Should I own more of this business?'
  > `mri_technical_score` = 'Is this chart still healthy?' Revisit if
  > correlation > 0.9 in backtest."
- **R4** ("Approaching ADD" noise): Addressed by C4.

### 1.5 AI's revised plan v2

Integrated all four refinements + risk responses. Owner approved
unconditionally.

---

## 2 · Round 2 — Four Final Recommendations

### 2.1 Owner's final four nudges

#### C5 · Calibration version (highest priority of this round)
> "Add `add_gate.version: '2.0.0'`. Persist `version` in
> `config_snapshot.version`. Historical recommendations reproducible
> even if the YAML evolves."

**Rationale:** Reproducibility across calibration changes is the
prerequisite for credible backtesting.

#### C6 · Rename UI state
> "Current `ELIGIBLE_ADD_BLOCKED` is not user-friendly. Rename to
> `READY_FOR_ADD` (or `READY_PENDING`). Example:
> 🟢 Ready for ADD
> ❌ Weekly breakout not confirmed
> ❌ Breakout too old"

**Rationale:** The stock is fundamentally ready; the user should see
*exactly* what is still missing, not feel rejected.

#### C7 · Gate confidence metric
> "Output not just binary passed/blocked. Expose
> `5/6 gates passed` or `Gate Score = 83%`. The user sees '🟢 Ready
> for ADD — 5/6 gates passed, missing: Weekly breakout'."

**Rationale:** Binary outputs are weak signals. A 5/6 stock is much
closer to ADD than a 1/6 stock — the UI should reflect that.

#### C8 · Backtest success metrics
> "In P6, don't stop at ≤ 5 ADDs/month. Also measure:
> - Number of ADD signals generated
> - % that outperform the benchmark at 20, 60, 120 trading days
> - Win rate vs the existing CAS-only model
> - Average maximum drawdown after an ADD signal"

**Rationale:** Evidence required to justify the additional complexity.
The new five-gate model should reduce false positives without sacrificing
winners.

### 2.2 Owner's answers to AI's clarifying questions

- **C1–C3 correctly integrated?** Yes.
- **C4 appropriate?** Yes.
- **P1 right first commit?** Yes. Doc-first sequence.
- **Remaining ambiguity:** G3 resistance source should be an **enum**,
  not free text:
  ```text
  PRIOR_52W_HIGH
  ALL_TIME_HIGH
  ```

  Enums are easier to validate, test, and query than arbitrary strings.

### 2.3 AI's plan v3 (this document)

Integrated C5–C9. Final design state:

| Refinement | Origin | Status |
|------------|--------|--------|
| C1 — ATH fallback | Round 1 | ✅ Integrated |
| C2 — Volume metadata versioned | Round 1 | ✅ Integrated |
| C3 — YAML-driven thresholds | Round 1 | ✅ Integrated |
| C4 — Approaching ADD cap | Round 1 | ✅ Integrated |
| C5 — Calibration version | Round 2 | ✅ Integrated |
| C6 — Rename UI state | Round 2 | ✅ Integrated |
| C7 — Gate confidence metric | Round 2 | ✅ Integrated |
| C8 — Backtest metrics | Round 2 | ✅ Integrated |
| C9 — Enum resistance source | Round 2 | ✅ Integrated |

---

## 3 · Final State

### 3.1 Gate spec (canonical)

| # | Gate | Threshold | Source |
|---|------|-----------|--------|
| G1 | decision_score | ≥ 85 (YAML) | `add_gate.decision_score_min` |
| G2 | mri_technical_score | ≥ 80 (YAML) | `add_gate.mri_technical_min` |
| G3 | weekly close > resistance | boolean | enum: PRIOR_52W_HIGH \| ALL_TIME_HIGH |
| G4 | breakout_day_volume ≥ 1.3× 20d | boolean (frozen) | `add_gate.breakout_volume_ratio` |
| G5 | breakout_age | ≤ 15 days | `add_gate.breakout_age_max` |
| + | confidence_stars | ≥ 4 (YAML) | `add_gate.confidence_stars_min` |

### 3.2 State model (canonical)

| CAS | Gates | Final state | UI | Action |
|-----|-------|-------------|-----|--------|
| < 80 | — | OBSERVE | ⚪ Observe | None |
| 80–84 | — | APPROACHING_ADD | 🟡 Approaching ADD | WATCH |
| ≥ 85 | some fail | READY_FOR_ADD | 🟢 Ready for ADD (n/N) | WATCH |
| ≥ 85 | all pass | ADD_SECOND_TRANCHE | 🚀 ADD SECOND TRANCHE | ADD |

### 3.3 Implementation order (canonical)

P1 docs → P2 indicators + migration → P3 engine → P4 API → P5 frontend
→ P6 backtest (with success metrics) → P7 wrap-up.

---

## 4 · Alternatives Considered

| Choice | Picked | Rejected | Why |
|--------|--------|----------|-----|
| Resistance definition | 52w high (with ATH fallback) | Daily breakout pivot; weekly EMA-13; prior weekly swing high | 52w high aligns with Decision 029/081 (Golden Setup). Daily pivot ties a strategic rule to a tactical pattern. EMA-13 measures trend, not breakout. Weekly swing high too noisy inside consolidations. |
| Volume threshold | Breakout-day ratio ≥ 1.3× | Today's volume ≥ 1.3× or 1.5×; weekly aggregate | Breakout-day captures institutional sponsorship when it matters. Today's volume penalizes healthy post-breakout consolidation. Weekly aggregation adds complexity without clear edge. |
| ADD floor | Keep CAS ≥ 85 + 5 gates | Lower ADD to CAS ≥ 80 | "The second ₹20k is earned." Lowering without backtest increases exposure based on intuition, not evidence. |
| Score overlap | Keep both `decision_score` + `mri_technical_score` | Drop one | Each answers a different question (ownership quality vs chart health). Revisit only if backtest reveals ρ > 0.9. |
| Surface noise | Top-20 cap, radar page only | Email/push notifications for all CAS 80+ | Owner wants to discover promising names early, not get alerted. Tighten later if still noisy. |

---

## 5 · Decision Log Reference

- **Decision 103** — V2 Pyramiding Discipline Gates
  - Full rationale: `Decisions.md` (entry to be added in P1)
  - Spec section: `docs/CAPITAL_ALLOCATION_SCORE_PLAN_2026-07-06.md` §14
  - Calibration: `config/calibration_registry.yaml` (5 PROPOSED entries)
  - Engine code: `engine_core/cas_recommendations.py` (`evaluate_add_gates`)
  - State model: `engine_core/cas_decision_layer.py` (`compute_layered_state`)
  - Schema: `migrations/010_add_second_tranche_gates.sql`

---

## 6 · Cross-References

- Implementation plan: `docs/CAPITAL_ALLOCATION_SCORE_PLAN_2026-07-06.md` §14
- Spec: `docs/CAS_SPEC.md` §6
- Calibration journal: `Calibration.md` (5 new entries)
- Session log: `Sessions.md` (multi-session handoff notes)
- Progress: `Progress.md` (new task + completion row)
