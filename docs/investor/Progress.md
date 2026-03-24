# BUILD PROGRESS

> [x] = Done | [/] = In Progress | [ ] = Not Started

---

## Phase 0: Session Persistence Infrastructure
- [x] README.md, SESSION.md, DECISIONS.md, PROGRESS.md, .llm-context.md created

---

## Phase 1: 10-Day Research Prototype

### Day 1 — Terraform Infrastructure
- [x] VPC provisioned (ap-south-1)
- [x] RDS PostgreSQL created (db.t3.micro, engine 15.15)
- [x] S3 bucket created (mri-dev-outputs-251876202726)
- [x] IAM roles created (ECS task execution + task role)
- [x] Secrets Manager: DB credentials stored
- [x] terraform apply outputs confirmed

### Day 2 — Data Ingestion
- [x] NSE EOD data source confirmed
- [x] data_loader.py written
- [x] Historical data (2005–present) loaded into RDS
- [x] Data quality report generated, duplicate/missing row validation passed

### Day 3 — Indicator Engine
- [x] EMA 50 + EMA 200 implemented and unit tested
- [x] 200 EMA slope (20-day regression) implemented
- [x] 6-month rolling high implemented
- [x] 20-day average volume implemented
- [x] 90-day relative strength vs Nifty implemented
- [x] Indicators stored in RDS

### Day 4 — Regime Engine
- [x] regime_engine.py written
- [x] Daily Risk-On/Off classification computed
- [x] Regime history table (2005–present) stored
- [x] Regime vs index chart generated

### Day 5–6 — Stock Trend Scoring Engine
- [x] trend_engine.py written
- [x] Daily 0–5 score computed for all stocks
- [x] No look-ahead bias confirmed
- [x] Score dataset stored in RDS
- [x] 20 random days manually spot-checked

### Day 7–8 — Portfolio Simulation Engine
- [x] portfolio_engine.py written
- [x] Entry logic implemented (Regime=Risk-On, Score ≥ 4, Top 10)
- [x] Exit logic implemented (Score ≤ 2, Regime shift, 20% trailing stop)
- [x] Transaction cost (0.4%) applied
- [x] Equity curve generated, trade log CSV exported to S3

### Day 9 — Metrics Module
- [x] CAGR, Max Drawdown, Sharpe, Sortino, Calmar calculated
- [x] Rolling 3-year CAGR calculated
- [x] Nifty buy-and-hold benchmark compared
- [x] Performance summary table exported

### Day 10 — Stress Tests + Final Report
- [x] 2008 crisis, 2020 COVID, 2010–2013 sideways simulations run
- [x] Transaction cost doubled (0.8%) test passed
- [x] Walk-forward validation (train 2005–2015, test 2016–present) passed
- [x] Final Markdown report compiled, all outputs stored in `outputs/`

### Go/No-Go Decision
- [x] CAGR > Nifty, Max DD < Nifty DD, Sharpe ≥ 1.0, Walk-forward Sharpe ≥ 0.8
- [x] Stable across 3+ regimes, survives doubled transaction cost

**VERDICT: GO. PHASE 1 COMPLETED. → PHASE 2: WEB APP MVP**

---

## Phase 2 — Web App MVP

### Step 1: Data Bridge — Nifty 50 (2024–March 2026)
- [x] Resumed RDS, established Bastion SSM tunnel
- [x] Bridged Nifty 50 stocks (+55,826 rows → 1,699,118 total) and index data (4,527 rows)
- [x] Verified: 0 duplicates, 0 null close prices, data through 2026-02-27

### Step 2: Engine Pipeline Re-run
- [x] Indicators: 1,699,118 rows computed
- [x] Regime: 4,527 days (BULL: 2916, BEAR: 788, NEUTRAL: 823)
- [x] Portfolio: 567 trades, ₹9,750,142 final equity, ~29% CAGR
- [x] Metrics: CAGR 28.18%, Sharpe 1.23, Max DD -33.53%

### Step 2b: Next-Day Execution Realism Test
- [x] Created `portfolio_engine_nextday.py` — executes at next-day open
- [x] Results: 573 trades, ₹5,764,534 equity, CAGR 25.32% (vs 29.04%, -3.7pp = overnight cost)

### Step 3: Client Signal Platform
- [x] Database migration: 6 tables (`clients`, `client_signals`, `client_actions`, `client_portfolio`, `client_equity`, `email_log`)
- [x] FastAPI backend: auth (JWT + bcrypt), signals API, action recording, portfolio/equity endpoints
- [x] Signal generator, email service (AWS SES), React dashboard with login, regime, signals, screener
- [x] Cron pipeline: `run_daily_pipeline.sh` — 5-step automated pipeline
- [x] Forgot Password flow (SES-based token reset)
- [x] AWS SES sandbox verification for beta testers
- [ ] **SES Production Access** — deferred until beta tester group grows (currently using sandbox + manual verification)

### Step 4: Nifty 500 Expansion
- [x] Bridged remaining 450 stocks, engines re-run on full universe, metrics verified

---

## Phase 3: Automation & Alerts (2026-03-16 → 2026-03-17)
- [x] Signal-only notification logic (suppress "No Change" updates)
- [x] Regime change trigger alerts (BULL/BEAR/NEUTRAL transitions)
- [x] Database restored: all 16 tables verified, 493 days of NIFTY50 index data recovered
- [x] Date sync confirmed (March 16 as latest regime state)
- [ ] **Client-specific ticker alerts** — ensure alerts only go to clients holding those tickers

---

## Phase 4: API Integrity & Production Stability (2026-03-16 → 2026-03-17)
- [x] Synchronized `portfolio_review.py` with refactored core engine
- [x] Eliminated redundant `grade_symbols_sync` for unified ingestion
- [x] Corrected `BackgroundTasks` import and async on-demand ingestion
- [x] Fixed `df.columns` truncation in `on_demand_ingest.py`
- [x] Added route aliases (dash/underscore support) for all portfolio routes
- [x] Restored `compute_indicators_for_symbols` in `indicator_engine.py`
- [x] Aligned `holdings-status` JSON response with React state (`storage_ready`)
- [x] Verified 16 tables in production, NIFTY50 data flowing to dashboard
- [x] Standardized FastAPI instance naming (`api.main:app`)

---

## Phase 5: Security & Git Cleanup (2026-03-17)
- [x] Deactivated leaked AWS keys; rotated to SES-only IAM user
- [x] Added `.env` to `.gitignore` and pushed clean history
- [x] Restored `api.main:app` to fix Render boot crashes
- [x] Responded to AWS security tickets, performed resource audit

---

## Phase 6: Port, Route & Auth Finalization (2026-03-17)
- [x] Matched Docker CMD to internal port 8000
- [x] Added `/holdings` alias for frontend compatibility
- [x] Handled missing email strings to prevent 422 errors
- [x] Confirmed `.env` scrubbed, keys moved to Render env vars
- [x] Resolved 422 errors via URL normalization and relaxed schema validation

---

## Phase 7: Auth & Handshake Stabilization (2026-03-17)
- [x] Wired real production routers into `api/main.py` (was using fake auth)
- [x] Made `TokenResponse.name` optional (fix for legacy NULL-name users)
- [x] Dependency audit: added missing fastapi, bcrypt, jose to `requirements.txt`
- [x] Fixed frontend URL normalization (double-slash → data loss on POST)
- [x] Fixed `[object Object]` error display → human-readable JSON
- [x] Standardized CORS middleware for credentials + dynamic origins
- [x] Upgraded `/api/portfolio-review/holdings` to return enriched list with P&L
- [x] Fixed CSV upload auth (persist user email, token-based identity resolution)

---

## Phase 8: Regrade Optimization & BSE Robustness (2026-03-17)
- [x] Bulk `yf.download` strategy (~5-8s vs ~40s for 33+ stocks)
- [x] 3-tier search chain: Bulk NSE → Bulk BSE → Numeric Scrip mappings

---

## Phase 9: Pipeline Restoration & Bulk Porting (2026-03-17)
- [x] Re-implemented legacy entry points for `pipeline.py` compatibility
- [x] Non-destructive schema/constraint migrations in `src/db.py`
- [x] Ported bulk NSE patterns + 1-month incremental top-ups (10-20x faster)

---

## Phase 10: Deployment & Sync Rescue (2026-03-17)
- [x] Created `src/ingestion_engine.py` and `scripts/mri_pipeline.py` (bypassed WSL/Git sync issue)
- [x] Pipeline is 🟢 GREEN on GitHub Actions

---

## Phase 11: Signal Visibility & Daily Summaries (2026-03-17)
- [x] Added `has_pending_signals` to `TokenResponse`
- [x] Overhauled `email_service.py` for daily persistence
- [x] Duplicate prevention and regime-only summaries verified

---

## Phase 12: BSE-Only Stock Expansion (2026-03-18)
- [x] ISIN-based deduplication for multi-exchange ingestion
- [x] BSE Group A stocks integrated into `mri_pipeline.py`
- [x] Automated daily updates for user-tracked Digital Twin holdings
- [x] Unified `stock_sectors` update logic for BSE-only companies

---

## Addendum: Digital Twin Persistence (2026-03-12 → 2026-03-13)
- [x] API ensures `client_external_holdings` exists before save/load/delete
- [x] Holdings status diagnostics (`/api/portfolio-review/holdings-status`)
- [x] Risk Audit UI: Storage Status box, delete-all with 2-step confirm
- [x] On-demand ingestion grades ungraded symbols with targeted indicator computation
- [x] Manual regrade button + synchronous endpoint for immediate score return
- [x] Bounded on-demand downloads to ~3 years (prevent Render stalls)
- [x] Dashboard falls back to Digital Twin holdings when full analysis fails
- [x] Fixed `Decimal * float` crash, live Yahoo pricing with EOD fallback
- [x] Risk Audit: sortable tables, LIVE/EOD/COST price labeling
- [x] Password reset uses deployed frontend URL, logs SES misconfigs

---

## Addendum: Render Deployment (2026-03-12)
- [x] Render blueprint (API + frontend + daily cron pipeline job)
- [x] API Dockerfile binds to Render `$PORT`
- [x] Non-destructive table creation, incremental loaders

---

## Addendum: Scheduling via GitHub Actions (2026-03-12)
- [x] Daily pipeline runs via GitHub Actions schedule (no Render cron billing)

---

## Addendum: SES Region & Diagnostics (2026-03-15)
- [x] `SES_REGION` override with validation, falls back to `AWS_REGION`
- [x] `GET /api/email/debug` endpoint for sender verification + quota checks
- [x] Forgot-password rolls back tokens on SES failure

---

## Addendum: Data Resilience & ISIN Bridging (2026-03-16)
- [x] Universal ISIN Translator resolving "UNKNOWN" stock errors
- [x] Wide-net ingestion: full NSE & BSE master lists (5,000+ symbols)
- [x] Automated BSE numeric code mapping (e.g., M&M → 500520)
- [x] Manual overrides for rebranded tickers (AGI, CIGNITI, etc.)
- [x] Wholesome Tiered Search: ISIN Bridge → NSE → BSE
- [x] Adaptive indicators for stocks with < 200 days history (50-day fallback)
- [x] Safe comparison logic (`.fillna()`) for rolling highs, regime engine
- [x] `ON CONFLICT DO NOTHING` for silent transaction rollback fix

---

## Addendum: Railway Port Fix (2026-03-19)
- [x] `Dockerfile.api` updated to use `$PORT` for Railway deploys
- [x] Backend and frontend both deploy and pass healthchecks on Railway

---

## Phase 13: MailerLite Mailing List Integration (2026-03-21)
- [x] Created `src/mailerlite.py` — MailerLite v2 API wrapper
- [x] Hooked into `api/auth.py` `register()` endpoint
- [x] Subscriber added to MailerLite group on sign-up

---

## Phase 14: Railway Migration & Mobile Optimization (2026-03-23)
- [x] **Unified Monolithic Deployment**: Frontend + backend in single Docker container
- [x] **Mobile Optimization**: Bottom nav bar for small screens, overhauled CSS
- [x] **Railway Migration**: Unified service architecture on Railway
- [x] **AWS Secrets Manager**: MailerLite credentials via `mri-mailerlite-credentials`
- [x] **0-100 Weighted Scoring**: Transitioned from 0-5 sum to 0-100 weighted engine
- [x] **Enhanced Daily Digest**: Portfolio + Watchlist status in holistic daily report
- [x] **Database Optimization**: Pruned `daily_prices` to 2-year window, optimized indices
