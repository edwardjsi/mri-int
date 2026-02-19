# SESSION LOG — Market Regime Intelligence (MRI)

> This file is updated at the END of every working session.
> At the START of every new session, paste the contents of `.llm-context.md` first.

---

## Session 001 — 2026-02-19

### What Was Done
- Defined product concept: Market Regime Intelligence SaaS for Indian equities
- Decided tech stack: Python + FastAPI + Next.js + PostgreSQL + Docker + AWS
- Defined three core engines: Regime Engine, Trend Score Engine, Portfolio Risk Engine
- Decided Phase 0 = 10-day viability prototype only (no SaaS yet)
- Defined Go/No-Go criteria (Sharpe ≥ 1, CAGR > Nifty, Drawdown < Nifty)
- Decided to build on AWS infra (ECS Fargate, RDS, S3, Terraform)
- Created session persistence infrastructure (README, SESSION, DECISIONS, PROGRESS, .llm-context)

### Decisions Made
- No microservices in V1 — single deployable container
- End-of-day data only (not intraday) — lower cost, cleaner signal
- Prototype uses 0–5 score (not full 0–100 weighted model) for speed
- AWS region: ap-south-1 (Mumbai)
- Terraform module structure mirrors Sovereign Retirement project

### Current State
- No code written yet
- No AWS resources provisioned yet
- Session persistence files created ✅
- Ready to begin Day 1: Terraform infrastructure

### Blockers / Open Questions
- None currently

### Next Session Must Start With
> Day 1: Terraform infrastructure skeleton
> - VPC (reuse existing module pattern)
> - RDS PostgreSQL (db.t3.micro, ap-south-1)
> - S3 bucket (for output storage)
> - IAM roles (ECS task execution + S3 + Secrets Manager)
> - Secrets Manager (DB credentials)
> Confirm: `terraform apply` outputs VPC ID, RDS endpoint, S3 bucket name

---

## Session 001 — 2026-02-19 (COMPLETED)

### What Was Done
- Created GitHub repo: edwardjsi/mri-int
- Created session persistence infrastructure (README, SESSION, DECISIONS, PROGRESS, .llm-context)
- Designed deterministic naming convention (mri-dev-{resource}) — no random suffixes
- Created full Terraform module structure (vpc, rds, s3, iam)
- Fixed PostgreSQL version 15.4 → 15.15 (15.4 not available in ap-south-1)
- Successfully ran terraform apply — all 6 outputs confirmed

### AWS Resources Live
- VPC: vpc-016df78c5fcbfab4e
- RDS: mri-dev-db.c9a44u2kqcf8.ap-south-1.rds.amazonaws.com
- S3: mri-dev-outputs-251876202726
- Secret: arn:aws:secretsmanager:ap-south-1:251876202726:secret:mri-dev-db-credentials-doP9bL
- IAM Execution Role: arn:aws:iam::251876202726:role/mri-dev-ecs-execution-role
- IAM Task Role: arn:aws:iam::251876202726:role/mri-dev-ecs-task-role

### Decisions Made
- Decision 009: PostgreSQL 15.15 (not 15.4 or 17)
- Decision 010: Repo lives on Windows filesystem /mnt/c/ — all execution via WSL only

### Current State
- Day 1 complete ✅
- Infrastructure live on AWS
- No Python code written yet
- Ready for Day 2: Data ingestion

### Next Session Must Start With
> Day 2: NSE EOD data ingestion
> - Confirm data source (eod2 / openchart / nsepython)
> - Write data_loader.py
> - Connect to RDS using credentials from Secrets Manager
> - Load NSE historical data 2005–present into daily_prices table
> - Run data quality checks
> DONE criteria: Row count > 0 in daily_prices, no duplicates, no missing dates

<!-- Append new sessions below. Never delete old ones. -->

## Session 002 — 2026-02-19

### What Was Done
- Fixed Terraform security group bug: RDS was attached to app SG instead of rds SG
- Added bastion security group to VPC module with port 22 ingress
- Updated RDS SG ingress to allow port 5432 from both app SG and bastion SG
- Imported pre-existing bastion SG into Terraform state
- Confirmed bastion → RDS connectivity via /dev/tcp test
- Established SSH tunnel (localhost:5433 → RDS:5432) via bastion
- Confirmed RDS connection successful via psycopg2
- Created `daily_prices` schema with UNIQUE(symbol, date) + index
- Upgraded yfinance from 0.2.36 to latest (fixed Yahoo API breakage)
- Ingested 20 Nifty 500 stocks × 247 days = 4,940 rows into RDS
- Ingested Nifty 50 index (^NSEI) 528 rows (2024–present) for regime engine
- Created `market_regime` and `stock_scores` tables
- Computed 200-SMA market regime: BULL 243 days, BEAR 86 days
- Computed ADX + RSI + 52W-high scores for all 20 stocks (4,680 rows)
- Top stocks by avg score: TITAN, AXISBANK, SBIN, LT, RELIANCE

### Decisions Made
- Use SMA-200 (not EMA-200) for regime filter — simpler, sufficient for prototype
- Score = 0–3 (ADX>25, RSI 50–70, price >90% of 52W high) — adapted from original 0–5
- yfinance as data source confirmed viable with 2s delay between requests
- Bastion SSH tunnel as DB access pattern for local development

### Current State
- Days 1–3 complete
- Infrastructure live on AWS ap-south-1
- Data pipeline working end-to-end
- Indicators and regime computed and stored in RDS
- Ready for Day 4: Backtesting Engine

### Blockers / Open Questions
- yfinance rate limiting (429) — mitigated with 2s delay; may need proxy for full 500 stocks
- Only 20 stocks ingested so far — expand to full Nifty 500 before final backtest

### Blockers / Open Questions
- yfinance rate limiting (429) — mitigated with 2s delay; may need proxy for full 500 stocks
- Only 20 stocks ingested so far — expand to full Nifty 500 before final backtest
- Bastion key lost — recreate key pair and bastion at start of Session 003 before any DB work


### Next Session Must Start With
> Day 4: Backtesting Engine
> - Entry rule: score ≥ 2 AND regime = BULL
> - Exit rule: score drops to 0 OR regime flips BEAR
> - Equal weight position sizing across selected stocks
> - Daily portfolio returns vs Nifty benchmark
> - SSH tunnel must be active before running any DB scripts
