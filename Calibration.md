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
