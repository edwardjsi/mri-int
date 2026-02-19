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
- ⬜ VPC provisioned (ap-south-1)
- ⬜ RDS PostgreSQL created (db.t3.micro)
- ⬜ S3 bucket created (mri-outputs)
- ⬜ IAM roles created (ECS task execution, S3, Secrets Manager)
- ⬜ Secrets Manager: DB credentials stored
- ⬜ `terraform apply` outputs confirmed

## Day 2 — Data Ingestion
- ⬜ NSE EOD data source confirmed
- ⬜ data_loader.py written
- ⬜ Historical data (2005–present) loaded into RDS
- ⬜ Data quality report generated
- ⬜ Duplicate/missing row validation passed

## Day 3 — Indicator Engine
- ⬜ EMA 50 implemented + unit tested
- ⬜ EMA 200 implemented + unit tested
- ⬜ 200 EMA slope (20-day regression) implemented
- ⬜ 6-month rolling high implemented
- ⬜ 20-day average volume implemented
- ⬜ 90-day relative strength vs Nifty implemented
- ⬜ Indicators stored in RDS

## Day 4 — Regime Engine
- ⬜ regime_engine.py written
- ⬜ Daily Risk-On/Off classification computed
- ⬜ Regime history table (2005–present) stored
- ⬜ Regime vs index chart generated

## Day 5–6 — Stock Trend Scoring Engine
- ⬜ trend_engine.py written
- ⬜ Daily 0–5 score computed for all stocks
- ⬜ No look-ahead bias confirmed
- ⬜ Score dataset stored in RDS
- ⬜ 20 random days manually spot-checked

## Day 7–8 — Portfolio Simulation Engine
- ⬜ portfolio_engine.py written
- ⬜ Entry logic implemented (Regime=Risk-On, Score ≥ 4, Top 10)
- ⬜ Exit logic implemented (Score ≤ 2, Regime shift, 20% trailing stop)
- ⬜ Transaction cost (0.4%) applied
- ⬜ Equity curve generated
- ⬜ Trade log CSV exported to S3

## Day 9 — Metrics Module
- ⬜ CAGR calculated
- ⬜ Max Drawdown calculated
- ⬜ Sharpe Ratio calculated
- ⬜ Sortino Ratio calculated
- ⬜ Calmar Ratio calculated
- ⬜ Rolling 3-year CAGR calculated
- ⬜ Nifty buy-and-hold benchmark compared
- ⬜ Performance summary table exported

## Day 10 — Stress Tests + Final Report
- ⬜ 2008 crisis simulation run
- ⬜ 2020 COVID crash simulation run
- ⬜ Sideways 2010–2013 simulation run
- ⬜ Transaction cost doubled (0.8%) test run
- ⬜ EMA parameter sensitivity (45/210) test run
- ⬜ Walk-forward validation (train 2005–2015, test 2016–present)
- ⬜ Final PDF report compiled
- ⬜ All outputs uploaded to S3
- ⬜ GitHub README finalized

---

## Go/No-Go Decision
- ⬜ CAGR > Nifty CAGR
- ⬜ Max Drawdown < Nifty Drawdown
- ⬜ Sharpe ≥ 1.0
- ⬜ Walk-forward Sharpe ≥ 0.8
- ⬜ Stable across 3+ regimes
- ⬜ Survives doubled transaction cost

**VERDICT: PENDING**
