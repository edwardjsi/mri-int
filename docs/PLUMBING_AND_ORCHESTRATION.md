# MRI System Plumbing & Orchestration Guide

This document maps the physical and logical "plumbing" of the MRI platform as of May 08, 2026. It is designed to help AI agents and developers bypass the initial "scrambling" phase when starting a new session.

## 📍 Workspace Environment

| Component | Path / Detail |
|-----------|---------------|
| **Current Root** | `/home/immanuels/Desktop/mri-int` |
| **Legacy Root** | `/home/edwar/mri-int` (Found in several shell scripts; do not use for local execution) |
| **Virtual Env** | `./venv` (Primary) or `./.venv` (Fallback) |
| **Python Path** | Must include root: `export PYTHONPATH=$PWD` |

---

## 🗄️ Database Architecture

The system uses a **Dual-Database** strategy:

1.  **Neon.tech (Production/Cloud)**:
    - Primary connection method: `DATABASE_URL` environment variable.
    - Used by GitHub Actions, Railway.app, and local development.
    - Key tables: `daily_prices`, `market_regime`, `stock_scores`, `clients`, `quality_verdicts`, `fundamental_financials`, `perx_reports`, `perx_scores`, `system_audit_logs`.

2.  **AWS RDS (Legacy/Backup)**:
    - Accessed via Bastion tunnel on **Local Port 5433**.
    - Credentials fetched via `aws secretsmanager` in `scripts/mri_daily.sh`.
    - **CRITICAL**: Never run `terraform destroy` without removing RDS from state (Decision 026).

---

## 🚀 The Pipeline (Data Flow)

The pipeline is defined in `scripts/pipeline_cloud.sh` and orchestrated via GitHub Actions (`.github/workflows/FINAL_FIX.yml`) — auto-triggers on push to `main`, Mon-Fri at 10:30 AM UTC (4:00 PM IST).

### **Execution Chain:**
1.  **Ingestion**: `engine_core/ingestion_engine` -> `load_indices()` then `load_stocks(symbols)`.
2.  **Indicators**: `engine_core/indicator_engine.py` (Updates last 60 rows by default).
3.  **Regime**: `engine_core/regime_engine.py` (Nifty 50 → Bullish/Bearish/Sideways via EMA 50/200).
4.  **Scoring**: `engine_core/regime_engine.py` -> `compute_stock_scores()` (Weighted 0-100 MRI Score, 7-step).
5.  **Signals**: `engine_core/signal_generator.py` (Generates Buy/Sell entries with 7-condition forensic trail).
6.  **STEE**: `engine_core/swing_execution_engine.py` (Breakout entries, 2R exits, audit logging).
7.  **Emails**: `engine_core/email_service.py` (Transactional alerts via AWS SES for MRI and STEE).
8.  **Health Monitor**: `scripts/pipeline_health_monitor.py` (Coverage/drift alerts via SES).
9.  **Quality Analysis**: Top 20 MRI candidates get QIF analysis via `engine_fundamental/`.

### **On-Demand Data Layers:**
- **PERX V1**: If `quality_verdicts` or `fundamental_financials` are missing for a symbol, `engine_perx/orchestrator.py` automatically fetches and computes them via `engine_fundamental/` before generating the report.

---

## 🧪 Backtesting & "Truth"

| File | Source of Truth | Status |
|------|-----------------|--------|
| `scripts/run_canonical_backtest.py` | `backups/20260304/daily_prices.csv` | **22.12% CAGR** (verified May 05, 2026) |
| `outputs/snapshot_canonical.md` | Locked performance metrics (26.8% CAGR on frozen snapshot) | Historical reference |

---

## ⚠️ Known Gotchas (Read This First)

1.  **Path Mismatch**: If you see `/home/edwar` in a script, it is a legacy path. Always use relative paths or the current `immanuels` root.
2.  **Missing `DATABASE_URL`**: If you get a "DATABASE_URL not set" error, the Neon connection string is not set in the session environment.
3.  **SMA vs EMA in Regime**: The `market_regime` table uses **EMA 50/EMA 200** (not SMA). The dashboard `RegimeCard` component now reflects this. The `/api/signals/regime` endpoint returns `ema_50` and `ema_200` columns.
4.  **Audit Logging**: `log_audit_event()` in `swing_execution_engine.py` silently swallows errors to keep the transaction clean. The `system_audit_logs` table is created by `api/schema.py` on app startup.
5.  **Frontend Build**: The Railway Docker image builds the frontend during `docker build`. Local changes to `frontend/src/` must be built (`npm run build`) and copied to `api/static/` before committing.
6.  **GitHub Actions Push Trigger**: The workflow triggers on every push to `main`. The market holiday gate (`scripts/check_market_holiday.py`) exits early on NSE holidays.

---

## 🛠️ Essential Commands

```bash
# Check if market is open (holiday/weekend gate)
python3 scripts/check_market_holiday.py

# Check database freshness (Drift detection)
python3 scripts/db_freshness_check.py

# Run full cloud pipeline (Requires DATABASE_URL)
bash scripts/pipeline_cloud.sh

# Diagnose EMA-50 NULLs
python3 scripts/diagnose_ema_issue.py

# Start local API (Port 8000)
uvicorn api.main:app --reload

# Build and push frontend to api/static
cd frontend && npm install && npm run build && cp -r dist/* ../api/static/

# Verify Python syntax
python -m py_compile api/perx.py engine_perx/orchestrator.py engine_core/swing_execution_engine.py
```