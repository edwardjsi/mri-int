# Calibration Journal — CAS (Capital Allocation Score)

> **"A recommendation is a scientific hypothesis.
> Calibration is the process of proving or disproving that hypothesis using observed outcomes."**
>
> Every change to weights, thresholds, or interpretation in the CAS engine
> MUST be logged here. Future contributors reading this journal should
> understand WHY a parameter is what it is, not just WHAT it is.

---

## What this journal tracks

| What | Where | When |
|------|-------|------|
| **Active parameters** (current values) | `config/capital_allocation.yaml` | Runtime config |
| **Parameter status** (hypothesis / validated) | `config/calibration_registry.yaml` | Status + intro date |
| **Parameter history** (what changed, when, why) | This file (`Calibration.md`) | Every change |
| **Calibration Debt** (unvalidated count) | `tools/calibration_debt.py` | Run anytime |

**Three questions this journal answers:**
1. What parameter changed?
2. Why did we change it?
3. Did the change actually improve outcomes?

---

## Format

Each entry follows this template:

```
### YYYY-MM-DD — <short title>

| Field | Before | After |
|-------|--------|-------|
| <parameter name> | <old value> | <new value> |

**Reason:** <one paragraph explaining the motivation>

**Expected effect:** <what we hypothesized would improve>

**Measured effect:** <what we observed (N recommendations later)>
```

If "Measured effect" is empty, the entry is **unvalidated** and counted as
calibration debt.

---

## Entries

### 2026-07-08 — Quality threshold raised (65 → 70)

| Field | Before | After |
|-------|--------|-------|
| `eligibility.min_quality` | 65 | 70 |

**Reason:** The CAS engine was producing too many mediocre breakouts.
Raising the QIF threshold from 65 to 70 ensures that only stocks with
demonstrated fundamental quality enter the eligible universe. The point
of MRI is fewer, better ideas — not more signals.

**Expected effect:** Reduce eligible universe by ~25%. Raise average
post-recommendation return by an unknown but positive amount.

**Measured effect:** *(pending — requires ≥500 recommendations with m6 outcomes)*

---

### 2026-07-08 — Winner multiplier cap softened (1.20 → 1.10)

| Field | Before | After |
|-------|--------|-------|
| `winner.max_boost` | 1.20 (cap +20%) | 1.10 (cap +10%) |

**Reason:** The old cap allowed a single existing winner to inflate CAS
by up to 20%, which biased capital allocation toward already-large
positions. This created portfolio concentration risk — the engine
rewarded chasing winners, which is the opposite of disciplined
allocation. Softening to 1.10 keeps winners slightly preferred but
removes the heavy concentration incentive.

**Expected effect:** Reduce portfolio concentration. Slow down compounding
into winners slightly (from 1.20× to 1.10×). Improve risk-adjusted returns
if the concentration hypothesis is correct.

**Measured effect:** *(pending — requires ≥100 ADD recommendations with m6 outcomes)*

---

### 2026-07-08 — Confidence redefined: stock quality → model certainty

| Field | Before | After |
|-------|--------|-------|
| `confidence_stars` definition | Stock quality (QIF-based) | Model certainty (data completeness, regime stability) |
| `compute_confidence_stars()` signature | `(qif_score, row)` | `(row, sub_scores, proxies_used, config)` |

**Reason:** Arguably the biggest philosophical change in CAS V1.0.
Previously, "5 stars" meant "high quality stock." Now it means
"high confidence in the model's recommendation." These are different
things — a stock can be high quality but recommended with low confidence
(thin history, regime change, missing indicators). The conflation caused
users to interpret stars as buy signals when they should have been
interpreted as data-quality flags.

This change aligns with the user's mental model: stars answer
"how much should I trust this recommendation?" not "is this a good stock?"

**Expected effect:** Users will see 2-3 star recommendations for high-QIF
stocks that have thin history (e.g., newly listed). This will reduce
"false confidence" in marginal setups while preserving confidence signals
for well-validated names.

**Measured effect:** *(pending — requires outcome data to compare star
distribution vs realized returns)*

---

### 2026-07-08 — Overhead Supply max_count_for_100 raised (10 → 20)

| Field | Before | After |
|-------|--------|-------|
| `subscore.overhead_supply.max_count_for_100` | 10 | 20 |

**Reason:** Distribution sanity check (V1.1d Gate 3) revealed that 83%
of Nifty 500 stocks were scoring exactly 100 on `overhead_supply_score`.
The metric had lost discriminatory power — 100 was the default for
most actively-traded stocks. Expert override per Decision 102 Q2:
"100 doesn't tell me anything. A good metric should spread stocks
across the range."

Raising `max_count_for_100` from 10 to 20 means a stock needs 20+
distinct swing highs (vs 10) in the last 6 months to saturate.
This widens the dynamic range and reduces saturation.

**Expected effect:** Overhead_supply_score distribution shifts from
83% at cap to ~20–40% at cap. Better differentiation between stocks
with light vs heavy overhead. CAS values decrease ~10-15 points for
stocks that previously had overhead_supply_score = 100 (now they
score 50–60 instead).

**Measured effect:** Saturation dropped from 83% → 35.5% (target was
20–40% — in range ✅). All 9 eligible stocks remain eligible; CAS
values decreased 5.79 mean / 5.50 median. Top-9 leaderboard preserved
(9/9 overlap, Spearman ρ=0.683). Calibration validated.

---

### 2026-07-13 — Add Gate V2 introduced (ADD_SECOND_TRANCHE discipline)

| Field | Before | After |
|-------|--------|-------|
| `add_gate.version` | (not present) | `"2.0.0"` |
| `add_gate.decision_score_min` | (CAS+stars only, in `action.add_cas_min`) | `85` (explicit gate) |
| `add_gate.mri_technical_min` | (not present) | `80` |
| `add_gate.breakout_volume_ratio` | (not present) | `1.3` |
| `add_gate.breakout_age_max` | (not present) | `15` |
| `add_gate.weekly_breakout_mode` | (not present) | `prior_52w` |
| `add_gate.weekly_breakout_min_history_weeks` | (not present) | `52` |
| `add_gate.confidence_stars_min` | `4` (hardcoded) | `4` (config-driven) |

**Reason:** Per Decision 103. The legacy `compute_action()` ADD path
required only `CAS ≥ 85` + `confidence_stars ≥ 4` + `has_existing_position=True`.
After BreakoutRadar adoption, owner judged this too loose — the second
₹20k should be **earned** through layered checks, not just because CAS
crossed 85. This entry introduces the V2 gate model with five conditions
(decision score, mri technical, weekly breakout, breakout-day volume,
breakout age) plus the config-driven confidence-stars precondition. All
seven new parameters are YAML-driven (no hardcoded Python constants,
owner refinement C3) and versioned (`add_gate.version: 2.0.0` snapshotted
into every `cas_recommendations.factor_snapshot.config_snapshot.version`,
owner refinement C5).

**Expected effect:** Reduce false-positive ADD signals — only candidates
that pass ALL five gates (plus confidence stars) earn the second tranche.
Real-world effect size: see G1–G5 individual entries below.

**Measured effect:** P6 backtest script `engine_core/backtest_v2_pyramiding.py`
executed on 2026-07-13 over 2026-01-01 → 2026-07-31 against Neon.
`cas_recommendations` contained only 9 historical rows (2026-07-07 batch);
0 V1.1d `ADD` signals and 0 V2 `ADD_SECOND_TRANCHE` signals were available.
Consequently all 6 §14.8 metrics failed with `n/a` values:
`signals_per_month`, `outperform_20d`, `outperform_60d`, `outperform_120d`,
`win_rate_vs_cas_only`, `avg_max_drawdown_60d`.  This is the expected
data-coverage gap, not a gate-design failure.  Next step: populate
historical recommendations by running `scripts/daily_cas_scanner.py` for
each historical trading date (full watchlist, no `--limit`), then re-run
the backtest.  Calibration entries remain `hypothesis` until the sample
contains enough ADD signals to compute all 6 metrics.

---

### 2026-07-13 — G1 decision_score_min introduced (85)

| Field | Before | After |
|-------|--------|-------|
| `add_gate.decision_score_min` | (not a separate gate) | `85` |

**Reason:** Per Decision 103, G1. `decision_score` is the capital
allocation gate — the only "score" gate. Single-responsibility principle
(owner Q1): `radar_priority` ranks the radar, `decision_score` answers
"should I own more of this business?", `mri_technical_score` answers
"is this chart still healthy?". Threshold matches the existing
`action.add_cas_min: 85` so legacy ADD-eligible stocks don't suddenly
disappear — they now need to also clear G2–G5.

**Expected effect:** No change in the set of CAS-85+ candidates reaching
the gate; the G1 floor anchors the layered check.

**Measured effect:** *(pending — P6 backtest executed but sample has 0
ADD signals; see main 2026-07-13 Add Gate V2 entry)*

---

### 2026-07-13 — G2 mri_technical_min introduced (80)

| Field | Before | After |
|-------|--------|-------|
| `add_gate.mri_technical_min` | (not present) | `80` |

**Reason:** Per Decision 103, G2. Adds explicit technical-structure
filter alongside G1's quality filter. Owner explicitly chose to keep
both gates despite partial overlap (Q1 follow-up): "decision_score =
'Should I own more of this business?' mri_technical_score = 'Is this
chart still healthy?' If you later find a correlation of 0.9+ in
backtests, then revisit it. Until then, I'd keep both."

**Expected effect:** Filters out stocks with strong fundamentals
(high decision_score) but broken technical structure (e.g. breakdown,
EMA stack violation). Tightens ADD signal without disturbing CAS
scoring itself.

**Measured effect:** *(pending — P6 backtest executed but sample has 0
ADD signals; see main 2026-07-13 Add Gate V2 entry)*

---

### 2026-07-13 — G4 breakout_volume_ratio introduced (1.3)

| Field | Before | After |
|-------|--------|-------|
| `add_gate.breakout_volume_ratio` | (not present) | `1.3` |
| `daily_prices.breakout_day_volume` | (not present) | (NUMERIC, populated on breakout day) |
| `daily_prices.breakout_day_avg20_volume` | (not present) | (NUMERIC) |
| `daily_prices.breakout_day_volume_ratio` | (not present) | (NUMERIC) |
| `daily_prices.volume_threshold_used` | (not present) | (NUMERIC, frozen) |
| `daily_prices.breakout_date_for_volume` | (not present) | (DATE, frozen) |
| `daily_prices.volume_confirmed_breakout` | (not present) | (BOOLEAN, frozen) |

**Reason:** Per Decision 103, G4 + owner refinement C2. Volume on the
actual breakout day is the canonical institutional-sponsorship signal —
it captures whether the breakout itself was sponsored. Threshold 1.3×
matches the existing STEE Step-5 entry rule (volume ≥ 1.3× 20d avg),
so we stay internally consistent. Critically, the ratio and the threshold
USED at computation time are both persisted: six months from now, if we
retune the threshold to 1.5×, we can still reconstruct exactly which
historical recommendations were generated under the 1.3× rule.

**Expected effect:** Eliminates breakouts that "drifted through"
resistance without institutional commitment. Reduces false positives
without adding daily recomputation overhead (computed once, frozen).

**Measured effect:** *(pending — P6 backtest executed but sample has 0
ADD signals; see main 2026-07-13 Add Gate V2 entry)*

---

### 2026-07-13 — G5 breakout_age_max introduced (15)

| Field | Before | After |
|-------|--------|-------|
| `add_gate.breakout_age_max` | (not present) | `15` (trading days) |

**Reason:** Per Decision 103, G5. Broader than the V1.1 eligibility
filter (`breakout_max_age_days: 5`) and the V1.1 market sub-gate
(`max_breakout_age_days: 3`). 15 trading days ≈ 3 weeks — wide enough
to allow pyramiding into a confirmed breakout that took a couple of
weeks to validate, tight enough that the opportunity hasn't matured.

**Expected effect:** Filters out matured breakouts (Day 30+) where
institutions have already distributed; preserves recently-broken-out
stocks still in price-discovery phase.

**Measured effect:** *(pending P6 backtest)*

---

### 2026-07-13 — G3 weekly breakout mode (PRIOR_52W_HIGH + ATH fallback)

| Field | Before | After |
|-------|--------|-------|
| `add_gate.weekly_breakout_mode` | (not present) | `prior_52w` |
| `add_gate.weekly_breakout_min_history_weeks` | (not present) | `52` |
| `daily_prices.prior_52w_high` | (not present) | (NUMERIC) |
| `daily_prices.all_time_high_before_current_week` | (not present) | (NUMERIC) |
| `daily_prices.resistance_source` | (not present) | (TEXT enum: `PRIOR_52W_HIGH` \| `ALL_TIME_HIGH`) |
| `daily_prices.weekly_close_above_resistance` | (not present) | (BOOLEAN) |

**Reason:** Per Decision 103, G3 + owner refinement C1 (ATH fallback) +
C9 (enum resistance source). Weekly close > prior 52-week high is the
"price discovery" signal; aligns with Decision 029/081 (Golden Setup
framework). Fallback to all-time-high for stocks with < 52 weeks of
history prevents emerging rerating candidates (listed 8–10 months ago)
from being permanently excluded — owner: "the system already favours
emerging rerating candidates. A company listed 8–10 months ago
shouldn't be permanently excluded just because it lacks a full year's
history." Both branches preserve the price-discovery intent. The
resistance source is a Python enum (`ResistanceSource.{PRIOR_52W_HIGH,
ALL_TIME_HIGH}`) not free text (owner refinement C9): "enums are easier
to validate, test, and query than arbitrary strings."

**Expected effect:** Thin-history rerating candidates are no longer
disqualified by G3; mature names still require genuine 52w-high break.

**Measured effect:** *(pending P6 backtest; track coverage of <1y
listings separately)*

---

## Calibration Debt

Run `venv/bin/python tools/calibration_debt.py` to see current count.

```
Total assumptions:  <N>
Validated:          <M>
Debt:               <N - M>
```

A growing debt is acceptable in early days (we haven't accumulated
enough recommendations). A debt of N=0 is suspicious — it means we're
not making any bets on untested parameters, which is research stagnation.

---

## How to add an entry

1. Make the parameter change in `config/capital_allocation.yaml` AND
   `config/calibration_registry.yaml` (status: hypothesis, today, etc.)
2. Add an entry to this file using the template above.
3. After outcomes accumulate, fill in "Measured effect" — when you do,
   update `calibration_registry.yaml` to mark `status: validated`.

Do NOT skip this journal. Undocumented parameter changes are technical debt.
