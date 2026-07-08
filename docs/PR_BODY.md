# Capital Allocation Score V1.1 — Release Candidate

> **This PR establishes the scoring and decision infrastructure. Future improvements should primarily come from outcome-based calibration rather than additional scoring factors.**

---

## Summary

Implements **Capital Allocation Score V1.1** (Decision 100/101/102) — transforms MRI from a breakout screener into a **portfolio decision engine**.

New capabilities:
- **Market Score** — composite of 7 weighted factors (regime, weekly trend, breakout, overhead supply, R/R, R/S, volume, sector)
- **Capital Allocation Score (CAS)** — Market Score × winner/concentration multipliers
- **Decision Layer** — tiers (WATCH / FIRST_TRANCHE / ADD_SECOND_TRANCHE), hysteresis (no flip-flops), NO_ACTION semantics
- **Outcome Tracking** — every recommendation (BUY/ADD/WATCH) is persisted with milestones at w1/w2/w4/m3/m6
- **Calibration Framework** — `Calibration.md` journal + `config/calibration_registry.yaml` registry
- **Regression Tolerance** — golden cases checked against ±2.0 CAS points

---

## Major Components

- **Eligibility engine** — 8 hard gates (regime, ema_stack, breakout_state, liquidity, quality, weekly_data, rs_data, qif_data)
- **Weekly trend indicators** — EMA10/20/50/100 stack, weekly HH/HL detection
- **Overhead supply indicators** — swing-high counts in last 126 days
- **Outcome persistence** — `cas_recommendations` + `cas_recommendation_outcomes` tables
- **Decision stability** — tier-based hysteresis (`±hysteresis_cas = 3.0` around tier boundaries)
- **Recommendation UUIDs** — `CAS-YYYY-MM-DD-SYMBOL` format, deterministic + human-readable
- **Calibration registry + journal** — every tunable versioned with status (hypothesis/validated/deprecated)
- **Regression tolerance tests** — golden cases from `tests/golden_cases.yaml`

---

## Validation (5-gate release candidate framework per Decision 102)

| Gate | Result | Detail |
|------|--------|--------|
| 1. All tests green | ✅ PASS | **259/259** pytest pass |
| 2. Golden cases | ✅ PASS | **7/7** within ±2.0 CAS tolerance |
| 3. Distribution sanity | ✅ PASS | Saturation **83% → 35.5%** post-calibration (target 20–40%) |
| 4. Top-20 eyeball test | ✅ PASS | 9/9 candidates pass Buffett sniff test |
| 5. Rank correlation | ✅ PASS | 9/9 leaderboard overlap preserved, Spearman ρ=0.683 |

Full technical detail: [`docs/CAS_V11D_VALIDATION.md`](./CAS_V11D_VALIDATION.md)

Top-9 eyeball test: [`docs/CAS_TOP20_V11D.md`](./CAS_TOP20_V11D.md)

---

## Calibration Notes

Applied during V1.1d (post-review override per expert feedback Q2):

- `subscore.overhead_supply.max_count_for_100`: **10 → 20**
  - Reason: 83% saturation at cap → no discriminatory power
  - Effect: Saturation now 35.5%, dynamic range restored
  - Status: **validated** via distribution check (not outcome-driven yet)

- **Calibration freeze**: V1.1 weights will not be tweaked for 100 recommendations after merge
- **Re-calibration triggers**: at 100 / 250 / 500 recommendations (not calendar intervals)
- **Outcomes will drive future tuning**: every NEW recommendation tracked → calibration journal entries once measured

---

## Known Limitations

- Sector strength still proxy-based (`sector.proxy_score_v1 = 50`)
- Weekly trend uses simple HH/HL (5-bar fractal detection deferred to V2)
- Overhead supply uses fixed swing-high counts (ATR-aware buckets deferred)
- Regime and QIF are API-layer integrations scheduled for V1.2
- Outcome tracking started 2026-07-07 — no calibration decisions yet from observed outcomes
- 6 thin-history symbols (3BBLACKBIO, SKFINDUS, VAML, VEDPOWER, VISL, VOGL) excluded (engine requires ≥20 rows)

---

## Follow-up: V1.2 Priorities (Decision 102 Q4)

1. **Regime-aware API** — read regime from detector, not hardcoded `BULLISH`
2. **QIF joins** — replace `proxy_score_v1` placeholder
3. **EMA50 fallback** — for thin-history stocks
4. **ATR-aware overhead buckets** — dynamic swing-high detection
5. **Weekly fractals** (V2+) — replace week-over-week HH/HL with 5-bar fractal detection

---

## Stats

- **Commits**: 23 ahead of `main`
- **Tests**: 104 → 259 (+155 over V1.0)
- **Migrations**: `008_capital_allocation_columns.sql`, `009_cas_recommendations.sql`
- **New tools**: `distribution_sanity_check.py`, `top20_report.py`, `calibration_debt.py`
- **New docs**: `CAS_SPEC.md`, `CAS_V11D_VALIDATION.md`, `CAS_TOP20_V11D.md`, `Calibration.md`

---

*Merge V1.1, let it run, start collecting recommendation outcomes. From here, the project's biggest improvements come from measuring how well the engine predicts successful capital allocation — not from making the scoring engine more elaborate.*
