# Market Regime Intelligence (MRI) — Viability Prototype v0.1

## What This Is
A rule-based quantitative backtesting research engine for Indian equities (NSE).
This is NOT a SaaS product. This is a 10-day viability prototype to determine
whether a Market Regime Filter + Stock Trend Score model has real statistical edge
over Nifty buy-and-hold.

If the model passes viability thresholds → we build the SaaS.
If it fails → we stop and reassess. No emotional attachment.

---

## Viability Threshold (Go/No-Go Criteria)
The model proceeds to SaaS ONLY IF:
- CAGR > Nifty CAGR (same period)
- Max Drawdown < Nifty Max Drawdown
- Sharpe Ratio ≥ 1.0
- Walk-forward Sharpe ≥ 0.8
- Stable across 3+ market regimes
- Does not collapse when transaction cost doubles

---

## Tech Stack

| Layer              | Technology                          |
|--------------------|-------------------------------------|
| Quant Engine       | Python (pandas, numpy, scipy)       |
| API Framework      | FastAPI (future SaaS phase)         |
| Database           | PostgreSQL on AWS RDS               |
| Containerization   | Docker + Docker Compose             |
| Orchestration      | AWS ECS Fargate (scheduled tasks)   |
| Infrastructure     | Terraform (modular)                 |
| CI/CD              | GitHub Actions → ECR → ECS          |
| Storage            | AWS S3 (outputs, reports, charts)   |
| Secrets            | AWS Secrets Manager                 |
| Monitoring         | AWS CloudWatch                      |
| Region             | ap-south-1 (Mumbai)                 |

---

## Project Phases

| Phase   | Description                                      | Pricing                  |
|---------|--------------------------------------------------|--------------------------|
| Phase 0 | 10-day research prototype + viability test       | Internal only            |
| Phase 1 | Retail SaaS                                      | ₹1,499 / ₹2,999 per month|
| Phase 2 | Advisor SaaS                                     | ₹15,000–₹40,000 per month|
| Phase 3 | Signal API monetization                          | TBD                      |
| Phase 4 | PMS / AIF (optional, long-term)                  | TBD                      |

---

## Repository Structure

```

mri-intelligence/
├── terraform/
│   ├── modules/
│   │   ├── vpc/
│   │   ├── rds/
│   │   ├── ecs/
│   │   ├── s3/
│   │   └── iam/
│   └── environments/
│       └── dev/
├── src/
│   ├── data_loader.py          \# Day 2: NSE EOD ingestion
│   ├── indicator_engine.py     \# Day 3: EMA, slope, RS, volume
│   ├── regime_engine.py        \# Day 4: Daily Risk-On/Off classification
│   ├── trend_engine.py         \# Day 5-6: Per-stock 0-5 scoring
│   ├── portfolio_engine.py     \# Day 7-8: Capital simulation
│   ├── metrics.py              \# Day 9: CAGR, Sharpe, Drawdown, etc.
│   └── stress_tests.py         \# Day 10: 2008, 2020, param sensitivity
├── outputs/
│   ├── equity_curve.csv
│   ├── trade_log.csv
│   └── performance_report.pdf
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .gitignore
├── README.md
├── SESSION.md
├── DECISIONS.md
├── PROGRESS.md
└── .llm-context.md

```

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

### 2. Stock Trend Score Engine (Prototype: 0–5)

| Condition                          | Points |
|------------------------------------|--------|
| 50 EMA > 200 EMA                   | 1      |
| 200 EMA slope > 0                  | 1      |
| Close > 6-month high               | 1      |
| Volume > 1.5× 20-day average       | 1      |
| Relative strength vs Nifty > 1     | 1      |
| **Total**                          | **5**  |

| Condition                          | Points |
|------------------------------------|--------|
| ADX > 25 (strong trend)            | 1      |
| RSI between 50–70                  | 1      |
| Price > 90% of 52-week high        | 1      |
| **Total**                          | **3**  |


### 3. Portfolio Risk Engine
User uploads holdings → system returns weighted risk level:

| Risk Level | Meaning                              |
|------------|--------------------------------------|
| Low        | Portfolio well-aligned with regime   |
| Moderate   | Some exposure to weak stocks         |
| High       | Significant holdings below 200 EMA  |
| Extreme    | Portfolio severely misaligned        |

---

## Strategy Rules (Prototype)

### Entry
- Market Regime = Risk-On
- Stock Score ≥ 4 out of 5
- Select Top 10 highest scoring stocks
- Equal weight allocation (10% per stock)
- Stock Score ≥ 2 (out of 3)

### Exit
- Stock Score drops to ≤ 2, OR
- Market Regime shifts to Risk-Off, OR
- 20% trailing stop is hit
- Stock Score drops to 0


### Assumptions
- Transaction cost: 0.4% round-trip
- No leverage
- No shorting
- Rebalance on end-of-day basis

---

## Daily Pipeline Flow (Post-Market)

```

1. Ingest new EOD data
2. Update indicators
3. Compute regime score
4. Compute stock trend scores
5. Store results in RDS
6. Export outputs to S3
7. Update CloudWatch metrics
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

