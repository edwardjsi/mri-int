# CAS V1.0 — Session N+2a Handoff for Expert Review

**Date:** 2026-07-08
**Branch:** `feature/capital-allocation-v1` (3 commits: `f4dc161` → `287f27c` → `b2c4a4a`)
**Spec:** `docs/CAPITAL_ALLOCATION_SCORE_PLAN_2026-07-06.md` (rev 3)
**Decision:** Decision 100 in `Decisions.md`

---

## TL;DR (share this with the expert)

I implemented the **Capital Allocation Score V1.0** (CAS) per Decision 100. It
answers "Which breakout deserves fresh capital today?" by combining a
two-stage filter (eligibility + market structure), a 7-factor weighted market
score, portfolio multipliers, and a 5-star confidence rating.

**Three commits on `feature/capital-allocation-v1`:**

1. **`f4dc161` — N+1 (engine + tests):** pure logic module
   `engine_core/capital_allocation.py` (~600 lines) + 104 unit tests +
   YAML config + golden-case basket.
2. **`287f27c` — N+1 rev 3 refinements:** owner-requested changes —
   confidence rewritten as 5 model-certainty stars (not stock quality), all
   calibration constants moved to YAML, missing data → ineligible, renamed
   `check_market_subgates` → `compute_market_structure`, added per-factor
   breakdown logging.
3. **`b2c4a4a` — N+2a (indicator wiring, this commit):** added 4 new
   indicator columns (`ema_100`, `rolling_high_52w`, `weekly_trend_score`,
   `overhead_supply_score`) end-to-end through `engine_core/indicator_engine.py`.

**What's NOT done yet (N+2b):** run the migration against prod DB, backfill
~1.6M rows for Nifty 500, smoke-test against the 5 golden-case symbols.
That's a separate session requiring DB credentials.

---

## Architecture (V1.0, rev 3)

```
   ┌─────────────────────────────────────────────────────────────────┐
   │  ELIGIBILITY (8 hard gates — instant REJECT if any fails)       │
   │    regime, ema_stack (4 cond), breakout_state, liquidity,       │
   │    quality, 52w_position, weekly_data, rs_data                  │
   └─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │  MARKET STRUCTURE (3 hard PASS/FAIL sub-gates)                  │
   │    trend ≥ 50   |   breakout_age ≤ 3   |   QIF ≥ 75             │
   └─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │  MARKET SCORE = weighted sum of 7 sub-scores (sum 100)          │
   │    regime 23 | weekly 21 | breakout 17 | overhead 14 |          │
   │    rs 11 | volume 8 | sector 6 (neutral proxy in V1.0)          │
   │  R/R removed from V1.0 (deferred to V1.1).                     │
   └─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │  CAS = Market × Winner × Concentration                          │
   │    Winner: 1 + (profit/10) × 0.10, clamped [0.85, 1.10]         │
   │    Concentration: 1 - clamp(weight/15, 0, 1) × 0.10             │
   └─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │  CONFIDENCE: 5 model-certainty stars (NOT stock quality)        │
   │    complete_data (≥90%), factor_agreement (std-dev≤20),         │
   │    stable_calculations (not at age cliff),                      │
   │    low_proxy_usage (≤0 proxies), indicator_freshness (≤5 days)  │
   └─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │  ACTION CHIP                                                    │
   │    CAS ≥ 85 → ADD SECOND TRANCHE                                │
   │    CAS 70–84 → FIRST TRANCHE                                    │
   │    CAS 50–69 → WATCH                                            │
   │    CAS < 50 → (no chip)                                         │
   └─────────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions (rev 3)

### 1. Confidence = model certainty, not stock quality

The original rev 2 spec had confidence stars that included "trend maturity"
and "breakout maturity" — both are stock-quality signals. Owner correctly
flagged this: confidence should measure "how much can we trust THIS score?"
not "is the stock good?" The 5 model-certainty stars are:

| Star | Question it answers | Source |
|------|---------------------|--------|
| Complete data | Are enough fields populated? | `data_completeness_pct ≥ 90%` |
| Factor agreement | Are sub-scores pointing same way? | `std-dev(aligned sub-scores) ≤ 20` |
| Stable calculations | Are we sitting on a noisy edge? | `breakout_age ≠ 4` |
| Low proxy usage | Are real indicators used? | `proxies_used count ≤ 0` |
| Indicator freshness | Are inputs current? | `data_age_days ≤ 5` |

`overhead_supply` is stored as "badness" (0 = clear air, 100 = massive
overhead) and inverted INTERNALLY in `compute_confidence_stars` before
factor_agreement std-dev. This is essential — otherwise an obvious good
stock would always lose a star.

### 2. All calibration constants in YAML

`config/capital_allocation.yaml` → `calibration.*` section holds:
- `rs_strong` (0.05), `volume_confirmed` (1.5), `overhead_clear_air` (30),
  `qif_high` (70), `weekly_strong` (75), `near_52wh_pct` (5),
  `breakout_early_max_age` (3), `age_decay` table.
- `confidence.complete_data_threshold_pct` (90),
  `confidence.factor_agreement_max_std_dev` (20),
  `confidence.stable_breakout_age_cliff` (4),
  `confidence.low_proxy_usage_max_proxies` (0),
  `confidence.indicator_freshness_max_age_days` (5).

**Zero magic numbers in `engine_core/`.** Backtesters tune YAML, never Python.

### 3. Missing critical data → ineligible, not score 0

Added 2 eligibility gates (`weekly_data`, `rs_data`). The model REFUSES to
score rather than guess with 0s. Portfolio-context fields
(`winner_profit_pct`, `concentration_weight_pct`) still default to neutral
1.0× when missing — those are optional inputs, not market data.

### 4. N+2a — 4 new indicator columns

| Column | Formula | Lookback | Used by |
|--------|---------|----------|---------|
| `ema_100` | `close.ewm(span=100)` | 100d | `ema100_rising` eligibility gate |
| `rolling_high_52w` | `high.rolling(252, min_periods=50).max()` | 252d | 52w position gate + Weekly Structure "within 5%" component |
| `weekly_trend_score` | 5-component composite (HH + HL + above EMA-13 + above EMA-20 + within 5% of 52w high), summed max 100 | weekly resample + ffill | Weekly Structure sub-score + Trend sub-gate |
| `overhead_supply_score` | `min(distinct_highs_above_close / 10 × 100, 100)` | 126d | Overhead Supply sub-score |

All 4 are computed by pure functions in `engine_core/cas_indicators.py`
(testable in isolation). The indicator pipeline in `indicator_engine.py`
just calls them and writes results to DB.

---

## File-by-File Change Summary (3 commits)

| File | Status | Purpose |
|------|--------|---------|
| `config/capital_allocation.yaml` | NEW (rev 3) | All thresholds + weights + calibration constants. Single source of truth. |
| `engine_core/capital_allocation.py` | NEW | Pure scoring engine. 6 public functions: `load_config`, `check_eligibility`, `compute_market_structure`, `compute_market_score`, `compute_market_score_breakdown`, `compute_portfolio_allocation_score`, `compute_confidence_stars`, `render_why_checklist`. No DB, no I/O. |
| `engine_core/test_capital_allocation.py` | NEW | 104 unit tests across eligibility, structure, sub-scores, multipliers, confidence, why-checklist, breakdown, golden cases. |
| `engine_core/cas_indicators.py` | NEW | 4 pure indicator functions + 1 helper. Used by `indicator_engine.py`. |
| `engine_core/test_cas_indicators.py` | NEW | 25 tests across EMA-100, rolling high, weekly trend, overhead supply. |
| `migrations/008_capital_allocation_columns.sql` | NEW | 4 ALTER TABLE statements + 3 partial/composite indexes. Idempotent. |
| `tests/golden_cases.yaml` | NEW | 7 regression scenarios (WELCORP, CHOLAFIN, PHOENIXLTD, NAVINFLUOR, POONAWALLA, BEARISH, MISSING_DATA). |
| `engine_core/indicator_engine.py` | MODIFIED | Wired 4 new columns into `INDICATOR_COLUMNS`, `compute_indicators`, UPDATE SQL, `fetch_symbols_needing_repair`. |
| `api/schema.py` | MODIFIED | Section "12d. CAS V1.0 (Decision 100)" — 4 ALTER + 2 partial indexes in auto-heal. |
| `docs/CAPITAL_ALLOCATION_SCORE_PLAN_2026-07-06.md` | MODIFIED | rev 2 → rev 3 (§5 Confidence rewritten, §7 File Changes updated, §8 Verification updated, §13 Revision Log added). |
| `Decisions.md` | MODIFIED | Decision 100 status DRAFT → APPROVED. Point #9 (Confidence) rewritten. Implementation log added. |
| `Sessions.md` + `Progress.md` | MODIFIED | Session N+1 + N+1 refinements + N+2a entries. |
| `requirements.txt` | MODIFIED | `pyyaml>=6.0` added. |

---

## Test Results

```
engine_core/test_capital_allocation.py   104 tests  PASS  0.47s
engine_core/test_cas_indicators.py        25 tests  PASS  0.67s
engine_core/test_guidance_email_sections.py  7 tests PASS  (slow)
engine_core/test_survivorship_bias.py      1 test   PASS  (slow)
────────────────────────────────────────────────────────────────
TOTAL                                    137 tests  PASS  14.31s
```

Integration sanity check (300-day synthetic uptrend):
- `ema_100` populates from row 99 onward (201/300 non-null — 99 warm-up rows)
- `rolling_high_52w` populates from row 49 onward (251/300 — 49 warm-up)
- `weekly_trend_score` fully populated (300/300 — forward-fills weekly → daily)
- `overhead_supply_score` fully populated (300/300 — returns 0 for warm-up)

---

## Open Questions for Expert Review

These were flagged during implementation but not yet resolved with the owner:

1. **`overhead_supply_score` algorithm:** currently uses `drop_duplicates()`
   on raw `high` values. Two different days with high=110.00 (exact float)
   are counted as 1, but two days with high=110.01 vs 110.04 are counted
   as 2. Should we round to 1% buckets to avoid this granularity artifact?

2. **`weekly_trend_score` HH/HL detection:** currently uses simple
   "this week's high > last week's high" comparison. The spec mentions a
   "5-bar fractal with confirmation lag" as an alternative. Which is more
   appropriate for Indian mid-cap weekly structure?

3. **EMA-100 warm-up:** the engine masks the first 99 rows as NaN. Should
   the eligibility gate `ema100_rising` fall back to `ema50` for symbols
   with thin history (mirrors the existing `ema_200` fallback)?

4. **Overhead Supply `max_count=10`:** per spec. Is 10 right for Indian
   mid-caps? With ~126 trading days × ~52 weeks × daily highs, a heavily
   traded stock easily has 20+ distinct highs above close. Worth
   backtesting 5, 10, 15?

5. **`age_decay` cliff at breakout_age=4 (rev 3):** the stable_calculations
   star specifically flags age=4 as unstable (the score drops 85→70).
   Should the cliff detection be more nuanced (e.g., age 3-5 zone)?

6. **`data_age_days` source:** currently read from the input row. Where
   does it actually come from in production? The freshness star gates on
   this; if the field isn't reliably populated, the star is meaningless.

7. **Per-factor log noise:** the breakdown logging is DEBUG-only, but a
   full Nifty 500 backfill is ~1.6M rows × 7 factors = 11.2M log lines
   even at DEBUG. Should we add a separate `cas_breakdown.log` file, or
   suppress by default?

8. **Branch strategy (3 PRs vs 1):** currently 3 PRs (engine → indicators →
   API/UI). If the expert wants to ship faster, we can squash to 1 PR.

---

## How to Run Locally

### Prerequisites
- Python 3.12+ (project uses 3.12)
- `venv/` already set up with: `pandas`, `numpy`, `psycopg2-binary`, `pyyaml`, `pytest`
- DB connection: `DATABASE_URL` env var (production Postgres on Railway)

### 1. Run all tests (no DB needed)

```bash
cd /home/immanuels/Desktop/mri-int
venv/bin/pytest engine_core/test_capital_allocation.py engine_core/test_cas_indicators.py -v
```

Expected: **129 passed in ~1s**.

For the full engine_core suite (slower, includes integration tests):
```bash
venv/bin/pytest engine_core/ -v
```

### 2. Run the migration against a DB

The migration is idempotent — safe to re-run any number of times.

```bash
# Option A: via psql
psql "$DATABASE_URL" -f migrations/008_capital_allocation_columns.sql

# Option B: rely on auto-heal — the api/schema.py auto-heal block
# runs on every API startup. Just restart the API and the columns appear.
```

**Expected result:** 4 new columns on `daily_prices`:
- `ema_100` NUMERIC DEFAULT NULL
- `rolling_high_52w` NUMERIC DEFAULT NULL
- `weekly_trend_score` NUMERIC DEFAULT NULL
- `overhead_supply_score` NUMERIC DEFAULT NULL
- 3 new partial/composite indexes.

### 3. Backfill Nifty 500 (~1.6M rows)

```bash
# Smoke test: first 2 batches of 25 symbols each (50 symbols)
MRI_INDICATOR_MAX_BATCHES=2 venv/bin/python -m engine_core.indicator_engine

# Full backfill: remove the env var, run in background, log to file
nohup venv/bin/python -m engine_core.indicator_engine > backfill.log 2>&1 &
echo $! > backfill.pid

# Monitor progress
tail -f backfill.log
```

Expected runtime: 5–10 minutes on Railway. The engine writes progress every
batch.

**Performance note:** the `overhead_supply_score` function uses a per-row
Python loop over the 126-day lookback. For 1.6M rows that's ~200M
comparisons. Acceptable for V1.0; if it becomes a bottleneck, can be
vectorized with numpy.

### 4. Smoke-test against the 5 golden-case symbols

```bash
# Inspect a few rows for each symbol in the golden basket
psql "$DATABASE_URL" -c "
SELECT symbol, date, ema_100, rolling_high_52w, weekly_trend_score, overhead_supply_score
FROM daily_prices
WHERE symbol IN ('WELCORP', 'CHOLAFIN', 'PHOENIXLTD', 'NAVINFLUOR', 'POONAWALLA')
  AND date = (SELECT MAX(date) FROM daily_prices)
ORDER BY symbol;
"
```

Then compare those values against `tests/golden_cases.yaml` expectations.

### 5. Run CAS on a real row

```bash
venv/bin/python <<'PY'
import yaml
from engine_core.capital_allocation import (
    load_config, check_eligibility, compute_market_structure,
    compute_market_score, compute_portfolio_allocation_score,
    compute_confidence_stars, render_why_checklist,
)

config = load_config("config/capital_allocation.yaml")

# Example: a passing row (WELCORP scenario from golden_cases.yaml)
row = {
    "regime": "BULLISH",
    "close": 580.0,
    "ema_20": 565.0, "ema_50": 545.0, "ema_100": 520.0, "ema_200": 480.0,
    "ema_100_slope_5": 2.5,
    "breakout_state": "BROKEN_OUT", "breakout_age": 2,
    "volume": 250000, "avg_volume_20d": 180000,
    "avg_volume_20d_close": 180000 * 580.0,  # for liquidity check
    "qif_score": 82,
    "rolling_high_52w": 595.0,
    "weekly_trend_score": 85,
    "rs_90d": 0.08,
    "overhead_supply_score": 22,
    "data_completeness_pct": 100.0,
    "data_age_days": 1,
    "winner_profit_pct": 8.0,
    "concentration_weight_pct": 5.0,
    "proxies_used": {"sector_strength": False},
}
elig = check_eligibility(row, config)
struct = compute_market_structure(row, config)
if elig["passed"] and struct["passed"]:
    sub_scores = {"regime": 100, "weekly": 85, "breakout": 90,
                  "overhead_supply": 22, "rs": 80, "volume": 70, "sector": 50}
    score = compute_market_score(sub_scores, row, config)
    cas = compute_portfolio_allocation_score(score, row, config)
    stars = compute_confidence_stars(row, sub_scores,
                                      row["proxies_used"], config)
    why = render_why_checklist(row, sub_scores, config)
    print(f"Eligibility: {elig}")
    print(f"Structure:   {struct}")
    print(f"Market Score: {score:.1f}")
    print(f"CAS:         {cas:.1f}")
    print(f"Stars:       {stars}/5")
    print(f"Why:")
    for line in why:
        print(f"  {line}")
PY
```

Expected output: eligibility PASS, structure PASS, market score ~85, CAS
~88, 4–5 stars, multi-line why-checklist.

### 6. View the design spec + decision

- **Spec:** `docs/CAPITAL_ALLOCATION_SCORE_PLAN_2026-07-06.md` (rev 3,
  13 sections including the Revision Log)
- **Decision:** `Decisions.md` line 2285+ (Decision 100)
- **Tests as documentation:** `engine_core/test_capital_allocation.py` —
  the test scenarios ARE the spec, executable.

---

## N+2b Update (2026-07-08 afternoon) — backfill complete, latent bug fixed

### What happened

1. **Migration 008 ran via psycopg2** (psql not installed locally) — 4 columns + 3 indexes created on prod DB.

2. **Full Nifty 500 backfill ran** — 961 symbols, 2.15M rows, 114,600 indicator updates written, ~32 min runtime, validation pass (NULL EMA-50 rate 0.0%).

3. **Latent bug discovered and hotfixed (`75f32b3`):**
   - Smoke test on 5 golden-case symbols initially showed 4/5 had `weekly_trend_score = NULL`
   - Root cause: `s_df = df[df["symbol"] == symbol].copy().sort_values("date")` preserved non-contiguous indices from the multi-symbol `df`. `compute_weekly_trend_score` silently returned NaN on non-first symbols because of `pd.date_range.reindex` mismatch.
   - Fix: `.copy().reset_index(drop=True)` — one-line change in `indicator_engine.py`.
   - **This bug was NOT introduced by CAS** — it was latent in the existing indicator pipeline, masked because single-symbol runs work correctly.
   - **Unit tests did NOT catch it** — `test_cas_indicators.py` calls pure functions directly with clean-index synthetic DataFrames.

4. **Post-fix coverage** (latest date 2026-07-07):

   | Column | Non-null symbols (of 498 active) |
   |--------|---------------------------------|
   | `ema_100` | 498 |
   | `rolling_high_52w` | 498 |
   | `weekly_trend_score` | 498 |
   | `overhead_supply_score` | 498 |

   **Weekly trend score distribution:** min=0, avg=44.4, max=100. 138 symbols (28%) ≥ 75 (high quality), 87 (17%) in 50–74 (medium), 273 (55%) < 50 (low).

5. **CAS engine integration sanity check:** ran an INDUSINDBK row through the full pipeline. Failed eligibility on `ema_stack` — this surfaced **5 new known gaps** (see next section).

### Known gaps surfaced by N+2b (please prioritize)

These block API-layer production of real CAS rows. Please tell me which must be solved before V1.1 ships vs which can defer to V1.2:

| # | Gap | Workaround now | Recommendation? |
|---|-----|----------------|-----------------|
| 1 | `ema_100_slope_5d` not computed by `indicator_engine.py`. CAS engine's `ema100_rising` gate reads this field. | Always fails gate | Must fix before V1.1 — quick (5 lines in indicator_engine.py) |
| 2 | `regime` (BULLISH/SIDEWAYS/BEARISH) lives in `market_regime` table, not `daily_prices`. | API must join | Defer — API can join in N+3 |
| 3 | `qif_score` lives in quality table. | API must join | Defer — API can join in N+3 |
| 4 | `data_completeness_pct` and `data_age_days` are derived fields, not in DB. | Compute at API layer | Defer — derive from existing fields |
| 5 | **Decimal → float** conversion needed before CAS engine receives DB rows. Currently throws `TypeError: Decimal * float`. | Convert at API call site | Recommend a single `normalize_row()` helper in `capital_allocation.py` — 10 lines, one place to audit |

### Plus the 8 open questions from the N+2a handoff

These still need expert input — they affect calibration and may matter for V1.1 outcomes. **Please answer the ones you can, and tell me which to defer:**

1. Should `overhead_supply_score` round to 1% buckets to avoid float granularity?
2. `weekly_trend_score` HH/HL: simple week-over-week, or 5-bar fractal with confirmation lag?
3. Should `ema_100` eligibility gate fall back to `ema_50` for thin-history stocks?
4. `overhead_supply_score max_count=10` — right for Indian mid-caps? Worth backtesting 5/10/15?
5. `age_decay` cliff at breakout_age=4 — should detection be a 3-5 zone?
6. Where does `data_age_days` come from in production? Is it reliably populated?
7. Per-factor breakdown logging — separate `cas_breakdown.log` file, or suppress by default?
8. Branch strategy: keep 3 PRs (engine → indicators → API/UI) or squash to 1?

---

## V1.1 Pre-check (proposed scope — please confirm before I start)

Owner approved these 6 work items for V1.1:

- **A. Outcome Tracking** — new table `cas_recommendation_outcomes` with path columns (entry, w1, w2, w4, max_drawdown). Helper `record_cas_outcome()` called from API when banner shown. **NO reports** — just start capturing for 6 months.
- **B. Decision Stability** — `stabilize_action(prev, today, config)` returns `UNCHANGED / UPGRADED / DOWNGRADED / NEW`. Dampens chip changes < 3 points.
- **C. "No Action" Recommendation** — API returns `{action: "NO_ACTION", reason: "..."}` when top-N list empty.
- **D. Design Principles §0** — 7 principles + identity statement at TOP of spec doc (before §1).
- **F. Regression Tolerance** — `assert_cas_within_tolerance(actual, expected, tolerance=2.0)` for golden cases.
- **NEW.** `Calibration.md` journal — every weight/threshold change logged (Date | Old | New | Reason | Expected Effect | Measured Effect) + a "Calibration Debt" counter.

Golden cases (E) **deferred** — wait for real outcomes.

**Please confirm:**

1. **Hysteresis scope:** should `stabilize_action()` apply to API response only, or also persist to DB?
2. **Outcome capture trigger:** on **every CAS row**, or only **eligible/recommended** rows? I recommend the latter (eligible rows only) to avoid storing noise.
3. **§0 location:** inline into existing spec doc, or a separate `docs/DESIGN_PRINCIPLES.md`? I recommend inline (single source of truth).
4. **Calibration Debt metric:** count of hard-coded numbers in `engine_core/` that aren't in YAML. Is this the right definition?
5. **Anything missing** from V1.1 scope you'd want before I start?

---

## Branch State

```
feature/capital-allocation-v1 (pushed to origin):
  0938bb0 docs(cas): record N+2b completion
  75f32b3 fix(indicator): reset_index in per-symbol filter
  b2c4a4a feat(cas): N+2a — 4 new indicator columns
  287f27c refactor(cas): N+1 rev 3 refinements
  f4dc161 feat(cas): N+1 — migration + engine + tests
  63f5fca docs(cas): freeze V1.0 design (rev 2) — on main, ancestor
```

I will not start V1.1 implementation until the expert has had a chance to weigh in on the 5 gaps + 8 open questions + 5 V1.1 scope questions above.


### 7. Branch and PR

```bash
# The branch is already pushed:
git branch -a | grep capital-allocation-v1

# To view the commits:
git log --oneline feature/capital-allocation-v1 ^main

# To open a PR (if you have gh CLI):
gh pr create --base main --head feature/capital-allocation-v1 \
  --title "feat(cas): Capital Allocation Score V1.0 (Decision 100, rev 3)" \
  --body-file docs/CAS_N2A_HANDOFF_2026-07-08.md
```

---

## Test Counts (for the expert's review checklist)

- 104 unit tests across all CAS scoring functions (eligibility, structure,
  sub-scores, multipliers, confidence, why-checklist, breakdown).
- 25 tests across the 4 new indicator functions (EMA-100, rolling high 52w,
  weekly trend, overhead supply).
- 7 golden-case scenarios (regression basket — `tests/golden_cases.yaml`).
- **Total: 137 tests pass in 14.31s.**

The test files are the executable spec — they document expected behavior
with concrete examples.
