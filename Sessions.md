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
<!-- Append new sessions below. Never delete old ones. -->
