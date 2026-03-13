# BUILD PROGRESS — 10-Day Prototype

> ✅ = Done | 🔄 = In Progress | ⬜ = Not Started | ❌ = Blocked

---

## Phase 0: Session Persistence Infrastructure
- ✅ README.md created
- ✅ SESSION.md created
- ✅ DECISIONS.md created
- ✅ PROGRESS.md created
- ✅ .llm-context.md created

---

## Day 1 — Terraform Infrastructure
- ✅ VPC provisioned (ap-south-1)
- ✅ RDS PostgreSQL created (db.t3.micro, engine 15.15)
- ✅ S3 bucket created (mri-dev-outputs-251876202726)
- ✅ IAM roles created (ECS task execution + task role)
- ✅ Secrets Manager: DB credentials stored
- ✅ terraform apply outputs confirmed


## Day 2 — Data Ingestion
- ✅ NSE EOD data source confirmed
- ✅ data_loader.py written
- ✅ Historical data (2005–present) loaded into RDS
- ✅ Data quality report generated
- ✅ Duplicate/missing row validation passed

## Day 3 — Indicator Engine
- ⬜ EMA 50 implemented + unit tested
- ⬜ EMA 200 implemented + unit tested
- ⬜ 200 EMA slope (20-day regression) implemented
- ⬜ 6-month rolling high implemented
- ⬜ 20-day average volume implemented
- ⬜ 90-day relative strength vs Nifty implemented
- ⬜ Indicators stored in RDS

## Day 4 — Regime Engine
- [x] regime_engine.py written
- [x] Daily Risk-On/Off classification computed
- [x] Regime history table (2005–present) stored
- [x] Regime vs index chart generated

## Day 5–6 — Stock Trend Scoring Engine
- ⬜ trend_engine.py written
- ⬜ Daily 0–5 score computed for all stocks
- ⬜ No look-ahead bias confirmed
- ⬜ Score dataset stored in RDS
- ⬜ 20 random days manually spot-checked

## Day 7–8 — Portfolio Simulation Engine
- [x] portfolio_engine.py written
- [x] Entry logic implemented (Regime=Risk-On, Score ≥ 4, Top 10)
- [x] Exit logic implemented (Score ≤ 2, Regime shift, 20% trailing stop)
- [x] Transaction cost (0.4%) applied
- [x] Equity curve generated
- [x] Trade log CSV exported to S3

## Day 9 — Metrics Module
- [x] CAGR calculated
- [x] Max Drawdown calculated
- [x] Sharpe Ratio calculated
- [x] Sortino Ratio calculated
- [x] Calmar Ratio calculated
- [x] Rolling 3-year CAGR calculated
- [x] Nifty buy-and-hold benchmark compared
- [x] Performance summary table exported

## Day 10 — Stress Tests + Final Report
- [x] 2008 crisis simulation run
- [x] 2020 COVID crash simulation run
- [x] Sideways 2010–2013 simulation run
- [x] Transaction cost doubled (0.8%) test run
- [x] Walk-forward validation (train 2005–2015, test 2016–present)
- [x] Final Markdown report compiled
- [x] All outputs stored in `outputs/` folder
- [x] GitHub README finalized

---

## Go/No-Go Decision
- [x] CAGR > Nifty CAGR
- [x] Max Drawdown < Nifty Drawdown
- [x] Sharpe ≥ 1.0
- [x] Walk-forward Sharpe ≥ 0.8
- [x] Stable across 3+ regimes
- [x] Survives doubled transaction cost

**VERDICT: GO. PHASE 1 COMPLETED.**
*PROCEEDING TO PHASE 2: WEB APP MVP!*

---

## Phase 2 — Web App MVP (NIFTY 50 first → NIFTY 500)
- [x] Initial React/Vite dashboard scaffolding generated
- [x] Baseline backtest placeholder CSVs wired into interactive UI
- [x] AWS billing audit performed — identified idle NAT GW ($32/mo) + Bastion ($7/mo)

### Step 1: Data Bridge — Nifty 50 (2024–March 2026)
- [x] Resume RDS from paused state
- [x] Establish Bastion SSM tunnel (local 5433 → RDS 5432)
- [x] Run `run_bridge_load.sh` to ingest bridge data for Nifty 50 stocks (+55,826 rows → 1,699,118 total)
- [x] Run bridge load for Nifty 50 index (4,527 index rows through 2026-02-27)
- [x] Verify: 0 duplicates, 0 null close prices, data through 2026-02-27

### Step 2: Engine Pipeline Re-run
- [x] Rerun `indicator_engine.py` — 1,699,118 rows computed
- [x] Rerun `regime_engine.py` — 4,527 regime days (BULL: 2916, BEAR: 788, NEUTRAL: 823)
- [x] Rerun `portfolio_engine.py` — 567 trades, ₹9,750,142 final equity, ~29% CAGR
- [x] Rerun `metrics_engine.py` — CAGR 28.18%, Sharpe 1.23, Max DD -33.53%, all Go/No-Go ✅

### Step 2b: Next-Day Execution Realism Test
- [x] Created `portfolio_engine_nextday.py` — executes at next-day open instead of same-day close
- [x] Created `run_portfolio_nextday.sh` runner script
- [x] Next-day backtest results: 573 trades, ₹5,764,534 equity, **CAGR 25.32%** (vs 29.04% original, -3.7pp gap = overnight execution cost)



### Step 3: Client Signal Platform
- [x] Database migration: 6 tables created (`clients`, `client_signals`, `client_actions`, `client_portfolio`, `client_equity`, `email_log`)
- [x] FastAPI backend: auth (JWT + bcrypt), signals API, action recording, portfolio/equity endpoints
- [x] Signal generator: `src/signal_generator.py` — BUY/SELL per client from latest scores/regime
- [x] Email service: `src/email_service.py` — AWS SES HTML digest with regime + signal tables
- [x] React dashboard: Login, regime card, signal cards with Executed/Skipped, screener, equity chart vs Nifty
- [x] Cron pipeline: `run_daily_pipeline.sh` — 5-step automated pipeline (ingest → indicators → regime → signals → emails)
- [x] First client registered and dashboard verified (regime: NEUTRAL, screener: working)
- [x] Forgot Password flow: Backend endpoints, React UI, AWS SES integration, explicit 404 feedback.
- [x] AWS SES sandbox verification for individual friend testing
- [ ] **TODO: Request AWS SES Production Access** to allow public user sign-ups to receive daily signal emails
- [ ] Cron entry on production server
=-=-=-=-
Because your AWS SES account is currently in the Sandbox, it means AWS will only send emails to addresses that you have explicitly verified in the AWS Console.

If a random user registers with john@example.com on your new live website, the pipeline will generate their signals perfectly in the database, but when 

email_service.py
 tries to send them their email, AWS SES will throw an error and block it.

Your Options:
Option 1: Request Production Access (Recommended for the public) You can easily move out of the sandbox so you can email anyone:

Go to AWS Console → Amazon SES → Account dashboard
Click "Request production access"
Fill out the short form (tell them you send daily stock alerts to registered users of your SaaS, and you have explicit opt-in).
They usually approve it within 24 hours. Free tier still covers 62,000 emails/month!
Option 2: Manually Verify Users (Good for private testing with friends) If you just want a few friends to test it right now without waiting for AWS approval:

They register on your site.
You go to AWS Console → Amazon SES → Verified identities.
Click "Create identity", choose "Email address", and type your friend's email.
AWS sends them an automated email with a verification link.
Once they click that link, your pipeline can successfully send them daily signals.
But yes, if you plan to share that mri-frontend.onrender.com link publicly on Twitter or with a wider group, you must do Option 1 first, or nobody will get their daily digests!

=-=-=-=-

### Step 4: Nifty 500 Expansion
- [x] Run `run_bridge_load.sh` for remaining 450 stocks
- [x] Rerun engines on full 500-stock universe
- [x] Verify performance metrics hold

---

### Phase 2 Addendum - Digital Twin Persistence (2026-03-12)
- [x] API ensures client_external_holdings exists before save/load/delete (prevents "upload succeeded but holdings not visible" issues on Neon/Render).

- [x] API + frontend now report verified persisted holdings counts and expose `GET /api/portfolio-review/holdings-status` for diagnostics (2026-03-13).
- [x] Risk Audit UI shows a "Storage Status" box (database + client_id + holdings_count) for fast environment mismatch debugging (2026-03-13).
- [x] Fixed `holdings-status` error `"0"` by using dict-safe cursor access for COUNT(*) on RealDictCursor connections (2026-03-13).
- [x] `GET /api/portfolio-review/holdings` no longer throws 500 if analysis tables are missing; it returns saved holdings with `analysis_error` (2026-03-13).
---

### Phase 2 Addendum - Render Full Stack (2026-03-12)
- [x] Render blueprint includes API + frontend + daily cron pipeline job.
- [x] API Dockerfile binds to Render $PORT.
- [x] Price table creation is non-destructive; incremental loaders ensure tables exist.

---

### Phase 2 Addendum - Scheduling Without Render Cron (2026-03-12)
- [x] Daily pipeline runs via GitHub Actions schedule (no Render billing/credit card required).
