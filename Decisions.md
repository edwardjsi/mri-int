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

<!-- Append new decisions below. Never delete or modify old ones. -->
