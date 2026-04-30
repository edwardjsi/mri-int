# Market Regime Intelligence (MRI) — Web App MVP

## What This Is
Earlier prototype reports suggested a strong edge for a Market Regime Filter + Stock Trend Score model versus Nifty buy-and-hold, but the current live rerun does not reproduce that headline result. Treat the historical claim as unverified until the backtest is rebuilt from a frozen, reproducible data snapshot.

We are now actively building Phase 2: A minimal viable SaaS React/Vite dashboard to interactively visualize the backtests and display the live daily portfolio.

---

## Viability Threshold (Go/No-Go Criteria)
The model proceeds to SaaS ONLY IF:
- CAGR > Nifty CAGR (same period)
- Max Drawdown < Nifty Max Drawdown
- Sharpe Ratio ≥ 1.0
- Walk-forward Sharpe ≥ 0.8
- Stable across 3+ market regimes
- Does not collapse when transaction cost doubles

## Tech Stack (Current Deployment)

| Layer              | Technology                          |
|--------------------|-------------------------------------|
| Quant Engine       | Python (pandas, numpy, scipy)       |
| Backend API        | FastAPI (Monolith Mode)             |
| Frontend           | React + Vite + Tailwind             |
| Database           | Neon.tech (Serverless PostgreSQL)   |
| Deployment         | Railway.app (Unified Service)       |
| Monitoring         | Railway Metrics + Health Checks     |

---

## Project Phases

| Phase   | Description                                      | Pricing                  |
|---------|--------------------------------------------------|--------------------------| 
| Phase 0 | 10-day research prototype + viability test       | Internal only            |
| Phase 1 | Retail SaaS MVP (Live: Railway)                  | ₹1,499 / ₹2,999 per month|
| Phase 2 | Advisor SaaS                                     | ₹15,000–₹40,000 per month|
| Phase 3 | Signal API monetization                          | TBD                      |
| Phase 4 | PMS / AIF (optional, long-term)                  | TBD                      |

---

## Repository Structure

```

mri-intelligence/
├── api/                        \# Backend routers (auth, signals, admin, etc.)
├── frontend/                   \# React/Vite/Tailwind Frontend
├── src/
│   ├── ingestion_engine.py     \# NSE/BSE EOD ingestion
│   ├── indicator_engine.py     \# EMA, slope, RS, volume
│   ├── regime_engine.py        \# Daily Risk-On/Off classification
│   └── signal_generator.py     \# Score-to-Signal logic
├── scripts/
│   └── mri_pipeline.py         \# Daily automation entry point
├── Dockerfile                  \# Unified Monolith Build
├── requirements.txt            \# Backend dependencies
├── .gitignore
├── README.md
├── SESSION.md
├── DECISIONS.md                \# Architectural log
├── PROGRESS.md                 \# Build status
└── .llm-context.md

```

---

## Current Pipeline Status (Post-Day 2)

The project has graduated from a 20-stock proof-of-concept into a fully functional, highly robust data pipeline:
- **Dataset**: Full Nifty 500 universe (~1.64 million daily data points from 2005-present).
- **Ingestion**: Automated robust backoff & retry mechanism to handle AWS SSM tunnel drops during multi-hour data loads.
- **Infrastructure**: AWS RDS PostgreSQL housed securely in a private subnet, accessed locally via an EC2 Bastion port-forwarding tunnel.
- **Data Quality**: 100% clean ingestion, 0 duplicates, 0 nulls, enforced by strict PostgreSQL unique constraints and `ON CONFLICT DO NOTHING` logic.
- **Infrastructure State**: Currently torn down to save costs. Database is backed up to S3, ready for a standard Terraform rebuild and RDS restore.

---

## Core Intelligence Engines

### 1. Market Regime Engine
Scores overall market health (0–100):

| Score   | Classification    |
|---------|-------------------|
| 80–100  | Strong Risk-On    |
| 60–79   | Risk-On           |
| 40–59   | Neutral           |
| 20–39   | Risk-Off          |
| 0–19    | Strong Risk-Off   |

### 2. Weighted Trend Score Engine (0–100)

| Indicator                  | Weight | Score Component |
|----------------------------|--------|-----------------|
| EMA 50 > 200               | 25%    | Trend Integrity |
| 200 EMA Slope > 0          | 25%    | Long-term Bias  |
| Relative Strength (90d)    | 20%    | Outperformance  |
| 6m Price Momentum          | 20%    | Alpha-Strength  |
| Volume Surge (10d)         | 10%    | Liquidity-Gate  |
| **Total**                  | **100**| **Trend Score** |

### 3. Portfolio Risk Engine
User uploads holdings → system returns weighted risk level:

| Risk Level | Meaning                              |
|------------|--------------------------------------|
| Low        | Portfolio well-aligned with regime   |
| Moderate   | Some exposure to weak stocks         |
| High       | Significant holdings below 200 EMA  |
| Extreme    | Portfolio severely misaligned        |

---

## 🛡️ Security & Stability Hardening (April 2026 Audit)

The platform has passed a comprehensive **Python** and **PostgreSQL** architectural audit:

- **Row Level Security (RLS)**: Every user's data is isolated at the database level. Even if an API query has a logic bug, User A cannot see User B's portfolio.
- **SQL Injection Prevention**: All queries use `psycopg2.sql` parameterization. No f-string interpolation is permitted in the analytics engine.
- **Connection Leak Remediation**: Database connections are strictly managed with `try...finally` blocks to ensure infinite uptime on serverless DBs like Neon.
- **64-bit Scalability**: Tracking tables use `BIGSERIAL` (64-bit) primary keys to support billions of rows.
- **Temporal Consistency**: Standardized to `TIMESTAMPTZ` for global-ready tracking.

---

## 🗺️ Architectural Codemaps
Detailed structural maps for developers and AI agents:
- [Backend Engine Codemap](docs/CODEMAPS/backend.md)
- [Database Schema Codemap](docs/CODEMAPS/database.md)

---

## Strategy Rules (0–100 Weighted Model)

### Entry
- Market Regime = **Risk-On** (Score > 60)
- Stock Trend Score ≥ **75 / 100**
- Select Top 10 highest scoring stocks
- Equal weight allocation (10% per stock)
- **Neutral Regime Grace**: Entries permitted if Score > 85.

### Exit
- Stock Trend Score drops to **≤ 40**, OR
- Market Regime shifts to **Risk-Off** (Score < 40), OR
- 20% trailing stop is hit
- Stock Trend Score drops to **0** (Immediate Flush)

---

## Daily Pipeline Flow (Post-Market)

```

1. Ingest new EOD data (`src/ingestion_engine.py`)
2. Update indicators (`src/indicator_engine.py`)
3. Compute regime score (`src/regime_engine.py`)
4. Compute stock trend scores (`src/signal_generator.py`)
5. Workflow Orchestration (`scripts/mri_pipeline.py`)
```

---

## Backtesting Periods

| Period      | Purpose                        |
|-------------|--------------------------------|
| 2005–2024   | Full historical simulation     |
| 2005–2015   | Walk-forward train period      |
| 2016–2024   | Walk-forward test period       |
| 2008        | Stress test — global crisis    |
| 2010–2013   | Stress test — sideways market  |
| 2020        | Stress test — COVID crash      |

---

## Performance Targets (Realistic)

| Metric         | Target           |
|----------------|------------------|
| CAGR           | > Nifty CAGR     |
| Max Drawdown   | < Nifty Drawdown |
| Sharpe Ratio   | ≥ 1.0            |
| Exposure       | 60–80%           |
| Sortino Ratio  | ≥ 1.2            |

---

## AWS Infrastructure

| Service             | Purpose                              |
|---------------------|--------------------------------------|
| RDS PostgreSQL      | Store prices, indicators, scores     |
| ECS Fargate         | Run scheduled batch jobs             |
| S3                  | Store outputs, charts, PDF report    |
| Secrets Manager     | DB credentials, API keys             |
| CloudWatch          | Pipeline logs and monitoring         |
| ECR                 | Docker image registry                |
| EventBridge         | Schedule daily EOD pipeline trigger  |

---

## Compliance Positioning
This system does NOT issue buy/sell signals.
It is a structured quantitative decision-support analytics platform only.
All outputs must be accompanied by appropriate disclaimers.

---

## Execution Rules
1. One module at a time — complete and verify before moving to the next
2. Every module has a clear DONE criteria
3. No features outside PROGRESS.md scope
4. No microservices — single container in prototype
5. No ML, no intraday, no UI in prototype phase
6. All architectural decisions logged in DECISIONS.md
7. SESSION.md and PROGRESS.md updated at end of every session

---

## Owner
- Solo developer — full-stack + AWS DevOps
- Location: Tirunelveli, Tamil Nadu, IN
- AWS Region: ap-south-1 (Mumbai)
- Build method: LLM-assisted, module-by-module
```
