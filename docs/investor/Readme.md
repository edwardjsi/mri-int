# Market Regime Intelligence (MRI) — Full-Stack Quantitative Platform

> A production-grade stock screening and risk intelligence platform for Indian markets (NSE + BSE), built on AWS and cost-optimized for lean deployment on Railway + Neon.

---

## Project Summary

MRI is an end-to-end quantitative analytics platform that:

1. **Ingests** daily end-of-day data for 800+ Indian stocks (Nifty 500 + BSE Group A + user-uploaded holdings)
2. **Computes** a proprietary 0–100 weighted trend score for every stock, every day
3. **Classifies** the overall market regime (Bull / Neutral / Bear) using a breadth-based model
4. **Generates** actionable BUY/SELL signals filtered by liquidity, sector diversification, and absolute momentum
5. **Delivers** a daily email digest to users with signals, portfolio status, and watchlist updates
6. **Hosts** a React dashboard with risk audit, digital twin portfolio tracking, and a stock screener

The system was originally built on a **full AWS production architecture** (ECS Fargate, RDS, ALB, CloudFront, EventBridge, SES, S3, Secrets Manager — all managed via Terraform). After successfully demonstrating enterprise-grade infrastructure, it was **deliberately migrated to a cost-optimized stack** (Railway + Neon) for lean beta testing at $0/month — with the ability to restore full AWS in ~10 minutes via `terraform apply` + `deploy.sh`.

---

## Architecture

### Production Architecture (AWS — Fully Buildable)

```
┌──────────────────────────────────────────────────────┐
│                    AWS ap-south-1                     │
│                                                      │
│  ┌─────────┐    ┌───────────┐    ┌───────────────┐  │
│  │CloudFront│───▸│ S3 Bucket │    │ Secrets Mgr   │  │
│  │  (CDN)   │    │ (Frontend)│    │ (DB creds,    │  │
│  └─────────┘    └───────────┘    │  API keys)    │  │
│                                   └───────────────┘  │
│  ┌─────────┐    ┌───────────┐    ┌───────────────┐  │
│  │   ALB   │───▸│ECS Fargate│───▸│ RDS PostgreSQL│  │
│  │         │    │ (FastAPI)  │    │ (Private Sub) │  │
│  └─────────┘    └───────────┘    └───────────────┘  │
│                                                      │
│  ┌─────────────┐    ┌─────────┐    ┌────────────┐  │
│  │ EventBridge  │───▸│ECS Task │    │  AWS SES   │  │
│  │ (4PM IST)   │    │(Pipeline)│    │  (Email)   │  │
│  └─────────────┘    └─────────┘    └────────────┘  │
│                                                      │
│  Terraform: 7 modules, ~30 managed resources         │
│  Infra: VPC, NAT GW, Bastion, IAM least-privilege   │
└──────────────────────────────────────────────────────┘
```

### Current Deployment (Cost-Optimized for Beta)

| Layer              | Service                                   |
|--------------------|-------------------------------------------|
| **Compute**        | Railway (unified Docker monolith)         |
| **Database**       | Neon.tech (serverless PostgreSQL, free)    |
| **Daily Pipeline** | GitHub Actions (scheduled cron, free)     |
| **Email Alerts**   | AWS SES (sandbox mode for beta testers)   |
| **Mailing List**   | MailerLite (subscriber onboarding)        |
| **IaC**            | Terraform modules preserved in `/terraform` |

**Monthly cost: $0** (vs ~$80/month on full AWS). Full AWS restore: `terraform apply` → `deploy.sh` (~10 min).

---

## Tech Stack

| Category           | Technologies                                                 |
|--------------------|--------------------------------------------------------------|
| **Backend**        | Python 3.11, FastAPI, Uvicorn                                |
| **Frontend**       | React 18, Vite, Recharts, CSS3                               |
| **Database**       | PostgreSQL 15 (Neon serverless / AWS RDS)                    |
| **Infrastructure** | Terraform (7 modules), Docker multi-stage builds             |
| **CI/CD**          | GitHub Actions → Railway auto-deploy, `deploy.sh` for AWS    |
| **Cloud (AWS)**    | ECS Fargate, ALB, RDS, S3, CloudFront, SES, Secrets Manager |
| **Cloud (Lean)**   | Railway, Neon.tech, GitHub Actions                           |
| **Data Sources**   | Yahoo Finance, NSE/BSE ISIN master lists                     |
| **Auth**           | JWT + bcrypt, password reset via SES                         |

---

## Scoring Engine — 0 to 100 Weighted

| Factor                      | Weight | What It Measures                     |
|-----------------------------|--------|--------------------------------------|
| EMA 50 / 200 Alignment      | 25     | Primary trend direction              |
| 200 EMA Slope (20-day)      | 25     | Trend acceleration                   |
| Relative Strength vs Nifty  | 20     | Outperformance vs benchmark          |
| Price vs 6-Month High       | 20     | Momentum / breakout proximity        |
| Volume Surge (20-day avg)   | 10     | Institutional participation signal   |

### Market Regime Classification

| Score Range | Classification  |
|-------------|-----------------|
| 80–100      | Strong Risk-On  |
| 60–79       | Risk-On         |
| 40–59       | Neutral         |
| 20–39       | Risk-Off        |
| 0–19        | Strong Risk-Off |

---

## Key Features

- **Daily Signal Generation** — Automated BUY/SELL signals with sector caps and liquidity gates
- **Digital Twin** — Users upload their actual brokerage portfolio for persistent MRI risk monitoring
- **Watchlist** — Track stocks not yet owned, receive daily score updates
- **Risk Audit** — CSV upload → instant weighted risk assessment (Low / Moderate / High / Extreme)
- **On-Demand Ingestion** — Unknown stocks auto-downloaded from Yahoo Finance, scored, and emailed
- **ISIN Bridge** — Cross-exchange symbol resolution (NSE ↔ BSE) using ISIN master lists
- **Adaptive Indicators** — Graceful fallback for recent IPOs with < 200 days of history
- **Landing Page** — Marketing-first entry for unauthenticated visitors

---

## Daily Pipeline Flow

```
GitHub Actions (4:00 PM IST, Mon–Fri)
  │
  ├── 1. Data Ingestion       → src/ingestion_engine.py
  │      (Nifty 500 + BSE + User Holdings, incremental ~2 min)
  │
  ├── 2. Indicator Computation → src/indicator_engine.py
  │      (EMA, slope, RS, volume — incremental, writes only new rows)
  │
  ├── 3. Market Regime         → src/regime_engine.py
  │      (Breadth-based Bull/Neutral/Bear classification)
  │
  ├── 4. Stock Scoring         → src/signal_generator.py
  │      (0–100 weighted score for every stock)
  │
  └── 5. Email Digest          → src/email_service.py
         (Signals + Portfolio + Watchlist status via AWS SES)

Orchestrator: scripts/mri_pipeline.py
Total runtime: < 5 minutes
```

---

## Backtesting Results

| Metric           | MRI Strategy | Nifty 50 Buy & Hold |
|------------------|--------------|----------------------|
| **CAGR**         | 26.39%       | ~10%                 |
| **Max Drawdown** | -33.53%      | -59.60%              |
| **Sharpe Ratio** | 1.23         | 0.42                 |

*Results include survivorship bias correction on Nifty 500 universe and T+1 execution slippage.*

---

## Compliance Note
This system is a quantitative decision-support analytics platform. It does not constitute investment advice or provide regulated buy/sell recommendations. All outputs are accompanied by appropriate disclaimers.
