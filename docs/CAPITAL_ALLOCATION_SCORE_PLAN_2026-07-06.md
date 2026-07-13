# Capital Allocation Score — V1.0 Design Doc

> **Status:** DRAFT — rev 2, awaiting owner approval before any code change.
> **Frozen:** 2026-07-06 (rev 1) → revised 2026-07-06 (rev 2)
> **Owner:** Immanuel Santosh
> **Source spec:** User-supplied observation 2026-07-06 ("Breakout Radar identifies who is breaking out, but not which deserves fresh capital today.") + rev 2 critique of the initial design.

---

## 1. Goal

A two-stage **Capital Allocation Score (CAS)** that answers two questions:

| Score | Question | Scope |
|---|---|---|
| **Market Score** | "How attractive is this stock today?" | Universal — identical for all users |
| **Portfolio Allocation Score** | "Should **I** put my next ₹20,000 here?" | Per-user — uses portfolio context |

The banner at the top of the **Breakout Radar** and **Dashboard** pages surfaces the top N candidates by Portfolio Allocation Score. Each card shows: Symbol, CAS, **Confidence (★)**, Action chip (FIRST TRANCHE / ADD SECOND TRANCHE / WATCH), **Breakout Age emoji** (🔥 Today / 🟢 Yesterday / 🟡 3 Days / ⚪ 5 Days), and a structured **Why** checklist (multi-line ✓ bullets, not a single sentence).

---

## 2. Frozen Decisions (rev 2)

### 2.1 Architecture: Hard Sub-Gates + Weighted Ranking

The Market Score is NOT a simple weighted sum. It is a sequence of hard PASS/FAIL checks followed by a weighted numeric score for survivors only.

```
Eligibility Filter (6 hard gates)
   ↓
   reject → out
   ↓
Market Score Hard Sub-Gates (3 hard gates: Trend, Breakout, Quality)
   ↓
   reject → out  (a stock cannot compensate for a weak weekly trend
                    with huge volume — we don't allow that in MRI)
   ↓
Market Numeric Score = weighted sum of remaining factors
                       (Regime, RS, Volume, Sector, Overhead Supply, plus
                        a softer numeric component from Weekly/Breakout/Quality)
   ↓
Portfolio Multipliers (Winner × Concentration)
   ↓
Portfolio Allocation Score (CAS)
   ↓
Confidence (★)
   ↓
Action Chip
```

### 2.2 Eligibility Filter Thresholds

| Rule | Threshold | Reason |
|---|---|---|
| Market Regime | BULLISH or SIDEWAYS (BEARISH passes only if `aggressive_mode = true`) | Avoid swimming against the tide |
| EMA Stack (RELAXED rev 2) | **4 conditions** (all must hold): `Close > EMA20` AND `EMA20 > EMA50` AND `EMA50 > EMA200` AND `EMA100_rising` | Strict `20>50>100>200` rejects some of the biggest winners (EMA100 hasn't crossed yet). The relaxed stack still enforces bullish structure. |
| Breakout | `breakout_state = BROKEN_OUT` AND `breakout_age ≤ 5` | Avoid stale setups |
| Liquidity | Avg traded value ≥ ₹10 Cr/day | Matches Decision 029 |
| Quality Score (RAISED rev 2) | QIF overall ≥ **70** (was 65) | "Fewer, better ideas" — MRI's whole point |
| 52-Week Position | `close ≥ 0.90 × rolling_high_52w` | Within 10% of 52w high — leaders, not laggards |

### 2.3 Market Score Hard Sub-Gates (rev 2 — these cannot be compensated)

| Sub-Gate | Threshold | Why |
|---|---|---|
| **Trend PASS/FAIL** | `weekly_trend_score ≥ 50` | Weekly structure must be meaningfully bullish. If not, stock is out regardless of volume/RS/sector strength. |
| **Breakout PASS/FAIL** | `breakout_age ≤ 3` | Stricter than eligibility (≤ 5). Filters for "fresh" not "early but no longer fresh". |
| **Quality PASS/FAIL** | `QIF ≥ 75` | Stricter than eligibility (≥ 70). Enforces high quality on top of passable quality. |

### 2.4 Market Score Weighted Factors (rev 2 rebalance)

R/R was **removed** (proxy was too arbitrary). Overhead Supply was **added**. Other factors were rebalanced to sum to 100.

| Factor | Weight | Why |
|---|---|---|
| Market Regime | 23% | Never fight the market — single biggest edge |
| Weekly Structure | 21% | Multi-component: HH + HL + above EMAs + near 52w high |
| Breakout Quality | 17% | Revised up — strategy is about fresh reratings |
| **Overhead Supply** (NEW) | 14% | The user's rev 2 insight: clean air matters; Poonawalla-style overhead is a real reason to pass |
| Relative Strength | 11% | Leaders keep leading |
| Volume | 8% | Institutions leave footprints |
| Sector Strength | 6% | Sector rotation matters but isn't decisive |
| **Total** | **100%** | |

`winner` (existing holding with profit) and `concentration` are **multipliers**, not weights.

### 2.5 Two-Score Model
- **Market Score** = weighted sum of sub-scores (only for stocks passing all sub-gates). Universal.
- **Portfolio Allocation Score** = Market Score × `winner_multiplier` × `concentration_multiplier`. Personalized.

### 2.6 Multiplier Model — "Existing Winner" (rev 2 — softened cap)

Per user spec: existing profit is a multiplier, not a weight. Cap reduced from +15% to **+10%** so existing holdings reinforce without dominating rankings.

| Profit % | Multiplier (rev 2) |
|---|---|
| +30% | 1.10 (clamped) |
| +10% | 1.10 |
| +5% | 1.05 |
| 0% | 1.00 |
| -5% | 0.95 |
| -10% | 0.90 |
| -15% | 0.85 (clamped) |

### 2.7 Concentration Penalty (unchanged)
At 0% weight → 1.00×. At ≥15% weight → 0.90× (max -10%).

### 2.8 Confidence (NEW rev 2)

A 0–5 **★** rating displayed next to the CAS. Stars depend on 5 binary criteria. Users grasp "5 of 5 stars" faster than "92% confidence".

| Star | Criterion | Threshold |
|---|---|---|
| ★ | No proxies used | All sub-scores use real data (no V1.0 sector proxy, no V1.0 RR proxy since RR is deferred) |
| ★ | Data completeness | ≥ 90% of expected columns populated |
| ★ | Factor agreement | Sub-scores within 20 std-dev (low disagreement) |
| ★ | Trend maturity | `weekly_trend_score ≥ 75` |
| ★ | Breakout maturity | `breakout_age ∈ [1, 3]` (not too fresh, not too stale) |

### 2.9 Breakout Age in UI (NEW rev 2)

Surfaced with emoji so users understand urgency:

| Age | Emoji | Meaning |
|---|---|---|
| 0 | 🔥 | Today |
| 1 | 🟢 | Yesterday |
| 2 | 🟢 | 2 Days |
| 3 | 🟡 | 3 Days |
| 4 | 🟡 | 4 Days |
| 5 | ⚪ | 5 Days |
| > 5 | ⚫ | Stale (not shown in eligibility-passing banner) |

### 2.10 Structured "Why" Templates (rev 2)

Multi-line ✓ checklist instead of single sentence. Templates evaluate row + sub-scores; matching lines are appended.

Example output:
```
✓ Weekly trend strengthening (HH + HL)
✓ Fresh breakout today (Day 0)
✓ Near 52-week high
✓ Strong RS (top quartile)
✓ Volume confirmation (2.3x average)
✓ Clear overhead supply (score 18/100)
✓ High QIF (82/100)
✓ Existing winner (+18%)
```

---

## 3. Per-Factor Sub-Score Formulas (rev 2)

### 3.1 Market Regime (23%)
- BULLISH → 100
- SIDEWAYS → 60
- BEARISH → 20

### 3.2 Weekly Structure (21%) — Multi-Component (rev 2)

NOT just EMA distance. Five binary components, summed, max 100:

| Component | Weight | Definition |
|---|---|---|
| Higher Highs confirmed | 25 | Current swing high > previous swing high (last N weeks) |
| Higher Lows confirmed | 25 | Current swing low > previous swing low |
| Above weekly EMA-13 | 20 | Close > `weekly_ema13` (forward-filled to daily) |
| Above weekly EMA-20 | 15 | Close > `weekly_ema20` |
| Within 5% of 52w high | 15 | `close ≥ 0.95 × rolling_high_52w` |

Note: `weekly_ema13` and `weekly_ema20` are computed via `daily_prices.resample('W-FRI').agg(...)` then forward-filled to daily. Higher Highs/Lows use a swing-detection algorithm (e.g., 5-bar fractal or rolling max with confirmation lag).

### 3.3 Breakout Quality (17%)
- Base = `100` if `breakout_age == 0`, else `AGE_DECAY[breakout_age]` per Decision 099.
- Volume bonus: `+10` if `volume ≥ 2 × avg_volume_20d`.
- Final = `clamp(base + volume_bonus, 0, 100)`.

### 3.4 Overhead Supply (14%, NEW rev 2)

Counts distinct swing highs in the last 6m that are above the current close. The more overhead resistance, the higher the score (worse for breakout).

```python
def overhead_supply_score(prices_df, current_close, lookback=126, max_count=10):
    recent = prices_df.tail(lookback)
    above_close = recent[recent['high'] > current_close]
    distinct_highs = above_close['high'].drop_duplicates()
    score = min(len(distinct_highs) / max_count * 100, 100)
    return score  # 0 = clear air, 100 = max resistance
```

**NEW column**: `overhead_supply_score` on `daily_prices`.

### 3.5 Risk/Reward (REMOVED from V1.0)

Per rev 2: dropped because the proxy was arbitrary. Returns in V1.1 with a real `support_3m` column.

### 3.6 Relative Strength (11%)
- `rs_90d` already on `daily_prices` (Decision 030).
- `score = clamp(rs_90d / 0.10 × 100, 0, 100)` (100 = Nifty +10% over 90d).

### 3.7 Volume (8%)
- `score = 100 × clamp((volume / avg_volume_20d - 1.0) / 2.0, 0, 1)`.

### 3.8 Sector Strength (6%)
- V1.0: `score = 50` (neutral proxy).
- V1.2: real `sector_rs_60d` column.

### 3.9 Portfolio Concentration (multiplier only)
- `weight_pct = (current_position_value / total_capital) × 100` (per-client).
- `multiplier = 1 - clamp(weight_pct / 15, 0, 1) × 0.10`.

---

## 4. Final Score → Action Chip

```
if cas >= 85:   action = "ADD SECOND TRANCHE"
elif cas >= 70: action = "FIRST TRANCHE"
elif cas >= 50: action = "WATCH"
else:           # not on banner
```

---

## 5. Confidence Stars → Display (rev 3: model certainty, not stock quality)

```python
def compute_confidence_stars(row, sub_scores, proxies_used, config):
    cal = config["calibration"]["confidence"]
    conf = config["confidence"]["factors"]
    stars = 0

    # 1. Complete data (≥ 90% of fields populated)
    if (row.get("data_completeness_pct") or 0) >= cal["complete_data_threshold_pct"]:
        stars += int(conf["complete_data"]["weight"])

    # 2. Factor agreement (sub-scores within 20 std-dev, ALL on goodness scale)
    # overhead_supply inverted BEFORE std-dev so all factors share direction
    if len(sub_scores) >= 2:
        aligned = {k: (100 - v if k == "overhead_supply" else v)
                   for k, v in sub_scores.items()}
        if float(np.std(list(aligned.values()), ddof=0)) <= cal["factor_agreement_max_std_dev"]:
            stars += int(conf["factor_agreement"]["weight"])

    # 3. Stable calculations (not at AGE_DECAY cliff, breakout_age=4)
    if row.get("breakout_age") != cal["stable_breakout_age_cliff"]:
        stars += int(conf["stable_calculations"]["weight"])

    # 4. Low proxy usage (real indicators preferred over placeholders)
    if sum(1 for v in proxies_used.values() if v) <= cal["low_proxy_usage_max_proxies"]:
        stars += int(conf["low_proxy_usage"]["weight"])

    # 5. Indicator freshness (data_age_days ≤ max_age_days)
    age_days = row.get("data_age_days")
    if age_days is not None and age_days <= cal["indicator_freshness_max_age_days"]:
        stars += int(conf["indicator_freshness"]["weight"])

    return min(stars, 5)
```

### Star Semantics (rev 3)

| Star | Question it answers | Source |
|------|---------------------|--------|
| Complete data       | Are enough fields populated to compute reliably?        | `data_completeness_pct ≥ 90%` |
| Factor agreement    | Are the sub-scores pointing the same direction?         | `std-dev(aligned sub-scores) ≤ 20` |
| Stable calculations | Are we sitting on a noisy edge case (AGE_DECAY cliff)?  | `breakout_age ≠ 4` |
| Low proxy usage     | Are real indicators used instead of placeholders?       | `proxies_used count ≤ 0` |
| Indicator freshness | Are the inputs current, not stale?                      | `data_age_days ≤ 5` |

### Why these (and not the rev 2 list)

**rev 2 had `trend_maturity` + `breakout_maturity`** as stars. Both are STOCK-QUALITY signals, not model-certainty signals. A stock can be high-quality but the model can be uncertain about its score (e.g., missing data, low agreement). Confidence should measure the latter, not the former.

- Trend strength and breakout freshness still appear in the CAS number, the Why-checklist, and the `breakout_age_emoji`. They are not lost — they are just in the right place.
- The `overhead_supply` sub-score uses "badness" semantics (0 = clear air = good). For factor_agreement std-dev, it is inverted (100 − raw) so all factors share the same "higher = better" direction. This is essential — otherwise an obvious good stock would always lose a star.

UI renders as `★★★★★` (filled), `☆☆☆☆☆` (empty), with hover tooltip explaining each star's state. Tunable thresholds live in `config/capital_allocation.yaml` → `calibration.confidence`.

---

## 6. V1.0 / V1.1 / V1.2 Scope (rev 3)

### V1.0 — THIS RELEASE (4 new columns)

| New column | Factor(s) it serves | Engine |
|---|---|---|
| `ema_100` | Eligibility (EMA stack — `ema100_rising` check) | `engine_core/indicator_engine.py` |
| `rolling_high_52w` | Eligibility (52w position) + Weekly Structure | `engine_core/indicator_engine.py` |
| `weekly_trend_score` | Weekly Structure + Trend sub-gate | `engine_core/indicator_engine.py` |
| `overhead_supply_score` | Overhead Supply | `engine_core/indicator_engine.py` |

Dropped from V1.0: `resistance_6m` (no longer needed without R/R; replaced by `overhead_supply_score`).

Intermediate columns computed in memory (not persisted): `weekly_ema13`, `weekly_ema20`, `hh_confirmed`, `hl_confirmed`.

**R/R fallback**: not used in V1.0. CAS formula just doesn't reference it.
**Sector fallback**: `score = 50` (neutral proxy) until V1.2.

### V1.1 — NEXT RELEASE (1 new column)
- `support_3m` on `daily_prices`. Enables real R/R sub-score, weight restored at 12% (Regime/Weekly/Breakout rebalance accordingly).

### V1.2 — LATER (1 new column + engine)
- `sector_rs_60d` on `stock_sectors`. Real Sector Strength sub-score.

### V2 — FUTURE (deferred)
- Per-row CAS column in radar tables.
- Cross-sectional ranking / z-score normalization.
- Weight rebalancing from backtest.
- Historical CAS time series.
- Dedicated "Capital Allocation" page (full-page UI with sortable columns, filters, position-size controls).
- Portfolio optimizer (sell-what-to-fund, sector exposure caps).
- Email integration (add CAS section to daily digest).

---

## 7. File Changes — V1.0 (rev 3)

| File | Change |
|---|---|
| `config/capital_allocation.yaml` (NEW) | Threshold + weight config (this doc is the spec). Rev 3 added `calibration` section — all numeric thresholds live here, NOT in Python. |
| `migrations/008_capital_allocation_columns.sql` (NEW) | `ALTER TABLE daily_prices ADD COLUMN IF NOT EXISTS ...` for 4 new columns |
| `engine_core/indicator_engine.py` | Add 4 new column computations; multi-component weekly trend; overhead supply |
| `engine_core/capital_allocation.py` (NEW) | `load_config(path)`, `check_eligibility` (8 gates incl. `weekly_data`, `rs_data`), `compute_market_structure` (rev 3 rename from `check_market_subgates`), `compute_market_score`, `compute_market_score_breakdown` (rev 3, for per-factor logging), `compute_portfolio_allocation_score`, `compute_confidence_stars` (rev 3: 5 model-certainty stars), `render_why_checklist` |
| `engine_core/test_capital_allocation.py` (NEW) | 24 scenarios / 92 unit tests + 7 golden-case scenarios / 7 regression tests = **104 tests** |
| `tests/golden_cases.yaml` (NEW) | Regression basket: WELCORP / CHOLAFIN / PHOENIXLTD / NAVINFLUOR / POONAWALLA + bearish + missing-data scenarios |
| `engine_core/email_service.py` (no change in V1.0) | V2: add CAS section to daily email |
| `api/breakout_status.py` | Wire CAS into existing `/radar`; new endpoint `GET /api/breakout/top-by-cas?limit=5&client_id=...`; include `market_score`, `cas`, `confidence_stars`, `breakout_age_emoji`, `why_checklist` in response |
| `api/schema.py` | Add 4 new indicator columns to auto-heal block (defense in depth) |
| `requirements.txt` | Add `pyyaml>=6.0` (needed to parse the YAML config) |
| `frontend/src/BreakoutRadar.tsx` | Compact CAS banner above existing sections; 5-card grid |
| `frontend/src/Dashboard.tsx` | Top banner; same endpoint; same card design |
| `frontend/src/api.ts` | New `getTopByCAS(limit, clientId?)` method |
| `frontend/src/CapitalAllocationCard.tsx` (NEW) | Card component: symbol, CAS, ★ confidence, action chip (color-coded), breakout age emoji, multi-line Why checklist |
| `docs/Sessions.md` + `docs/Progress.md` | Session entry (N+1: pure engine + tests; N+2: indicators; N+3: API + UI) |
| `Decisions.md` | Decision 100 — Capital Allocation Score V1.0 (rev 3) |

---

## 7a. Branch Strategy

Three PRs, one per implementation session. Makes review and revert clean.

| PR | Branch | Scope |
|----|--------|-------|
| PR1 | `feature/capital-allocation-v1` | Migration + pure engine + tests (this session, N+1) |
| PR2 | `feature/capital-allocation-v1-indicators` | Indicator engine wiring + schema auto-heal + backfill (N+2) |
| PR3 | `feature/capital-allocation-v1-api-ui` | API endpoints + frontend components (N+3) |

---

## 8. Verification Plan — V1.0 (rev 3)

1. **Indicator engine** (`engine_core/indicator_engine.py`) — N+2:
   - `python3 -c "import ast, sys; ast.parse(open(sys.argv[1]).read())"` → clean.
   - Run on 5 hand-picked symbols from `tests/golden_cases.yaml` regression basket
     (CHOLAFIN, WELCORP, PHOENIXLTD, NAVINFLUOR, POONAWALLA); verify all 4 new columns
     populate with non-null values for the last 60 trading days.
   - Manual cross-check of `weekly_trend_score` for 1 stock: should sum the 5 components correctly per the plan doc §3.2.
   - Manual cross-check of `overhead_supply_score` for Poonawalla (should be HIGH, lots of overhead) vs NAVINFLUOR (should be LOW, clear air).
2. **CAS unit tests** (`engine_core/test_capital_allocation.py`, NEW) — N+1:
   - **104 tests** total, all passing as of rev 3:
     - 5 sub-score (regime, weekly 6 cases, breakout 11 cases, overhead_supply, rs+volume+sector).
     - 3 portfolio multiplier (winner 8 cases, concentration 5 cases, combined).
     - 9 eligibility / structure (combined pass, multi-fail, regime 4 cases, EMA stack 4 cases, trend/breakout/quality structure, all-required, weekly_data, rs_data).
     - 5 confidence (per-star 12 cases, full 5 stars, zero, partial 3, max-clamped).
     - 3 why-checklist (matching lines, missing fields, value interpolation).
     - 2 breakdown (score + contributions sum; matches simple).
     - **7 golden-case regression scenarios** from `tests/golden_cases.yaml`.
   - Run: `pytest engine_core/test_capital_allocation.py -v`.
3. **API** (`api/breakout_status.py`) — N+3:
   - `python3 -c "import ast, sys; ast.parse(open(sys.argv[1]).read())"` → clean.
   - Curl `/api/breakout/top-by-cas?limit=5` against Railway → 5 cards with non-null `cas`, `confidence_stars`, `action`, `breakout_age_emoji`, `why_checklist[]`.
   - Curl `/api/breakout/radar` → each row now includes `market_score`, `cas`, `confidence_stars`, `eligibility_passed`, `structure_passed`.
4. **Frontend** — N+3:
   - `npx tsc --noEmit` → 0 errors.
   - `npm run build` → 0 errors, no chunk-size regression.
   - Visual spot-check on Railway: banner renders, action chips color-coded (green/amber/blue), Why text shows as multi-line checklist, confidence stars render correctly, breakout age emoji visible.
5. **Live**: Railway deploy + visual banner spot-check + curl smoke tests.

---

## 9. Risk Analysis

| Risk | Likelihood | Mitigation |
|---|---|---|
| 4 new columns blow up indicator runtime | Med | Each is single pandas op; ~10% overhead |
| Weekly aggregation DST/holiday edge cases | Low | `resample('W-FRI')` is stable for Indian market |
| Sub-gate rejection rate too high (banner empty) | Med | "Show all" fallback bypasses eligibility + sub-gates, returns top 5 by raw Market Score |
| Overhead Supply score too noisy | Med | Conservative max_count = 10 swing highs; verify on Poonawalla vs NAVINFLUOR before shipping |
| HH/HL swing detection false positives | Low | Use 5-bar fractal with confirmation lag (require 3 bars after to confirm); test on 5 known symbols |
| Confidence stars always 3/5 (mediocre) | Low | Tunable via YAML per criterion; can rebalance weights later |
| EMA `ema100_rising` noise | Low | Use 5-day slope; only fires if slope > 0 with absolute magnitude > 0.1% |

---

## 10. Out of Scope (V1.0)

- Per-row CAS column in the radar tables (V2)
- Cross-sectional ranking / z-score normalization (V2)
- Weight rebalancing from backtest (V2)
- Historical CAS time series (V2)
- Dedicated "Capital Allocation" page (V2)
- Portfolio optimizer (V2)
- LLM explanation of top drivers (defer unless requested)
- Email integration (V2 — add CAS section to daily digest)
- Webhook / push notification on banner change (V2+)

---

## 11. Rev 2 Design Rationale

This is the user's rev 2 critique distilled:

1. **"Don't use a weighted score for the Market Score."** — Fixed by adding hard sub-gates for Trend, Breakout, Quality. A weak weekly trend no longer gets papered over by huge volume.
2. **"EMA Stack is too strict."** — Relaxed from `20>50>100>200` to 4-component check (Close>20, 20>50, 50>200, EMA100 rising).
3. **"Quality ≥ 70."** — Raised from 65 to 70.
4. **"Liquidity 10 Cr is fine."** — Unchanged.
5. **"Biggest missing feature: Overhead Supply."** — Added new 14% weighted factor; new `overhead_supply_score` column.
6. **"Weekly Trend Score too simplistic."** — Upgraded from EMA distance to 5-component score (HH, HL, above weekly EMA-13/20, within 52w high).
7. **"R/R proxy worries me. Remove it."** — Dropped from V1.0. Returns in V1.1 with real `support_3m`.
8. **"Sector = 50. Perfect."** — Kept.
9. **"Winner multiplier cap 1.10."** — Reduced from 1.15 to 1.10.
10. **"Concentration penalty excellent. No change."** — Kept.
11. **"Surface Breakout Age in UI with emoji."** — Added: 🔥🟢🟡⚪⚫.
12. **"Make Why a structured checklist, not a single sentence."** — Done via `why_templates` list with template strings and conditions.
13. **"Biggest missing: Confidence (★), not Score."** — Added 5-star rating with 5 binary criteria, displayed next to CAS.

---

## 12. Open Questions for Owner (before code)

None. All 13 design points locked 2026-07-06 (rev 2).

---

## 13. Revision Log

### rev 3 — 2026-07-07 (Implementation Refinements)

Owner reviewed rev 2 implementation and requested 8 design refinements + 1 recommendation. All applied:

| # | Change | Why |
|---|--------|-----|
| 1 | Confidence = **5 model-certainty stars**, not stock quality | Stock-quality signals (trend/breakout maturity) belong in CAS, not in confidence about the score itself |
| 2 | Confidence criteria: Complete data, Factor agreement, Stable calculations, Low proxy usage, Indicator freshness | All 5 dimensions measure "how much can we trust THIS score" |
| 3 | **All calibration constants moved to YAML `calibration.*`** | Backtesting should tune YAML, never touch Python |
| 4 | Invert `overhead_supply` BEFORE factor_agreement std-dev | All factors share the same semantic direction (higher = better) |
| 5 | Missing critical market data → **Ineligible, not score of 0** | The model REFUSES to score rather than guess with 0s |
| 6 | Added 2 eligibility gates: `weekly_data`, `rs_data` | Explicit missing-data failure modes (defense in depth) |
| 7 | Renamed `check_market_subgates` → `compute_market_structure` | Investment-concept-aligned naming (assesses structure, not just "sub-gates") |
| 8 | Added `compute_market_score_breakdown()` for per-factor logging | Log/return contributions from day one, even before UI displays them |
| +1 | Created `tests/golden_cases.yaml` regression basket | Curated scenarios (WELCORP, CHOLAFIN, etc.) protect against tuning regressions |

Branch strategy: 3 PRs (engine → indicators → API/UI). PR1 is `feature/capital-allocation-v1`.

**Documentation invariant (per owner):** Design Doc → YAML → Code → Sessions.md. Never let code intentionally diverge from spec. When the design changes, update all artifacts.

### rev 2 — 2026-07-06 (Initial Design Freeze)

13 design points from user feedback. See §11 for the rationale. Key decisions:
- R/R removed from V1.0 (deferred to V1.1)
- Overhead Supply added as new sub-score
- Market Score has 3 hard sub-gates (not just weighted sum)
- EMA stack relaxed (4 conditions, not strict 20>50>100>200)
- Winner cap reduced 1.15 → 1.10
- Confidence stars added
- Why-checklist restructured (multi-line, not single sentence)

---

## 14. V2 Pyramiding Discipline Gates (Decision 103, 2026-07-13)

### 14.1 Why this exists

The current `ADD_SECOND_TRANCHE` path (`compute_action` in `engine_core/cas_recommendations.py`) only checks three conditions: `CAS ≥ 85`, `confidence_stars ≥ 4`, and `has_existing_position=True`. After BreakoutRadar adoption, owner judged this too loose — the second ₹20k should be **earned** through layered checks, not just because CAS crossed 85.

This section defines the V2 gate model that protects capital deployment while preserving the existing CAS ≥ 85 / 5-star discipline.

### 14.2 Gate spec (canonical)

All five gates must pass for an action to upgrade from `READY_FOR_ADD` to `ADD_SECOND_TRANCHE`.

| # | Gate | Threshold | Source | Purpose |
|---|------|-----------|--------|---------|
| G1 | `decision_score ≥ 85` | `add_gate.decision_score_min` | YAML | Capital allocation quality |
| G2 | `mri_technical_score ≥ 80` | `add_gate.mri_technical_min` | YAML | Technical structure still strong |
| G3 | `weekly_close > resistance` | computed; enum source | enum | True breakout — price discovery |
| G4 | `volume_confirmed_breakout == True` | `add_gate.breakout_volume_ratio` (default 1.3) | YAML + DB | Institutional sponsorship |
| G5 | `breakout_age ≤ 15 trading days` | `add_gate.breakout_age_max` | YAML | Opportunity still fresh |

Plus the existing precondition `confidence_stars ≥ add_gate.confidence_stars_min` (default 4) — now also YAML-driven.

### 14.3 G3 resistance selection (C1 thin-history fallback)

```text
history_weeks = floor((today - earliest_price_date) / 7)
mode = "PRIOR_52W_HIGH"     if history_weeks ≥ add_gate.weekly_breakout_min_history_weeks (default 52)
       "ALL_TIME_HIGH"       otherwise
resistance = prior_52w_high                       if mode == "PRIOR_52W_HIGH"
             all_time_high_before_current_week    if mode == "ALL_TIME_HIGH"
gate passed iff weekly_close > resistance
```

Both columns precomputed on `daily_prices`. `resistance_source` stored as enum per row for auditability.

Rationale (owner): "The system already favours emerging rerating candidates. A stock listed 8–10 months ago shouldn't be permanently excluded just because it lacks a full year of history."

### 14.4 G4 versioned metadata (C2)

`volume_confirmed_breakout` is computed **once** on the breakout day and frozen. To support future calibration audits, the following columns are persisted alongside the boolean:

| Column | Purpose |
|--------|---------|
| `breakout_day_volume` | Raw volume on breakout day |
| `breakout_day_avg20_volume` | 20-day average volume at breakout day |
| `breakout_day_volume_ratio` | Computed ratio (e.g. 2.4) |
| `volume_threshold_used` | The actual threshold applied (e.g. 1.3) — so 6 months later, if we change the threshold to 1.5, we still know which historical recommendations were generated under the 1.3 rule |
| `breakout_date_for_volume` | Date the ratio was computed |
| `volume_confirmed_breakout` | Boolean: `ratio is not None AND ratio ≥ volume_threshold_used` |

### 14.5 Decision state model (4 layers)

| CAS | Gates | Final state | UI | Action |
|-----|-------|-------------|-----|--------|
| < 80 | — | `OBSERVE` | ⚪ Observe | None |
| 80–84 | — | `APPROACHING_ADD` | 🟡 Approaching ADD | WATCH |
| ≥ 85 | some fail | `READY_FOR_ADD` | 🟢 Ready for ADD (n/N gates passed) | WATCH |
| ≥ 85 | all pass + position + stars | `ADD_SECOND_TRANCHE` | 🚀 ADD SECOND TRANCHE | ADD |

`READY_FOR_ADD` was renamed from `ELIGIBLE_ADD_BLOCKED` (C6) — the stock is fundamentally ready; the user should see exactly what is still missing.

`READY_FOR_ADD` surfaces `gates_passed / gates_total` and a list of specific missing gates (C7 gate confidence metric). Binary passed/blocked was rejected as too lossy.

### 14.6 Architectural invariants

1. **No hardcoded gate constants in Python.** Every threshold reads from `config/capital_allocation.yaml` under `add_gate.*` (C3).
2. **Calibration version persisted.** `add_gate.version: "2.0.0"` is snapshotted into `cas_recommendations.factor_snapshot.config_snapshot.version` on every recommendation (C5). Historical recommendations remain reproducible even if the YAML evolves.
3. **Resistance source is a Python enum** (`ResistanceSource.{PRIOR_52W_HIGH, ALL_TIME_HIGH}`), not free text (C9). Validated, testable, queryable.
4. **Score single-responsibility.** `radar_priority` ranks the radar; `decision_score` is the capital allocation gate (G1); `mri_technical_score` is technical confirmation (G2). These are intentionally separate — overlap of `decision_score` × `mri_technical_score` is acceptable per owner (different questions). Revisit only if backtest correlation ρ > 0.9.
5. **Backward compatible.** If `evaluate_add_gates()` is called with `gate_inputs=None`, `compute_action()` falls back to the legacy CAS+stars-only behavior. Existing 259 tests stay green; V2 ships incrementally.
6. **`approaching_add` surface cap.** CAS 80–84, top 20 by `radar_priority`, radar page only, no notifications (C4). Tunable via `approaching_add.radar_top_n`.

### 14.7 `evaluate_add_gates()` output shape

```python
{
    "all_passed": bool,
    "gates_passed": int,                                  # C7
    "gates_total": int,                                   # C7
    "gate_score_pct": float,                              # C7 — gates_passed / gates_total × 100
    "blocked_gates": list[str],
    "gate_results": {
        "G1_decision_score":      {"value": float, "threshold": 85, "passed": bool},
        "G2_mri_technical_score": {"value": float, "threshold": 80, "passed": bool},
        "G3_weekly_breakout":     {"value": bool, "weekly_close": float, "resistance": float, "resistance_source": "PRIOR_52W_HIGH" | "ALL_TIME_HIGH", "passed": bool},
        "G4_volume_confirmed":    {"value": bool, "ratio": float, "threshold_used": float, "passed": bool},
        "G5_breakout_age":        {"value": int, "max": 15, "passed": bool},
        "confidence_stars":       {"value": int, "min": 4, "passed": bool},
    },
    "resistance_source": "PRIOR_52W_HIGH" | "ALL_TIME_HIGH",   # C9 enum
    "final_state": "ADD_SECOND_TRANCHE" | "READY_FOR_ADD",
    "config_snapshot": {                                    # C5 audit
        "version": "2.0.0",
        "add_gate": {...},
    },
}
```

### 14.8 P6 backtest success metrics (C8)

Before the 5 `PROPOSED` gate thresholds move to `VALIDATED`, the following must hold on trailing 6 months of data:

| Metric | Definition | Target |
|--------|-----------|--------|
| ADD signals/month | Count of new ADD recommendations in trailing 30d | ≤ 5 |
| % outperform benchmark @ 20d | `(return_pct_20d - benchmark_return_pct_20d) > 0` | ≥ 60% |
| % outperform benchmark @ 60d | Same at 60 trading days | ≥ 60% |
| % outperform benchmark @ 120d | Same at 120 trading days | ≥ 55% |
| Win rate vs CAS-only model | 5-gate ADD wins / CAS-only ADD signals in same period | ≥ CAS-only win rate |
| Avg max drawdown after ADD | Mean of (lowest close in 60d post-ADD) / entry − 1 | < −12% |

If any target missed → write `Calibration.md` journal entry; tighten before validation. Do NOT silently adjust thresholds.

### 14.9 Schema delta

```sql
-- G3
ALTER TABLE daily_prices
  ADD COLUMN IF NOT EXISTS prior_52w_high NUMERIC,
  ADD COLUMN IF NOT EXISTS all_time_high_before_current_week NUMERIC,
  ADD COLUMN IF NOT EXISTS resistance_source TEXT,
  ADD COLUMN IF NOT EXISTS weekly_close_above_resistance BOOLEAN;

-- G4 (versioned metadata, not just boolean)
ALTER TABLE daily_prices
  ADD COLUMN IF NOT EXISTS breakout_day_volume NUMERIC,
  ADD COLUMN IF NOT EXISTS breakout_day_avg20_volume NUMERIC,
  ADD COLUMN IF NOT EXISTS breakout_day_volume_ratio NUMERIC,
  ADD COLUMN IF NOT EXISTS volume_threshold_used NUMERIC,
  ADD COLUMN IF NOT EXISTS breakout_date_for_volume DATE,
  ADD COLUMN IF NOT EXISTS volume_confirmed_breakout BOOLEAN;
```

Full migration: `migrations/010_add_second_tranche_gates.sql` (P2).

### 14.10 Alternatives considered (rejected)

| Choice | Picked | Rejected | Why rejected |
|--------|--------|----------|--------------|
| Resistance | 52w high + ATH fallback | Daily pivot / weekly EMA-13 / prior swing high | 52w high aligns with Decision 029/081; alternatives tie strategic rule to tactical pattern or measure trend not breakout |
| Volume threshold | Breakout-day ratio ≥ 1.3× | Today's ratio / 1.5× / weekly aggregate | Captures institutional sponsorship at the moment that matters; doesn't penalize healthy post-breakout consolidation |
| ADD floor | Keep CAS ≥ 85 + 5 gates | Lower ADD to CAS ≥ 80 | Owner: "the second ₹20k is earned" — lowering without backtest is intuition not evidence |
| Score overlap | Keep both `decision_score` + `mri_technical_score` | Drop one | Each answers a different question; revisit only after backtest ρ > 0.9 |
| Surface noise | Top-20 cap, radar page only | Email notifications for CAS 80+ | Alert fatigue; tighten later if still noisy |

### 14.11 Implementation phases (P1 → P7)

| Phase | Scope | Status |
|-------|-------|--------|
| **P1** | Decision 103 + §14 + YAML `add_gate`/`approaching_add` + calibration registry + Sessions.md + Progress.md | **In progress (docs only)** |
| P2 | Migration `010_*.sql` + 4 new indicator functions + unit tests | Pending |
| P3 | `evaluate_add_gates()` + extended `compute_action()` + `compute_layered_state()` + tests | Pending |
| P4 | API enrichment + new `GET /api/cas/add-eligibility` | Pending |
| P5 | Frontend `AddStatusChip` + BreakoutRadar column integration | Pending |
| P6 | Backtest validation against 6 trailing months (6 success metrics) | Pending |
| P7 | Final: Sessions.md, Progress.md, Decisions.md final entry, push | Pending |

### 14.12 Cross-references

- Discussion record: `docs/CAS_V2_PYRAMIDING_DISCUSSION_2026-07-13.md`
- Calibration journal: `Calibration.md` (5 new entries)
- Calibration registry: `config/calibration_registry.yaml` (5 new `PROPOSED` entries)
- Spec: `docs/CAS_SPEC.md` §6
- Implementation: `engine_core/cas_recommendations.py` (`evaluate_add_gates`), `engine_core/cas_decision_layer.py` (`compute_layered_state`), `engine_core/cas_indicators.py` (4 new pure functions)
- Migration: `migrations/010_add_second_tranche_gates.sql`

### 14.13 Calibration freeze

All 5 new gate thresholds are `PROPOSED`. Move to `VALIDATED` only after P6 hits all 6 success metric targets. **No weight/gate tweaks for 100 ADD recommendations post-merge** — re-validate at 100 / 250 / 500 ADD signals, same as CAS V1.1 freeze (Decision 102).

