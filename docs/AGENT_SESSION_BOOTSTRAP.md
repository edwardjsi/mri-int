# Agent Session Bootstrap

> **Read this file FIRST at the start of every new session.**
> It is the compressed memory of prior sessions so you do not re-spend tokens
> re-reading the whole repo. Last updated: 2026-06-29.

This file exists because each session starts stateless. The only thing that
survives between sessions is what is written to the repo. This file is the
single entry point — read it, then branch into specific files only as needed.

---

## 1. What this project is (one paragraph)

MRI (Market Regime Intelligence) is a quantitative equity intelligence platform
for Indian listed equities (NSE/BSE). It combines: (a) a 7-step weighted
technical momentum score (MRI Score, 0–100), (b) a 7-agent fundamental quality
framework (QIF), (c) a GPT-powered forensic bear/bull debate engine, (d) a
swing-trade breakout execution engine (STEE), and (e) a PE re-rating discovery
layer (PERX/AAE). Daily pipeline ingests Nifty 500 EOD prices, computes
indicators, regime, scores, signals, and emails a digest. Backend = FastAPI
monolith on Railway; DB = Neon.tech (prod) + AWS RDS (legacy/backup); frontend
= React+Vite+Tailwind served from the same container. Solo dev: Immanuel
Santosh.

## 2. Where the canonical truth lives

| Need | Read |
|------|------|
| Project overview / architecture | `Readme.md` |
| System plumbing + data flow | `docs/PLUMBING_AND_ORCHESTRATION.md` |
| This bootstrap (you are here) | `docs/AGENT_SESSION_BOOTSTRAP.md` |
| All architectural decisions | `Decisions.md` (append-only; next free # = 099) |
| Session-by-session history | `Sessions.md` |
| Milestones / what's done / what's next | `Progress.md`, `Tasks.md` |
| Agent rules + RDS protection | `AGENTS.md` |
| PRDs in repo | `docs/PRD_001_MOSI_LITE_ENGINE.md`, `docs/Perx PRD.md`, `docs/AAE_PRD.md`, `docs/SWING_TRADING_PRD.md` |

**Critical rules (NEVER violate):** See `AGENTS.md` — RDS protection (Decisions
026/027). Never `terraform destroy` without `terraform state rm module.rds.*`.
Never suggest `terraform destroy -target=module.vpc`. Never weaken RDS
`deletion_protection` / `skip_final_snapshot=false` / `prevent_destroy=true`.

## 3. Repo layout (only the dirs that matter)

```
mri-int/
├── api/                    # FastAPI routers (auth, signals, breakout_status, pe_expansion, ...)
│   ├── main.py             # app + router registration
│   ├── schema.py           # CREATE TABLE IF NOT EXISTS for ALL tables (idempotent, auto-heals on startup)
│   ├── breakout_status.py  # /api/breakout/radar + /api/breakout/map  ← MOSI Lite integration point
│   └── deps.py             # get_db dependency
├── engine_core/            # regime, indicators, ingestion, signals, STEE, email
│   └── regime_engine.py   # compute_stock_scores() → writes stock_scores.total_score (the MRI 0–100 score)
├── engine_fundamental/     # QIF 7-agent scoring; collector.py (yfinance); pipeline.py
├── engine_qualitative/     # QIL narrative layer
├── engine_debate/          # GPT bear/bull forensic debate + cache
├── engine_guidance/        # management guidance credibility + ConvictionEngine
├── engine_perx/            # PE re-rating orchestrator + report builder
├── engine_mosi/            # MOSI Lite engine (NEW — added 2026-06-29)  ← see §6
├── frontend/src/           # React dashboard
│   ├── App.tsx             # main shell, page router
│   ├── BreakoutRadar.tsx   # Breakout Radar UI  ← MOSI Lite display point
│   └── api.ts              # fetch wrapper; getBreakoutRadar() → /breakout/radar
├── scripts/                # pipeline_cloud.sh, backtest_*.py, health monitors
├── migrations/             # SQL migrations (idempotent ADD COLUMN IF NOT EXISTS)
├── docs/                   # all PRDs, plans, session notes
└── terraform/              # modules: vpc, rds, ecs, s3, iam
```

## 4. Key DB tables + columns (the ones you'll actually JOIN)

| Table | Key columns | Notes |
|-------|-------------|-------|
| `daily_prices` | symbol, date, close, high, low, volume, ema_50, ema_200, ema_200_slope_20, rolling_high_6m, avg_volume_20d, rs_90d, high_10d, breakout_state | breakout_state ∈ {BROKEN_OUT, READY_TO_BREAKOUT, CONSOLIDATING}. No 52w-high column — derive via window over 255 rows. |
| `stock_scores` | date, symbol, **total_score** (0–100 MRI), condition_ema_50_200, condition_ema_200_slope, condition_6m_high, condition_volume, condition_rs, condition_breakout_10d, condition_price_quality | Written by `regime_engine.compute_stock_scores()`. This is `technicalScore` / `mri_score`. |
| `fundamental_financials` | symbol, year, revenue, ebitda, net_profit, total_assets, capital_employed, receivables, inventory, debt, equity, operating_cashflow, free_cashflow | Yearly. Compute sales/profit growth YoY from consecutive years. |
| `quality_verdicts` | symbol (UNIQUE), score, category, revenue_score, margin_score, leverage_score, wc_score, roce_score, evolution_score, qil_score, flags, **agent_details JSONB** (Decision 098 — per-quarter metrics + trajectory) | agent_details may be `'{}'::jsonb` for un-backfilled stocks — handle null/empty. |
| `client_watchlist` | client_id, symbol | |
| `client_portfolio` | client_id, symbol, is_open | |

Schema is idempotent — `api/schema.py` runs `CREATE TABLE IF NOT EXISTS` +
`ALTER TABLE ... ADD COLUMN IF NOT EXISTS` on app startup. Adding columns is safe.

## 5. Data-availability audit for MOSI Lite (PRD-001)

PRD input field → where it lives in the repo. **Bottom line: every field is
already available — no new data collection needed.**

| PRD field | Source | Table.column / derivation |
|-----------|--------|---------------------------|
| `technicalScore` (MRI) | ✅ | `stock_scores.total_score` |
| `salesGrowth` | ✅ derivable | `fundamental_financials.revenue` YoY, or `quality_verdicts.agent_details.by_quarter[].growth_yoy_pct` |
| `profitGrowth` | ✅ derivable | `fundamental_financials.net_profit` YoY |
| `roce` | ✅ | `quality_verdicts.roce_score` (0–10) + `agent_details` underlying % |
| `roe` | ✅ derivable | `fundamental_financials.net_profit / equity` |
| `debtToEquity` | ✅ | `fundamental_financials.debt / equity` |
| `promoterHolding` | ✅ | `promoter_holding_pct` (schema.py line 469) |
| `52WeekHigh` | ✅ derivable | `MAX(high) OVER (PARTITION BY symbol ORDER BY date ROWS 255 PRECEDING)`; fallback `rolling_high_6m` |
| `quarterlyGrowth` (acceleration) | ✅ | `quality_verdicts.agent_details.by_quarter[]` (Decision 098 backfill) |
| Stage 2 trend | ✅ derivable | `ema_50 > ema_200 AND ema_200_slope_20 > 0` (Weinstein Stage 2) |
| `sector`, `industry` | ✅ | `prde_companies.sector/industry` |
| `marketCap` | ✅ derivable | close × shares outstanding (yfinance) — not critical for Lite |
| Breakout Radar UI | ✅ exists | `frontend/src/BreakoutRadar.tsx` + `api/breakout_status.py` `/api/breakout/radar` |

## 6. MOSI Lite implementation (PRD-001) — in progress 2026-06-29

**Decision 099 (FINAL):** Implement in **Python** (`engine_mosi/`), not the
PRD's literal `services/mosiLite.ts`. Reason: repo has no JS test runner but
has 47+ pytest tests; user explicitly chose "fit existing infra." Pure
functions + swappable-output-contract goal still met — UI renders only the
output dict, so MOSI Lite → Full MOSI swap needs no UI change.

**Scoring (max 100):**
- M Macro (20): sector > market (10), industry > sector (10)
- O Operating (30): sales growth >15% (10), profit growth >15% (10), ROCE >20% (10)
- S Structural (30): near 52w high (10), Stage 2 trend (10), quarterly acceleration (10)
- I Institutional (20): promoter holding >50% (10), debt/equity <0.5 (10)

- `decisionScore = clamp(0.6*MRI + 0.4*MOSI, 0, 100)`
- `confidence`: Bull→HIGH, Sideways→MEDIUM, Bear→LOW (regime = module constant, default SIDEWAYS)
- `recommendation`: ≥90 TODAYS_PICK, 80–89 RESEARCH, 70–79 WATCHLIST, <70 IGNORE

**Files (planned/done):**
- `engine_mosi/mosi_lite.py` — pure functions
- `engine_mosi/test_mosi_lite.py` — 7+ pytest cases (ROCE, sales, debt, missing data, decision, confidence, recommendation)
- `api/breakout_status.py` — enrich `/radar` query to JOIN stock_scores + quality_verdicts + fundamental_financials + daily_prices, then call `analyze_stock()` per row
- `frontend/src/BreakoutRadar.tsx` — render MRI / MOSI Lite / Decision / Confidence / Recommendation; sort by Decision Score desc

## 7. Standard verification commands

```bash
# Python syntax check
python -m py_compile api/breakout_status.py engine_mosi/mosi_lite.py

# Run backend tests (47+ exist)
python -m pytest engine_core engine_fundamental engine_debate api -q

# Run MOSI Lite tests
python -m pytest engine_mosi/test_mosi_lite.py -v

# Frontend typecheck + build
cd frontend && npx tsc --noEmit && npm run build

# Start local API
uvicorn api.main:app --reload
```

## 8. How to start a session (the 5-minute ramp)

1. Read this file.
2. `git log --oneline -10` to see what shipped recently.
3. `tail -60 Sessions.md` + `tail -60 Progress.md` for current state.
4. Check `Decisions.md` for the latest decision number (next = 099+).
5. Only then read deep docs if the task needs them.

---

*If you add a new engine, table, or major capability, append a row to §4/§5/§6
so the next session inherits it. Keep this file under ~250 lines.*
