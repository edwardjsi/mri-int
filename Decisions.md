# ARCHITECTURAL DECISIONS LOG

> Every significant decision is recorded here with its reason.
> This prevents re-litigating decisions in future sessions.

---

## Decision 001 — End-of-Day Only (No Intraday)
Date: 2026-02-19
Decision: Process only EOD (end-of-day) data, not intraday.
Reason: Lower complexity, lower cost, cleaner signals, lower compliance friction.
Status: FINAL — do not revisit in prototype phase.

## Decision 002 — No ML in V1
Date: 2026-02-19
Decision: No machine learning models in prototype or V1 SaaS.
Reason: Must be deterministic, explainable, and backtestable. Avoid black-box risk.
Status: FINAL.

## Decision 003 — Single Container (No Microservices)
Date: 2026-02-19
Decision: Single Dockerized Python service for all quant engines.
Reason: Reduce complexity in prototype phase. Microservices only after SaaS launch.
Status: FINAL for prototype.

## Decision 004 — AWS Region ap-south-1
Date: 2026-02-19
Decision: All AWS resources in Mumbai (ap-south-1).
Reason: Lowest latency for NSE data ingestion; aligns with existing infra.
Status: FINAL.

## Decision 005 — PostgreSQL on RDS (Not Local)
Date: 2026-02-19
Decision: Use AWS RDS PostgreSQL even in prototype phase.
Reason: Makes it a proper DevOps portfolio project, not just a local script.
Status: FINAL.

## Decision 006 — Terraform Module Reuse
Date: 2026-02-19
Decision: Reuse vpc, rds, ecs, iam module structure from Sovereign Retirement project.
Reason: Proven pattern, faster execution, consistent naming.
Status: FINAL.

## Decision 007 — Prototype Score Model: 0–5 (Not 0–100)
Date: 2026-02-19
Decision: Use simplified 0–5 binary scoring for the prototype.
Reason: Faster to build and validate. Upgrade to weighted 0–100 in SaaS phase.
Status: FINAL for prototype only.

## Decision 008 — No UI in Prototype
Date: 2026-02-19
Decision: No frontend, no dashboard, no API in prototype phase.
Reason: Output is CSV + PDF performance report only. SaaS UI comes after viability is proven.
Status: FINAL.

---

## Decision 009 — PostgreSQL Engine Version 15.15
Date: 2026-02-19
Decision: Use PostgreSQL 15.15 on RDS instead of 15.4 or 17.
Reason: 15.4 not available in ap-south-1. 15.15 confirmed available.
Status: FINAL.

## Decision 010 — WSL-Only Execution
Date: 2026-02-19
Decision: Repo lives on Windows filesystem /mnt/c/ — all execution via WSL only.
Reason: Avoids Windows/Linux line ending and permission conflicts.
Status: FINAL.

## Decision 011 — Scoring Model Adapted to 0–3
Date: 2026-02-19
Decision: Prototype uses 0–3 score (ADX>25, RSI 50–70, price >90% of 52W high) instead of original 0–5.
Reason: EMA-based conditions require more historical data; simplified for speed.
Status: FINAL for prototype only.

## Decision 012 — SMA-200 (Not EMA-200) for Regime Filter
Date: 2026-02-19
Decision: Use SMA-200 instead of EMA-200 for market regime classification.
Reason: Simpler, sufficient for prototype, widely understood.
Status: FINAL for prototype only.

## Decision 013 — Robust DB Connection Retries over SSM
Date: 2026-02-21
Decision: Implement automated connection retries in psycopg2 with increased TCP timeouts.
Reason: AWS SSM Port Forwarding tunnels aggressively time out idle TCP connections while yfinance is processing data.
Status: FINAL.

## Decision 014 — Nifty 500 Row Limit Expectation
Date: 2026-02-21
Decision: Acknowledge ~1.6 million rows is the maximum historical dataset for Nifty 500 from 2005-present.
Reason: Due to recent IPOs, most companies do not have 20 years of history.
Status: FINAL.

## Decision 015 — Weekend Infrastructure Teardown
Date: 2026-02-21
Decision: Destroy AWS infrastructure using Terraform and back up the RDS database to S3.
Reason: To save costs over the weekend/pause period and prove the infrastructure-as-code and data recovery processes.
Status: FINAL.

## Decision 016 — Bridge Data Gap Before Frontend
Date: 2026-03-02
Decision: Ingest the ~2-year data gap (early 2024 – March 2026) for all Nifty 500 stocks + Nifty 50 index before advancing Phase 2 frontend work. Rerun the full engine pipeline (Indicators → Regime → Scores → Portfolio) to produce current-day signals.
Reason: The existing DB has data only through early 2024. The dashboard must show live, present-day signals to be useful. Data foundation must be current before any frontend wiring.
Status: FINAL.

## Decision 017 — AWS Cost Management: Pause/Resume Pattern
Date: 2026-03-02
Decision: Use RDS pause/resume (not full Terraform teardown) for short breaks. Reserve `terraform destroy` for week-long gaps only. Monitor NAT Gateway and Bastion costs actively.
Reason: Billing audit revealed NAT Gateway ($32/mo) and Bastion EC2 ($7/mo) were silently billing while RDS was paused. Full teardown saves ~$43/mo but adds rebuild overhead.
Status: FINAL.

## Decision 018 — Nifty 50 First, Then Nifty 500
Date: 2026-03-02
Decision: Launch the Phase 2 Web App MVP with Nifty 50 stocks only. Expand to Nifty 500 after successful validation.
Reason: Faster iteration, lower API load, quicker validation cycle. Nifty 50 covers the most liquid and widely followed stocks. Full 500 expansion follows once the pipeline is proven end-to-end.
Status: FINAL.

## Decision 019 — Next-Day Open Execution Engine
Date: 2026-03-02
Decision: Add `portfolio_engine_nextday.py` that executes trades at next day's open price instead of same-day close. Signals generated at EOD, execution deferred to next morning open. This is the realistic execution model.
Reason: Same-day close execution is unrealistic — in practice, signals are reviewed after market close and orders placed for the next morning. This eliminates execution timing bias.
Status: FINAL.

## Decision 020 — Client Signal Platform Architecture
Date: 2026-03-02
Decision: Build a client-facing signal platform with: MailerLite for onboarding emails, AWS SES for daily signal digests, cron-based automation (4PM IST Mon-Fri), three-tier price capture (default→self-reported→broker API), per-client equity tracking vs Nifty.
Reason: Enables controlled testing with a small crowd before full SaaS launch. Self-reported prices with next-day-open defaults balances accuracy with user effort.
Status: FINAL.

## Decision 021 — Nifty 500 Expansion Deferred Until Post-SaaS Launch
Date: 2026-03-03
Decision: Do NOT expand to Nifty 500 until the SaaS product is successfully launched and operational with Nifty 50. This supersedes the timing implied in Decision 018.
Reason: Focus all engineering effort on shipping a working SaaS product with Nifty 50 first. Nifty 500 expansion is a scaling concern, not a launch requirement. Premature expansion adds data load time, API costs, and complexity without improving the core product validation.
Status: FINAL.

## Decision 022 — SaaS Deployment Architecture: ECS Fargate + CloudFront + EventBridge
Date: 2026-03-03
Decision: Deploy MRI platform using: (1) ECS Fargate behind ALB for FastAPI backend, (2) S3 + CloudFront for React frontend with API proxy via `/api/*` path pattern, (3) EventBridge scheduled ECS task at 4PM IST Mon-Fri for the daily data pipeline. All infrastructure managed via Terraform. SES in sandbox mode for email delivery.
Reason: ECS Fargate provides fully managed container orchestration (no EC2 to maintain), CloudFront serves as a single domain for both frontend and API (avoiding CORS), and EventBridge + Fargate gives serverless cron execution (pay only for ~5min/day pipeline runtime). This architecture demonstrates DevOps best practices for portfolio/interview purposes.
Endpoints: API: `mri-dev-alb-*.ap-south-1.elb.amazonaws.com`, Frontend: `d1evxo8lp0e0eg.cloudfront.net`
Status: FINAL.
## Decision 023 — Full-Scale Architecture Demonstrated → Cost-Conscious Testing Phase
Date: 2026-03-03
Context: The MRI platform was built and deployed as a **production-grade, full-scale DevOps project** demonstrating enterprise best practices:
  - **Infrastructure as Code**: Terraform modules for VPC, RDS, IAM, ECS, S3, CloudFront (6 modules, ~30 resources)
  - **Container Orchestration**: ECS Fargate behind ALB with ECR, health checks, auto-restart
  - **CI/CD Pipeline**: One-command `deploy.sh` — Docker build → ECR push → ECS rolling deployment → S3 sync → CloudFront invalidation
  - **Serverless Automation**: EventBridge scheduled ECS tasks for daily pipeline
  - **Security**: Private subnets for RDS + ECS, NAT Gateway, Secrets Manager, IAM least-privilege roles
  - **Frontend CDN**: S3 + CloudFront with API proxy, SPA routing, OAC-based access control
  - **Email Service**: AWS SES for client signal digests
  Full-scale cost: ~$80/month.
Decision: Transition to a **cost-conscious testing phase** for the next 6 months. Keep only RDS (stopped, ~$3/mo storage) and CloudFront/S3 (free). Spin up infrastructure daily at 4PM IST for ~30 minutes, run pipeline, then tear down. Estimated cost: ~$5/month. The full-scale architecture can be restored at any time via `terraform apply` + `deploy.sh` (~10 minutes) when going public.
Reason: During the testing phase with a small group of users, 24/7 infrastructure is unnecessary. This reduces 6-month costs from ~$480 to ~$27 while retaining all data and the ability to scale back up instantly.
Status: FINAL.
## Decision 024 — Client Investment Features: RS Ranking, Capital Management, Execution Tracking
Date: 2026-03-03
Decision: Enhance client-facing platform with: (1) RS-based stock ranking — signals sorted by score DESC then relative strength DESC to resolve ties, (2) Add Capital — users can increase their investment capital at any time, (3) Execution Dialog — prompts for actual price and quantity with auto-calculated 10% allocation suggestion, (4) Daily P&L Summary — shows today's portfolio change vs yesterday, (5) Auto-quantity — signal cards display suggested share count based on 10% of total capital / stock price.
Reason: Previous system generated signals without position sizing guidance and hardcoded qty=10. These features make the platform usable for real testing with actual capital.
Status: FINAL.

## Decision 025 — Daily Operations Workflow for Testing Phase
Date: 2026-03-03
Decision: Use a single `mri_daily.sh` script that: (1) starts RDS + bastion, (2) opens SSM tunnel, (3) runs the full pipeline locally, (4) starts a local API server for testers to log in and execute signals, (5) waits for admin to press Enter, (6) tears down everything. Testers get ~15min daily at 4PM IST to mark yesterday's signals as executed and view new signals. Signals generated at 4PM Day N are executed in broker at 9:15AM Day N+1, and marked in the system at 4PM Day N+1. Smallcase/Zerodha subscription is the eventual monetization path (~6 months out).
Reason: Minimises AWS costs (~$0.07/day) while giving testers a functional daily window. The admin controls the lifecycle manually until the platform scales.
Status: FINAL.

## Decision 026 — INCIDENT: RDS Destroyed by Terraform Dependency Cascade
Date: 2026-03-04
Incident: Running `terraform destroy -target=module.vpc -target=module.s3 -target=module.iam -target=module.frontend` **also destroyed `module.rds`** because the RDS module depends on VPC resources (subnets, security groups). Terraform's `-target` flag follows the dependency graph and destroys dependents. All 1.7M rows of stock data, 3 client accounts, indicators, signals, and portfolio data were lost. S3 buckets were also emptied by the destroy.
Root Causes:
  1. `deletion_protection = false` — AWS allowed the RDS instance to be deleted
  2. `skip_final_snapshot = true` — no backup was taken before deletion
  3. `prevent_destroy` lifecycle rule was not set — Terraform did not block the destroy
  4. `-target=module.vpc` cascaded to destroy the RDS module (dependency chain)
Recovery: Full pipeline re-run from Yahoo Finance data + re-register client accounts.
Lesson: **NEVER use `terraform destroy -target` on resources that have dependents you want to keep.** Always use state removal (`terraform state rm`) to protect resources before destroying.
Status: FINAL — NEVER FORGET.

## Decision 027 — Triple-Layer RDS Protection
Date: 2026-03-04
Decision: Implement three safeguards to prevent accidental RDS destruction:
  1. **Terraform `prevent_destroy = true`** — Terraform will refuse to plan any destroy of the RDS instance. Must be manually removed from config to destroy.
  2. **AWS `deletion_protection = true`** — AWS API will reject delete requests. Must be disabled in AWS Console or via CLI first.
  3. **`skip_final_snapshot = false`** — Even if both above are bypassed, AWS takes a final snapshot (`mri-dev-db-final-snapshot`) before deletion.
  4. **Safe teardown script** (`scripts/mri_safe_teardown.sh`) — Removes RDS from Terraform state before running destroy, so Terraform never even attempts to touch RDS.
  5. **Original teardown script deprecated** — `scripts/mri_teardown.sh` replaced by `mri_safe_teardown.sh` for daily use.
Reason: Decision 026 incident. Data loss is unacceptable.
Status: FINAL — DO NOT WEAKEN THESE PROTECTIONS.

## Decision 028 — Nifty 500 Expansion (Overrides Decision 021)
Date: 2026-03-04
Decision: Expand the daily pipeline from Nifty 50 to Nifty 500 immediately. Updated NSE symbol list URL in `scripts/pipeline.py`, `run_daily_pipeline.sh`, and `run_bridge_load.sh`. The existing database already contains ~488 Nifty 500 stocks from historical backup data.
Reason: User decision to broaden signal coverage now rather than waiting for SaaS launch. Historical data already covers most Nifty 500 stocks.
Impact: Daily data ingestion will take ~15-20 min (vs ~3 min for Nifty 50). Indicator and scoring computation will process more rows.
Status: FINAL — supersedes Decision 021.

## Decision 029 — Phase 1 Risk Filters: Liquidity Gate + Sector Cap + Cash Toggle
Date: 2026-03-04
Context: Based on comprehensive quantitative research (see `docs/market_cap_diversification.md`, 37 cited sources) on the "Problem of Equivalence" when scoring stocks across different market caps.
Decision: Implement three filters in `signal_generator.py` before stock selection:
  1. **₹10 Cr ADTV Liquidity Gate** — `avg_volume_20d × close > ₹10 Cr` applied in SQL. Eliminates illiquid stocks at the database level. Based on O'Neil/Minervini methodology and Nifty 500 Momentum 50 Index methodology.
  2. **Sector Concentration Cap** — Max 3 stocks from any single sector (30%). Prevents "thematic traps" where a sector correction wipes out the portfolio. Uses `stock_sectors` table (to be populated), falls back to UNKNOWN.
  3. **Cash Toggle** — Skip a slot if the best available stock scores below 3/5. Implements "Absolute Momentum" — don't invest in the best of a bad bunch.
Impact: Signal reason text now includes ADTV (₹ Cr) for transparency. Scoring query returns ADTV alongside RS.
Phase 2 (future): Hybrid multi-cap slotting (7+3), volatility-adjusted momentum, quality factor integration, correlation filtering.
Status: FINAL.

## Decision 030 — Incremental Pipeline Optimization
Date: 2026-03-05
Context: Full pipeline on Nifty 500 (1.79M rows) took ~3.5 hours via SSM tunnel. Bottleneck was DB writes for indicators (2 hrs) and stock scores (25 min), both rewriting all 1.79M rows every run.
Decision: Make both engines incremental — compute on full history (needed for EMA accuracy) but only write new rows:
  1. **indicator_engine.py**: Fetches `ema_50` column to detect NULL rows. Only UPDATEs rows where `ema_50 IS NULL`. Early-exits if 0 new rows.
  2. **regime_engine.py**: Uses `LEFT JOIN stock_scores ... WHERE ss.date IS NULL` to only fetch and score unscored rows. Tables no longer DROPped on each run (`CREATE IF NOT EXISTS`).
Impact: Daily pipeline drops from ~3.5 hours to ~30 minutes. The 30-min floor is Yahoo Finance download time for 500 stocks.
To force full recompute (e.g., after formula change): `UPDATE daily_prices SET ema_50 = NULL;` and `DELETE FROM stock_scores;`
Status: FINAL.

## Decision 031 — Incremental Yahoo Finance Data Fetch
Date: 2026-03-05
Context: Daily pipeline Step 1 was downloading full 20-year history (2005→today) for all 500 stocks every run, taking ~25 min even though only 1-2 new days were needed.
Decision: Add `get_last_date()` to `data_loader.py`. Queries DB for `MAX(date)`, then fetches from `(last_date - 5 days)` to today. The 5-day overlap catches any gaps or corrections. Falls back to `START_DATE` (2005) if no data exists.
Impact: Daily Yahoo download drops from ~25 min to ~2-3 min. Full pipeline total: ~3.5 hrs → ~5-8 min.
Status: FINAL.

## Decision 032 — Forgot Password Flow using AWS SES
Date: 2026-03-09
Decision: Implemented a "Forgot Password" feature that uses secure, random 32-character tokens stored in a new `password_reset_tokens` table, and sends reset links via AWS SES. Returns explicit 404 for missing accounts rather than a generic security message.
Reason: Users need a way to recover access. AWS SES is already configured. Returning an explicit 404 improves UX over security-through-obscurity since this is a private prototype phase.
Status: FINAL.

## Decision 033 — Free-Tier Cloud Migration: Neon.tech + Render.com
Date: 2026-03-10
Decision: Migrate from full AWS stack (~$80/mo) to a free-tier hybrid deployment for the 6-month testing phase:
  1. **Database**: AWS RDS → **Neon.tech** free tier (500MB Serverless PostgreSQL). Standard PostgreSQL = zero code changes. ~200-300MB data fits within limit.
  2. **API Backend**: ECS Fargate + ALB + NAT → **Render.com** free tier Docker web service. Same `Dockerfile.api`, health checks, env vars.
  3. **Frontend**: S3 + CloudFront remains as-is (essentially free at current traffic).
  4. **Daily Pipeline**: EventBridge → ECS → `scripts/pipeline_cloud.sh` connecting directly to Neon (no bastion tunnel needed).
  5. **Config Changes**: Added `DATABASE_URL` env var support, `DB_SSL=true` toggle, `VITE_API_URL` build-time config, `CORS_ORIGINS` env var. All backward-compatible with original AWS setup.
  All AWS Terraform IaC preserved in repository. Set `cost_conscious_mode = false` and run `terraform apply` + `deploy.sh` to restore full AWS in ~10 minutes.
Reason: $0/month vs $80/month for a testing phase with <10 users. Infrastructure-as-code portfolio value retained. Pragmatic, cost-aware engineering decision.
Status: FINAL.

## Decision 034 — Portfolio Review Engine (No New Tables)
Date: 2026-03-11
Decision: Add `portfolio_review_engine.py` that evaluates any user-submitted portfolio against MRI's existing intelligence. Computes per-holding risk factors based on stock trend scores (0–5), EMA-200 position, and market regime alignment. Aggregates into weighted risk score and classifies as Low/Moderate/High/Extreme. **No new database tables** — reads from existing `stock_scores`, `market_regime`, and `daily_prices`. API endpoints: `POST /api/portfolio-review/analyze` and `GET /api/portfolio-review/quick/{symbol}`.
Reason: Implements SaaS Blueprint Journey 3 (Portfolio Risk Audit). Keeping it read-only against existing tables avoids schema migration complexity and keeps the engine stateless/deterministic.
Status: FINAL.

## Decision 035 — Asynchronous On-Demand Data Ingestion
Date: 2026-03-11
Decision: Add asynchronous on-demand asset ingestion capabilities using FastAPI `BackgroundTasks` to automatically download historical data via Yahoo Finance (`.NS` then `.BO`) for any user-uploaded symbols not currently in the Nifty 500 MRI database. The system returns an immediate partial report for known stocks, natively backfills the DB, triggers incremental engine scoring, and then emails the final complete HTML report via AWS SES.
Reason: Prevents database bloat from storing the entire illiquid NSE/BSE universe daily. Scales data ingestion organically based exactly on what users actually own. Gracefully handles 20-minute latency for missing data by returning partial frontend results immediately and finalizing via email.
Status: FINAL.

## Decision 036 — Persistent User Holdings (Digital Twin Layer)
Date: 2026-03-12
Decision: Implement a persistent `client_external_holdings` table to store user-uploaded assets (symbol, quantity, avg_cost). This "Digital Twin" layer exists alongside the internal strategy-generated `client_portfolio` and receives real-time MRI risk evaluation (scores, alignment, 200 EMA status) and P&L tracking based on latest `daily_prices`.
Reason: Evolution from one-off CSV uploads to a persistent monitoring tool. Enables users to track their actual holdings against MRI intelligence permanently, fulfilling the "another layer" requirement.
Status: IMPLEMENTING.

<!-- Append new decisions below. Never delete or modify old ones. -->
## Decision 037 — Retain Render for Daily Pipeline (No GitHub Actions)
Date: 2026-03-16
Decision: Keep the daily data pipeline (`data_loader.py`) executing within the Render environment using reduced data lookback windows (5 days for existing stocks, ~3 years for newly uploaded user stocks) rather than offloading to external cron services like GitHub Actions.
Reason: Respects Phase 2 MVP constraints. By heavily optimizing the data ingestion boundaries, the pipeline comfortably avoids Render's 512MB out-of-memory crashes. This keeps the architecture unified, avoids introducing new infrastructure dependencies, and organically supports daily tracking of custom user BSE/NSE uploads.
Status: FINAL.

## Decision 038 — Shift to ISIN-Based Cross-Exchange Mapping
Date: 2026-03-16
Decision: Implement an in-memory "ISIN Bridge" that maps user-provided NSE symbols to BSE numeric scrip codes for all backend data fetching.
Reason: Yahoo Finance's NSE string formatting (e.g., 'M&M.NS') is inconsistent and prone to 404 errors. Numeric BSE codes (e.g., '500520.BO') are immutable and 100% reliable. The ISIN bridge allows users to keep using their familiar broker-provided symbols while the backend benefits from the reliability of the BSE data universe.
Status: FINAL.

## Decision 039 — Tiered Search Strategy for Data Ingestion
Date: 2026-03-16
Decision: Adopted a three-tier search strategy for yfinance downloads: 1. ISIN-mapped BSE code, 2. Raw Symbol (NSE), 3. Raw Symbol (BSE).
Reason: This approach ensures zero-friction for the user. It handles broker-specific naming quirks automatically and prevents "UNKNOWN" grades even if the official ISIN master lists have discrepancies.
Status: FINAL.

## Decision 041 — Adaptive Trend Fallback for Recent Listings
Date: 2026-03-16
Decision: Modified the indicator engine to fallback from a 200-day EMA to a 50-day EMA when price history is insufficient.
Reason: New listings (like One Global) or recent corporate actions would otherwise result in null indicators and failed scoring. Using the 50-day EMA as a proxy ensures the user still receives a trend-alignment grade based on available data.
Status: FINAL.

## Decision 042 — Definitive Scrip Mapping for Non-Standard Tickers
Date: 2026-03-16
Decision: Implemented a manual override dictionary for specific broker-exported symbols that diverge from official NSE/BSE ISIN master lists.
Reason: To ensure a friction-less "Drop and Grade" experience for users coming from Zerodha/Upstox/Groww, the system must bridge naming discrepancies (e.g., CIGNITITEC to BSE:534758) instantly.
Status: FINAL.

## Decision 043 — Safe Indicator Fallbacks for Recent Listings
Date: 2026-03-16
Decision: Implemented `.fillna(df['close'])` for the `rolling_high_6m` calculation in the scoring engine.
Reason: Stocks with less than 6 months of history return a `None` value for rolling highs, which causes Python's comparison operators to crash the entire thread. Filling with the current price effectively treats the "all-time high" as today's price for new stocks, allowing the scoring logic to complete without losing data for other symbols in the batch.
Status: FINAL.