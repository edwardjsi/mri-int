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
