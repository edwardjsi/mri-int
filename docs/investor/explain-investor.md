# MRI Platform — Investor's Explanation

> A plain-English walkthrough of every engine in the Market Regime
> Intelligence (MRI) platform: what each one does, how it works
> mechanically, what data it uses, and where to be skeptical.
>
> Every quantitative claim in this document traces back to a specific
> file in this repository. See the **Source Files** section at the
> end — open those files to verify anything that smells off.

---

## What This Repo Is

MRI is a backtested, rule-based quantitative stock-selection and
risk-management system for **Indian listed equities (NSE / BSE)**, built
as a full-stack platform (Python pipeline + FastAPI backend + React
dashboard + Postgres database, deployed on Railway/Neon, originally on
AWS ECS/RDS). The system scores every Nifty 500 stock daily on a
0–100 momentum scale, overlays a market-regime filter on the Nifty 50,
applies seven fundamental "quality" agents, and (in its newest layer)
synthesizes everything into an "expected rerating" score with an AI
debate report. A separate swing-trading engine turns the top-scoring
stocks into concrete entry/stop/target rules.

The intended user experience: post-market email → log into dashboard →
see today's market regime + top-scoring stocks → click a stock → get
a forensic-debate PDF → execute via the swing rules → portfolio is
monitored daily against regime drift.

**What it is not:** a consumer product you can sign up for today, a
brokerage-connected auto-trader, or a price-prediction engine. It is
a research and decision-support platform.

---

## The Big Picture — How The Layers Fit Together

```
            ┌──────────────────────────────┐
            │  Daily EOD Prices (Yahoo/NSE) │
            │  + Quarterly Financials       │
            │  + Earnings Call Transcripts  │
            └──────────────┬───────────────┘
                           │
                ┌──────────┴──────────┐
                ▼                     ▼
        ┌──────────────┐      ┌────────────────┐
        │  Regime       │      │  Indicators     │
        │  (Nifty 50)   │      │  (per stock)    │
        └──────┬───────┘      └────────┬───────┘
               │                       │
               └───────────┬───────────┘
                           ▼
                 ┌─────────────────────┐
                 │  MRI Score (0–100)  │ ← 7 technical conditions
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │  QIF (Fundamentals) │ ← 7 quality agents
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │  AI Debate (GPT-4o) │ ← narrative analysis
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │  PERX / AAE         │ ← composite + lifecycle
                 └─────────────────────┘

         (Parallel track: STEE Swing Execution Engine takes
          the top-scoring stocks and produces concrete trades
          with stop loss, position size, and exit rules.)
```

The regime filter gates everything downstream: if Nifty 50 says
BEARISH, the system goes to cash and writes SELL signals for all
open positions regardless of what individual stocks look like.

---

## Headline Track Record — And How Seriously To Take It

The repo includes a **17-year, 4,237-day backtest** on the full Nifty
500 universe, constructed with two important reality checks:

1. **Survivorship-bias-corrected** — the universe includes stocks that
   were later delisted or merged, not just the survivors you see today.
2. **T+1 execution slippage** — signals buy at the *next day's open*,
   not the same-day close. This is the honest way to simulate "you
   saw the email after market close and acted the next morning."

| Metric | MRI Strategy | Nifty 50 (buy-and-hold) |
|---|---|---|
| CAGR | **26.39%** | 10.08% |
| Max Drawdown | **−35.00%** | −59.86% |
| Sharpe Ratio | **1.48** | ~0.42 |
| Total Trades | 588 | — |
| Final equity (from ₹100k) | ₹67.6 lakh | — |

Source: `FINAL_REPORT.md` (header table + Scenario 1).

A separate walk-forward validation trained the rules on 2005–2015 and
tested them on 2016–2024. Out-of-sample CAGR was **35.78%** with a
Sharpe of 1.44 — *slightly better* than training. That is the single
most encouraging piece of evidence in the repo because it suggests
the rules are not curve-fit.

### Caveats an investor must internalise

- **Backtest ≠ live performance.** Even a well-constructed backtest
  assumes frictionless execution, zero emotion, perfect fills, and no
  tax. Live performance is almost always worse.
- **The regime filter did most of the work.** A large fraction of the
  alpha vs Nifty is simply "be in cash during bear markets." That is
  robust but it is also *lagging* by construction (EMA-200 needs ~200
  trading days to react). The 2020 COVID crash test shows the model
  still lost 18.9% before flipping to BEARISH.
- **Transaction costs are assumed but not punitive.** The system has
  a transaction-cost stress test; results degrade at 2× costs but
  don't collapse.
- **Capacity is bounded but irrelevant for a small investor.** ~35
  trades per year on Nifty 500 names is comfortably executable below
  ₹50 Cr AUM.
- **It is a codebase, not a product.** You cannot `git clone` and
  subscribe. You would consume it as a service if/when the SaaS ships,
  or borrow the mental models and apply them manually.

---

## Every Layer, Explained

### 1. Market Regime Filter

**File:** `engine_core/regime_engine.py`, function `compute_market_regime()`

The full rule is four lines of code:

```python
if   close > ema_200 and ema_50 > ema_200:  classification = 'BULLISH'
elif close < ema_200 and ema_50 < ema_200:  classification = 'BEARISH'
elif abs(close - ema_200) / ema_200 <= 0.02: classification = 'SIDEWAYS'
else:                                       classification = 'NEUTRAL'
```

That is the entire regime model. Four states from two exponential
moving averages (50-day and 200-day) of the Nifty 50 close.

**Why it matters:** this layer is doing the heaviest lifting in the
backtest. Going to cash during BEAR periods is what produces the
~−35% max drawdown vs Nifty's −60%. In the 2008 GFC stress test
(`FINAL_REPORT.md` Scenario 2), the model rotated to cash early and
finished the period at +5.26% vs Nifty −29.22%.

**Investor critique:**

- ✅ Dead simple, no curve-fitting room, auditable in 5 seconds.
- ⚠️ **Lagging by construction.** EMA-200 reflects ~200 trading days
  of price. By the time it flips to BEAR, you have already given back
  ~10–15% from the top.
- ⚠️ **Whipsaw risk in SIDEWAYS markets.** The 2% band around
  EMA-200 means the regime can flip easily in flat tape.
- ⚠️ **Binary worldview.** No "rising-volatility-but-still-bullish"
  nuance. That is a feature for simplicity, a flaw for nuance.

---

### 2. MRI Score (0–100) — Daily Stock Ranking

**File:** `engine_core/regime_engine.py`, function
`compute_stock_scores_for_symbols()` (around lines 175–210).

Each stock gets a 0–100 score based on seven technical conditions,
each weighted. **Important:** the README documents these weights as
25 / 25 / 20 / 20 / 10, but the **actual code** uses:

| # | Condition | Weight | Mechanic |
|---|---|---|---|
| 1 | `ema_50 ≥ ema_200` | **25** | Primary trend |
| 2 | `ema_200_slope_20 ≥ 0` (20-day linear regression slope) | **25** | Trend acceleration |
| 3 | `rs_90d > 0` (relative strength vs Nifty) | **15** | Outperformance |
| 4 | `close ≥ rolling_high_6m × 0.99` | **15** | Near 6-month high |
| 5 | `close > high_10d` | **10** | 10-day breakout |
| 6 | `volume > 1.5 × avg_volume_20d` | **5** | Volume surge |
| 7 | `(close − low) / (high − low) ≥ 0.7` | **5** | Price quality (close in top 30% of day's range) |

A score of **100 (Golden Setup 🚀)** requires all seven conditions to
fire on the same day. That is rare — the README states 80+ qualifies
as "High Conviction Buy."

**Investor critique:**

- ✅ Each condition is a well-known technical filter in the
  Minervini / O'Neil momentum tradition.
- ⚠️ **The weights are judgment calls, not optimized outputs.** A
  26% CAGR is what happens *with these specific weights*. Nobody ran
  a grid search over the weights in front of you (and arguably they
  should not — that is the path to curve-fitting).
- ⚠️ **Score treats binary signals as continuous.** A stock with
  score 75 (three 25-weight conditions) is mechanically equivalent
  to one at 50 (two 25-weight conditions). The granularity is
  coarser than the headline 0–100 number suggests.
- ⚠️ **NaN handling is permissive.** The code does
  `rolling_high_6m.fillna(close).fillna(0)`, which means a brand-new
  IPO with no 6-month history will trivially pass the 6-month-high
  test by filling with its own close. Same trick is used for EMA
  gaps and volume. This masks data-quality issues at the edges of
  the universe.

---

### 3. Signal Generator — Scores Into Buy/Sell

**File:** `engine_core/signal_generator.py` (constants at lines 14–20).

The signal generator takes the regime + scores and produces per-client
buy and sell recommendations. The hardcoded thresholds at the top:

```
MAX_POSITIONS     = 10     # max open positions per client
MIN_BUY_SCORE     = 75     # BULL regime entry threshold
                       85  # NEUTRAL / SIDEWAYS threshold (tighter)
MAX_SELL_SCORE    = 40     # auto-SELL if a holding drops below
MIN_ADTV          = ₹10 Cr # liquidity gate (avg daily turnover)
MAX_SECTOR_STOCKS = 3      # sector concentration cap
MIN_ABSOLUTE_SCORE = 50    # "cash toggle" — never buy below this
```

**The flow:**

1. If regime is **BEARISH**, auto-SELL every open position
   regardless of individual stock scores.
2. Otherwise, check each holding's score; SELL anything ≤ 40.
3. If regime is BULLISH / NEUTRAL / SIDEWAYS and the client has fewer
   than 10 positions, top up with the highest-scoring stocks not
   already held, skipping ones that fail the liquidity gate or
   breach the sector cap.

**Investor critique:**

- ✅ 10-position cap is sane for an individual investor. The sector
  cap prevents concentration risk.
- ✅ The "cash toggle" (skipping scores < 50 even if regime allows)
  is a smart safety valve against weak setups.
- ⚠️ **Advisory only.** Signals are written to the `client_signals`
  table and emailed. Nothing is auto-executed. As an investor, you
  act manually.
- ⚠️ **Sector cap may be cosmetic.** The `_get_sector_proxy()`
  function returns `"UNKNOWN"` when the `stock_sectors` table is
  empty, and the comment mentions falling back to "first letter of
  symbol as proxy." If that table is not populated, the sector cap
  is effectively a no-op.

---

### 4. STEE — Swing Execution Engine

**File:** `engine_core/swing_execution_engine.py` (constants at lines 22–30).

STEE turns the top-scoring stocks into actual trades with concrete
entry, stop, size, and exit rules. The hardcoded parameters:

```
RISK_PER_TRADE_PCT = 0.01   # 1% of capital at risk per trade
MIN_ADTV           = ₹10 Cr
MAX_GAP_UP_PCT     = 4.0    # skip entries that gap up >4%
MAX_ATR_MULT       = 2.0    # skip candles >2× ATR (overextended)
ATR_STOP_MULT      = 2.0    # stop distance = 2× ATR
ATR_SIZE_MULT      = 1.5    # min risk per share for sizing
```

**Entry trigger (must pass all five):**

1. Regime ≠ BEARISH
2. `close > high_10d` (10-day high breakout)
3. `volume > 1.5 × avg_volume_20d` (volume confirmation)
4. `(close − low) / (high − low) ≥ 0.7` (close in top 30% of range)
5. Gap-up < 4% AND candle range ≤ 2 × ATR

**Position sizing formula:**

```python
qty = (Capital × 1%) / max(entry - 5d_low, 1.5 × ATR)
```

The ATR blend is genuinely clever — volatile names automatically get
smaller position sizes. In SIDEWAYS regimes the risk per trade is
halved to 0.5%.

**Exit ladder (priority order):**

1. **Hard stop:** close ≤ stop loss (whichever is *higher* of 5-day
   low or entry − 2× ATR).
2. **Trailing ratchet:** once the trade is ≥1R in profit, trail the
   stop to current price − 0.5R.
3. **Partial profit:** exit 50% at 2R (entry + 2× risk).
4. **Trend break:** exit the remaining 50% if close < EMA-10.

Every entry and exit is logged to `system_audit_logs` with reason
codes (`STOP_LOSS`, `TRAIL_UPDATE`, `PARTIAL_EXIT`, `TRAILING_STOP_EMA10`).
That kind of audit trail is unusual discipline for a retail-grade
system.

**Investor critique:**

- ✅ Hybrid exit (partial at 2R + EMA-10 trail for remainder) is
  professional-grade money management.
- ✅ ATR-based stop prevents being shaken out on normal volatility.
- ⚠️ The file references `TRAIL_ACTIVATE_AT_R` and `TRAIL_DISTANCE_R`
  but those constants are not defined in this file. They likely
  live in `engine_core/config.py`. If you actually run this, confirm
  the trailing-stop parameters are loaded correctly.
- ⚠️ The SIDEWAYS-regime 0.5% risk modifier is sensible but not
  documented in the README.

---

### 5. QIF — The 7 Fundamental Quality Agents

**File:** `engine_fundamental/agents.py` (seven independent functions).

Each agent is a deterministic rule-based scorer that returns a 0–10
score with a human-readable reason. The seven:

| # | Agent | Mechanic | What it catches |
|---|---|---|---|
| 1 | **Revenue Quality** | 10 if YoY growth > 12% with non-declining margins; 7 if > 8%; 3 otherwise | Genuine growth vs stagnation |
| 2 | **Margin Quality** | 10 if EBITDA margins trending up; 7 if flat; 2 if declining | Pricing power / moat |
| 3 | **Operating Leverage** | 10 if EBITDA growth ≥ 1.5× revenue growth | Scale economics vs M&A optics |
| 4 | **Working Capital** | **2 (red flag)** if receivables growth > revenue growth + 5pp; else 8 | **Channel stuffing** — receivables outpacing sales is one of the most reliable fraud-detection heuristics in practice |
| 5 | **Capital Efficiency (ROCE vs WACC)** | 10 if ROCE > WACC + 5pp; 7 if > WACC; **0** if < WACC | Pure economic-profit test |
| 6 | **Business Evolution** | 8 if assets growing AND margins stable/up; else 5 | Capacity expansion proxy |
| 7 | **Financial Translation** | 10 if (EBITDA − Δreceivables) / net profit > 0.8; else as low as 2 | **Earnings-quality audit** — flags profits without cash backing |

WACC is **hardcoded at 12%** in the file.

**Investor critique:**

- ✅ These are the heuristics a good fundamental analyst uses,
  codified deterministically. The receivables-vs-revenue check is
  genuinely valuable — it would have flagged Satyam-style
  aggressive revenue recognition years before the crash.
- ⚠️ **Each agent uses only 2 data points** (latest vs prior year).
  A business turning around after one bad quarter will score poorly
  because one bad observation dominates.
- ⚠️ **WACC is sector-blind.** 12% is fine for diversified Indian
  equities, but banks should discount at ~9% and capital-intensive
  infra should discount at ~13%+. A bank with ROCE 13% gets a "0"
  here when it should be a "7".
- ⚠️ **No real cash-flow statement.** The Financial Translation
  agent uses receivables as a proxy for cash conversion — better
  than nothing, but inferior to actual CFO/EBITDA which would
  require an explicit cash flow dataset.
- ⚠️ **No debt-quality check beyond ROCE.** A company with great
  margins but rising leverage is invisible to these agents.

---

### 6. AI Forensic Debate Engine

**File:** `engine_qualitative/debate.py` (called from
`engine_perx/orchestrator.py`).

This is the GPT-4o-mini layer. The debate receives:

- QIF snapshot (the 7-agent scores and reasons)
- MRI snapshot (the 0–100 technical score with sub-conditions)
- Transcript extracts from `engine_qualitative/narrative_tracer.py`
- Guidance extracts from `engine_guidance/guidance_extractor.py`
- Credibility scoring from `narrative_credibility_scorer.py`

It produces a structured bull thesis, bear thesis, verdict
(score/10 + BUY/HOLD/AVOID), and "what would change my mind."

The PERX layer then converts the verdict into a numeric adjustment:

```python
# From engine_perx/scoring.py
debate_adjustment = (debate_score - 5.0) * 2.0   # range: -20 to +20
```

So the AI's verdict can move PERX by at most ±20 points — small
relative to the deterministic components, large enough to break ties.

**Investor critique:**

- ✅ The adjustment is *small* (±20 max). The AI is a tie-breaker,
  not the boss. If you disable the debate call, the system still
  functions.
- ✅ The credibility-scoring agents explicitly try to detect
  "Management Theatre" — when tone doesn't match words, or when
  positive assertions are made while omitting negative qualifiers
  found elsewhere.
- ⚠️ **This is GPT-4o-mini, not GPT-4o.** It is the cheap, fast
  model. Fine for triage but prone to generic-sounding analysis.
- ⚠️ **Narrative scraping reliability is unproven.** The
  transcript-discovery logic depends on data sources that may not
  cover all Nifty 500 names reliably.
- ⚠️ **No validation against known frauds or pumps.** The
  credibility score is architecturally impressive but I see no
  evidence it has been back-tested against historical
  management-deception cases. Treat the debate as one input, not
  as gospel.

---

### 7. PERX / AAE — The Synthesis Layer

**File:** `engine_perx/orchestrator.py` + `engine_perx/scoring.py`.

PERX is the institutional-grade composite that pulls everything
together. The actual formula (`compute_perx_score`):

```
PERX = (MRI      × 0.35)
     + (QIF      × 0.40)
     + (STEE     × 0.15)
     + (Trajectory × 0.10)
     + Debate adjustment
     − (Fragility × 0.15)
```

So **fundamentals (QIF) actually weigh more than technicals (MRI)** —
40% vs 35%. Trajectory is only 10%, swing setup only 15%.

**Lifecycle classification** (`classify_lifecycle_stage`):

- PERX ≥ 82 + MRI ≥ 80 + QIF ≥ 75 + Low fragility → **Institutional Expansion**
- PERX ≥ 72 + MRI ≥ 70 + QIF ≥ 70 → **Early Rerating** ← the sweet spot
- PERX ≥ 85 + High fragility → **Euphoria** (warning flag)
- Else → **Accumulation** or **Distribution**

The fragility penalty (`compute_fragility_snapshot`) is the only
risk overlay. It adds points for:

- Negative QIF score change vs prior snapshot (+20)
- Negative trajectory velocity (+10)
- QIF already in REJECT bucket (+30)
- Debt / Equity ≥ 1.0 (+20) or ≥ 0.5 (+10)
- Strong technical score but no breakout confirmation (+15)
- Weak technical confirmation overall (+15)

**Investor critique:**

- ✅ Weights are documented in code and make sense.
- ✅ Lifecycle classification is genuinely useful — "Early
  Rerating" is exactly the category an investor actually wants.
- ⚠️ **Fragility is the only risk layer.** No macro overlay, no
  interest-rate sensitivity, no commodity-price sensitivity for
  commodity-linked businesses, no currency risk for exporters or
  importers. A perfect PERX score on a commodity exporter mid-cycle
  is dangerous.
- ⚠️ **No sector-relative normalization in PERX itself.** A QIF of
  60 in IT services (sector medians are tight) and a QIF of 60 in
  capital goods (high variance) are treated identically.
- ⚠️ **Trajectory weight is too low at 10%.** Score velocity is one
  of the most predictive inputs over a 6–18 month horizon. The
  current weighting under-emphasizes it.
- ⚠️ **AAE is the newest and least validated layer.** The
  governance, ownership, and narrative agents (`aae_*.py`) are
  architecturally ambitious but operationally unproven. There is
  no out-of-sample backtest yet.

---

## Cross-Cutting Strengths

1. **Disciplined layering.** Every module is deterministic and
   independently auditable. You can disable the AI debate and the
   system still runs. You can disable the fundamental agents and
   the technical system still runs. There is no hidden dependency.
2. **Realistic backtest construction.** Survivorship-bias-corrected
   universe + T+1 execution slippage + transaction-cost stress
   test + walk-forward out-of-sample validation. Better than 95% of
   retail backtests you will see anywhere.
3. **Risk controls are baked in.** Regime filter, position caps,
   sector caps, ATR-based sizing, hard stops, partial profit,
   trailing stop, audit logging — risk management is treated as a
   first-class feature, not an afterthought.
4. **Defensive coding.** NaN handling, holiday gates, schema
   auto-heal, connection cleanup, parameterized SQL queries, the
   documented RDS-safeguard history (`Decisions.md` Decisions
   026/027). This is not a one-off script — it is production-grade
   engineering.

---

## Cross-Cutting Weaknesses

1. **Regime lag is the dominant edge and the dominant risk.**
   EMA-200 takes ~200 trading days to react. In a fast crash
   (COVID test: −18.9% before flip), you bleed first.
2. **Hardcoded magic numbers everywhere.** WACC = 12%, MIN_BUY_SCORE
   = 75/85, MAX_GAP_UP_PCT = 4%, ATR multiples, score weights.
   None are sector-adjusted. None are documented as optimization
   outputs — they are judgment calls. That is honest, but it also
   means a single set of numbers has to work across IT services,
   banks, capital goods, FMCG, and pharma.
3. **No short side.** The 2008 stress test showed +5.26% return by
   going to cash; shorting would have done much better. But shorting
   is operationally complex for retail Indian investors (SLB, F&O
   eligibility, borrow costs, taxes on speculative income).
4. **QIF is point-in-time, not trajectory.** Each agent uses the
   latest year vs the prior year only. Five-year trends are
   invisible. A business turning around after a bad year will
   score poorly because one bad observation dominates.
5. **Capacity ceiling.** ~35 trades per year on Nifty 500 names
   is comfortably executable below ₹50 Cr AUM. Beyond that you
   start to move the market on smaller names and the slippage
   assumption breaks.
6. **The AAE narrative layer is architecturally ambitious but
   operationally unproven.** The credibility-scoring,
   intonation-extraction, and management-theatre detectors are
   interesting ideas. I see no evidence they have been validated
   against historical narrative-pump or accounting-fraud cases.
   The PDFs they produce look professional but the underlying
   signal-to-noise ratio is unmeasured.

---

## How I Would Actually Use This As A Small Investor

If I were deploying real money against this codebase today, here is
what I would do:

1. **Run it in shadow mode for 6 months.** Subscribe to the daily
   email, watch the signals, but execute manually with paper
   trades. Compare *your* P&L to MRI's signals. The gap between
   the two is your real edge — it will be smaller than the
   backtest's 26% CAGR, and you need to know by how much before
   you commit real capital.
2. **Trust the regime filter and the 7-step MRI score.** Both are
   rule-based, transparent, and well-tested in the backtest.
   They are the most defensible parts of the system.
3. **Use the QIF as a filter, not a trigger.** It is good at saying
   "avoid this one" (the receivables-vs-revenue red flag is
   genuinely valuable). It is less good at saying "buy this one"
   because of the 2-data-point limitation and sector-blind WACC.
4. **Discount the AI debate to a tie-breaker.** Use it only when
   two stocks have identical mechanical scores and you genuinely
   cannot choose. Do not let it override a clear technical + QIF
   signal.
5. **Run the STEE rules on your broker terminal manually.** The
   entry / stop / size / exit rules are documented well enough
   that you do not need the system to execute them. The 1%-risk
   sizing, the 2R partial, the EMA-10 trailing exit are sound
   money management on their own.
6. **Skip PERX until it has a verified out-of-sample track
   record.** It is the newest layer and the most architecturally
   ambitious — which is precisely why it is the least validated.
   Wait until you can see how PERX-flagged candidates actually
   performed 6 and 12 months later, on a universe that was not
   used to design the scoring weights.

---

## Source Files

Everything in this document traces to one of the following files in
this repository. Open them to verify any claim that smells off.

### Architecture and backtest

- `Readme.md` — system overview, scoring framework documentation
- `docs/PLUMBING_AND_ORCHESTRATION.md` — system map and data flow
- `FINAL_REPORT.md` — Phase 10 stress test, all backtest scenarios
- `AAE V3.md` — Active Alpha Engine PRD, philosophical foundations
- `SaaS_Blueprint.md` — Phase 1 SaaS product architecture
- `MRI_UNIVERSE_IMPLEMENTATION.md` — universe validation logic
- `Decisions.md` — Decision 026 (RDS destroy incident),
  Decision 027 (RDS safeguards), and the architecture decision log

### Core engines

- `engine_core/regime_engine.py` — Market regime + MRI Score
  (the 7-condition scoring is in `compute_stock_scores_for_symbols`)
- `engine_core/indicator_engine.py` — EMA, RS, ATR, rolling highs
- `engine_core/signal_generator.py` — Buy/sell signal generation,
  client portfolio logic, tracking tables
- `engine_core/swing_execution_engine.py` — STEE entry / exit /
  position sizing
- `engine_core/ingestion_engine.py` — Daily EOD data ingestion
- `engine_core/email_service.py` — AWS SES daily digest
- `engine_core/config.py` — Pipeline configuration
  (where `TRAIL_ACTIVATE_AT_R` / `TRAIL_DISTANCE_R` likely live)

### Fundamental quality

- `engine_fundamental/agents.py` — The 7 QIF agents, full source
- `engine_fundamental/pipeline.py` — QIF aggregation
- `engine_fundamental/collector.py` — Financial statement fetcher
- `engine_fundamental/trajectory.py` — Score velocity engine
- `engine_fundamental/sector_engine.py` — Sector-relative analysis
- `engine_fundamental/governance_engine.py` — Governance kill switch

### Qualitative / debate

- `engine_qualitative/debate.py` — GPT-4o-mini forensic debate
- `engine_qualitative/extractor.py` — QIL extraction layer
- `engine_qualitative/credibility_scorer.py` — Credibility scoring
- `engine_qualitative/narrative_tracer.py` — Transcript delta
  tracking

### Guidance

- `engine_guidance/guidance_extractor.py` — Management guidance
  extraction from transcripts
- `engine_guidance/guidance_verifier.py` — Guidance-vs-actuals check
- `engine_guidance/credibility_scorer.py` — Credibility weighting

### PERX / AAE synthesis

- `engine_perx/orchestrator.py` — PERX scan orchestrator
- `engine_perx/scoring.py` — Composite formula, lifecycle
  classification, fragility scoring
- `engine_perx/report_builder.py` — Report assembly
- `engine_perx/pdf_generator.py` — Branded PDF output
- `engine_perx/sector.py` — Sector context
- `engine_perx/analogs.py` — Historical rerating analogs
- `engine_perx/investor_context.py` — Investor-context aggregation

### AAE specific

- `engine_perx/aae_orchestrator.py` — AAE master orchestrator
- `engine_perx/aae_sourcing_agent.py` — Candidate sourcing
- `engine_perx/aae_structural_signal_agent.py` — Structural signal
- `engine_perx/aae_macro_agent.py` — Macro overlay
- `engine_perx/aae_re_rating_orchestrator.py` — Re-rating master
- `engine_perx/aae_execution_monitoring_agent.py` — Execution
  monitoring

---

*Document version: 2026-06-17. The MRI codebase is actively
developed. Weights, thresholds, and architecture may have changed
since this was written. Always re-verify against the current
source before relying on any specific claim.*
