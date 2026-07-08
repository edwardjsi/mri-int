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

## ✅ Day 73: Watchlist Hardening & UX (Completed 2026-05-04)
- [x] **Sortable Watchlist**: Implemented client-side sorting for Symbols, Prices, MRI Scores, and Trends.
- [x] **Header UI**: Added dynamic sort icons and hover states to the Watchlist table.
- [x] **Code Hardening Audit**: Verified fix for `debate.py` proxy conflict; implemented `ValueError` hardening for `quality_alerts.py`. Full details in [FORENSIC_HARDENING.md](file:///home/immanuels/Desktop/mri-int/docs/FORENSIC_HARDENING.md).
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

## 🚧 Upcoming: AAE Phase 3 Enhancements
- [ ] **Sector Comparison Index Layer** (See `docs/SECTOR_COMPARISON_PLAN.md`)
  - [x] Step 1: Database & Seed Data (Schema expansion for indices).
  - [x] Step 2: Collector & Automation (yfinance index fetcher).
  - [x] Step 3: Analytical Engine (Sector Tailwind, Relative Momentum, Peer Spread).
  - [x] Step 4: UI / Frontend (Sector Heatmap API and React Lens integration).

---

## ✅ Day 74: Capital Allocation Score V1.1 — Release Candidate Ready (Completed 2026-07-08)

Implements Decision 100/101/102 — transforms MRI from a breakout screener into a portfolio decision engine.

- [x] **V1.1a — Engine correctness:** 174 tests, EMA100 slope, overhead_supply_score, weekly_trend_score
- [x] **V1.1b — Outcome tracking + persistence:** `cas_recommendations` + `cas_recommendation_outcomes` tables, daily_outcome_updater cron, milestones at w1/w2/w4/m3/m6
- [x] **V1.1c — Decision layer + calibration journal:** `cas_decision_layer.py` (tiers, hysteresis, NO_ACTION, lifecycle), `Calibration.md`, `config/calibration_registry.yaml`, `tools/calibration_debt.py`, 39 tests
- [x] **V1.1d — Release candidate validation:** `tools/distribution_sanity_check.py`, `tools/top20_report.py`, 4-gate framework
- [x] **Calibration override (Decision 102 Q2):** `overhead_supply.max_count_for_100` 10→20. Saturation 83%→35.5%. YAML-wired via `_get_overhead_max_count()` helper. Calibration registry entry marked `validated`.
- [x] **5-gate validation PASS:** tests (259/259), golden cases (7/7 ±2.0 CAS), distribution (PASS, 2 informational WARN), Top-20 eyeball (9/9 pass), rank correlation (9/9 overlap, Spearman ρ=0.683)
- [x] **Historical distribution (Q1 follow-up):** 6 weekly samples, mean eligible=0.67%, range 0.2–1.4% — consistent sparse-breakout environment
- [x] **Documentation synced:** `docs/CAS_SPEC.md`, `docs/CAS_V11D_VALIDATION.md`, `docs/CAS_TOP20_V11D.md`, `docs/PR_BODY.md`, `Calibration.md`, Decisions 101/102
- [x] **Branch:** `feature/capital-allocation-v1`, 24 commits ahead of `main`, all pushed, working tree clean
- [x] **Calibration freeze:** no weight tweaks for 100 recommendations post-merge; re-validate at 100/250/500

### 📦 Deliverable

- 259 tests pass (+155 over V1.0)
- 5 gates: tests, golden cases, distribution, eyeball, rank correlation
- Top-9 candidates pass Buffett sniff test: TITAN, ALKEM, GLAND, INDUSINDBK, JBCHEPHARM, PNBHOUSING, INOXINDIA, ADANIENSOL, PAYTM

### ⏭️ Tomorrow's First Action (BLOCKED on tooling)

`gh` CLI is not installed. Install + authenticate, then:

```bash
gh auth login                    # one-time
gh pr create \
  --base main \
  --head feature/capital-allocation-v1 \
  --title "Capital Allocation Score V1.1 — Release Candidate" \
  --body-file docs/PR_BODY.md
```

### 🚧 V1.2 Backlog (Decision 102 Q4)

1. Regime-aware API (read from detector, not hardcoded BULLISH) — highest impact
2. QIF joins (replace `proxy_score_v1` placeholder)
3. EMA50 fallback for thin-history stocks
4. ATR-aware overhead buckets
5. Weekly fractals (V2+) — replace week-over-week HH/HL

### 🎯 Project Phase Transition

> **V1.x = scoring infrastructure.** From here, the project's biggest improvements come from **measuring how well the engine predicts successful capital allocation**, not from making the scoring engine more elaborate. **V2.x = outcome-driven calibration.**

