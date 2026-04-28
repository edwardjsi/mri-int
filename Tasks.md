# Daily Tasks Log

> This file tracks the daily, session-by-session goals and completion status of the Market Regime Intelligence (MRI) project.

---

## ✅ Day 1: Infrastructure Setup (Completed 2026-02-19)
- [x] Create project repository (`edwardjsi/mri-int`).
- [x] Set up session persistence files (`README.md`, `SESSION.md`, `DECISIONS.md`, `PROGRESS.md`, `.llm-context.md`).
- [x] Create modular Terraform structure (VPC, RDS, IAM, S3).
- [x] Provision VPC in `ap-south-1`.
- [x] Provision RDS PostgreSQL DB (Engine 15.15) on `db.t3.micro`.
- [x] Create S3 Bucket for outputs.
- [x] Establish IAM roles (ECS execution and task roles).
- [x] Store DB credentials in AWS Secrets Manager.
- [x] Confirm successful `terraform apply` and output variables.

---

## ✅ Day 2: Data Ingestion (Completed 2026-02-21)
- [x] Confirm data source (yfinance/NSE).
- [x] Resolve WSL port 5432 collision and map SSH tunnel to port 5433 via Bastion.
- [x] Develop robust connection retry logic for SSM/yfinance timeouts in `src/db.py`.
- [x] Write `data_loader.py`.
- [x] Load historical pricing data (2005–present) for Nifty 50 Index.
- [x] Load historical pricing data for the full Nifty 500 universe (~1.64M rows).
- [x] Validate Upsert (`ON CONFLICT DO NOTHING`) logic.
- [x] Ensure 0 duplicates and 0 null close prices.
- [x] Create initial schema tables for `market_regime` and `stock_scores`.

---

## ✅ Day 3: Indicator Engine (Completed 2026-02-23)

### Pre-Requisite: Infrastructure Rebuild
- [x] Run `terraform apply` to reinstate the torn-down AWS infrastructure.
- [x] Connect Bastion and verify the RDS database was properly restored from S3 backups.

### Core Development: `indicator_engine.py`
- [x] Write logic to compute the 50-day Exponential Moving Average (EMA).
- [x] Write logic to compute the 200-day Exponential Moving Average (EMA).
- [x] Create function to evaluate the 20-day regression slope of the 200 EMA.
- [x] Implement calculation for the 6-month rolling high.
- [x] Calculate the 20-day average trading volume.
- [x] Compute the 90-day relative strength tracking against the Nifty 50 index (`^NSEI`).

### Integration & Verification
- [x] Calculate the above metrics retrospectively for the entire Nifty 500 dataset (~1.6M rows).
- [x] Persist all calculated indicators to the RDS database.
- [x] Verify there are no null values for the newly added columns (excluding necessary historical look-back nulls).

---

## ✅ Day 27: Deployment Rescue & Rebranding (Completed 2026-03-17)
- [x] Resolved persistent `ImportError` in CI/CD by rebranding core modules to `ingestion_engine.py`.
- [x] Bypassed WSL/Git cache "ghosting" by implementing the `RESCUE MRI Pipeline` workflow.
- [x] Verified full 500-stock daily ingestion on GitHub Actions in under 5 minutes.
- [x] Finalized 3-tier fallback logic for BSE/NSE symbol resolution.

## ✅ Day 28: Railway Deployment Fix (Completed 2026-03-19)
- [x] Updated Dockerfile.api to use $PORT for uvicorn.
- [x] Redeployed backend on Railway; healthcheck now passes.
- [x] Both frontend and backend live on Railway.
---

## ✅ Day 68: Platform Restoration & Hardening (Completed 2026-04-28)
- [x] **Pipeline Freshness:** Synchronized dashboard to 0 days drift (April 28, 2026).
- [x] **Schema Repair:** Fixed missing EMA columns in `market_regime` table.
- [x] **indicator Fix:** Recomputed 53,400 indicator rows, resolving the NULL epidemic.
- [x] **STEE Alerts:** Verified and fixed swing trading breakout email triggers.
- [x] **Prevention:** Implemented Data Quality SLA and database retry logic.
- [x] **Documentation:** Created comprehensive Plumbing Guide and updated Agent Rules.

## ✅ Day 69: 7-Step Institutional Upgrade (Completed 2026-04-28)
- [x] **Core Upgrade:** Transitioned from legacy 5-point to formal 7-step weighted scoring (0-100 scale).
- [x] **Indicator Expansion:** Implemented 10-day Breakout and Price Quality (Day Range) metrics.
- [x] **Forensic Persistence:** Updated Signal Generator to store all 7 technical flags for every trade signal.
- [x] **UI Overhaul:** Implemented the 7-point checklist grid and Golden Setup (🚀) indicators in the frontend.
- [x] **Transparency:** Integrated specific "Bear Market" momentum trading rules into the dashboard UI.

## ✅ Day 70: Quality Investor Framework Integration (Completed 2026-04-28)
- [x] **Fundamental Engine:** Built a modular 7-agent scoring system for Revenue, Margin, Leverage, WC, ROCE, Evolution, and Translation.
- [x] **Data Collection:** Implemented `collector.py` for automated multi-year financial fetching from Yahoo Finance.
- [x] **Schema Expansion:** Added idempotent tables for `fundamental_financials` and `quality_verdicts`.
- [x] **API Implementation:** Exposed fundamental quality data and recompute triggers via FastAPI.
- [x] **Frontend Visualization:** Built the `QualityVerdict` component and integrated it into the stock details modal.
- [x] **Pipeline Automation:** Integrated fundamental analysis into `pipeline_cloud.sh` to auto-refresh top picks.
---

## ✅ Day 71: Qualitative Intelligence Layer (Phase 2) (Completed 2026-04-28)
- [x] **QIL Engine:** Built a narrative-based analysis layer using GPT-4o-mini for investment signal extraction.
- [x] **Narrative Validation:** Implemented deterministic cross-checks to flag management narrative mismatches.
- **Performance:** Upgraded to asynchronous data fetching (`aiohttp`) and disk-based caching.
- [x] **Reporting:** Created `scripts/weekly_quality_report.py` for automated Top-20 quality summaries.
- [x] **Integration:** Hooked QIL into the fundamental pipeline for enhanced scoring accuracy.
---

## ✅ Day 72: Score Trajectory & Portfolio Intelligence (Completed 2026-04-28)
- [x] **Trajectory Engine:** Implemented `trajectory.py` for Velocity and Trend detection.
- [x] **Persistence:** Expanded `quality_verdicts` and added `quality_verdicts_history` for multi-period analysis.
- [x] **Portfolio Manager:** Built rule-based sizing (Kelly Criterion) and drawdown protection.
- [x] **Alerting:** Automated "Explosive Improver" triggers in `quality_alerts.py`.
- [x] **Validation:** Built `quality_backtest.py` to prove the "Quality Improves First" edge.
